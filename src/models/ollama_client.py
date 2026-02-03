import base64
import json
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.console import Console

from src.models.base_model import BaseModelClient
from src.screen_capture import image_to_base64
from config import OLLAMA_API_URL, OLLAMA_MODEL_NAME, VLM_BEHAVIOR_PROMPT

console = Console()

class OllamaClient(BaseModelClient):
    def __init__(self):
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def query(
        self,
        text: str,
        image: Optional[object] = None,
        context: str = "",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        if not OLLAMA_API_URL:
            return "Error: OLLAMA_API_URL is not configured."

        if not text.strip():
            return "Error: No query text provided."

        # Build prompt
        full_prompt = text
        if context:
            full_prompt = f"{context}\n\nBased on our conversation and any provided image, please answer:\n{text}"

        messages = []
        # System prompt
        sys_prompt = system_prompt if system_prompt else VLM_BEHAVIOR_PROMPT
        messages.append({"role": "system", "content": sys_prompt})

        # User message
        user_message = {"role": "user", "content": full_prompt}

        # Add image if provided
        if image is not None:
            try:
                image_bytes = image_to_base64(image)
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                user_message["images"] = [image_b64]
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to encode image: {e}[/yellow]")

        messages.append(user_message)

        options = {
            "num_predict": 512,
        }
        if json_mode:
             # Some Ollama models support "format": "json" at top level, but not all. 
             # We can put it in options or top level depending on API version.
             # Standard Ollama API v0.1.x supports 'format': 'json' in the request body.
             pass 

        payload = {
            "model": OLLAMA_MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        
        if json_mode:
            payload["format"] = "json"

        try:
            response = self._session.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            return content.strip() if content else "No response content from the model."

        except Exception as e:
            console.print(f"[red]Error querying Ollama: {e}[/red]")
            return f"Error: {e}"
