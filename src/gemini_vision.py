import os
import base64
from typing import Optional, Dict, List, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
from config import VISION_MODEL_NAME

load_dotenv()

def _get_client() -> Optional[genai.Client]:
    """Initializes and returns the Gemini client using the API key from environment variables.

    Returns:
        Optional[genai.Client]: The initialized Gemini client, or None if the API key is missing.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not found.")
        return None
    return genai.Client(api_key=api_key)

def _generate_content(contents: List[types.Content], prompt_desc: str) -> Optional[Dict[str, Any]]:
    """Internal helper to generate image content using the Gemini API.

    Args:
        contents: A list of Content objects to send to the model.
        prompt_desc: A description of the prompt for logging purposes.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the generated image(s) or an error message.
            Returns None if the client cannot be initialized.
    """
    client = _get_client()
    if not client: 
        return None

    # Using the specific model requested by user
    model = VISION_MODEL_NAME

    # Configure for Image generation
    generate_content_config = types.GenerateContentConfig(
        response_modalities=[
            "IMAGE",
        ],
        safety_settings=[types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="OFF"
        ),types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="OFF"
        ),types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="OFF"
        ),types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="OFF"
        )],
    )

    print(f"Processing image request: {prompt_desc}")
    
    try:
        generated_image_b64 = None
        text_response = ""
        finish_reason = "UNKNOWN"
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            try:
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish_reason = chunk.candidates[0].finish_reason

                if (
                    chunk.candidates is None
                    or not chunk.candidates
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue
                
                for part in chunk.candidates[0].content.parts:
                    if part.text:
                        text_response += part.text
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        generated_image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                        # If we found an image, we can stop looking (unless we want multi-image)
                        break
                
                if generated_image_b64:
                    break
            except Exception as inner_e:
                print(f"Error processing chunk: {inner_e}")
                # Continue to next chunk if one fails, or break? Usually break.
                continue

        if generated_image_b64:
            return {"images": [generated_image_b64]}
        else:
            base_msg = text_response.strip() if text_response else "No image data found."
            error_msg = f"{base_msg} (Finish Reason: {finish_reason})"
            print(f"Generation failed. Model response: {error_msg}")
            return {"error": error_msg}

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {"error": str(e)}

def generate_image(prompt: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Generates a new image based on a text prompt.

    Args:
        prompt: The text description of the image to generate.
        **kwargs: Arbitrary keyword arguments (unused but accepted for compatibility).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the generated image(s) or an error message.
    """
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    return _generate_content(contents, f"Generate: {prompt}")

def edit_image(base64_images: List[str], prompt: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Edits existing image(s) based on a text prompt.

    Args:
        base64_images: A list of base64-encoded strings representing the images to edit.
        prompt: The text instructions for editing the image.
        **kwargs: Arbitrary keyword arguments (unused but accepted for compatibility).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the generated/edited image(s) or an error message.
    """
    parts = [types.Part.from_text(text=prompt)]
    
    for b64 in base64_images:
        parts.append(
            types.Part.from_bytes(
                data=base64.b64decode(b64), 
                mime_type="image/jpeg"
            )
        )

    contents = [
        types.Content(
            role="user",
            parts=parts,
        ),
    ]
    return _generate_content(contents, f"Edit: {prompt}")
