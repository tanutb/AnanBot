import chromadb
import torch
from PIL import Image
from transformers import (
                AutoModel, 
                AutoTokenizer, 
                CLIPProcessor, 
                CLIPModel)
import hashlib
import easyocr
from collections import deque 
from config import (
                THRESHOLD,
                MEMORY_RECALL_COUNT,
                SYSTEM_PROMPT,
                IMAGE_DECISION_PROMPT,
                NAME,
                MEMORY_PROMPT,
                COLLECTION_NAME,
                CHROMA_DB_PATH,
                MODEL_NAME,
                CLIP_MODEL_NAME,
                OCR_LANGUAGES,
                HISTORY_MAXLEN,
                CONTEXT_LENGTH_IMAGE,
                CONTEXT_LENGTH_TEXT
                    )
from src.stable_diffusion import generate_image


class Multimodal : 
    def __init__(self):
        """
        Initializes the multimodal model and its components.
        Attributes:
            OCR_READERS (easyocr.Reader): An instance of the EasyOCR reader initialized with specified languages.
            clip_model (CLIPModel): The CLIP model loaded from the pretrained model name.
            clip_processor (CLIPProcessor): The CLIP processor loaded from the pretrained model name.
            model (AutoModel): The main model loaded from the pretrained model name with specified configurations.
            tokenizer (AutoTokenizer): The tokenizer associated with the main model.
            chroma_client (chroma.PersistentClient): The ChromaDB client initialized with the specified database path.
            collection (chroma.Collection): The collection obtained or created in the ChromaDB client.
            history (deque): A deque to store history with a maximum length defined by HISTORY_MAXLEN.
        """
        
        self.OCR_READERS = easyocr.Reader(OCR_LANGUAGES)
        # Load models and tokenizer
        self.clip_model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
        self.clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map='auto')
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map='auto')

        # Initialize ChromaDB client and collection
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        self.history = deque(maxlen=HISTORY_MAXLEN)

    
    def generate_memory_id(self,memory):
        """
        Generates a unique memory ID using MD5 hashing.
        Args:
            memory (str): The memory string to be hashed.
        Returns:
            str: The MD5 hash of the memory string in hexadecimal format.
        """

        return hashlib.md5(memory.encode('utf-8')).hexdigest()
        
    # Helper functions
    def transform_embeddings(self, embeddings, target_dim):
        """
        Transforms the given embeddings to the target dimension.
        Parameters:
        embeddings (numpy.ndarray): The input embeddings with shape (n_samples, n_features).
        target_dim (int): The target dimension to transform the embeddings to.
        Returns:
        numpy.ndarray: The transformed embeddings with shape (n_samples, target_dim).
        Raises:
        ValueError: If the target dimension is greater than the original dimension of the embeddings.
        """

        if target_dim <= embeddings.shape[1]:
            return embeddings[:, :target_dim]
        else:
            raise ValueError(f"Target dimension {target_dim} must be less than or equal to the original dimension {embeddings.shape[1]}")

    def get_image_embedding(self, image_path):
        """
        Generates an embedding for a given image using a CLIP model.
        Args:
            image_path (str): The file path to the image.
        Returns:
            numpy.ndarray: A flattened numpy array representing the image embedding.
        """

        image = Image.open(image_path).convert("RGB")
        inputs = self.clip_processor(images=image, return_tensors="pt", padding=True)
        inputs = {key: val.to(self.clip_model.device) for key, val in inputs.items()}
        with Image.open(image_path).convert("RGB") as image:
            inputs = self.clip_processor(images=image, return_tensors="pt", padding=True)
            inputs = {key: val.to(self.clip_model.device) for key, val in inputs.items()}
            with torch.no_grad():
                outputs = self.clip_model.get_image_features(**inputs)
            return self.transform_embeddings(outputs.cpu(), 384).numpy().flatten()


    def get_text_embedding(self,text):
        """
        Generates a text embedding for the given input text using a CLIP model.
        Args:
            text (str): The input text to be embedded.
        Returns:
            numpy.ndarray: A flattened numpy array representing the text embedding.
        """

        inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        inputs = {key: val.to(self.clip_model.device) for key, val in inputs.items()}
        with torch.no_grad():
            outputs = self.clip_model.get_text_features(**inputs)
        return self.transform_embeddings(outputs.cpu(), 384).numpy().flatten()
    

    def get_text_embedding(self, text):
        """
        Generates a text embedding for the given input text using a CLIP model.
        Args:
            text (str): The input text to be embedded.
        Returns:
            numpy.ndarray: A flattened numpy array representing the text embedding.
        """

        inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        inputs = {key: val.to(self.clip_model.device) for key, val in inputs.items()}
        with torch.no_grad():
            outputs = self.clip_model.get_text_features(**inputs)
        return self.transform_embeddings(outputs.cpu(), 384).numpy().flatten()
    
    def parse_memories(self,assistant_message):
        """
        Parses the assistant's message to extract memories in the form of question-answer pairs.
        Args:
            assistant_message (str): The message from the assistant containing memories 
                                     formatted as "{qa}...{answer}...".
        Returns:
            list: A list of dictionaries, each containing 'qa' and 'answer' keys with 
                  corresponding extracted values.
        """

        memories = []
        for memory in assistant_message.split("{qa}"):
            if "{answer}" in memory:
                qa, answer = memory.split("{answer}", 1)
                memories.append({"qa": qa.strip(), "answer": answer.strip()})
        return memories
    
    def generate_text(self, text: str, image_path: str = None):
        """
        Generates a response based on the provided text and optional image.
        Args:
            text (str): The input text to generate a response for.
            image_path (str, optional): The path to an image file to be used in generating the response. Defaults to None.
        Returns:
            dict: A dictionary containing the generated response with the key "response".
        """

        if text:
            response = self._process_text_input(text)
            if response:
                return response

        history = self._update_history(text)
        prompt_injection, input_embedding, query_type = self._prepare_prompt_injection(image_path, text)
        memories = self.collection.query(query_embeddings=[input_embedding], n_results=MEMORY_RECALL_COUNT)
        chat_section = self._build_chat_section(history, query_type)
        prompt_injection = self._update_prompt_injection_with_memories(prompt_injection, memories)

        msgs = [{'role': 'user', 'content': chat_section + prompt_injection}]
        image_data = self._load_image(image_path)
        assistant_message = self._generate_assistant_message(msgs, image_data)
        self.history.append({"role": "assistant", "content": assistant_message})

        self._store_memories(text, assistant_message, image_path)
        return {"response": assistant_message}

    def _process_text_input(self, text):
        """
        Processes the given text input and determines whether to generate an image based on the model's response.
        Args:
            text (str): The input text to be processed.
        Returns:
            dict or None: If the model's response contains '{gen}', returns a dictionary with the generated image and a response message.
                          If the model's response contains '{notplz}', returns None.
                          Otherwise, returns None.
        """

        __chat = "USER :" + text + IMAGE_DECISION_PROMPT

        if '{gen}' in text:
            print("Generate Image")
            keywords = text.replace("{gen} ", "") if text.startswith("{gen}") else text.replace("{gen}", "")
            image_generation = generate_image(keywords)
            img = image_generation['images'][0]
            assistant_message = f"generated image with the following keywords: {keywords}"
            return {"response": assistant_message, "img": img}
        

        print("CHAT: ", __chat)
        msgs = [{'role': 'user', 'content': __chat}]
        DES_ANSWER = self.model.chat(
            image=None,
            msgs=msgs,
            tokenizer=self.tokenizer,
            max_tokens=100,
            mode="instruct"
        )
        print("ANSWER: ", DES_ANSWER)

        if '{gen}' in DES_ANSWER:
            print("Generate Image")
            keywords = DES_ANSWER.replace("{gen}", "")
            prompt = f"Generate an image with the following keywords: {keywords}"
            image_generation = generate_image(prompt)
            img = image_generation['images'][0]
            assistant_message = f"generated image with the following keywords: {keywords}"
            return {"response": assistant_message, "img": img}
        elif '{no}' in DES_ANSWER:
            print("Not Generate Image")
            return None
        return None

    def _update_history(self, text):
        """
        Updates the conversation history with the given text and returns a formatted copy of the history.
        Args:
            text (str): The text to be added to the history as a user message.
        Returns:
            list: A copy of the conversation history with formatted messages.
        """

        self.history.append({"role": "user", "content": text})
        history_copy = [message.copy() for message in self.history]

        for message in history_copy:
            if message["role"] == "user" and message["content"]:
                message["content"] = "USER: " + message["content"] + "\n"
            elif message["role"] == "assistant" and message["content"]:
                message["content"] = NAME + ": " + message["content"] + "\n"
        return history_copy

    def _prepare_prompt_injection(self, image_path, text):
        """
        Prepares the prompt injection based on the provided image or text input.
        Args:
            image_path (str): The file path to the image to be processed. If provided, the image will be read and text will be extracted using OCR.
            text (str): The text input to be processed if no image is provided.
        Returns:
            tuple: A tuple containing:
                - prompt_injection (str): The extracted text from the image formatted as a prompt injection, or an empty string if no image is provided.
                - input_embedding (Any): The embedding of the image or text input.
                - query_type (str): The type of query, either "image" or "text".
        """

        if image_path:
            result = self.OCR_READERS.readtext(image_path, detail=0, paragraph=True)
            if result != []:
                prompt_injection = "- Extracted text from the image:\n"
                for line in result:
                    prompt_injection += f"  {line}\n"
                prompt_injection += "End of extracted text\n\n"
            input_embedding = self.get_image_embedding(image_path)
            query_type = "image"
            prompt_injection = ''
        else:
            prompt_injection = ""
            input_embedding = self.get_text_embedding(text)
            query_type = "text"
        return prompt_injection, input_embedding, query_type

    def _build_chat_section(self, history, query_type):
        """
        Builds the chat section string from the given history and query type.
        Args:
            history (list): A list of message dictionaries containing the chat history.
            query_type (str): The type of query, either "image" or "text".
        Returns:
            str: The constructed chat section string.
        """

        chat_section = f"{SYSTEM_PROMPT}\n"
        context_length = -CONTEXT_LENGTH_IMAGE if query_type == "image" else -CONTEXT_LENGTH_TEXT
        for message in history[context_length:]:
            chat_section += message["content"]
        return chat_section

    def _update_prompt_injection_with_memories(self, prompt_injection, memories):
        """
        Updates the prompt injection string with relevant memories.
        This method appends relevant memory information to the given prompt injection string.
        If no relevant memories are found (i.e., all memory distances are above a certain threshold),
        the prompt injection string is cleared.
        Args:
            prompt_injection (str): The initial prompt injection string to be updated.
            memories (dict): A dictionary containing memory information with the following keys:
                - "ids" (list): A list of memory IDs.
                - "distances" (list): A list of distances corresponding to each memory.
                - "documents" (list): A list of memory documents.
        Returns:
            str: The updated prompt injection string.
        """

        prompt_injection += f"{NAME} knows these things:\n\n"
        high_distance = True

        for j in range(len(memories["ids"][0])):
            if memories['distances'][0][j] < THRESHOLD:
                prompt_injection += f"- {memories['documents'][0][j]}\n"
                high_distance = False

        if high_distance:
            prompt_injection = ""
        else:
            prompt_injection += "\nEnd of knowledge section\n"
        return prompt_injection

    def _load_image(self, image_path):
        """
        Loads an image from the specified file path and converts it to RGB format.
        Args:
            image_path (str): The path to the image file.
        Returns:
            PIL.Image.Image: A copy of the loaded image in RGB format, or None if the image_path is not provided.
        """

        if image_path:
            with Image.open(image_path).convert('RGB') as img:
                return img.copy()
        return None

    def _generate_assistant_message(self, msgs, image_data):
        """
        Generates an assistant message based on the provided messages and image data.
        Args:
            msgs (list): A list of messages to be processed by the model.
            image_data (Any): The image data to be used by the model.
        Returns:
            str: The generated assistant message with the assistant's name removed.
        """

        answer = self.model.chat(
            image=image_data,
            msgs=msgs,
            tokenizer=self.tokenizer,
            max_tokens=200,
            mode="instruct"
        )
        return answer.replace(f"{NAME}: ", "")

    def _store_memories(self, text, assistant_message, image_path):
        """
        Stores memories based on the provided text, assistant message, and optional image path.
        Args:
            text (str): The user's input text.
            assistant_message (str): The assistant's response message.
            image_path (str, optional): The path to an image file. Defaults to None.
        Returns:
            None
        """

        Chat = f'''USER : {text} \n f"{NAME}: {assistant_message}'''
        msgs = [{'role': 'user', 'content': Chat + MEMORY_PROMPT}]
        M_answer = self.model.chat(
            image=None,
            msgs=msgs,
            tokenizer=self.tokenizer,
            max_tokens=200,
            mode="instruct"
        )
        M_assistant_message = M_answer

        existing_memories = set(self.generate_memory_id(memory) for memory in self.collection.get()['documents'])
        parsed_memories = self.parse_memories(M_assistant_message)

        new_memories = [
            {
                "id": self.generate_memory_id(memory["qa"] + memory["answer"]),
                "document": f"{memory['qa']} {memory['answer']}",
                "metadata": {"type": "short-term", "modality": "image" if image_path else "text"},
                "embedding": self.get_image_embedding(image_path) if image_path else None
            }
            for memory in parsed_memories
            if self.generate_memory_id(memory["qa"] + memory["answer"]) not in existing_memories
        ]

        for memory in new_memories:
            self.collection.upsert(
                ids=[memory["id"]],
                documents=[memory["document"]],
                metadatas=[memory["metadata"]],
                embeddings=[memory["embedding"]] if memory["embedding"] is not None else None
            )
            existing_memories.add(memory["id"])
