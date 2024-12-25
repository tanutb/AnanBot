import chromadb
import uuid
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
import uvicorn
from pydantic import BaseModel
from typing import Optional
import requests
import hashlib

# Function to generate a consistent ID based on the content of the memory
def generate_memory_id(memory_content):
    return hashlib.sha256(memory_content.encode('utf-8')).hexdigest()


torch.manual_seed(0)

model = AutoModel.from_pretrained('openbmb/MiniCPM-Llama3-V-2_5-int4', trust_remote_code=True, torch_dtype=torch.bfloat16, device_map='auto')
tokenizer = AutoTokenizer.from_pretrained('openbmb/MiniCPM-Llama3-V-2_5-int4', trust_remote_code=True, torch_dtype=torch.bfloat16, device_map='auto')

chroma_client = chromadb.PersistentClient(path="./memories/chroma.db")
collection = chroma_client.get_or_create_collection(name="v01haha")

history = []

__NAME = 'NuAnantachai'
MEMORY_PROMPT = '''\nGiven only the information above, what are 3 most salient high level questions we can answer about the subjects in the conversation? Separate each question and answer pair with \"{qa}\", \"{answer}\" respectively
For example, DO NOT COPY MY EXAMPLES 
- "{qa}What is the meaning of life? {answer}The meaning of life is 42".
- "{qa} What's capital of Thailand? {answer} Bangkok".
, and only output the question and answer, no explanations.'''
BANNED_TOKENS = ""
STOP_STRINGS = ["\n", "<|eot_id|>"]

SYSTEM_PROMPT = '''Continue the chat dialogue below. Write only a single reply for the character's name "NuAnantachai" without quotes. Answer in not long sentance.
NuAnantachai is a character in the chat dialogue. This character is a human who is a streamer. The character will answer questions with the rough personality and strong language.
He is not friendly at all. He loves to play Overwatch 2. He is a mercy main in Overwatch 2. oPuto is his idol. This character is gay.
'''

THRESHOLD = 0.7

MEMORY_RECALL_COUNT = 2
i = 0
app = FastAPI()
class ChatRequest(BaseModel):
    text: str
    image_path: str = None

@app.post("/chat/")
async def chat_endpoint(request: ChatRequest):
    global i
    history.append({"role": "user", "content": request.text})
    history_copy = [message.copy() for message in history]
    for message in history_copy:
        if message["role"] == "user" and message["content"] != "":
            message["content"] = "USER" + ": " + message["content"] + "\n"
        elif message["role"] == "assistant" and message["content"] != "":
            message["content"] = __NAME + ": " + message["content"] + "\n"

    if request.image_path:
        memories = {"ids": [[]], "distances": [[]], "documents": [[]]}
        chat_section = f"{SYSTEM_PROMPT}\n"
        for message in history_copy[-1:]:
            chat_section += message["content"]
    else:
        memories = collection.query(query_texts=request.text, n_results=MEMORY_RECALL_COUNT)

        chat_section = f"{SYSTEM_PROMPT}\n"
        for message in history_copy[-5:]:
            chat_section += message["content"]

    # Initialize the prompt injection
    prompt_injection = f"{__NAME} knows these things:\n\n"

    high_distance = True

    # Append relevant memories to the knowledge section
    for j in range(len(memories["ids"][0])):
        if memories['distances'][0][j] < THRESHOLD:  # Threshold for including memories
            prompt_injection += f"- {memories['documents'][0][j]}\n"
            high_distance = False

    # Finalize the knowledge section
    if high_distance:
        prompt_injection = ""  # Clear if no relevant memories
    else:
        prompt_injection += "\nEnd of knowledge section\n"

    # Debugging: Print distances and details for debugging purposes
    for j in range(len(memories["ids"][0])):
        print(f"Memory {j}: Distance: {memories['distances'][0][j]}")
        if memories['distances'][0][j] < THRESHOLD:
            print(f"Inject this memory due to having distance {memories['distances'][0][j]}")

    print("prompt_injection: ", prompt_injection)

    msgs = [{'role': 'user', 'content': chat_section + prompt_injection}]
    image_data = Image.open(request.image_path).convert('RGB') if request.image_path else None
    answer = model.chat(
        image=image_data,
        msgs=msgs,
        tokenizer=tokenizer,
        max_tokens=200,
        mode="instruct"
    )
    assistant_message = answer
    assistant_message = assistant_message.replace(f"{__NAME}: ", "")
    history.append({"role": "assistant", "content": assistant_message})

    Chat = f'''USER : {request.text} \n f"{__NAME}: {assistant_message}'''
    ### memory update
    # Ensure unique memories and consistent IDs
    msgs = [{'role': 'user', 'content': Chat + MEMORY_PROMPT}]
    M_answer = model.chat(
        image=None,
        msgs=msgs,
        tokenizer=tokenizer,
        max_tokens=200,
        mode="instruct"
    )
    M_assistant_message = M_answer

    # Get all existing memories
    all_memories = collection.get()
    existing_memories = set(generate_memory_id(memory) for memory in all_memories['documents'])

    print('existing_memories : ', existing_memories)
    # Split the assistant message and check for duplicates
    for memory in M_assistant_message.split("{qa}"):
        memory = memory.strip()
        if memory != "":
            memory_id = generate_memory_id(memory)
            if memory_id not in existing_memories:
                # Upsert new memory with a consistent ID
                collection.upsert(ids=[memory_id], documents=[memory], metadatas=[{"type": "short-term"}])
                existing_memories.add(memory_id)  # Add the new ID to the existing memories set

    print("\n\n M_answer : " ,M_answer)

    return JSONResponse(content={"response": assistant_message})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8119)