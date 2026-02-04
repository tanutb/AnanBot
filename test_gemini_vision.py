import os
import base64
from src.gemini_vision import generate_image, edit_image
from dotenv import load_dotenv

load_dotenv()

def save_b64_image(b64_str, filename):
    with open(filename, "wb") as f:
        f.write(base64.b64decode(b64_str))
    print(f"Saved {filename}")

def test_generation():
    print("Testing Image Generation...")
    prompt = "A cute robot holding a flower, cyberpunk style"
    result = generate_image(prompt)
    
    if result and "images" in result:
        save_b64_image(result["images"][0], "test_gen_output.png")
        return result["images"][0]
    else:
        print("Generation Failed")
        return None

def test_editing(base64_img):
    print("\nTesting Image Editing...")
    if not base64_img:
        print("Skipping edit test due to generation failure")
        return

    prompt = "Make the robot hold a sword instead of a flower"
    result = edit_image(base64_img, prompt)
    
    if result and "images" in result:
        save_b64_image(result["images"][0], "test_edit_output.png")
    else:
        print("Editing Failed")

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in environment.")
    else:
        generated_b64 = test_generation()
        test_editing(generated_b64)
