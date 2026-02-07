import time
from typing import Dict, Any, Optional
from colorama import Fore
from src.components.common import log, load_json, save_json
from config import MAX_TOKENS_SUMMARY, SUMMARY_PROMPT

class KarmaManager:
    def __init__(self, karma_file: str = "./memories/karma.json") -> None:
        """Initializes the KarmaManager.

        Args:
            karma_file: Path to the JSON file storing karma and user info.
        """
        self.karma_file = karma_file
        self.karma_db = load_json(self.karma_file)

    def get_info(self, user_id: str) -> Dict[str, Any]:
        """Retrieves information about a user, including karma score and summary.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            A dictionary containing user details (score, username, summary, etc.).
        """
        entry = self.karma_db.get(user_id)
        if isinstance(entry, int):
            return {"score": entry, "username": "Unknown"}
        elif isinstance(entry, dict):
            return entry
        return {"score": 0, "username": "Unknown"}

    def get_score(self, user_id: str) -> int:
        """Retrieves the karma score for a user.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            The user's current karma score. Defaults to 0 if not found.
        """
        return self.get_info(user_id).get("score", 0)

    def update_score(self, user_id: str, change: int, username: Optional[str] = None) -> int:
        """Updates the karma score for a user by a specified amount.

        Args:
            user_id: The unique identifier of the user.
            change: The amount to change the score by (positive or negative).
            username: The display name of the user (optional).

        Returns:
            The new karma score.
        """
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
        """Sets the karma score for a user to a specific value.

        Args:
            user_id: The unique identifier of the user.
            score: The new karma score.

        Returns:
            The new karma score.
        """
        current_info = self.get_info(user_id)
        old_score = current_info.get("score", 0)
        
        current_info["score"] = score
        self.karma_db[user_id] = current_info
        
        save_json(self.karma_file, self.karma_db)
        log("KARMA", f"User {user_id} karma set: {old_score} -> {score}", Fore.YELLOW)
        return score

    def update_user_summary(self, client: Any, model_name: str, user_id: str, user_text: str, ai_reply: str) -> None:
        """Updates the user's persona summary based on recent interactions.

        Args:
            client: The API client instance used to generate the summary.
            model_name: The name of the model to use for summarization.
            user_id: The unique identifier of the user.
            user_text: The user's input text.
            ai_reply: The AI's response text.
        """
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

    def get_details(self, user_id: str) -> Dict[str, Any]:
        """Alias for get_info. Retrieves full user details.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            A dictionary containing user details.
        """
        return self.get_info(user_id)
