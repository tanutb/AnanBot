import time
from colorama import Fore
from src.components.common import log, load_json, save_json
from config import MAX_TOKENS_SUMMARY, SUMMARY_PROMPT

class KarmaManager:
    def __init__(self, karma_file: str = "./memories/karma.json"):
        self.karma_file = karma_file
        self.karma_db = load_json(self.karma_file)

    def get_info(self, user_id: str) -> dict:
        entry = self.karma_db.get(user_id)
        if isinstance(entry, int):
            return {"score": entry, "username": "Unknown"}
        elif isinstance(entry, dict):
            return entry
        return {"score": 0, "username": "Unknown"}

    def get_score(self, user_id: str) -> int:
        return self.get_info(user_id).get("score", 0)

    def update_score(self, user_id: str, change: int, username: str = None) -> int:
        current_info = self.get_info(user_id)
        current_score = current_info.get("score", 0)
        
        new_score = current_score + change
        
        # Update score and username, preserve other fields (like summary)
        current_info["score"] = new_score
        if username:
            current_info["username"] = username
            
        self.karma_db[user_id] = current_info
        
        save_json(self.karma_file, self.karma_db)
        log("KARMA", f"User {user_id} ({username}) karma updated: {current_score} -> {new_score}", Fore.YELLOW)
        return new_score

    def set_score(self, user_id: str, score: int) -> int:
        current_info = self.get_info(user_id)
        old_score = current_info.get("score", 0)
        
        current_info["score"] = score
        self.karma_db[user_id] = current_info
        
        save_json(self.karma_file, self.karma_db)
        log("KARMA", f"User {user_id} karma set: {old_score} -> {score}", Fore.YELLOW)
        return score

    def update_user_summary(self, client, model_name: str, user_id: str, user_text: str, ai_reply: str):
        current_info = self.get_info(user_id)
        current_summary = current_info.get("summary", "No summary yet.")
        
        # Don't update for trivial inputs
        if len(user_text) < 5:
            return

        log("SUMMARY", "Updating user summary...", Fore.MAGENTA)
        
        prompt = SUMMARY_PROMPT.format(
            current_summary=current_summary,
            user_text=user_text,
            ai_reply=ai_reply
        )
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_SUMMARY
            )
            
            content = response.choices[0].message.content
            if content:
                new_summary = content.strip()
                
                if len(new_summary) > 5 and new_summary != current_summary:
                    current_info["summary"] = new_summary
                    current_info["last_interaction"] = time.time()
                    self.karma_db[user_id] = current_info
                    save_json(self.karma_file, self.karma_db)
                    log("SUMMARY", f"Summary updated: {new_summary[:50]}...", Fore.GREEN)
                else:
                    log("SUMMARY", "No significant change in summary.", Fore.YELLOW)
            else:
                 log("SUMMARY", "Received empty response for summary update.", Fore.YELLOW)
                
        except Exception as e:
            log("ERROR", f"Failed to update summary: {e}", Fore.RED)

    def get_details(self, user_id: str) -> dict:
        return self.get_info(user_id)
