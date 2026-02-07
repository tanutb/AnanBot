from typing import Final
import os
import requests
import discord
from dotenv import load_dotenv
from discord import Intents, Message, File, ChannelType, Embed, Color, Interaction, app_commands
from utils.responses import get_response, get_user_profile_data, set_user_karma, set_bot_debug_mode
import base64
from PIL import Image
from io import BytesIO
from utils import ChatRequest
from config import DISCORD_TOKEN

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# STEP 1: BOT SETUP - Using SubclassPattern for Better Sync
class AnanBotClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        # We attach the tree to 'self'
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        # For production, you might want to sync globally (remove guild=...) 
        # but it takes up to an hour. For now, we sync globally on startup.
        print("Syncing commands globally...")
        await self.tree.sync()
        print("Commands synced!")

client = AnanBotClient()

# STEP 2: MESSAGE FUNCTIONALITY
async def send_message(message: Message, user_message: str, is_mentioned: bool) -> None:
    user_id = str(message.author.id)
    username = str(message.author.display_name)
    context_id = str(message.channel.id)

    try:
        image_paths = []
        
        # 1. Handle Reply Context (Images & Text)
        reply_context = ""
        if message.reference and message.reference.resolved:
            ref_msg = message.reference.resolved
            if isinstance(ref_msg, Message):
                reply_context = f"[Replying to {ref_msg.author.display_name}: \"{ref_msg.content}\"]\n"
                
                # Process images from the replied message
                if ref_msg.attachments:
                    for attachment in ref_msg.attachments:
                        if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                            # Use attachment ID to ensure uniqueness
                            filename = f"{attachment.id}_{attachment.filename}"
                            path = f"./downloads/{filename}"
                            await attachment.save(path)
                            image_paths.append(path)

        # 2. Handle Current Message Images
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                    # Use attachment ID to ensure uniqueness
                    filename = f"{attachment.id}_{attachment.filename}"
                    path = f"./downloads/{filename}"
                    await attachment.save(path)
                    image_paths.append(path)
        
        mtext = reply_context + user_message
        if image_paths and not user_message and not reply_context:
             mtext = "What is this image about?"
             
        chat_request = ChatRequest(
            text=mtext, 
            image_paths=image_paths, 
            user_id=user_id,
            context_id=context_id,
            username=username,
            is_mentioned=is_mentioned
        )
        response: str = get_response(chat_request)

        target = message.channel

        if isinstance(response, dict) and "response" in response:
            text_response = response["response"]
            
            if "img" in response and response["img"]:
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
    print(f'{client.user} is now running!')

# --- SLASH COMMANDS (Attached to client.tree) ---

@client.tree.command(name="debug", description="Toggle Debug Mode")
@app_commands.describe(mode="True/False or On/Off")
async def debug_command(interaction: Interaction, mode: str):
    await interaction.response.defer()
    
    is_on = mode.lower() in ["true", "on", "1", "yes"]
    result = set_bot_debug_mode(is_on)
    
    if "error" in result:
        await interaction.followup.send(f"❌ Failed: {result['error']}")
    else:
        status = "ON" if result.get("debug_mode") else "OFF"
        await interaction.followup.send(f"🔧 Debug Mode is now **{status}**")

@client.tree.command(name="profile", description="Check your Karma and Persona summary")
async def profile_command(interaction: Interaction):
    user_id = str(interaction.user.id)
    username = str(interaction.user.display_name)
    
    await interaction.response.defer()
    
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

@client.tree.command(name="setkarma", description="Set a user's Karma score (Admin/Debug)")
@app_commands.describe(user="The user to modify", score="The new karma score")
async def set_karma_command(interaction: Interaction, user: discord.User, score: int):
    user_id = str(user.id)
    username = user.display_name
    
    await interaction.response.defer()
    
    result = set_user_karma(user_id, score)
    
    if "error" in result:
        await interaction.followup.send(f"❌ Failed: {result['error']}")
    else:
        await interaction.followup.send(f"✅ Updated Karma for **{username}** to `{score}`.")

@client.tree.command(name="resetkarma", description="Reset a user's Karma score to 0")
@app_commands.describe(user="The user to reset")
async def reset_karma_command(interaction: Interaction, user: discord.User):
    user_id = str(user.id)
    username = user.display_name
    
    await interaction.response.defer()
    
    result = set_user_karma(user_id, 0)
    
    if "error" in result:
        await interaction.followup.send(f"❌ Failed: {result['error']}")
    else:
        await interaction.followup.send(f"🔄 Reset Karma for **{username}** to `0`.")


# STEP 4: HANDLING INCOMING MESSAGES
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    
    if message.guild is None:
        return

    # COMMAND: !debug <on/off>
    if message.content.strip().lower().startswith("!debug"):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!debug <on/off>`")
            return
            
        mode_str = parts[1].lower()
        is_on = mode_str in ["on", "true", "1", "yes"]
        
        result = set_bot_debug_mode(is_on)
        
        if "error" in result:
            await message.channel.send(f"❌ Failed: {result['error']}")
        else:
            status = "ON" if result.get("debug_mode") else "OFF"
            await message.channel.send(f"🔧 Debug Mode is now **{status}**")
        return

    # COMMAND: !profile
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

    # COMMAND: !setkarma @User <score>
    if message.content.strip().lower().startswith("!setkarma"):
        try:
            parts = message.content.split()
            if len(message.mentions) != 1 or len(parts) < 3:
                await message.channel.send("Usage: `!setkarma @User <score>`")
                return
            
            target_user = message.mentions[0]
            new_score = int(parts[-1])
            
            result = set_user_karma(str(target_user.id), new_score)
            
            if "error" in result:
                await message.channel.send(f"❌ Failed: {result['error']}")
            else:
                await message.channel.send(f"✅ Updated Karma for **{target_user.display_name}** to `{new_score}`.")
        except ValueError:
             await message.channel.send("❌ Error: Score must be an integer.")
        return

    # COMMAND: !resetkarma @User
    if message.content.strip().lower().startswith("!resetkarma"):
        if len(message.mentions) != 1:
            await message.channel.send("Usage: `!resetkarma @User`")
            return
            
        target_user = message.mentions[0]
        result = set_user_karma(str(target_user.id), 0)
        
        if "error" in result:
            await message.channel.send(f"❌ Failed: {result['error']}")
        else:
            await message.channel.send(f"🔄 Reset Karma for **{target_user.display_name}** to `0`.")
        return

    is_mentioned = client.user in message.mentions
    is_reply = (message.reference is not None and message.reference.resolved and message.reference.resolved.author == client.user)
    is_targeted = is_mentioned or is_reply

    username: str = str(message.author)
    user_message: str = message.content
    channel: str = str(message.channel)

    print(f'[{channel}] {username}: "{user_message}" (Tagged: {is_targeted})')

    if is_mentioned:
        user_message = user_message.replace(f'<@{client.user.id}>', '').strip()
        user_message = user_message.replace(f'<@!{client.user.id}>', '').strip()

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                print(f"Image received from {username}: {attachment.url}")
                os.makedirs("./downloads", exist_ok=True)
                await attachment.save(f"./downloads/{attachment.filename}")
                print(f"Image saved as ./downloads/{attachment.filename}")
                
    await send_message(message, user_message, is_targeted)

# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)

if __name__ == '__main__':
    main()
