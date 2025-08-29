# handlers/claim.py

import sqlite3
import random
import time
from pyrogram import filters
from pyrogram.types import Message
from config import app

# ---------------- Connect to your main DB ----------------
db = sqlite3.connect("waifu_bot.db", check_same_thread=False)
cursor = db.cursor()

# ---------------- Ensure user claims table exists ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_claims (
    user_id INTEGER PRIMARY KEY,
    last_claim INTEGER DEFAULT 0
)
""")
db.commit()

# ---------------- /claim Command ----------------
@app.on_message(filters.command("claim"))
async def claim_waifu(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name

    # Check cooldown
    cursor.execute("SELECT last_claim FROM user_claims WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    current_time = int(time.time())
    if row:
        last_claim = row[0]
        if current_time - last_claim < 86400:  # 24 hours cooldown
            remaining = 86400 - (current_time - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply_text(f"⏳ You already claimed a waifu! Come back in {hours}h {minutes}m.")
            return

    # Fetch all waifu cards from DB
    cursor.execute("SELECT id, name, anime, rarity, event, media_type, media_file FROM waifu_cards")
    waifus = cursor.fetchall()
    if not waifus:
        await message.reply_text("❌ No waifus available yet.")
        return

    # Pick a random waifu (ignore rarity)
    waifu = random.choice(waifus)
    waifu_id, name, anime, rarity, event, media_type, media_file = waifu

    # Update last claim time
    cursor.execute("INSERT OR REPLACE INTO user_claims (user_id, last_claim) VALUES (?, ?)", (user_id, current_time))
    db.commit()

    # ---------------- Prepare message ----------------
    profile_text = (
        f"🌸 Yay~ you caught a cutie! 🌸\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 𝐖𝐚𝐢𝐟𝐮 𝐈𝐃: {waifu_id}\n"
        f"✨ 𝐍𝐚𝐦𝐞: {name}\n"
        f"⛩️ 𝐀𝐧𝐢𝐦𝐞: {anime}\n"
        f"💖 𝐑𝐚𝐫𝐢𝐭𝐲: {rarity}\n"
        f"🎀 𝐄𝐯𝐞𝐧𝐭/𝐓𝐡𝐞𝐦𝐞: {event}\n"
        f"🕊️ 𝐂𝐥𝐚𝐢𝐦𝐞𝐝 𝐛𝐲: {username}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Next claim ready in 24h~ 💫🎀"
    )

    # Send waifu card
    if media_type == "photo":
        await message.reply_photo(media_file, caption=profile_text)
    else:
        await message.reply_video(media_file, caption=profile_text)
