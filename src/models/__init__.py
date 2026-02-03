from config import MODEL_TYPE
from src.models.base_model import BaseModelClient
from src.models.ollama_client import OllamaClient
from src.models.gemini_client import GeminiClient
from src.models.openai_client import OpenAIClient

def get_model_client() -> BaseModelClient:
    """
    Factory function to get the configured model client.
    """
    model_type = MODEL_TYPE.lower()
    
    if model_type == "ollama":
        return OllamaClient()
    elif model_type == "gemini":
        return GeminiClient()
    elif model_type == "openai":
        return OpenAIClient()
    else:
        # Default fallback or error
        raise ValueError(f"Unknown MODEL_TYPE: {model_type}")
