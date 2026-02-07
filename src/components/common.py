import os
import json
from colorama import Fore, Style, init

init(autoreset=True)

def log(section: str, message: str, color: str = Fore.WHITE, debug: bool = True) -> None:
    """Helper to print debug messages to the console.

    Args:
        section: The name of the section or component generating the log.
        message: The message to log.
        color: The Colorama color code for the section tag.
        debug: Whether to print the message (defaults to True).
    """
    if debug:
        print(f"{color}[{section.upper()}]{Style.RESET_ALL} {message}")

def load_json(filepath: str) -> dict:
    """Loads JSON data from a file.

    Args:
        filepath: The path to the JSON file.

    Returns:
        A dictionary containing the loaded JSON data, or an empty dict if loading fails.
    """
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log("ERROR", f"Failed to load {filepath}: {e}", Fore.RED)
            return {}
    return {}

def save_json(filepath: str, data: dict) -> None:
    """Saves data to a JSON file.

    Args:
        filepath: The path to the JSON file.
        data: The dictionary to save.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("ERROR", f"Failed to save {filepath}: {e}", Fore.RED)
