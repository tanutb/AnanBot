# Real-Time Screen Capture and VLM Agent Architecture

This document outlines the architecture for a real-time agent that captures the screen, transcribes user voice commands, and uses a Vision Language Model (VLM) to answer questions based on the visual context.

## Core Components

The agent will be composed of several key modules that work together:

1.  **`main.py` - Orchestrator:**
    *   The main entry point of the application.
    *   It contains the primary loop that listens for a user trigger (e.g., a hotkey).
    *   It coordinates the workflow between all other modules.

2.  **`config.py` - Configuration:**
    *   A centralized place to store all settings.
    *   This includes API endpoints for the VLM, hotkey configurations, audio device settings, and other constants.

3.  **`src/screen_capture.py` - Screen Capture Module:**
    *   Responsible for capturing the user's screen.
    *   It will have a function to grab a screenshot and return it as an image object (e.g., a PIL Image).
    *   This module will use efficient libraries like `mss` and `Pillow` for low-latency capture.

4.  **`src/stt.py` - Speech-to-Text (STT) Module:**
    *   Handles capturing audio from the user's microphone and transcribing it into text.
    *   It will listen for a user's voice command after the trigger hotkey is pressed.
    *   We will use a library like `SpeechRecognition` which supports various STT engines (Google, Whisper, etc.).

5.  **`src/vlm_client.py` - VLM API Client:**
    *   This module is responsible for communicating with your custom VLM model deployed with vLLM.
    *   It will contain a function that takes a screenshot and a text query as input.
    *   It will then format and send an API request (HTTP POST) to the vLLM endpoint.
    *   It will handle the response from the API and return the VLM's text answer.

6.  **`src/tts.py` - Text-to-Speech (TTS) Module:**
    *   Converts the text response from the VLM into audible speech.
    *   This provides a more natural, agent-like interaction.
    *   Libraries like `gTTS` or `pyttsx3` will be used to generate and play the audio.

## High-Level Workflow

The agent will operate based on the following sequence of events:

1.  The user presses a pre-configured hotkey.
2.  The **Orchestrator** (`main.py`) detects the hotkey press.
3.  It immediately calls the **Screen Capture Module** to take a screenshot of the current screen.
4.  Simultaneously, it activates the **STT Module** to listen for the user's spoken query.
5.  Once the user finishes speaking, the STT module transcribes the audio into a text string.
6.  The orchestrator then sends the captured screenshot and the transcribed text to the **VLM API Client**.
7.  The VLM client sends the data to the vLLM endpoint and receives a text response.
8.  This response is passed to the **TTS Module**, which converts the text to speech and plays it back to the user.
9.  The agent returns to a waiting state, ready for the next hotkey press.

## Project Structure

The project will be organized into the following directory structure:

```
.
├── src/
│   ├── screen_capture.py
│   ├── stt.py
│   ├── vlm_client.py
│   └── tts.py
├── utils/
│   └── ...
├── main.py
├── config.py
├── requirements.txt
└── architecture.md
```
