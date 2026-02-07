import os
import base64
import uuid
from typing import Optional
from colorama import Fore
from src.components.common import log

class ImageHandler:
    def __init__(self, image_dir: str = "./memories/images") -> None:
        """Initializes the ImageHandler.

        Args:
            image_dir: Directory where images will be stored.
        """
        self.image_dir = image_dir
        os.makedirs(self.image_dir, exist_ok=True)

    def save_image_to_disk(self, b64_data: str) -> str:
        """Saves base64 image data to disk.

        Args:
            b64_data: The base64 encoded string of the image.

        Returns:
            The file path where the image was saved, or an empty string on failure.
        """
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

    def load_image_from_disk(self, path: str) -> Optional[str]:
        """Loads an image from disk and converts it to a base64 string.

        Args:
            path: The file path of the image to load.

        Returns:
            The base64 encoded string of the image, or None if loading fails.
        """
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            log("ERROR", f"Failed to load image from disk: {e}", Fore.RED)
            return None

    def encode_image(self, image_path: str) -> str:
        """Reads an image file from disk and encodes it as a base64 string.

        Args:
            image_path: The file path of the image.

        Returns:
            The base64 encoded string of the image.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
