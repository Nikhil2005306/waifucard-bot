# handlers/start.py

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config, app
from database import Database
from datetime import datetime
import os

db = Database()

# Paths for images
LOG_IMAGE_PATH = "log.jpg"          # For user log
WELCOME_IMAGE_PATH = "welcome.jpg"  # For welcome message
GROUP_LOG_IMAGE = "photo_2025-08-22_11-52-42.jpg"   # For group log

# ------------------- USER START -------------------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    user_id = user.id
    username = user.username if user.username else "None"
    first_name = user.first_name if user.first_name else "Unknown"

    # Save user in DB
    db.add_user(user_id, username, first_name)

    # --------- One-time User Log (only in DM) ---------
    if message.chat.type == "private" and not db.is_first_logged(user_id):
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")

        caption = f"""
🌸 𝒩𝑒𝓌 𝒰𝓈𝑒𝓇 𝒥𝑜𝒾𝓃𝑒𝒹! 🌸

👤 Name: {first_name}
🏷️ Username: @{username}
🆔 ID: {user_id}

📅 Date: {date_str}
⏰ Time: {time_str}
"""

        try:
            if os.path.exists(LOG_IMAGE_PATH):
                await client.send_photo(
                    chat_id=Config.SUPPORT_CHAT_ID,
                    photo=LOG_IMAGE_PATH,
                    caption=caption
                )
            else:
                await client.send_message(
                    chat_id=Config.SUPPORT_CHAT_ID,
                    text=caption
                )
            db.set_first_logged(user_id)
        except Exception as e:
            print(f"❌ Failed to send user log: {e}")

    # --------- Welcome Message (DM or Group) ---------
    welcome_text = f"""
🌸 𝒲𝑒𝓁𝒸𝑜𝓂𝑒, 𝒟𝒶𝓇𝓁𝒾𝓃𝑔! 🌸

🍰 You’ve been warmly greeted by **Alisa Mikhailovna Kujou** 💕

👤 **User Info**:
🌸 Name: {first_name}
🏷️ Username: @{username}
🆔 ID: {user_id}

📜 **Available Commands:**
Type /help to explore 🎀

✨ “Let’s collect waifus and build memories together~” 💫
"""

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add me to Group", url=f"https://t.me/{Config.BOT_USERNAME}?startgroup=true")],
        [
            InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP),
            InlineKeyboardButton("📢 Support Channel", url=Config.UPDATE_CHANNEL)
        ],
        [InlineKeyboardButton("👑 Owner", url=f"https://t.me/{Config.OWNER_USERNAME.strip('@')}")]
    ])

    if os.path.exists(WELCOME_IMAGE_PATH):
        await message.reply_photo(
            photo=WELCOME_IMAGE_PATH,
            caption=welcome_text,
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            text=welcome_text,
            reply_markup=buttons
        )

# ------------------- GROUP LOG -------------------
@app.on_chat_member_updated()
async def bot_added_to_group(client, event):
    """
    Triggered when bot is added to a group
    Works with Pyrogram v1
    """
    try:
        if event.new_chat_member and event.new_chat_member.user.id == client.me.id:
            # Bot was added to a group
            chat = event.chat
            db.add_group(chat.id, chat.title)

            now = datetime.now()
            date_str = now.strftime("%d/%m/%Y")
            time_str = now.strftime("%H:%M:%S")

            caption = f"""
🌸 𝒩𝑒𝓌 𝒢𝓇𝑜𝓊𝓅 𝐴𝒹𝒹𝑒𝒹! 🌸

📛 Group: {chat.title}
🆔 ID: {chat.id}

📅 Date: {date_str}
⏰ Time: {time_str}
"""

            if os.path.exists(GROUP_LOG_IMAGE):
                await client.send_photo(
                    chat_id=Config.SUPPORT_CHAT_ID,
                    photo=GROUP_LOG_IMAGE,
                    caption=caption
                )
            else:
                await client.send_message(
                    chat_id=Config.SUPPORT_CHAT_ID,
                    text=caption
                )

    except Exception as e:
        print(f"❌ Failed to log group add: {e}")
