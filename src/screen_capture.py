# src/screen_capture.py
import mss
from PIL import Image
import io
from rich.console import Console # Import Console

# Create a global console object for rich printing
console = Console()

def capture_screen():
    """
    Captures the primary monitor's screen and returns it as a PIL Image.

    Returns:
        PIL.Image.Image: The captured screen image.
    """
    with mss.mss() as sct:
        # Get information of monitor 1
        monitor_number = 1
        mon = sct.monitors[monitor_number]

        # Grab the data
        sct_img = sct.grab(mon)

        # Create an Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

def image_to_base64(image, max_size=2000):
    """
    Converts a PIL Image to a base64 encoded byte string.
    Resizes the image if either width or height exceeds max_size (default: 800 pixels).

    Args:
        image (PIL.Image.Image): The image to convert.
        max_size (int): The maximum dimension (width or height) allowed.

    Returns:
        bytes: The bytes of the PNG encoded image (not the string-encoded base64).
    """
    # Resize if needed so that neither dimension exceeds max_size, preserving aspect ratio
    width, height = image.size
    if max(width, height) > max_size:
        if width >= height:
            new_width = max_size
            new_height = int((max_size / width) * height)
        else:
            new_height = max_size
            new_width = int((max_size / height) * width)
        image = image.resize((new_width, new_height), Image.LANCZOS)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return buffered.getvalue()


if __name__ == '__main__':
    # Example usage: capture the screen and save it to a file
    try:
        screenshot = capture_screen()
        screenshot.save("screenshot.png")
        console.print("[cyan]Screenshot saved to screenshot.png[/cyan]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")

