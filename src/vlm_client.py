# src/vlm_client.py
"""
VLM (Vision Language Model) client for Ollama API.
Optimized for efficient API communication with image support.
"""

import base64
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.console import Console

from config import OLLAMA_API_URL, OLLAMA_MODEL_NAME, VLM_BEHAVIOR_PROMPT
from src.screen_capture import image_to_base64

console = Console()

# Configure session with retry logic for reliability
_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """
    Returns a reusable requests session with retry configuration.
    Singleton pattern for connection pooling efficiency.
    """
    global _session
    if _session is None:
        _session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session


def query_vlm(
    image: Optional[object] = None,
    text: str = "",
    context: str = "",
    timeout: int = 120,
    stream: bool = False,
) -> str:
    """
    Sends a query to the Ollama API with optional image and conversation context.

    Args:
        image: PIL.Image.Image or None - The screenshot/image to analyze
        text: The user's text query
        context: Recent conversation history for continuity
        timeout: Request timeout in seconds
        stream: Whether to stream the response

    Returns:
        str: The VLM response text, or an error message
    """
    if not OLLAMA_API_URL:
        return "Error: OLLAMA_API_URL is not configured."

    if not text.strip():
        return "Error: No query text provided."

    # Build user prompt with context
    if context and context.strip():
        user_prompt = (
            f"{context}\n\n"
            f"Based on our conversation and any provided image, please answer:\n{text}"
        )
    else:
        user_prompt = text

    # Construct user message
    user_message = {"role": "user", "content": user_prompt}

    # Add image if provided
    if image is not None:
        try:
            image_bytes = image_to_base64(image)
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            user_message["images"] = [image_b64]
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to encode image: {e}[/yellow]")

    # Build payload
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "messages": [
            {"role": "system", "content": VLM_BEHAVIOR_PROMPT},
            user_message,
        ],
        "stream": stream,
        "options": {
            "num_predict": 512,  # Limit response length for speed
        },
    }

    # Make API request
    try:
        session = _get_session()
        response = session.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        # Parse response
        data = response.json()
        content = data.get("message", {}).get("content", "")
        
        if not content:
            return "No response content from the model."
        
        return content.strip()

    except requests.exceptions.Timeout:
        console.print("[red]Error: Request timed out[/red]")
        return "Sorry, the request timed out. Please try again."
    
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Cannot connect to Ollama[/red]")
        return "Sorry, cannot connect to Ollama. Please ensure the service is running."
    
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]HTTP Error: {e}[/red]")
        return f"API error: {e.response.status_code}"
    
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return "An unexpected error occurred while querying the model."


def check_ollama_connection() -> bool:
    """
    Checks if Ollama is reachable.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        # Try to reach Ollama's base URL (remove /api/chat)
        base_url = OLLAMA_API_URL.rsplit("/api", 1)[0]
        response = requests.get(base_url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


if __name__ == "__main__":
    from src.screen_capture import capture_screen

    console.print("[bold]Testing VLM Client[/bold]\n")

    # Test connection
    console.print("[dim]Checking Ollama connection...[/dim]")
    if check_ollama_connection():
        console.print("[green]✓ Ollama is reachable[/green]")
    else:
        console.print("[red]✗ Cannot reach Ollama[/red]")

    # Test text-only query
    console.print("\n[yellow]Test 1: Text-only query[/yellow]")
    response = query_vlm(text="What is 2 + 2?")
    console.print(f"Response: {response}")

    # Test with screenshot
    console.print("\n[yellow]Test 2: Query with screenshot[/yellow]")
    screenshot = capture_screen()
    response = query_vlm(image=screenshot, text="Briefly describe what you see.")
    console.print(f"Response: {response}")
