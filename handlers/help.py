# handlers/help.py

from pyrogram import filters
from config import app, Config

# Simple role check (expandable later if you store roles in DB)
def get_role(user_id: int):
    if user_id == Config.OWNER_ID:
        return "owner"
    elif user_id in Config.ADMINS:   # list of admin IDs in config.py
        return "admin"
    else:
        return "user"


HELP_TEXT = {
    "user": """
🌸 **Available Commands** 🌸

🎀 **General Commands**:
/start – Begin your journey with Alisa 🌸
/help – Show this help message 📖
/profile – View your collection stats 👤
/inventory – View your waifu collection 💮
/daily – Claim your daily gift (5000 💎) ✨
/weekly – Claim your weekly treasure (25,000 💎) 🌙
/monthly – Claim your monthly blessing (50,000 💎) 🌸
/claim – Summon a random waifu (daily) 🎐
/collect – Collect a waifu from active drop 💫
/search [name] – Search waifus by name 🔎
/wishlist – Manage your waifu wishlist 📝
/fav [waifu_id] – Set your favorite waifu 💞

🛍️ **Market Commands**:
/buy [waifu_id] – Buy a waifu 💖
/mymarket – Browse your waifus for sale 🛒
/sell [waifu_id] [price] – Put a waifu up for sale 💎
/gift [waifu_id] – Gift a waifu to another user 🎁
/trade [user] – Trade waifus with another collector 🤝

📊 **Stats Commands**:
/top – Global top collectors 👑
/tdtop – Today’s top collectors 🌙
/ctop – Top collecting chats 🏮
/dropcount – Check messages until next drop ⏳
/rarity – View waifu rarity tiers 🧚
/checkwaifu [id] – Show waifu details 🌸
/collectionvalue – Total collection worth 💎
""",

    "admin": """
👮 **Admin Commands**:
/addwaifu – Add new waifu card 🌸
/setdrop [number] – Set messages required per drop 🎲
/dropnow – Force a waifu drop 🌈
/gban – Global ban a user 🚫
/gunban – Global unban user 🔓
/reset – Reset user’s collection ♻️
/announce [text] – Send announcement 📢
/event [name] – Start event 🎉
""",

    "owner": """
👑 **Owner Commands**:
/makeadmin [user_id] – Grant admin privileges 🎖️
/removeadmin [user_id] – Revoke admin privileges ❌
/give [waifu_id] – Give waifu to user 🌹
/cleardb – Clear all waifus 🗑️
/deleteallwaifu – Delete all waifus 💀
/backupdb – Backup database 💾
/showdb – Show bot usage statistics 📊
"""
}


@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    user_id = message.from_user.id
    role = get_role(user_id)

    text = HELP_TEXT["user"]  # default
    if role == "admin":
        text += HELP_TEXT["admin"]
    elif role == "owner":
        text += HELP_TEXT["admin"] + HELP_TEXT["owner"]

    await message.reply_text(text)
