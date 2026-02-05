import os
import base64
import uuid
from colorama import Fore
from src.components.common import log

class ImageHandler:
    def __init__(self, image_dir: str = "./memories/images"):
        self.image_dir = image_dir
        os.makedirs(self.image_dir, exist_ok=True)

    def save_image_to_disk(self, b64_data: str) -> str:
        """Saves base64 image data to disk and returns the relative path."""
        try:
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            path = os.path.join(self.image_dir, filename)
            
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            
            return path
        except Exception as e:
            log("ERROR", f"Failed to save image to disk: {e}", Fore.RED)
            return ""

    def load_image_from_disk(self, path: str) -> str | None:
        """Loads image from disk and returns base64 string."""
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            log("ERROR", f"Failed to load image from disk: {e}", Fore.RED)
            return None

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
