# app.py
import gradio as gr
import requests
import base64
from PIL import Image
import io

# --- Configuration ---
# This should ideally be read from config.py or an environment variable,
# but we'll hardcode it here for simplicity in this standalone Gradio app.
VLM_API_URL = "http://127.0.0.1:8000/generate" 

# --- VLM Client Logic ---
# This is a simplified version of the logic from src/vlm_client.py
def query_vlm_api(image, text, history):
    """
    Sends a query to the VLM API with an image and a text prompt.

    Args:
        image (PIL.Image.Image): The screenshot image.
        text (str): The user's text query.
        history (list): The Gradio chat history.

    Returns:
        str: The text response from the VLM, or an error message.
    """
    if not image or not text:
        return "Please provide an image and a text query.", history

    # Create context from history
    context = "Conversation history:\n"
    for user_msg, assistant_msg in history:
        context += f"User asked: '{user_msg}'\nAgent responded: '{assistant_msg}'\n"
    
    full_prompt = f"{context}\nBased on the conversation and the new image, answer the question:\nUser: {text}"

    # Convert image to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    headers = {"Content-Type": "application/json"}
    payload = {
        "prompt": {
            "text": full_prompt,
            "images": [image_base64]
        },
        "max_tokens": 150,
        "temperature": 0.7
    }

    try:
        response = requests.post(VLM_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        vlm_response = response.json().get("text", "No text found in response.")
        history.append((text, vlm_response))
        return "", history
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error: {e}"
        return "", history + [(text, error_msg)]
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        return "", history + [(text, error_msg)]

# --- Gradio Interface ---
with gr.Blocks(theme=gr.themes.Soft(), title="VLM Agent Demo") as demo:
    gr.Markdown("# 🤖 Vision Language Model Agent Demo")
    gr.Markdown("This demo simulates the real-time agent. Upload a screenshot, ask a question, and see the VLM's response.")

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(type="pil", label="Screenshot")
            text_input = gr.Textbox(label="Your Question", placeholder="e.g., What is the main subject of this image?")
            submit_btn = gr.Button("Ask Agent", variant="primary")
        
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Conversation", height=500)
    
    # The action that runs when the button is clicked
    submit_btn.click(
        fn=query_vlm_api,
        inputs=[image_input, text_input, chatbot],
        outputs=[text_input, chatbot]
    )

    gr.Markdown("---")
    gr.Markdown("### How to Use:")
    gr.Markdown("1. **Start your vLLM server.** Make sure it's running and accessible at the URL configured in this app (`{}`).".format(VLM_API_URL))
    gr.Markdown("2. **Upload an image** that simulates a screen capture.")
    gr.Markdown("3. **Type your question** in the text box.")
    gr.Markdown("4. **Click 'Ask Agent'** to send the image and question to the VLM.")
    gr.Markdown("5. The conversation will appear in the chat window.")


if __name__ == "__main__":
    demo.launch()
