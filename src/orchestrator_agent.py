# src/orchestrator_agent.py
"""
Lightweight orchestrator agent using direct Ollama API calls.
The VLM model autonomously decides when to capture screenshots.
Conversation history is always included for context continuity.
"""

import re
import json
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from rich.console import Console
from PIL import Image
import requests
import base64

from config import OLLAMA_API_URL, OLLAMA_MODEL_NAME, VLM_BEHAVIOR_PROMPT, IMAGE_STORAGE_PATH
from src.screen_capture import capture_screen, image_to_base64
from src.memory_manager import retrieve_recent_context, save_interaction, get_recent_interactions_data

console = Console()

# Ensure image storage exists
os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)

# Decision prompt for VLM - let the model decide autonomously
SCREENSHOT_DECISION_PROMPT = """
You are a decision module. Your only task is to decide whether a visual input is REQUIRED.

User query:
"{query}"

Recent conversation history:
{context}

Respond with ONLY a valid JSON object:
{{
  "action": "screenshot" | "use_past_image" | "none",
  "image_index": integer or null,
  "reason": "short, factual reason"
}}

STRICT RULES (follow in order):

1. action = "screenshot"
   Choose this IF AND ONLY IF the user EXPLICITLY requests to see, read, check, or analyze
   the CURRENT screen or what is visible right now.
   - Implicit hints, assumptions, or general questions are NOT sufficient.
   - Ignore any past images when deciding this.

2. action = "use_past_image"
   Choose this ONLY IF the user explicitly refers to a PREVIOUS image or screenshot
   already present in the conversation (e.g., "that image", "the last screenshot").
   - Set image_index to the correct index.
   - If no clear index can be identified, use "none" instead.

3. action = "none"
   Choose this in ALL other cases.
   - Normal conversation
   - General questions
   - Text-only requests
   - Ambiguous or indirect references to visuals

DEFAULT BEHAVIOR:
- When uncertain, ALWAYS return "none".
- Never guess user intent.
- Do not request images yourself.

JSON response only:
"""



def _ask_vlm_needs_screenshot(query: str, context: str) -> Dict[str, any]:
    """
    Ask the VLM to autonomously decide on visual data source.
    """
    try:
    # Default prompt is already formatted with placeholders in global scope
        prompt = SCREENSHOT_DECISION_PROMPT.format(
            query=query,
            context=context if context else "(No previous conversation)"
        )
        
        payload = {
            "model": OLLAMA_MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "num_predict": 100,
                "temperature": 0.1,
            }
        }
        
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        content = response.json().get("message", {}).get("content", "")
        console.print(f"[yellow] VLM decision: {content}[/yellow]")
        # Parse JSON
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            decision = json.loads(json_match.group())
            return {
                "action": decision.get("action", "none"),
                "image_index": decision.get("image_index"),
                "reason": decision.get("reason", "")
            }
            
    except Exception as e:
        console.print(f"[yellow]VLM decision error: {e}[/yellow]")
    
    return {"action": "none", "reason": "error fallback"}


def _gather_data(query: str) -> Tuple[Optional[object], str, Optional[str]]:
    """
    Gathers data (context + image) for the query.
    
    Returns:
        Tuple of (image_object, context_string, image_path_string)
    """
    image_obj = None
    image_path = None
    context_str = ""
    history_items = []
    
    # 1. Load History & Build Context
    console.print("[dim]📚 Loading conversation history...[/dim]")
    try:
        raw_history = get_recent_interactions_data(n=5)
        
        lines = ["Here is the recent conversation history:"]
        for idx, item in enumerate(raw_history): # 0 is oldest in the list returned? No, get_recent_... returns oldest->newest
            # We want indices to match what the prompt helper says (0 is most recent?) 
            # Actually, standard is usually chronological. Let's make the prompt guidelines match the list.
            # "image_index" to the index number... let's reverse the list for the prompt so 0 is most recent
            
            # Re-process to make 0 the most recent for the VLM prompt
            rev_idx = len(raw_history) - 1 - idx
            item["temp_index"] = rev_idx
            
            ts_str = str(item["timestamp"])[:19]
            img_mark = f" [Image Available (index {rev_idx})]" if item.get("image_path") else ""
            lines.append(f"[{ts_str}] User: {item['user_query']}{img_mark}")
            lines.append(f"[{ts_str}] Agent: {item['vlm_response']}")
            history_items.append(item)
            
        context_str = "\n".join(lines) if raw_history else ""
        if context_str:
            console.print("[green]✓ Context loaded[/green]")
        else:
             console.print("[dim]  (No previous conversation)[/dim]")
            
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load context: {e}[/yellow]")

    # 2. Ask VLM for Decision
    console.print("[dim]🤔 Checking visual context needs...[/dim]")
    decision = _ask_vlm_needs_screenshot(query, context_str)
    action = decision.get("action")
    console.print(f"[dim]   → Action: {action} ({decision.get('reason')})[/dim]")

    # 3. Execute Action
    if action == "screenshot":
        console.print("[dim]📸 Capturing new screen...[/dim]")
        try:
            image_obj = capture_screen()
            # Save to disk
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            save_path = os.path.join(IMAGE_STORAGE_PATH, filename)
            image_obj.save(save_path)
            image_path = save_path
            console.print(f"[green]✓ Captured & Saved: {filename}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Capture failed: {e}[/red]")
            
    elif action == "use_past_image":
        idx = decision.get("image_index")
        if idx is not None and isinstance(idx, int):
            # Find the item with this index (we assigned temp_index earlier)
            target = next((item for item in history_items if item.get("temp_index") == idx), None)
            if target and target.get("image_path"):
                path = target["image_path"]
                if os.path.exists(path):
                    try:
                        image_obj = Image.open(path)
                        image_path = path
                        console.print(f"[green]✓ Loaded past image: {os.path.basename(path)}[/green]")
                    except Exception as e:
                        console.print(f"[red]✗ Failed to load image {path}: {e}[/red]")
                else:
                     console.print(f"[yellow]⚠ Image file not found: {path}[/yellow]")
            else:
                console.print(f"[yellow]⚠ No image found at index {idx}[/yellow]")
    
    return image_obj, context_str, image_path


def _query_vlm_final(image: Optional[object], query: str, context: str) -> str:
    """
    Make the final VLM query to generate the response.
    """
    # Build user prompt
    if context and context.strip():
        user_prompt = f"{context}\n\nBased on our conversation and any provided image, please answer:\n{query}"
    else:
        user_prompt = query
    
    # Build message
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
        "stream": False,
        "think" : False,
    }
    
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        content = response.json().get("message", {}).get("content", "")
        print(content)
        return content.strip() if content else "No response from the model."
        
    except requests.exceptions.Timeout:
        return "Sorry, the request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Sorry, cannot connect to Ollama. Please ensure the service is running."
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return "An error occurred while generating the response."


def run_agent(user_query: str) -> str:
    """
    Main entry point for the orchestrator agent.
    
    Process:
    1. Always load conversation history for context continuity
    2. VLM autonomously decides if screenshot is needed
    3. Gather required data (screenshot if needed, context always)
    4. Generate final response
    
    Args:
        user_query: The user's input query
        
    Returns:
        The agent's response string
    """
    console.print(f"\n[bold cyan]🤖 Processing:[/bold cyan] {user_query}")
    
    # Gather data - context is always loaded, VLM decides on screenshot
    screenshot, context, image_path = _gather_data(user_query)
    
    # Log what we're using
    data_used = []
    if screenshot:
        data_used.append("screenshot")
    if context:
        data_used.append("context")
    
    if data_used:
        console.print(f"[dim]Using: {', '.join(data_used)}[/dim]")
    else:
        console.print("[dim]Direct query (no additional data)[/dim]")
    
    # Generate response
    console.print("[dim]💭 Generating response...[/dim]")
    response = _query_vlm_final(screenshot, user_query, context)
    
    # Save interaction with image path if one was used
    try:
        # Note: We only save image_path if we actually used one. 
        # For historical images, we might choose to save the path again to indicate this interaction relied on it.
        save_interaction(user_query, response, image_path=image_path)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save: {e}[/yellow]")
    
    console.print("[green]✓ Done[/green]\n")
    return response


def run_agent_fast(user_query: str) -> str:
    """
    Fast mode: Uses only keyword detection (no VLM confirmation).
    Faster but slightly less accurate.
    """
    return run_agent(user_query)


def run_agent_with_screenshot(user_query: str) -> str:
    """
    Force screenshot capture regardless of detection.
    Use when you always want visual context.
    """
    console.print(f"\n[bold cyan]🤖 Processing (forced screenshot):[/bold cyan] {user_query}")
    
    # Always capture screenshot
    console.print("[dim]📸 Capturing screen...[/dim]")
    screenshot = None
    image_path = None
    try:
        screenshot = capture_screen()
        # Save to disk
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = os.path.join(IMAGE_STORAGE_PATH, filename)
        screenshot.save(save_path)
        image_path = save_path
        console.print(f"[green]✓ Screenshot captured & saved[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed: {e}[/red]")
    
    # Load context explicitly since we bypassed _gather_data for the screenshot part
    context = ""
    try:
        context = retrieve_recent_context(user_query, n=3)
    except Exception:
        pass
    
    # Generate response
    console.print("[dim]💭 Generating response...[/dim]")
    response = _query_vlm_final(screenshot, user_query, context)
    
    try:
        save_interaction(user_query, response, image_path=image_path)
    except Exception:
        pass
    
    console.print("[green]✓ Done[/green]\n")
    return response


if __name__ == "__main__":
    # Test the decision system
    test_queries = [
        "What's on my screen?",
        "Hello, how are you?",
        "What did we talk about earlier?",
        "Read the text in this window",
        "Tell me a joke",
    ]
    
    console.print("[bold]Testing Decision System[/bold]\n")
    
    for query in test_queries:
        console.print(f"\n{'='*50}")
        console.print(f"[bold]Query:[/bold] {query}")
        
        kw_s, kw_c = _quick_keyword_check(query)
        console.print(f"  Keywords: screenshot={kw_s}, context={kw_c}")
        
        if kw_s or kw_c:
            decision = _ask_vlm_decision(query)
            console.print(f"  VLM Decision: {decision}")
