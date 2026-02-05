from typing import Final
import os
import requests
from dotenv import load_dotenv
from discord import Intents, Client, Message, File, ChannelType, Embed, Color, Interaction, app_commands
from utils.responses import get_response, get_user_profile_data
import base64
from PIL import Image
from io import BytesIO
from utils import ChatRequest
from config import DISCORD_TOKEN

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True  # NOQA
client: Client = Client(intents=intents)
tree = app_commands.CommandTree(client)

# STEP 2: MESSAGE FUNCTIONALITY
async def send_message(message: Message, user_message: str, is_mentioned: bool) -> None:
    user_id = str(message.author.id)
    username = str(message.author.display_name)

    try:
        image_paths = []
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                    # Use the path where on_message saved it, or save it here if not saved (on_message saves it)
                    # We assume on_message saved it to ./downloads/filename
                    # To be safe, let's just use the path logic consistent with on_message
                    path = f"./downloads/{attachment.filename}"
                    image_paths.append(path)
        
        mtext = user_message
        if image_paths and not user_message:
             mtext = "What is this image about?"
             
        chat_request = ChatRequest(
            text=mtext, 
            image_paths=image_paths, 
            user_id=user_id,
            username=username,
            is_mentioned=is_mentioned
        )
        response: str = get_response(chat_request)

        # Handle Response (Always to channel)
        target = message.channel

        if isinstance(response, dict) and "response" in response:
            text_response = response["response"]
            
            if "img" in response and response["img"]:
                # Decode and send image
                image_data = base64.b64decode(response['img'])
                image_bytes = BytesIO(image_data)
                
                await target.send(text_response)
                await target.send(file=File(image_bytes, filename='generated_image.png'))
            else:
                await target.send(text_response)
        else:
             await target.send(str(response))
            
    except Exception as e:
        print(e)


# STEP 3: HANDLING THE STARTUP FOR OUR BOT
@client.event
async def on_ready() -> None:
    await tree.sync()
    print(f'{client.user} is now running!')

@tree.command(name="profile", description="Check your Karma and Persona summary")
async def profile_command(interaction: Interaction):
    user_id = str(interaction.user.id)
    username = str(interaction.user.display_name)
    
    await interaction.response.defer() # Defer in case API is slow
    
    data = get_user_profile_data(user_id)
    
    if "error" in data:
        await interaction.followup.send(data["error"])
        return

    score = data.get("score", 0)
    summary = data.get("summary", "No summary yet.")
    
    embed = Embed(title=f"User Profile: {username}", color=Color.gold())
    embed.add_field(name="Karma Score", value=str(score), inline=False)
    embed.add_field(name="Persona Summary", value=summary, inline=False)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    await interaction.followup.send(embed=embed)


# STEP 4: HANDLING INCOMING MESSAGES
@client.event
async def on_message(message: Message) -> None:
    # 1. Ignore messages from the bot itself
    if message.author == client.user:
        return
    
    # 2. Ignore Private Messages (DMs)
    if message.guild is None:
        return

    # COMMAND: !profile (Get Karma & Persona) - Fallback/Legacy
    if message.content.strip().lower() == "!profile":
        user_id = str(message.author.id)
        username = str(message.author.display_name)
        
        data = get_user_profile_data(user_id)
        
        if "error" in data:
            await message.channel.send(data["error"])
            return

        score = data.get("score", 0)
        summary = data.get("summary", "No summary yet.")
        
        embed = Embed(title=f"User Profile: {username}", color=Color.gold())
        embed.add_field(name="Karma Score", value=str(score), inline=False)
        embed.add_field(name="Persona Summary", value=summary, inline=False)
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
        
        await message.channel.send(embed=embed)
        return

    # 3. Check if Bot is Mentioned or Replied to
    is_mentioned = client.user in message.mentions
    is_reply = (message.reference is not None and message.reference.resolved and message.reference.resolved.author == client.user)
    
    # "is_mentioned" flag for the model (True if tagged OR replied to)
    is_targeted = is_mentioned or is_reply

    username: str = str(message.author)
    user_message: str = message.content
    channel: str = str(message.channel)

    print(f'[{channel}] {username}: "{user_message}" (Tagged: {is_targeted})')

    # 4. Clean the Message: Remove the bot's mention tag <@ID> if present
    if is_mentioned:
        # Remove the mention string (e.g. <@123456789>)
        user_message = user_message.replace(f'<@{client.user.id}>', '').strip()
        # Also handle nickname mentions <@!ID>
        user_message = user_message.replace(f'<@!{client.user.id}>', '').strip()

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
                
    await send_message(message, user_message, is_targeted)

# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)


if __name__ == '__main__':
    main()