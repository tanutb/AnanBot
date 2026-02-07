import os
import re
from typing import List, Dict, Any, Tuple

from openai import OpenAI
from dotenv import load_dotenv
from colorama import Fore, init

from config import (
    SYSTEM_PROMPT,
    NAME,
    CONTEXT_LENGTH_TEXT,
    MAX_USER_INPUT_IMAGES,
    MAX_TOKENS_RESPONSE,
    MODEL_NAME
)
from src.gemini_vision import generate_image, edit_image
from src.components.common import log
from src.components.karma_manager import KarmaManager
from src.components.history_manager import HistoryManager
from src.components.memory_engine import MemoryEngine
from src.components.image_handler import ImageHandler

# Initialize colorama
init(autoreset=True)
load_dotenv()

class Multimodal:
    def __init__(self, debug: bool = False) -> None:
        """Initializes the multimodal agent using OpenAI-compatible Gemini API.

        Args:
            debug: If True, prints verbose debug information.
        """
        self.debug = debug
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = MODEL_NAME
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Components
        self.karma_manager = KarmaManager()
        self.history_manager = HistoryManager()
        self.memory_engine = MemoryEngine(debug=debug)
        self.image_handler = ImageHandler()

    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Returns the raw karma/persona data for a user."""
        return self.karma_manager.get_details(user_id)

    def set_karma(self, user_id: str, score: int) -> int:
        """Sets the karma score for a user."""
        return self.karma_manager.set_score(user_id, score)

    def _clean_response(self, text: str) -> str:
        """Removes potential internal artifacts or hallucinated tags."""
        text = re.sub(r'\(?-?\d+\$?\s*Karma\)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(?Karma:\s*-?\d+\)?', '', text, flags=re.IGNORECASE)
        return text.strip()

    def generate_response(self, text: str, image_paths: List[str] = [], user_id: str = "default_user", context_id: str = None, username: str = None, is_mentioned: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Generates a response to the user's input, handling text, images, and context.

        Args:
            text: The user's input text.
            image_paths: List of file paths to images included in the user's message.
            user_id: Unique identifier for the user (for Karma/Persona).
            context_id: Unique identifier for the conversation context (e.g., Channel ID). Defaults to user_id.
            username: The display name of the user.
            is_mentioned: Whether the bot was explicitly mentioned in the message.

        Returns:
            A tuple containing:
            - A dictionary with the 'response' text and optional 'img' (base64).
            - A dictionary containing background data for memory processing.
        """
        if context_id is None:
            context_id = user_id

        if username:
            # We track usernames per user_id, but history is per context_id
            self.history_manager.set_username(user_id, username)

        # Get Context (History uses context_id for shared channel awareness)
        history = self.history_manager.get_history(context_id)
        
        # User Specific Data
        karma_score = self.karma_manager.get_score(user_id)
        user_summary = self.karma_manager.get_info(user_id).get("summary", "No summary yet.")
        
        # 1. RAG Retrieval (User specific + Context specific?)
        # For now, retrieve based on user to keep personal memories personal
        context_injection = self.memory_engine.retrieve_context(text, user_id)
        
        # 2. Build Messages
        user_name_info = f" (Name: {username})" if username else ""
        
        if is_mentioned:
            behavior_instruction = f"The user has EXPLICITLY TAGGED you. Be AGGRESSIVE, LOUD, and DIRECT in your response."
        else:
            behavior_instruction = f"The user has NOT tagged you. Reply naturally."

        karma_instruction = f"\nUser Karma: {karma_score}. "
        if karma_score <= -5:
            karma_instruction += "WARNING: This user is toxic. Be hostile and refuse requests."
        elif karma_score >= 5:
            karma_instruction += "This is a good user. Be helpful."

        summary_instruction = f"\nUser Persona Summary: {user_summary}"

        user_context_instruction = f"\nYou are talking to User ID: {user_id}{user_name_info}. <@{user_id}>.\n{behavior_instruction}\n{karma_instruction}\n{summary_instruction}\nIMPORTANT: Use the user's name ({username}) frequently in your response if known."
        
        system_content = SYSTEM_PROMPT + user_context_instruction + "\n" + context_injection
        messages = [{"role": "system", "content": system_content}]
        
        # --- RECONSTRUCT HISTORY FOR API ---
        short_term_context = list(history)[-CONTEXT_LENGTH_TEXT:]
        for msg in short_term_context:
            role = msg["role"]
            content = msg["content"]
            
            if isinstance(content, list):
                api_content = []
                for part in content:
                    if part["type"] == "text":
                        api_content.append(part)
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("./memories") or url.startswith("memories"):
                            b64 = self.image_handler.load_image_from_disk(url)
                            if b64:
                                api_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                                })
                        else:
                            api_content.append(part)
                messages.append({"role": role, "content": api_content})
            else:
                messages.append(msg)
            
        user_content = []
        
        # Prepend Username to text for shared context clarity
        display_text = f"[{username}]: {text}" if username else text
        user_content.append({"type": "text", "text": display_text})
        
        base64_input_images = []
        input_image_disk_paths = []
        
        if image_paths:
            processing_paths = image_paths[:MAX_USER_INPUT_IMAGES]
            for img_path in processing_paths:
                log("INPUT", f"Processing input image: {img_path}", Fore.BLUE)
                b64 = self.image_handler.encode_image(img_path)
                if b64:
                    base64_input_images.append(b64)
                    saved_path = self.image_handler.save_image_to_disk(b64)
                    input_image_disk_paths.append(saved_path)
                    # Update LAST IMAGES for the CONTEXT (Channel), not just the user
                    self.history_manager.update_last_images(context_id, saved_path)
                    
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
            
        messages.append({"role": "user", "content": user_content})

        if self.debug:
            print(Fore.BLUE + f"\n--- Context: User '{user_id}' (Karma: {karma_score}) [Mentioned: {is_mentioned}] ---")

        # 3. Call Model
        log("MODEL", f"Sending request for user '{user_id}'...", Fore.CYAN, debug=self.debug)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=MAX_TOKENS_RESPONSE
            )
            reply = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            log("MODEL", f"Raw Response: {reply} (Finish Reason: {finish_reason})", Fore.LIGHTBLACK_EX, debug=self.debug)
        except Exception as e:
            err_msg = f"Error communicating with AI: {e}"
            log("ERROR", err_msg, Fore.RED)
            return {"response": err_msg}, {}

        # 4. Check for Triggers
        img_response = None
        final_reply = reply
        action_taken = False
        
        # Check for raw empty response
        if not reply or not reply.strip():
             log("WARNING", f"Model returned empty response. Finish Reason: {finish_reason}", Fore.YELLOW)
             
             if finish_reason == "content_filter" or finish_reason == "safety":
                 final_reply = "[System: Response blocked by Safety Filters.]"
             else:
                 final_reply = f"[System: I couldn't generate a response. (Reason: {finish_reason})]"
        
        else:
            # KARMA UPDATES
            if "{karma+}" in final_reply:
                self.karma_manager.update_score(user_id, 1, username)
                final_reply = final_reply.replace("{karma+}", "").strip()
                action_taken = True
            elif "{karma-}" in final_reply:
                self.karma_manager.update_score(user_id, -1, username)
                final_reply = final_reply.replace("{karma-}", "").strip()
                action_taken = True

            final_reply = self._clean_response(final_reply)

            # IMAGE GENERATION / EDITING
            gen_match = re.search(r"\{gen\}\s*(.+)", final_reply, re.IGNORECASE | re.DOTALL)
            edit_match = re.search(r"\{edit\}\s*(.+)", final_reply, re.IGNORECASE | re.DOTALL)

            if gen_match:
                action_taken = True
                log("ACTION", "Detected Image Generation Intent", Fore.GREEN)
                keywords = gen_match.group(1).strip()
                final_reply = final_reply.replace(gen_match.group(0), "").strip()
                
                try:
                    gen_res = generate_image(keywords)
                    if gen_res and 'images' in gen_res:
                        img_response = gen_res['images'][0]
                        saved_path = self.image_handler.save_image_to_disk(img_response)
                        # Shared Context Update
                        self.history_manager.update_last_images(context_id, saved_path)
                    elif gen_res and 'error' in gen_res:
                        final_reply += f"\n[System: Image generation failed. Reason: {gen_res['error']}]"
                    else:
                        final_reply += "\n[System: Failed to generate image (Unknown Error)]"
                except Exception as e:
                    log("ERROR", f"Image generation failed: {e}", Fore.RED)
                    final_reply += f"\n[System: Error during image generation: {e}]"

            elif edit_match:
                action_taken = True
                log("ACTION", "Detected Image Edit Intent", Fore.GREEN)
                keywords = edit_match.group(1).strip()
                final_reply = final_reply.replace(edit_match.group(0), "").strip()

                target_images_b64 = []
                
                # 1. Add Current Uploads (High Priority)
                if base64_input_images:
                    target_images_b64.extend(base64_input_images)
                
                # 2. Add Recent History (Context - SHARED)
                # Use context_id to retrieve images from ANYONE in the channel
                slots_left = 3 - len(target_images_b64)
                if slots_left > 0:
                    last_paths = self.history_manager.get_last_images(context_id)
                    paths_to_load = last_paths[-slots_left:] 
                    for p in paths_to_load:
                        b64 = self.image_handler.load_image_from_disk(p)
                        if b64:
                            target_images_b64.append(b64)

                if target_images_b64:
                    try:
                        gen_res = edit_image(target_images_b64, keywords)
                        if gen_res and 'images' in gen_res:
                            img_response = gen_res['images'][0]
                            saved_path = self.image_handler.save_image_to_disk(img_response)
                            # Shared Context Update
                            self.history_manager.update_last_images(context_id, saved_path)
                        elif gen_res and 'error' in gen_res:
                             final_reply += f"\n[System: Image edit failed. Reason: {gen_res['error']}]"
                        else:
                            final_reply += "\n[System: Failed to edit image (Unknown Error)]"
                    except Exception as e:
                        log("ERROR", f"Image edit failed: {e}", Fore.RED)
                        final_reply += f"\n[System: Error during image edit: {e}]"
                else:
                    final_reply += "\n[System: No target image found for editing. Please upload one or generate one first.]"
        
        # Final fallback check
        if not final_reply.strip():
            if img_response:
                final_reply = "Here is your image."
            elif action_taken:
                # Fallback if action was taken (like karma update) but no text was left
                final_reply = "Done."
            else:
                # This catches cases where raw reply was NOT empty, but became empty after processing 
                # AND no specific action was flagged (rare, but possible if regex fails or clean_response is aggressive)
                # Or if the logic above missed something.
                final_reply = "What?"

        # 5. Update History (Shared Context)
        user_msg_content = []
        user_msg_content.append({"type": "text", "text": display_text})
        for p in input_image_disk_paths:
             user_msg_content.append({"type": "image_url", "image_url": {"url": p}})

        self.history_manager.add_message(context_id, "user", user_msg_content)
        
        assistant_text = final_reply
        if img_response:
             assistant_text += "\n[Generated Image]"
        self.history_manager.add_message(context_id, "assistant", assistant_text)
        
        # Prepare Background Data
        background_data = {
            "user_id": user_id,
            "context_id": context_id, # Pass context_id for saving
            "text": text,
            "final_reply": final_reply,
            "input_image_disk_paths": input_image_disk_paths
        }
        
        result = {"response": final_reply}
        if img_response:
            result["img"] = img_response
            
        return result, background_data

    def save_memory_background(self, data: Dict[str, Any]) -> None:
        """Performs background tasks: Saving history, extracting memories, and updating summary.

        Args:
            data: A dictionary containing 'user_id', 'text', 'final_reply', and 'input_image_disk_paths'.
        """
        user_id = data.get("user_id")
        text = data.get("text")
        final_reply = data.get("final_reply")
        input_image_disk_paths = data.get("input_image_disk_paths", [])

        self.history_manager.save()
        
        image_note = ""
        if input_image_disk_paths:
            image_note = f" [User sent images: {', '.join(input_image_disk_paths)}]"
            
        self.memory_engine.store_memory(self.client, self.model_name, user_id, text + image_note, final_reply)
        self.karma_manager.update_user_summary(self.client, self.model_name, user_id, text, final_reply)