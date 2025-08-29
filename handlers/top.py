# top.py

from pyrogram import Client, filters
from database import Database
from config import app  # make sure 'app' is your pyrogram client instance

db = Database()

# ---------------- /top ----------------
@app.on_message(filters.command("top"))
async def global_top(client, message):
    rows = db.cursor.execute("""
        SELECT u.user_id, u.username, IFNULL(SUM(uw.amount),0) as total_cards
        FROM users u
        LEFT JOIN user_waifus uw ON uw.user_id = u.user_id
        GROUP BY u.user_id
        ORDER BY total_cards DESC
        LIMIT 10
    """).fetchall()

    text = "👑 Global Top Collectors:\n\n"
    for i, (uid, uname, total) in enumerate(rows, 1):
        name = uname if uname else f"User {uid}"
        text += f"{i}. {name} — {total} cards\n"
    await message.reply_text(text)

# ---------------- /tdtop ----------------
@app.on_message(filters.command("tdtop"))
async def today_top(client, message):
    rows = db.cursor.execute("""
        SELECT u.user_id, u.username, IFNULL(SUM(uw.amount),0) AS today_cards
        FROM users u
        LEFT JOIN user_waifus uw ON uw.user_id = u.user_id
        WHERE uw.last_collected IS NOT NULL AND date(uw.last_collected) = date('now')
        GROUP BY u.user_id
        ORDER BY today_cards DESC
        LIMIT 10
    """).fetchall()

    text = "🌙 Today's Top Collectors:\n\n"
    if not rows:
        text += "No waifus collected today."
    else:
        for i, (uid, uname, total) in enumerate(rows, 1):
            name = uname if uname else f"User {uid}"
            text += f"{i}. {name} — {total} cards\n"
    await message.reply_text(text)

# ---------------- /ctop ----------------
@app.on_message(filters.command("ctop"))
async def chat_top(client, message):
    rows = db.cursor.execute("""
        SELECT user_id, username, daily_crystals + weekly_crystals + monthly_crystals + given_crystals AS total_balance
        FROM users
        ORDER BY total_balance DESC
        LIMIT 10
    """).fetchall()

    text = "🏮 Top Collecting Users (by Crystals):\n\n"
    for i, (uid, uname, bal) in enumerate(rows, 1):
        name = uname if uname else f"User {uid}"
        text += f"{i}. {name} — {bal} crystals\n"
    await message.reply_text(text)
