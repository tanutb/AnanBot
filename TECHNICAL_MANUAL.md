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
This is the brain of the operation. It manages:
- **State**: Holds conversation history (`deque`), user profiles (`JSON`), and ephemeral context.
- **RAG Loop**: Retrieves relevant past memories before generating a response.
- **Tool Use**: Detects intent tags (e.g., `{gen}`, `{edit}`, `{karma+}`) in the LLM's raw output and executes the corresponding Python functions.
- **Async Processing**: Handles response generation synchronously for speed, while offloading memory storage and summarization to background threads.

### 2. Memory Systems
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
- `CONTEXT_LENGTH_IMAGE` (Default: 2): How many previous images the bot can "see" in its history.
- `MAX_TOKENS_MEMORY`: Limit for the fact-extraction sub-agent.
- `THRESHOLD` (Default: 1.0): Distance threshold for RAG retrieval validity.

## 📂 Directory Structure

```
C:\Github\AnanBot
├── api.py                  # FastAPI Entrypoint
├── config.py               # Global Constants
├── discord_bot.py          # Discord Client
├── src
│   ├── multimodal.py       # Main Agent Class
│   ├── gemini_vision.py    # Image Generation Logic
│   └── ...
├── memories\               # Persistent Data (GitIgnored recommended)
│   ├── chroma.db\          # Vector Store
│   ├── images\             # Generated/Saved Images
│   ├── karma.json          # User Profiles
│   └── chat_history.json   # JSON Chat Logs
└── utils
    └── responses.py        # Helper to bridge API <-> Bot
```
