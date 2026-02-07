import os
import hashlib
import time
import datetime
from typing import List, Dict, Optional, Any

import chromadb
from google import genai
from google.genai import types
from colorama import Fore

from src.components.common import log
from config import (
    CHROMA_DB_PATH, 
    COLLECTION_NAME, 
    THRESHOLD, 
    MEMORY_RECALL_COUNT, 
    NAME, 
    MEMORY_PROMPT, 
    MAX_TOKENS_MEMORY,
    EMBEDDING_MODEL_NAME
)

class MemoryEngine:
    def __init__(self, debug: bool = False) -> None:
        """Initializes the MemoryEngine with ChromaDB and GenAI client.

        Args:
            debug: If True, prints verbose debug information.
        """
        self.debug = debug
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        # Google GenAI Client for Embeddings
        if self.api_key:
            self.genai_client = genai.Client(api_key=self.api_key)
        else:
            log("ERROR", "GOOGLE_API_KEY not found. Embeddings will fail.", Fore.RED)

        # ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    def generate_memory_id(self, content: str) -> str:
        """Generates a unique ID for a memory based on its content using MD5.

        Args:
            content: The text content of the memory.

        Returns:
            The MD5 hash of the content.
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_embedding(self, text: str) -> List[float]:
        """Generates a vector embedding for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector. Returns an empty list on failure.
        """
        try:
            result = self.genai_client.models.embed_content(
                model=EMBEDDING_MODEL_NAME,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            return result.embeddings[0].values
        except Exception as e:
            log("ERROR", f"Embedding error: {e}", Fore.RED)
            return []

    def retrieve_context(self, query: str, user_id: str) -> str:
        """Retrieves relevant memories for a user based on a query.

        Args:
            query: The search query (usually the user's latest message).
            user_id: The unique identifier of the user.

        Returns:
            A formatted string containing relevant memories, or an empty string if none found.
        """
        log("RAG", f"Querying memory for: '{query}'", Fore.CYAN, debug=self.debug)
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
                
                # Get timestamp
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                ts = meta.get("timestamp", 0)
                date_str = "Unknown Date"
                if ts:
                    date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')

                retrieved_docs_debug.append({
                    "id": mem_id,
                    "score": dist,
                    "content": doc[:50] + "...",
                    "date": date_str
                })

                if dist < THRESHOLD:
                    found_memories.append({
                        "ts": ts,
                        "date": date_str,
                        "doc": doc
                    })

        # Sort by timestamp descending (newest first)
        found_memories.sort(key=lambda x: x["ts"], reverse=True)

        for mem in found_memories:
            context_str += f"- [{mem['date']}] {mem['doc']}\n"
        
        if self.debug:
            print(Fore.CYAN + "\n--- RAG Retrieval Details ---")
            print(f"Query: {query}")
            print("Candidates:")
            for item in retrieved_docs_debug:
                status = f"{Fore.GREEN}ACCEPTED" if item['score'] < THRESHOLD else f"{Fore.RED}REJECTED"
                print(f"  - ID: {item['id']} | Score: {item['score']:.4f} ({status}{Fore.CYAN})")
            print("-----------------------------" + Fore.RESET)

        if found_memories:
            context_str = f"{NAME} remembers about you (recent first):\n" + context_str + "\n"
        
        return context_str

    def parse_memories(self, text: str) -> List[Dict[str, str]]:
        """Parses the raw text output from the memory extraction model.

        Args:
            text: The raw text containing generated memories.

        Returns:
            A list of dictionaries, each with 'qa' and 'answer' keys.
        """
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

    def store_memory(self, client: Any, model_name: str, user_id: str, user_text: str, assistant_response: str) -> None:
        """Extracts and stores new memories from a conversation turn.

        Args:
            client: The API client instance used for memory extraction.
            model_name: The name of the model to use.
            user_id: The unique identifier of the user.
            user_text: The user's input text.
            assistant_response: The assistant's response text.
        """
        if len(user_text.strip()) < 3:
             log("MEMORY", "Skipping memory extraction for short input.", Fore.YELLOW)
             return

        log("MEMORY", "Attempting to extract and store new memories...", Fore.MAGENTA)
        chat_content = f"Participating User ID: {user_id}\nUSER: {user_text}\n{NAME}: {assistant_response}\n{MEMORY_PROMPT}"
        
        try:
            extraction = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": chat_content}],
                max_tokens=MAX_TOKENS_MEMORY
            )
            extracted_text = extraction.choices[0].message.content
            
            if not extracted_text or "NO_MEMORY" in extracted_text:
                log("MEMORY", "No new facts identified (NO_MEMORY).", Fore.YELLOW)
                return

            log("MEMORY", f"Raw extraction: {extracted_text}", Fore.LIGHTBLACK_EX)
            
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
                log("MEMORY", f"Stored {count} new memories.", Fore.GREEN)
            else:
                log("MEMORY", "No new unique memories to store.", Fore.YELLOW)
                
        except Exception as e:
            log("MEMORY", f"Memory storage failed: {e}", Fore.RED)