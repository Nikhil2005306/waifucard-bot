# config.py

import os
from pyrogram import Client

class Config:
    # -------------------------------
    # Bot credentials from environment
    # -------------------------------
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment variables!")
    if not API_ID or not API_HASH:
        raise ValueError("API_ID and/or API_HASH are not set in environment variables!")

    # -------------------------------
    # Database
    # -------------------------------
    DB_PATH = os.environ.get("DB_PATH", "waifu_bot.db")  # default if not set

    # -------------------------------
    # Owner & Support details
    # -------------------------------
    OWNER_ID = int(os.environ.get("OWNER_ID", 7606646849))
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "7606646849,6398668820").split(",")]
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@Professornikhil")
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "https://t.me/Alisabotsupport")
    SUPPORT_CHAT_ID = int(os.environ.get("SUPPORT_CHAT_ID", "-1002669919337"))
    UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "https://t.me/AlisaMikhailovnaKujoui")
    
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "Waifusscollectionbot")

    # -------------------------------
    # Crystal Rewards
    # -------------------------------
    DAILY_CRYSTAL = int(os.environ.get("DAILY_CRYSTAL", 5000))
    WEEKLY_CRYSTAL = int(os.environ.get("WEEKLY_CRYSTAL", 25000))
    MONTHLY_CRYSTAL = int(os.environ.get("MONTHLY_CRYSTAL", 50000))

# -------------------------------
# Create Pyrogram Client
# -------------------------------
app = Client(
    "waifu_bot",
    api_id=int(Config.API_ID),
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
)

# Expose constants at top level
OWNER_ID = Config.OWNER_ID
ADMINS = Config.ADMINS
