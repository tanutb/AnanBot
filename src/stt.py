# src/stt.py
import speech_recognition as sr
from rich.console import Console # Import Console

# Create a global console object for rich printing
console = Console()

from config import MICROPHONE_NAME, ENERGY_THRESHOLD, PHRASE_TIMEOUT

def listen_for_command():
    """
    Listens for a command from the user's microphone and transcribes it to text.

    Returns:
        str: The transcribed text, or None if speech could not be recognized.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = ENERGY_THRESHOLD
    
    mic_index = None
    if MICROPHONE_NAME:
        mic_list = sr.Microphone.list_microphone_names()
        try:
            mic_index = mic_list.index(MICROPHONE_NAME)
        except ValueError:
            console.print(f"[yellow]Microphone '{MICROPHONE_NAME}' not found. Using default microphone.[/yellow]")
            
    with sr.Microphone(device_index=mic_index) as source:
        console.print("[green]Listening for your command...[/green]")
        recognizer.adjust_for_ambient_noise(source)
        
        try:
            audio = recognizer.listen(source, timeout=PHRASE_TIMEOUT, phrase_time_limit=PHRASE_TIMEOUT)
        except sr.WaitTimeoutError:
            console.print("[dim]No speech detected.[/dim]")
            return None
            
    try:
        console.print("[dim]Recognizing...[/dim]")
        # Using Google's speech recognition
        # text = recognizer.recognize_google(audio, language="th-TH") 
        text = recognizer.recognize_google(audio)

        console.print(f"[bold blue]You said:[/bold blue] {text}")
        return text
    except sr.UnknownValueError:
        console.print("[red]Google Speech Recognition could not understand audio.[/red]")
        return None
    except sr.RequestError as e:
        console.print(f"[bold red]Could not request results from Google Speech Recognition service; {e}[/bold red]")
        return None

if __name__ == '__main__':
    # Example usage: listen for a command and print it
    command = listen_for_command()
    if command:
        console.print(f"[green]Transcribed command:[/green] {command}")

