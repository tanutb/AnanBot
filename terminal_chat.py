import asyncio
import os
import sys
import base64
from colorama import Fore, Style, init
from src.multimodal import Multimodal

# Initialize colorama
init(autoreset=True)

async def main():
    print(Fore.CYAN + Style.BRIGHT + """
    ========================================
       AnanBot Terminal Interface (Test)
    ========================================
    """ + Style.RESET_ALL)
    
    # Initialize Agent with Debug Mode ON
    print(Fore.YELLOW + "Initializing Multimodal Agent..." + Style.RESET_ALL)
    agent = Multimodal(debug=True)
    user_id = "terminal_tester"
    username = "TerminalUser"
    
    print(Fore.GREEN + "Ready! Type 'exit' or 'quit' to stop.")
    print(Fore.GREEN + "Commands:")
    print(Fore.GREEN + "  [img:path/to/image.jpg] Message   -> Send image")
    print(Fore.GREEN + "  [tag] Message                     -> Simulate tagging the bot (Aggressive Mode)")
    
    while True:
        try:
            user_input = input(Fore.BLUE + Style.BRIGHT + "\nYou: " + Style.RESET_ALL).strip()
        except EOFError:
            break
            
        if user_input.lower() in ["exit", "quit"]:
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            break
            
        if not user_input:
            continue

        # Parse inputs
        image_path = None
        is_mentioned = False
        text_input = user_input
        
        # Check for tag
        if "[tag]" in text_input:
            is_mentioned = True
            text_input = text_input.replace("[tag]", "").strip()

        # Check for image
        if text_input.startswith("[img:") and "]" in text_input:
            end_idx = text_input.find("]")
            image_path = text_input[5:end_idx].strip()
            text_input = text_input[end_idx+1:].strip()
            
            if not os.path.exists(image_path):
                print(Fore.RED + f"Error: Image file '{image_path}' not found." + Style.RESET_ALL)
                continue
        
        print(Fore.MAGENTA + "AnanBot is thinking..." + Style.RESET_ALL)
        
        # Run blocking call in a thread
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: agent.generate_text(
                text_input, 
                image_path, 
                user_id=user_id, 
                username=username, 
                is_mentioned=is_mentioned
            )
        )
        
        # Display Response
        print(Fore.CYAN + Style.BRIGHT + f"{agent.model_name}: " + Style.RESET_ALL + response["response"])
        
        if "img" in response:
            filename = f"generated_{len(agent.get_user_history(user_id))}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(response["img"]))
            print(Fore.YELLOW + f"  [Image Saved to {filename}]" + Style.RESET_ALL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")