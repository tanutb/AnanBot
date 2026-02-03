from google import genai
from google.genai import types
from typing import Optional
from rich.console import Console

from src.models.base_model import BaseModelClient
from src.screen_capture import image_to_base64
from config import GOOGLE_API_KEY, GEMINI_MODEL_NAME, VLM_BEHAVIOR_PROMPT

console = Console()

class GeminiClient(BaseModelClient):
    def __init__(self):
        if not GOOGLE_API_KEY:
            console.print("[red]Error: GOOGLE_API_KEY is not configured.[/red]")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=GOOGLE_API_KEY)
                self.model_name = GEMINI_MODEL_NAME
            except Exception as e:
                console.print(f"[red]Error configuring Gemini: {e}[/red]")
                self.client = None

    def query(
        self,
        text: str,
        image: Optional[object] = None,
        context: str = "",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        if not self.client:
            return "Error: Gemini client not initialized."

        # Prepare parts
        parts = []
        
        # 1. Add Image if present
        if image is not None:
            try:
                image_bytes = image_to_base64(image)
                # The new SDK uses types.Part.from_bytes or similar structure
                parts.append(types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/png"
                ))
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to encode image for Gemini: {e}[/yellow]")

        # 2. Add Context and Text
        full_text = text
        if context:
            full_text = f"{context}\n\nBased on our conversation and any provided image, please answer:\n{text}"
        
        parts.append(types.Part.from_text(text=full_text))

        # System Instruction
        sys_prompt_text = system_prompt if system_prompt else VLM_BEHAVIOR_PROMPT
        
        # Config
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt_text,
            temperature=0.7 if not json_mode else 0.1,
        )

        if json_mode:
             config.response_mime_type = "application/json"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=config
            )
            
            return response.text.strip() if response.text else ""

        except Exception as e:
            console.print(f"[red]Error querying Gemini: {e}[/red]")
            return f"Error: {e}"
