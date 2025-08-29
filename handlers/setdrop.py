# handlers/setdrop.py

import sqlite3
from pyrogram import filters
from pyrogram.types import Message
from config import Config, app

DB_PATH = "waifu_bot.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Ensure current_drops table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS current_drops (
    chat_id INTEGER PRIMARY KEY,
    waifu_id INTEGER,
    collected_by INTEGER DEFAULT NULL
)
""")
conn.commit()

# In-memory drop counter
drop_settings = {}  # {chat_id: {"target": int, "count": int}}

# ---------------- /setdrop Command ----------------
@app.on_message(filters.command("setdrop") & filters.group, group=1)
async def set_drop(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Validate input
    try:
        target_msg = int(message.text.split(" ", 1)[1])
    except (IndexError, ValueError):
        await message.reply_text("❌ Usage: /setdrop <number_of_messages>")
        return

    # -------- Proper Limits --------
    if user_id == Config.OWNER_ID:
        if target_msg < 1:
            await message.reply_text("👑 Owner can set drop to minimum 1 message.")
            return
    elif user_id in Config.ADMINS:
        if target_msg < 20:
            await message.reply_text("⚠️ Admins cannot set drop below 20 messages.")
            return
    else:
        if target_msg < 60:
            await message.reply_text("⚠️ Normal users cannot set drop below 60 messages.")
            return

    # Set drop
    drop_settings[chat_id] = {"target": target_msg, "count": 0}
    await message.reply_text(f"✅ Card drop set! A random card will drop after {target_msg} messages in this group.")

# ---------------- Message Tracker ----------------
@app.on_message(filters.group, group=2)  # lower priority, runs after /start
async def drop_tracker(client, message: Message):
    chat_id = message.chat.id

    # Ignore service messages
    if message.service:
        return

    # Ignore commands so /start and other commands are not blocked
    if message.text and message.text.startswith("/"):
        return

    if chat_id not in drop_settings:
        return

    drop_settings[chat_id]["count"] += 1
    if drop_settings[chat_id]["count"] < drop_settings[chat_id]["target"]:
        return

    # Reset counter
    drop_settings[chat_id]["count"] = 0

    # Select random card
    try:
        cursor.execute("""
            SELECT id, name, anime, rarity, event, media_type, media_file
            FROM waifu_cards
            ORDER BY RANDOM() LIMIT 1
        """)
        card = cursor.fetchone()
        if not card:
            return
    except Exception as e:
        print(f"❌ Error fetching card: {e}")
        return

    # Save drop
    cursor.execute(
        "INSERT OR REPLACE INTO current_drops (chat_id, waifu_id, collected_by) VALUES (?, ?, NULL)",
        (chat_id, card[0])
    )
    conn.commit()

    # Send drop message
    drop_text = "🎉 A new waifu card has appeared! 🎴\nType /collect <name> to claim it before someone else!"
    try:
        if card[5] == "photo":
            await message.reply_photo(card[6], caption=drop_text)
        else:
            await message.reply_video(card[6], caption=drop_text)
    except Exception as e:
        print(f"❌ Failed to send drop: {e}")
