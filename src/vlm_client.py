# src/vlm_client.py
"""
VLM (Vision Language Model) client.
Acts as a facade for the configured model backend (Ollama, Gemini, OpenAI).
"""

from typing import Optional
from rich.console import Console

from src.models import get_model_client

console = Console()

def query_vlm(
    image: Optional[object] = None,
    text: str = "",
    context: str = "",
    timeout: int = 120, # kept for signature compatibility, but might be handled in client
    stream: bool = False, # Stream not yet fully supported in adapters, ignored for now
) -> str:
    """
    Sends a query to the configured VLM API.
    
    Args:
        image: PIL.Image.Image or None
        text: User query
        context: Conversation history
        timeout: Request timeout (depreciated/handled by adapter)
        stream: Stream response (depreciated/ignored)
    
    Returns:
        str: Model response
    """
    client = get_model_client()
    return client.query(text=text, image=image, context=context)


def check_connection() -> bool:
    """
    Checks if the configured model service is reachable.
    For Cloud APIs (Gemini/OpenAI), this might just be a no-op or a simple ping.
    """
    # Simple test query
    try:
        client = get_model_client()
        # A simple ping query that doesn't cost much or is fast
        client.query(text="ping", image=None, context="") 
        return True
    except Exception as e:
        console.print(f"[red]Connection check failed: {e}[/red]")
        return False


if __name__ == "__main__":
    from src.screen_capture import capture_screen

    console.print("[bold]Testing VLM Client[/bold]\n")

    # Test connection
    console.print("[dim]Checking connection...[/dim]")
    if check_connection():
        console.print("[green]✓ Model is reachable[/green]")
    else:
        console.print("[red]✗ Cannot reach Model[/red]")

    # Test text-only query
    console.print("\n[yellow]Test 1: Text-only query[/yellow]")
    response = query_vlm(text="What is 2 + 2?")
    console.print(f"Response: {response}")

    # Test with screenshot
    console.print("\n[yellow]Test 2: Query with screenshot[/yellow]")
    screenshot = capture_screen()
    response = query_vlm(image=screenshot, text="Briefly describe what you see.")
    console.print(f"Response: {response}")
