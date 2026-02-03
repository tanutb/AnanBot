import base64
from typing import Optional
from rich.console import Console
from openai import OpenAI, OpenAIError

from src.models.base_model import BaseModelClient
from src.screen_capture import image_to_base64
from config import OPENAI_API_KEY, OPENAI_MODEL_NAME, VLM_BEHAVIOR_PROMPT

console = Console()

class OpenAIClient(BaseModelClient):
    def __init__(self):
        if not OPENAI_API_KEY:
            console.print("[red]Error: OPENAI_API_KEY is not configured.[/red]")
            self.client = None
        else:
            self.client = OpenAI(api_key=OPENAI_API_KEY)

    def query(
        self,
        text: str,
        image: Optional[object] = None,
        context: str = "",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        if not self.client:
            return "Error: OpenAI client not initialized (missing API key)."

        # Prepare messages
        messages = []
        
        # System Prompt
        sys_prompt = system_prompt if system_prompt else VLM_BEHAVIOR_PROMPT
        messages.append({"role": "system", "content": sys_prompt})
        
        # User Message content
        user_content = []
        
        full_text = text
        if context:
            full_text = f"{context}\n\nBased on our conversation and any provided image, please answer:\n{text}"
            
        user_content.append({"type": "text", "text": full_text})
        
        if image is not None:
            try:
                image_bytes = image_to_base64(image)
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }
                })
            except Exception as e:
                 console.print(f"[yellow]Warning: Failed to encode image for OpenAI: {e}[/yellow]")

        messages.append({"role": "user", "content": user_content})

        try:
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=messages,
                max_tokens=512,
                response_format=response_format
            )
            
            return response.choices[0].message.content.strip()

        except OpenAIError as e:
            console.print(f"[red]Error querying OpenAI: {e}[/red]")
            return f"Error: {e}"
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return f"Error: {e}"
