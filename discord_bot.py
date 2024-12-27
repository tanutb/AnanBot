from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message, File
from utils.responses import get_response
import base64
from PIL import Image
from io import BytesIO
from utils import ChatRequest
from config import DISCORD_TOKEN

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
load_dotenv()
TOKEN: Final[str] = DISCORD_TOKEN

# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True  # NOQA
client: Client = Client(intents=intents)

# STEP 2: MESSAGE FUNCTIONALITY
async def send_message(message: Message, user_message: str) -> None:

    if user_message :
        if is_private := user_message[0] == '?':
            user_message = user_message[1:]
    else :
        is_private = False
    try:
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                image_path = f"./downloads/{attachment.filename}"
                if user_message:
                    mtext = "What is this image about? if it's have text Extracted describe it."
                else : 
                    mtext = user_message
                chat_request = ChatRequest(text=mtext, image_path=image_path)
                response: str = get_response(chat_request)
        else :
            chat_request = ChatRequest(text=user_message)
            response: str = get_response(chat_request)

        if is_private:
            if isinstance(response, dict) and "response" in response and "img" in response:
                image_data = base64.b64decode(response['img'])
                image = Image.open(BytesIO(image_data))
                # Save the image to a BytesIO object
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                # Send the image as a file
                await message.author.send(response["response"])
                await message.author.send(file=File(image_bytes, filename='image.png'))
            else:
                await message.author.send(response["response"])
        else:
            if isinstance(response, dict) and "response" in response and "img" in response:
                
                image_data = base64.b64decode(response['img'])
                image = Image.open(BytesIO(image_data))
                # Save the image to a BytesIO object
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                # Send the image as a file
                await message.channel.send(response["response"])
                await message.channel.send(file=File(image_bytes, filename='image.png'))
            else:
                await message.channel.send(response["response"])
            
    except Exception as e:
        print(e)


# STEP 3: HANDLING THE STARTUP FOR OUR BOT
@client.event
async def on_ready() -> None:
    print(f'{client.user} is now running!')


# STEP 4: HANDLING INCOMING MESSAGES
@client.event
async def on_message(message: Message) -> None:
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    username: str = str(message.author)
    user_message: str = message.content
    channel: str = str(message.channel)

    print(f'[{channel}] {username}: "{user_message}"')

    # Check if the message contains attachments
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                print(f"Image received from {username}: {attachment.url}")
                # Create the downloads directory if it doesn't exist
                os.makedirs("./downloads", exist_ok=True)
                # You can download the image if needed
                await attachment.save(f"./downloads/{attachment.filename}")
                print(f"Image saved as ./downloads/{attachment.filename}")
                
    await send_message(message, user_message)

# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)


if __name__ == '__main__':
    main()


