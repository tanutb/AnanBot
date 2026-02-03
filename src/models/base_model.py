from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class BaseModelClient(ABC):
    """
    Abstract base class for VLM/LLM clients.
    """

    @abstractmethod
    def query(
        self,
        text: str,
        image: Optional[object] = None,
        context: str = "",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Send a query to the model.

        Args:
            text: The user's text query.
            image: Optional PIL Image object.
            context: Conversation history or context string.
            system_prompt: Optional system prompt to override default.
            json_mode: Whether to enforce JSON output (if supported).

        Returns:
            The model's response text.
        """
        pass
