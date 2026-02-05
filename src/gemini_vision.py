import os
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def _get_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not found.")
        return None
    return genai.Client(api_key=api_key)

def _generate_content(contents, prompt_desc):
    client = _get_client()
    if not client: 
        return None

    # Using the specific model requested by user
    model = "gemini-3-pro-image-preview"

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
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or not chunk.candidates
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            
            for part in chunk.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    generated_image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    break
            
            if generated_image_b64:
                break

        if generated_image_b64:
            return {"images": [generated_image_b64]}
        else:
            print("No image data found in response.")
            return None

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

def generate_image(prompt: str, **kwargs):
    """
    Generates a new image based on text prompt.
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

def edit_image(base64_images: list[str], prompt: str, **kwargs):
    """
    Edits existing image(s) based on text prompt.
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
