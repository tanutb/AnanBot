from collections import deque
from colorama import Fore
from src.components.common import log, load_json, save_json
from config import HISTORY_MAXLEN, CONTEXT_LENGTH_IMAGE

class HistoryManager:
    def __init__(self, history_file: str = "./memories/chat_history.json"):
        self.history_file = history_file
        self.histories = {}
        self.usernames = {}
        self.last_images = {} # Stores LIST of image PATHS per user
        self._load()

    def _load(self):
        raw_data = load_json(self.history_file)
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
                
        log("SYSTEM", f"Loaded {count} messages for {len(self.histories)} users.", Fore.CYAN)

    def save(self):
        serializable_data = {}
        for user_id, msgs in self.histories.items():
            serializable_data[user_id] = {
                "username": self.usernames.get(user_id, "Unknown"),
                "messages": list(msgs),
                "last_image": self.last_images.get(user_id, [])
            }
        save_json(self.history_file, serializable_data)

    def get_history(self, user_id: str) -> deque:
        if user_id not in self.histories:
            self.histories[user_id] = deque(maxlen=HISTORY_MAXLEN)
        return self.histories[user_id]
    
    def set_username(self, user_id: str, username: str):
        self.usernames[user_id] = username

    def add_message(self, user_id: str, role: str, content: any):
        history = self.get_history(user_id)
        history.append({"role": role, "content": content})

    def update_last_images(self, user_id: str, image_path: str):
        if user_id not in self.last_images:
            self.last_images[user_id] = []
        
        # Append new image path
        self.last_images[user_id].append(image_path)
        
        # Keep only the last N images
        if len(self.last_images[user_id]) > CONTEXT_LENGTH_IMAGE:
            self.last_images[user_id] = self.last_images[user_id][-CONTEXT_LENGTH_IMAGE:]
            
    def get_last_images(self, user_id: str) -> list[str]:
        return self.last_images.get(user_id, [])
