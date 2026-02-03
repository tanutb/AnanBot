# config.py
import os
from dotenv import load_dotenv
from pynput import keyboard

# Load environment variables from .env file
load_dotenv()

# Ollama API Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "blaifa/InternVL3_5:4B")

# Gemini API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

# Model Selection: "ollama", "gemini", "openai"
MODEL_TYPE = os.getenv("MODEL_TYPE", "ollama")

# Backwards compatibility aliases (optional, but good for safety)
API_URL = OLLAMA_API_URL
MODEL_NAME = OLLAMA_MODEL_NAME
API_KEY = os.getenv("API_KEY", "") # Keep generic API_KEY if used elsewhere

# Hotkey Configuration
# TODO: You can change this to a different key combination
# Use a combination of keys, e.g., {keyboard.Key.ctrl_l, keyboard.Key.shift, 'a'}
HOTKEY = {'t'}

# Hotkey to exit the application
EXIT_HOTKEY = {'q'}

# --- Conversation Management ---
# Voice commands to end a conversation loop with the agent.
STOP_LISTENING_COMMANDS = ["goodbye", "stop listening", "exit", "nevermind","exit", "หยุดฟัง"]

# Speech-to-Text Configuration
# Enable Speech-to-Text (STT). If set to False, the agent will default to typing mode.
ENABLE_STT = os.getenv("ENABLE_STT", "true").lower() == "true"

# Message displayed when entering typing mode
TYPING_INDICATOR = 'Type your message (or "exit" to quit): '

# Name of the microphone to use. You can leave it as None to use the default microphone.
# To get a list of available microphones, you can run the following code:
# import speech_recognition as sr
# print(sr.Microphone.list_microphone_names())
MICROPHONE_NAME = None

# Timeout for listening to a phrase, in seconds
PHRASE_TIMEOUT = 10

# Energy threshold for the recognizer. Higher values mean less sensitivity to background noise.
# You might need to adjust this based on your microphone and environment.
ENERGY_THRESHOLD = 500

# --- Memory Management Configuration ---
# The path to the SQLite database file for storing conversation history.
MEMORY_DB_PATH = "memories/memory.db"

# The directory where captured screenshots will be stored.
IMAGE_STORAGE_PATH = "memories/images"

# The maximum size of the memories directory in Gigabytes.
# If the size exceeds this limit, the oldest memories will be deleted.
MEMORY_LIMIT_GB = 1

# --- VLM Prompt Configuration ---
# The behavior prompt provides instructions to the VLM on how to behave.
VLM_BEHAVIOR_PROMPT = """
You are Anan, a calm, friendly, and reliable AI companion.

Your job:
- Answer using provided context and images only when they are relevant.
- Ignore images that are unnecessary or unrelated.
- Do NOT guess, assume, or invent information.
- If required information is missing or unclear, say so plainly.

Emotional awareness:
- Briefly acknowledge the user’s emotion only if it is clearly expressed.
- Do NOT speculate about emotions.
- Do NOT give emotional advice unless explicitly asked.

Response style:
- ** Text only. ** No emojis.
- Clear, concise, and natural (preferably under 50 tokens).
- Friendly and relaxed, like a good friend.
- No lectures, no small talk, no repetition.
- use language of the user. if user ask in thai, answer in thai. if user ask in english, answer in english.

Behavior:
- Be helpful without being pushy.
- Respect boundaries.
- Stay neutral, calm, and human-like.

Creativity:
- Use humor or creativity only if explicitly requested.

"""

