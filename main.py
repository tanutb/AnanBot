# main.py
import time
from pynput import keyboard
from rich.console import Console # Import Console
from config import HOTKEY, EXIT_HOTKEY, STOP_LISTENING_COMMANDS
from src.screen_capture import capture_screen
from src.stt import listen_for_command
from src.vlm_client import query_vlm
from src.tts import say
from src.memory_manager import prune_memory_if_needed
from src.orchestrator_agent import run_agent, run_agent_fast

# Create a global console object for rich printing
console = Console()


# --- State Management ---
# A set to keep track of currently pressed keys
pressed_keys = set()
# A flag to prevent the hotkey from being triggered multiple times
hotkey_pressed = False

def get_key_name(key):
    """
    Helper function to get a readable name for a key.
    """
    if hasattr(key, 'char'):
        return key.char
    return str(key).replace('Key.', '')

def on_press(key):
    """
    Callback function for when a key is pressed.
    Handles adding keys to `pressed_keys` and triggering hotkeys.
    """
    global hotkey_pressed

    # Add the key to our set of pressed keys
    if hasattr(key, 'char') and key.char is not None:
        pressed_keys.add(key.char)
    else:
        pressed_keys.add(key)

    console.print(f"[dim]Pressed keys: {pressed_keys}[/dim]")
    # Check for exit hotkey
    # Use a temporary set for comparison to handle key representation differences
    current_keys_for_exit_check = {k.char if hasattr(k, 'char') else k for k in pressed_keys}
    if EXIT_HOTKEY.issubset(current_keys_for_exit_check):
        console.print("\n[bold red]--- Exit hotkey pressed. Terminating agent. ---[/bold red]")
        say("Goodbye!")
        return False  # Stop the listener

    # Check for activation hotkey
    current_keys_for_activation_check = {k.char if hasattr(k, 'char') else k for k in pressed_keys}
    if not hotkey_pressed and HOTKEY.issubset(current_keys_for_activation_check):
        hotkey_pressed = True
        on_hotkey_activated()

def on_release(key):
    """
    Callback function for when a key is released.
    Handles removal of key from `pressed_keys` and resets `hotkey_pressed` flag.
    """
    global hotkey_pressed

    # Determine which representation of the key to remove
    key_to_remove = key.char if hasattr(key, 'char') and key.char is not None else key
    
    # Remove the key from our set
    if key_to_remove in pressed_keys:
        pressed_keys.remove(key_to_remove)
    # Also try removing the raw key object if it exists
    if key in pressed_keys:
        pressed_keys.remove(key)

    # Reset the hotkey_pressed flag
    current_keys_for_check = {k.char if hasattr(k, 'char') else k for k in pressed_keys}
    if hotkey_pressed and not HOTKEY.issubset(current_keys_for_check):
        hotkey_pressed = False

def on_hotkey_activated():
    """The main function to execute when the hotkey is pressed."""
    console.print("\n[bold green]--- Hotkey Activated! Starting Conversation ---[/bold green]")
    
    say("I'm listening...")
    
    # --- Start Conversation Loop ---
    while True:
        # 1. Listen for a voice command
        command = listen_for_command()
        
        if not command:
            say("I didn't catch that.")
            continue # Listen again

        # Check for stop commands
        if command.lower().strip() in STOP_LISTENING_COMMANDS:
            say("Goodbye!")
            break # Exit the conversation loop

        console.print(f"[bold blue]User asked:[/bold blue] '{command}'")

        # 2. Run the agent to get the final answer (also saves to memory)
        final_answer = run_agent(command)
        
        # 3. Speak the response
        say(final_answer)

        # 4. Prune memory if necessary
        prune_memory_if_needed(verbose=False)
        
    console.print("[bold red]--- Conversation Ended ---[/bold red]")

def main():
    """Main function to start the listener."""
    console.print("[bold yellow]Screen capture agent with memory is running...[/bold yellow]")
    
    # Convert hotkey set to a string for display
    activation_hotkey_str = ' + '.join([get_key_name(k) for k in HOTKEY])
    exit_hotkey_str = ' + '.join([get_key_name(k) for k in EXIT_HOTKEY])
    
    console.print(f"[green]Press {activation_hotkey_str} to activate.[/green]")
    console.print(f"[red]Press {exit_hotkey_str} to exit.[/red]")

    # Start listening for keyboard events
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
if __name__ == '__main__':
    main()
