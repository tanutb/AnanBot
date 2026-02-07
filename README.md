# 🤖 AnanBot: Advanced Multimodal AI Agent

**AnanBot** is a cutting-edge, personality-driven AI agent capable of understanding text and images, remembering past interactions, and generating creative visual content. Built on **Google Gemini**, **ChromaDB**, and **FastAPI**, it bridges the gap between static chatbots and evolving digital companions.

## 🚀 Key Features

### 🧠 **Multimodal Intelligence**
- **See & Understand**: Analyzes images and text seamlessly using Google's Gemini 1.5 Pro/Flash models.
- **Contextual Awareness**: Maintains conversation history to provide relevant and coherent responses.

### 💾 **Infinite Memory (RAG)**
- **Long-term Recall**: Utilizes **ChromaDB** to store and retrieve specific facts about users (e.g., "You remember I like pizza").
- **Adaptive Persona**: Dynamically updates a summary of the user's personality and preferences after every interaction.

### 🛠️ **Developer Tools (Debug Mode)**
- **Real-time Insights**: Toggle debug mode to see a detailed "Debug Profile" appended to every response.
- **Transparency**: View the exact RAG context used, history depth, raw model output, and specific actions taken (e.g., "Gen Image", "Karma +1").
- **Console Mirroring**: Debug logs are printed to both the chat interface and the server console for easy monitoring.

### 🎨 **Visual Creativity (Image Workflow)**
- **Image Generation**: Detects `{gen}` intent to create stunning visuals on the fly.
- **Image Editing**: Detects `{edit}` intent to modify existing images. **Strict Source Control**: Prioritizes explicit user input/replies. If no input is provided, falls back to the *single most recent* history image.
- **Powered by GEMINI NANO BANANA**: Utilizing the `gemini-3-pro-image-preview` model for high-fidelity synthesis.

### ⚡ **High-Performance Architecture**
- **Asynchronous Core**: Decoupled response generation from memory storage. Users get **instant replies** while the bot creates memories in the background.
- **Robust API**: Fully functional FastAPI backend with `BackgroundTasks` for optimal latency.

### ⚖️ **Karma & Behavior System**
- **Social Credit System**: Tracks user behavior (Karma). High karma leads to helpful responses; low karma triggers hostile/defensive traits.
- **Dynamic Personality**: The bot's attitude shifts based on who it's talking to.

---

## 🛠️ System Architecture

> 📘 **For a deep dive into the codebase, check out the [Technical Manual](TECHNICAL_MANUAL.md).**

### 1. General Processing Flow (Async Optimized)
AnanBot uses an asynchronous "Fire-and-Forget" memory model to ensure zero latency for the user.

```mermaid
graph LR
    User[User Input] --> API[FastAPI Endpoint]
    API --> Agent[Multimodal Agent]
    
    subgraph Core Components
        Agent --> Hist[HistoryManager]
        Agent --> Karma[KarmaManager]
        Agent --> RAG[MemoryEngine]
    end

    Agent -->|1. Generate| Response[Immediate Response]
    Response --> User
    
    API -.->|2. Background Task| RAG
    RAG -->|Extract Facts| LLM[Gemini Analyzer]
    RAG -->|Store Vectors| Chroma[ChromaDB]
    Karma -->|Update Profile| JSON[User Profile DB]
```

### 2. 🖼️ Picture & Image Workflow
How AnanBot handles visual requests:

```mermaid
graph TD
    A[User Request] -->|Analysis| B(Gemini Model)
    B --> C{Intent Detected?}
    
    C -- "{gen} cat" --> D[Generation Pipeline]
    D -->|Prompt| E[Gemini Nano Banana]
    E -->|New Image| F[Response with Image]
    
    C -- "{edit} make it blue" --> G[Editing Pipeline]
    G -->|Fetch Last Image| H[History/Disk]
    H -->|Img + Prompt| E
    
    C -- No Intent --> I[Standard Text Response]
```

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Google Cloud API Key (with access to Gemini 3 Pro Image Preview)

### Setup
1. **Clone the Repository**
   ```bash
   git clone https://github.com/tanutb/AnanBot.git
   cd AnanBot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   # Core
   GOOGLE_API_KEY=your_gemini_key_here
   DISCORD_TOKEN=your_discord_token_here
   
   # Model Settings
   GEMINI_MODEL_NAME=gemini-1.5-flash
   
   # Image Generation
   # No external URL needed for GEMINI NANO BANANA (Native Integration)
   ```

---

## 🎮 Usage

### 1. Discord Bot (Production Mode)
Run the bot to interact via Discord channels.
```bash
python discord_bot.py
```
**Commands:**
- `!profile`: Check your current Karma and Persona.
- `!debug on` / `!debug off`: Toggle detailed debug logging in chat.
- `/debug mode:True`: Slash command alternative for toggling debug mode.
- Reply to an image with "make it blue" to edit it instantly.

### 2. FastAPI Server (Backend Mode)
Start the API server for external integrations.
```bash
python api.py
```
*Docs available at `http://localhost:8119/docs`*

### 3. Terminal Chat (Debug Mode)
Test the agent directly in your console.
```bash
python terminal_chat.py
```

---

## ⚠️ Notes & Disclaimer
- **Image Generation**: Uses `gemini-3-pro-image-preview` which may have rate limits or access requirements.
- **Memory**: The first run will initialize the ChromaDB vector store.
- **Optimization**: We recently moved memory operations to background tasks. This massively improves perceived latency but means "memories" might take a few seconds to settle after a reply.

---

<p align="center">
    Made with ❤️ and excessive amounts of Caffeine.
</p>