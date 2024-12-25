from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message, File
from responses import get_response

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
load_dotenv()
TOKEN: Final[str] = 'MTMyMTA0MjYzODQwNDg0NTU4OA.GxYDl2.QUwkr8GIHDBkOzP2iStPwAPaTipSIWsHsIPPIw'

# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True  # NOQA
client: Client = Client(intents=intents)

from pydantic import BaseModel
class ChatRequest(BaseModel):
    text: str
    image_path: str = None

# STEP 2: MESSAGE FUNCTIONALITY
async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty because intents were not enabled probably)')
        return

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]

    try:
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                image_path = f"./downloads/{attachment.filename}"
                chat_request = ChatRequest(text=user_message, image_path=image_path)
                response: str = get_response(chat_request)
        else :
            chat_request = ChatRequest(text=user_message)
            response: str = get_response(chat_request)

        await message.author.send(response) if is_private else await message.channel.send(response)
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
                # You can download the image if needed
                await attachment.save(f"./downloads/{attachment.filename}")
                print(f"Image saved as ./downloads/{attachment.filename}")
                
    await send_message(message, user_message)

# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)


if __name__ == '__main__':
    main()


