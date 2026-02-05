# 📘 AnanBot Technical Manual

This document provides a deep dive into the architecture, data flow, and component design of AnanBot. It is intended for developers contributing to the project or those wishing to understand the "ghost in the machine."

## 🏗️ High-Level Architecture

AnanBot is built as a **Modular Multimodal Agent**. It decouples the *interaction layer* (Discord/Terminal/API) from the *intelligence layer* (Core Agent).

```
[Interaction Layer]       [Intelligence Layer]           [Storage Layer]
     |                           |                             |
Discord Bot <----> API <---> Multimodal Agent <---> Memory Manager (ChromaDB/JSON)
     |             |             |                             |
Terminal Chat <----|             +----> Gemini API (Google)    +----> Images (Local Disk)
```

## 🧩 Core Components

### 1. The `Multimodal` Class (`src/multimodal.py`)
The `Multimodal` class acts as the central orchestrator. It has been refactored to delegate specific responsibilities to specialized components, ensuring a clean separation of concerns.

**Key Responsibilities:**
- **Orchestration**: Coordinates data flow between the API, the LLM, and various managers.
- **Intent Execution**: Detects specific intents (e.g., `{gen}`, `{edit}`, `{karma+}`) in the model's output and triggers the appropriate handlers.
- **Response Assembly**: Combines text responses with generated images and metadata before returning them to the caller.

### 2. Component Managers (`src/components/`)
The monolithic logic has been broken down into:

- **`MemoryEngine` (`memory_engine.py`)**:
    - Manages **ChromaDB** interactions.
    - Handles **RAG (Retrieval-Augmented Generation)**: Embeds queries using `text-embedding-004`, searches the vector store, and formats retrieved memories for context injection.
    - **Fact Extraction**: Uses a secondary LLM call to extract permanent facts from conversation turns.

- **`KarmaManager` (`karma_manager.py`)**:
    - Manages persistent user profiles (`karma.json`).
    - Tracks **Karma Scores** (influencing bot personality) and **Persona Summaries** (auto-updating descriptions of the user).

- **`HistoryManager` (`history_manager.py`)**:
    - Handles short-term memory (RAM-based `deque`).
    - Manages the context window (`HISTORY_MAXLEN`) for both text and images, ensuring the LLM receives the most relevant recent conversation history.

- **`ImageHandler` (`image_handler.py`)**:
    - Handles I/O operations for images.
    - Manages Base64 encoding/decoding and saving generated/uploaded images to disk (`./memories/images/`).

### 3. Memory Systems
AnanBot uses a **Tri-Layer Memory Architecture**:

| Layer | Type | Storage | Persistence | Purpose |
|-------|------|---------|-------------|---------|
| **Short-Term** | `deque` | RAM | Session-only | Holds the last `HISTORY_MAXLEN` messages for immediate context. |
| **Long-Term** | Vector | ChromaDB | Disk | Stores facts, preferences, and Q&A pairs. Retrieved via semantic search. |
| **Profile** | Structured | JSON | Disk | Tracks Karma scores, usernames, and a high-level "Persona Summary" (e.g., "User is a python dev who likes cats"). |

#### Memory Ingestion Flow
1. **Extraction**: After every turn, a dedicated LLM call extracts facts into `{qa} Question {answer} Answer` format.
2. **Vectorization**: Facts are embedded using `text-embedding-004`.
3. **Storage**: Vectors are pushed to ChromaDB with metadata (User ID, Timestamp).
4. **Summarization**: A separate LLM call updates the 100-word "Persona Summary" if the conversation warrants it.

### 3. Image Generation Pipeline (`src/gemini_vision.py`)
AnanBot has moved away from Stable Diffusion to a native **Gemini Nano Banana** workflow.

- **Generation (`{gen}`)**:
  - Uses `gemini-3-pro-image-preview`.
  - Prompts are fed directly from the agent's creativity.
  - Output is base64 encoded, saved to `./memories/images/`, and returned.

- **Editing (`{edit}`)**:
  - Requires a "Source Image".
  - The system looks for `MAX_USER_INPUT_IMAGES` in the current request.
  - If none are found, it looks back at `last_images` in the user's history.
  - Sends `[Image, Prompt]` to the model for pixel-level modification.

### 4. Karma System
A simplified social credit system that influences the bot's system prompt.
- **Storage**: `memories/karma.json`.
- **Thresholds**:
  - **< -5**: Activates "Hostile Mode" (refusals, insults).
  - **> +5**: Activates "Helpful Mode".
- **Dynamic Injection**: The user's current score and standing are injected into the System Prompt *before* every response generation.

## 🔌 API Specification (`api.py`)

The system exposes a FastAPI backend for external integrations.

### `POST /chat/`
Main interaction endpoint.
- **Input**:
  ```json
  {
    "text": "Hello bot",
    "image_paths": [],
    "user_id": "123",
    "username": "User",
    "is_mentioned": false
  }
  ```
- **Output**: JSON containing the text response and optionally a base64 encoded image.
- **Behavior**: Spawns a `BackgroundTasks` to handle memory storage, ensuring sub-second response times.

### `GET /user/{user_id}/details`
Debug endpoint to inspect a user's profile.
- **Output**:
  ```json
  {
    "score": 10,
    "summary": "A friendly developer...",
    "username": "Dev1"
  }
  ```

## ⚙️ Configuration & Constants

Key settings in `config.py`:
- `HISTORY_MAXLEN` (Default: 100): How many messages to keep in RAM.
- `CONTEXT_LENGTH_IMAGE` (Default: 3): How many previous images the bot can "see" in its history.
- `MAX_TOKENS_MEMORY`: Limit for the fact-extraction sub-agent.
- `THRESHOLD` (Default: 1.0): Distance threshold for RAG retrieval validity.

## 📂 Directory Structure

```
C:\Github\AnanBot
├── api.py                  # FastAPI Entrypoint
├── config.py               # Global Constants
├── discord_bot.py          # Discord Client
├── src
│   ├── multimodal.py       # Main Agent Orchestrator
│   ├── gemini_vision.py    # Image Generation Logic
│   ├── components\
│   │   ├── memory_engine.py   # RAG & Vector Store
│   │   ├── karma_manager.py   # User Profiles & Karma
│   │   ├── history_manager.py # Chat History (RAM)
│   │   ├── image_handler.py   # Image I/O Utils
│   │   └── common.py          # Shared Utilities
│   └── ...
├── memories\               # Persistent Data (GitIgnored recommended)
│   ├── chroma.db\          # Vector Store
│   ├── images\             # Generated/Saved Images
│   ├── karma.json          # User Profiles
│   └── chat_history.json   # JSON Chat Logs
└── utils
    └── responses.py        # Helper to bridge API <-> Bot
```
