# # src/tts.py
# from f5_tts_th.tts import TTS
# import soundfile as sf
# from rich.console import Console
# import tempfile
# import os
# import re
# import numpy as np

# # Create a global console object for rich printing
# console = Console()

# # Initialize Thai TTS model (v1 recommended for best Thai pronunciation)
# tts = TTS(model="v1") 
# # v1: Pronounces Thai more accurately. v2: Reduces word mispronunciations via IPA.

# def clean_text_for_tts(text):
#     """
#     Removes any characters from the text that the TTS system cannot process.
#     Keeps only Thai characters, spaces, and basic punctuation.
#     """
#     # Allow Thai chars, whitespace, punctuation, digits, quotes, etc.
#     return ''.join(
#         c for c in text
#         if re.match(r"[ก-๙\u0E00-\u0E7F\s.,?()\[\]\"'«»:;0-9\-]", c)
#     )

# def say(
#     text, 
#     ref_audio=r"C:\Github\AnanBot\Recording (22).m4a", 
#     ref_text="ได้รับข่าวคราวของเราที่จะหาที่มันเป็นไปที่จะจัดขึ้น.", 
#     step=32, 
#     cfg=1.7, 
#     speed=1.5
# ):
#     """
#     Speaks the given text using f5_tts_th TTS and plays the audio.
#     Args:
#         text (str): The text to be spoken.
#         ref_audio (str, optional): Path to reference audio for speaker imitation. If None, use default.
#         ref_text (str, optional): Reference transcript for speaker imitation. If None, use text.
#         step (int): Number of diffusion steps.
#         cfg (float): CFG scale.
#         speed (float): Speed ratio (1.0 = normal).
#     """

#     console.print(f"[yellow]TEXT : {text}.[/yellow]")
#     safe_text = clean_text_for_tts(text)
#     if safe_text != text:
#         console.print(f"[yellow]Warning: Some characters were removed for TTS compatibility.[/yellow]")

#     # When ref_audio is provided, ref_text MUST also be provided (cannot be None)!
#     # If only ref_audio or only ref_text is provided, fallback to None for both to avoid library crash.
#     use_ref = ref_audio is not None and ref_text is not None
#     ref_audio_infer = ref_audio if use_ref else None
#     ref_text_infer = ref_text if use_ref else None

#     wav = tts.infer(
#         ref_audio=ref_audio_infer,  # None by default or if either is missing
#         ref_text=ref_text_infer if ref_text_infer is not None else safe_text,  # fallback to safe_text if not using ref
#         gen_text=safe_text,
#         step=step,
#         cfg=cfg,
#         speed=speed
#     )

#     # Ensure wav is at least 1D or 2D (sf.write expects shape (num_samples,) or (num_samples, channels))
#     wav_np = np.array(wav)
#     if wav_np.ndim == 0:
#         raise ValueError("Audio output is empty or scalar; cannot write to file.")
#     if wav_np.ndim == 1:
#         # mono channel vector, fine
#         if wav_np.shape[0] == 0:
#             raise ValueError("Audio output is empty. Nothing to write.")
#     elif wav_np.ndim == 2:
#         # (num_samples, channels), fine
#         if wav_np.shape[0] == 0:
#             raise ValueError("Audio output has zero samples.")
#     else:
#         # More than 2D, squeeze and try again
#         wav_np = np.squeeze(wav_np)
#         if wav_np.ndim == 1:
#             if wav_np.shape[0] == 0:
#                 raise ValueError("Audio output is empty after squeezing.")
#         elif wav_np.ndim == 2:
#             if wav_np.shape[0] == 0:
#                 raise ValueError("Audio output is empty after squeezing.")
#         else:
#             raise ValueError(f"Audio output has unexpected shape after squeeze: {wav_np.shape}")

#     # Make sure for 1D output it's (num_samples,), for 2D it's (num_samples, channels)
#     # For a mono signal, explicitly make it 2D if you want, but sf.write accepts 1D also.
#     # For this, let's stay robust: sf.write wants 1D or 2D (n, ch)
#     # Write to a temporary wav file and play it
#     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
#         filename = tmp.name
#         sf.write(filename, wav_np, 24000)
#     try:
#         # Play with system audio player
#         if os.name == 'nt':  # Windows
#             import winsound
#             winsound.PlaySound(filename, winsound.SND_FILENAME)
#         else:
#             import subprocess
#             if os.system("which afplay > /dev/null 2>&1") == 0:
#                 subprocess.run(["afplay", filename])
#             elif os.system("which aplay > /dev/null 2>&1") == 0:
#                 subprocess.run(["aplay", filename])
#             elif os.system("which paplay > /dev/null 2>&1") == 0:
#                 subprocess.run(["paplay", filename])
#             else:
#                 console.print("[red]No known audio player found for your OS.[/red]")
#         console.print(f"[magenta]Agent says:[/magenta] {safe_text}")
#     finally:
#         if os.path.exists(filename):
#             os.remove(filename)

# if __name__ == '__main__':
#     # Example usage:
#     say("สวัสดี นี่คือการทดสอบระบบแปลงข้อความเป็นเสียงภาษาไทย")
#     say("ฉันคือเอเจนต์จับภาพหน้าจอแบบเรียลไทม์")


# src/tts.py
import pyttsx3
from rich.console import Console # Import Console

# Create a global console object for rich printing
console = Console()

def say(text):
    """
    Speaks the given text using the system's text-to-speech engine.

    Args:
        text (str): The text to be spoken.
    """
    engine = pyttsx3.init()
    engine.say(text)
    console.print(f"[magenta]Agent says:[/magenta] {text}")
    engine.runAndWait()

if __name__ == '__main__':
    # Example usage:
    say("Hello! This is a test of the text-to-speech system.")
    say("I am a real-time screen capture agent.")