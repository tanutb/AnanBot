import os
import json
from colorama import Fore, Style, init

init(autoreset=True)

def log(section: str, message: str, color=Fore.WHITE, debug: bool = True):
    """Helper to print debug messages."""
    if debug:
        print(f"{color}[{section.upper()}]{Style.RESET_ALL} {message}")

def load_json(filepath: str) -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log("ERROR", f"Failed to load {filepath}: {e}", Fore.RED)
            return {}
    return {}

def save_json(filepath: str, data: dict):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("ERROR", f"Failed to save {filepath}: {e}", Fore.RED)
