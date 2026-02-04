import os
import base64
import hashlib
import time
import json
import re
import uuid
from collections import deque
from typing import List, Optional, Dict, Any

import chromadb
from openai import OpenAI
from google import genai
from google.genai import types
from dotenv import load_dotenv
from colorama import Fore, Style, init

from config import (
    THRESHOLD,
    MEMORY_RECALL_COUNT,
    SYSTEM_PROMPT,
    NAME,
    MEMORY_PROMPT,
    COLLECTION_NAME,
    CHROMA_DB_PATH,
    HISTORY_MAXLEN,
    CONTEXT_LENGTH_IMAGE,
    CONTEXT_LENGTH_TEXT
)
from src.gemini_vision import generate_image, edit_image

# Initialize colorama
init(autoreset=True)
load_dotenv()

class Multimodal:
    def __init__(self, debug: bool = False):
        """
        Initializes the multimodal agent using OpenAI-compatible Gemini API.
        Args:
            debug (bool): If True, prints verbose debug information.
        """
        self.debug = debug
        # OpenAI Client for Gemini
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Google GenAI Client for Embeddings
        self.genai_client = genai.Client(api_key=self.api_key)

        # ChromaDB for Long-term Memory (RAG)
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)

        # Persistence Paths
        self.karma_file = "./memories/karma.json"
        self.history_file = "./memories/chat_history.json"
        self.image_dir = "./memories/images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Load Data
        self.karma_db = self._load_json(self.karma_file)
        self.histories = {}
        self.usernames = {}
        self.last_images = {} # Stores LIST of image PATHS per user
        self._load_history()

    def log(self, section: str, message: str, color=Fore.WHITE):
        """Helper to print debug messages."""
        if self.debug:
            print(f"{color}[{section.upper()}]{Style.RESET_ALL} {message}")

    def _load_json(self, filepath: str) -> Dict:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log("ERROR", f"Failed to load {filepath}: {e}", Fore.RED)
                return {}
        return {}

    def _save_json(self, filepath: str, data: Dict):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log("ERROR", f"Failed to save {filepath}: {e}", Fore.RED)

    def _save_image_to_disk(self, b64_data: str) -> str:
        """Saves base64 image data to disk and returns the relative path."""
        try:
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            path = os.path.join(self.image_dir, filename)
            
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            
            return path
        except Exception as e:
            self.log("ERROR", f"Failed to save image to disk: {e}", Fore.RED)
            return ""

    def _load_image_from_disk(self, path: str) -> Optional[str]:
        """Loads image from disk and returns base64 string."""
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            self.log("ERROR", f"Failed to load image from disk: {e}", Fore.RED)
            return None

    def _load_history(self):
        raw_data = self._load_json(self.history_file)
        count = 0
        
        for user_id, entry in raw_data.items():
            if isinstance(entry, list): # Legacy
                self.histories[user_id] = deque(entry, maxlen=HISTORY_MAXLEN)
                self.usernames[user_id] = "Unknown"
                count += len(entry)
            elif isinstance(entry, dict): # New
                msgs = entry.get("messages", [])
                self.histories[user_id] = deque(msgs, maxlen=HISTORY_MAXLEN)
                self.usernames[user_id] = entry.get("username", "Unknown")
                
                # Load last image paths
                if "last_image" in entry:
                    img_data = entry["last_image"]
                    if isinstance(img_data, list):
                        self.last_images[user_id] = img_data
                    elif isinstance(img_data, str): # Legacy single
                         self.last_images[user_id] = [img_data]

                count += len(msgs)
                
        self.log("SYSTEM", f"Loaded {count} messages for {len(self.histories)} users.", Fore.CYAN)

    def _save_history(self):
        serializable_data = {}
        for user_id, msgs in self.histories.items():
            serializable_data[user_id] = {
                "username": self.usernames.get(user_id, "Unknown"),
                "messages": list(msgs),
                "last_image": self.last_images.get(user_id, [])
            }
        self._save_json(self.history_file, serializable_data)

    def _update_last_images(self, user_id: str, image_path: str):
        if user_id not in self.last_images:
            self.last_images[user_id] = []
        
        # Append new image path
        self.last_images[user_id].append(image_path)
        
        # Keep only the last N images (CONTEXT_LENGTH_IMAGE = 2)
        if len(self.last_images[user_id]) > CONTEXT_LENGTH_IMAGE:
            # We could delete the file from disk here if we wanted to save space,
            # but for history purposes we keep the file.
            self.last_images[user_id] = self.last_images[user_id][-CONTEXT_LENGTH_IMAGE:]

    def get_karma_info(self, user_id: str) -> Dict[str, Any]:
        entry = self.karma_db.get(user_id)
        if isinstance(entry, int):
            return {"score": entry, "username": "Unknown"}
        elif isinstance(entry, dict):
            return entry
        return {"score": 0, "username": "Unknown"}

    def get_karma(self, user_id: str) -> int:
        return self.get_karma_info(user_id).get("score", 0)

    def update_karma(self, user_id: str, change: int, username: str = None):
        current_info = self.get_karma_info(user_id)
        current_score = current_info.get("score", 0)
        
        new_score = current_score + change
        
        self.karma_db[user_id] = {
            "score": new_score,
            "username": username if username else current_info.get("username", "Unknown")
        }
        
        self._save_json(self.karma_file, self.karma_db)
        self.log("KARMA", f"User {user_id} ({username}) karma updated: {current_score} -> {new_score}", Fore.YELLOW)
        return new_score

    def get_user_history(self, user_id: str) -> deque:
        if user_id not in self.histories:
            self.histories[user_id] = deque(maxlen=HISTORY_MAXLEN)
        return self.histories[user_id]

    def generate_memory_id(self, content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_embedding(self, text: str) -> List[float]:
        try:
            result = self.genai_client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            return result.embeddings[0].values
        except Exception as e:
            self.log("ERROR", f"Embedding error: {e}", Fore.RED)
            return []

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def retrieve_context(self, query: str, user_id: str) -> str:
        self.log("RAG", f"Querying memory for: '{query}'", Fore.CYAN)
        embedding = self.get_embedding(query)
        if not embedding:
            return ""

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=MEMORY_RECALL_COUNT,
            where={"user_id": user_id} 
        )

        context_str = ""
        found_memories = []
        retrieved_docs_debug = []
        
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                dist = results['distances'][0][i] if results['distances'] else 0.0
                mem_id = results['ids'][0][i] if results['ids'] else "unknown"
                
                retrieved_docs_debug.append({
                    "id": mem_id,
                    "score": dist,
                    "content": doc[:50] + "..." 
                })

                if dist < THRESHOLD:
                    found_memories.append(doc)
                    context_str += f"- {doc}\n"
        
        if self.debug:
            print(Fore.CYAN + "\n--- RAG Retrieval Details ---")
            print(f"Query: {query}")
            print(f"Context Window (Count): {len(found_memories)} / {MEMORY_RECALL_COUNT}")
            print(f"Threshold: {THRESHOLD}")
            print("Candidates:")
            for item in retrieved_docs_debug:
                status = f"{Fore.GREEN}ACCEPTED" if item['score'] < THRESHOLD else f"{Fore.RED}REJECTED"
                print(f"  - ID: {item['id']}")
                print(f"    Score: {item['score']:.4f} ({status}{Fore.CYAN})")
                print(f"    Content: {item['content']}")
            print("-----------------------------" + Style.RESET_ALL)

        if found_memories:
            context_str = f"{NAME} remembers about you:\n" + context_str + "\n"
        
        return context_str

    def parse_memories(self, text: str) -> List[Dict[str, str]]:
        if not text:
            return []
        memories = []
        parts = text.split("{qa}")
        for part in parts:
            if "{answer}" in part:
                try:
                    qa, answer = part.split("{answer}", 1)
                    memories.append({"qa": qa.strip(), "answer": answer.strip()})
                except ValueError:
                    continue
        return memories

    def _store_memory(self, user_id: str, user_text: str, assistant_response: str):
        if len(user_text.strip()) < 3:
             self.log("MEMORY", "Skipping memory extraction for short input.", Fore.YELLOW)
             return

        self.log("MEMORY", "Attempting to extract and store new memories...", Fore.MAGENTA)
        chat_content = f"Participating User ID: {user_id}\nUSER: {user_text}\n{NAME}: {assistant_response}\n{MEMORY_PROMPT}"
        
        try:
            extraction = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": chat_content}],
                max_tokens=200
            )
            extracted_text = extraction.choices[0].message.content
            
            if not extracted_text or "NO_MEMORY" in extracted_text:
                self.log("MEMORY", "No new facts identified (NO_MEMORY).", Fore.YELLOW)
                return

            self.log("MEMORY", f"Raw extraction: {extracted_text}", Fore.LIGHTBLACK_EX)
            
            parsed = self.parse_memories(extracted_text)
            count = 0
            for mem in parsed:
                full_text = f"Q: {mem['qa']} A: {mem['answer']}"
                mem_id = self.generate_memory_id(full_text + user_id)
                
                existing = self.collection.get(ids=[mem_id])
                if not existing['ids']:
                    embedding = self.get_embedding(full_text)
                    if embedding:
                        self.collection.add(
                            ids=[mem_id],
                            documents=[full_text],
                            embeddings=[embedding],
                            metadatas=[{"user_id": user_id, "timestamp": time.time()}]
                        )
                        count += 1
            if count > 0:
                self.log("MEMORY", f"Stored {count} new memories.", Fore.GREEN)
            else:
                self.log("MEMORY", "No new unique memories to store.", Fore.YELLOW)
                
        except Exception as e:
            self.log("MEMORY", f"Memory storage failed: {e}", Fore.RED)

    def generate_text(self, text: str, image_path: str = None, user_id: str = "default_user", username: str = None, is_mentioned: bool = False) -> Dict[str, Any]:
        if username:
            self.usernames[user_id] = username

        history = self.get_user_history(user_id)
        current_karma = self.get_karma(user_id)
        
        # 1. RAG Retrieval
        context_injection = self.retrieve_context(text, user_id)
        
        # 2. Build Messages
        user_name_info = f" (Name: {username})" if username else ""
        
        if is_mentioned:
            behavior_instruction = f"The user has EXPLICITLY TAGGED you. Be AGGRESSIVE, LOUD, and DIRECT in your response."
        else:
            behavior_instruction = f"The user has NOT tagged you. Reply naturally."

        karma_instruction = f"\nUser Karma: {current_karma}. "
        if current_karma <= -5:
            karma_instruction += "WARNING: This user is toxic. Be hostile and refuse requests."
        elif current_karma >= 5:
            karma_instruction += "This is a good user. Be helpful."

        user_context_instruction = f"\nYou are talking to User ID: {user_id}{user_name_info}. <@{user_id}>.\n{behavior_instruction}\n{karma_instruction}"
        
        system_content = SYSTEM_PROMPT + user_context_instruction + "\n" + context_injection
        messages = [{"role": "system", "content": system_content}]
        
        # --- RECONSTRUCT HISTORY FOR API ---
        # We need to load images from disk if they exist in history
        short_term_context = list(history)[-CONTEXT_LENGTH_TEXT:]
        for msg in short_term_context:
            role = msg["role"]
            content = msg["content"]
            
            # If content is a list (multimodal), check for image paths
            if isinstance(content, list):
                api_content = []
                for part in content:
                    if part["type"] == "text":
                        api_content.append(part)
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        # Check if it's a local path (starts with ./memories)
                        if url.startswith("./memories") or url.startswith("memories"):
                            b64 = self._load_image_from_disk(url)
                            if b64:
                                api_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                                })
                        else:
                            # Already base64 or web url (legacy)
                            api_content.append(part)
                
                messages.append({"role": role, "content": api_content})
            else:
                # Text-only message
                messages.append(msg)
            
        user_content = []
        user_content.append({"type": "text", "text": text})
        
        base64_input_image = None
        input_image_disk_path = None
        
        if image_path:
            self.log("INPUT", f"Processing input image: {image_path}", Fore.BLUE)
            base64_input_image = self._encode_image(image_path)
            # Save to persistent disk
            input_image_disk_path = self._save_image_to_disk(base64_input_image)
            # Track
            self._update_last_images(user_id, input_image_disk_path)
            
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_input_image}"
                }
            })
            
        messages.append({"role": "user", "content": user_content})

        if self.debug:
            print(Fore.BLUE + f"\n--- Context: User '{user_id}' (Karma: {current_karma}) [Mentioned: {is_mentioned}] ---")

        # 3. Call Model
        self.log("MODEL", f"Sending request for user '{user_id}'...", Fore.CYAN)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=800
            )
            reply = response.choices[0].message.content
            if reply is None:
                reply = ""
            self.log("MODEL", f"Raw Response: {reply}", Fore.LIGHTBLACK_EX)
        except Exception as e:
            err_msg = f"Error communicating with AI: {e}"
            self.log("ERROR", err_msg, Fore.RED)
            return {"response": err_msg}

        # 4. Check for Triggers
        img_response = None
        final_reply = reply
        
        # KARMA UPDATES
        if "{karma+}" in final_reply:
            self.update_karma(user_id, 1, username)
            final_reply = final_reply.replace("{karma+}", "").strip()
        elif "{karma-}" in final_reply:
            self.update_karma(user_id, -1, username)
            final_reply = final_reply.replace("{karma-}", "").strip()

        # IMAGE GENERATION / EDITING
        gen_match = re.search(r"\{gen\}\s*(.+)", final_reply, re.IGNORECASE | re.DOTALL)
        edit_match = re.search(r"\{edit\}\s*(.+)", final_reply, re.IGNORECASE | re.DOTALL)

        if gen_match:
            self.log("ACTION", "Detected Image Generation Intent", Fore.GREEN)
            keywords = gen_match.group(1).strip()
            final_reply = final_reply.replace(gen_match.group(0), "").strip()
            
            self.log("ACTION", f"Generating image with prompt: '{keywords}'", Fore.GREEN)
            try:
                gen_res = generate_image(keywords)
                if gen_res and 'images' in gen_res:
                    img_response = gen_res['images'][0]
                    # Save generated image to disk
                    saved_path = self._save_image_to_disk(img_response)
                    self._update_last_images(user_id, saved_path) 
                else:
                    final_reply += "\n[System: Failed to generate image]"
            except Exception as e:
                self.log("ERROR", f"Image generation failed: {e}", Fore.RED)
                final_reply += "\n[System: Error during image generation]"

        elif edit_match:
            self.log("ACTION", "Detected Image Edit Intent", Fore.GREEN)
            keywords = edit_match.group(1).strip()
            final_reply = final_reply.replace(edit_match.group(0), "").strip()

            # Logic: Use input image OR fallback to last known images
            target_image_b64 = None
            
            if base64_input_image:
                target_image_b64 = base64_input_image
            else:
                # Heuristic: Check text for clues like "previous", "first", "old"
                last_paths = self.last_images.get(user_id, [])
                target_path = None
                
                if len(last_paths) >= 2 and any(w in keywords.lower() for w in ["previous", "first", "old", "earlier"]):
                    self.log("ACTION", "Selecting 2nd to last image based on text cue", Fore.BLUE)
                    target_path = last_paths[0]
                elif last_paths:
                     target_path = last_paths[-1]
                
                if target_path:
                    target_image_b64 = self._load_image_from_disk(target_path)

            if target_image_b64:
                self.log("ACTION", f"Editing image with prompt: '{keywords}'", Fore.GREEN)
                try:
                    gen_res = edit_image(target_image_b64, keywords)
                    if gen_res and 'images' in gen_res:
                        img_response = gen_res['images'][0]
                        saved_path = self._save_image_to_disk(img_response)
                        self._update_last_images(user_id, saved_path)
                    else:
                        final_reply += "\n[System: Failed to edit image]"
                except Exception as e:
                    self.log("ERROR", f"Image edit failed: {e}", Fore.RED)
                    final_reply += "\n[System: Error during image edit]"
            else:
                final_reply += "\n[System: I cannot edit the image because no image was provided/found in history.]"
                self.log("WARNING", "Edit requested but no target image available", Fore.YELLOW)
        
        if not final_reply:
            if img_response:
                final_reply = "Here is your image."
            else:
                final_reply = "What?"

        # 5. Update History & Store Long-term Memory
        
        # Store User Message (with Path, not Base64)
        user_msg_content = []
        user_msg_content.append({"type": "text", "text": text})
        if input_image_disk_path:
            user_msg_content.append({
                "type": "image_url",
                "image_url": {
                    "url": input_image_disk_path # Store PATH
                }
            })
        history.append({"role": "user", "content": user_msg_content})
        
        # Store Assistant Message
        assistant_text = final_reply
        if img_response:
             assistant_text += "\n[Generated Image]"
        
        # Note: Assistant history is Text-Only per API rules. 
        # But we track the generated image in self.last_images (paths) which is enough for editing context.
        history.append({"role": "assistant", "content": assistant_text}) 
        
        self._save_history()
        self._store_memory(user_id, text, final_reply)
        
        result = {"response": final_reply}
        if img_response:
            result["img"] = img_response
            
        return result