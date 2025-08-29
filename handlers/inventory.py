# handlers/inventory.py
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import app
from database import Database

db = Database()

ITEMS_PER_PAGE = 10

# ---------------- /inventory Command ----------------
@app.on_message(filters.command("inventory"))
async def inventory(client, message):
    user_id = message.from_user.id
    page = 0  # default page
    await send_inventory_page(client, message.chat.id, user_id, page)


async def send_inventory_page(client, chat_id, user_id, page):
    offset = page * ITEMS_PER_PAGE

    # ---------------- Get user's favorite card ----------------
    db.cursor.execute("SELECT waifu_id FROM user_fav WHERE user_id = ?", (user_id,))
    fav_row = db.cursor.fetchone()
    fav_card = None
    if fav_row:
        fav_id = fav_row[0]
        db.cursor.execute("SELECT id, name, anime, rarity, event, media_type, media_file FROM waifu_cards WHERE id = ?", (fav_id,))
        fav_card = db.cursor.fetchone()

    # ---------------- Get user's owned waifus ----------------
    db.cursor.execute("""
        SELECT uw.waifu_id, wc.name, wc.rarity, uw.amount
        FROM user_waifus uw
        JOIN waifu_cards wc ON uw.waifu_id = wc.id
        WHERE uw.user_id = ?
        ORDER BY uw.amount DESC
        LIMIT ? OFFSET ?
    """, (user_id, ITEMS_PER_PAGE, offset))
    rows = db.cursor.fetchall()

    total_cards = db.cursor.execute("SELECT SUM(amount) FROM user_waifus WHERE user_id = ?", (user_id,)).fetchone()[0] or 0

    # ---------------- Handle empty inventory ----------------
    if not rows and not fav_card:
        await client.send_message(chat_id, "❌ You have no waifus yet!")
        return

    text_lines = ["━━━ 🎀 Your Waifu Collection 🎀 ━━━"]
    text_lines.append(f"Showing {ITEMS_PER_PAGE} Waifus ~\n")

    # ---------------- Include favorite card at top ----------------
    if fav_card:
        fav_text = f"❤️ Favorite Waifu\n📷 {fav_card[1]} | ID: {fav_card[0]} | {fav_card[3]} | Owned: 1×"
        text_lines.append(fav_text)
        fav_media = fav_card[5], fav_card[6]  # media_type, media_file
    else:
        fav_media = None

    # ---------------- Add normal collection ----------------
    for idx, row in enumerate(rows, start=1):
        text_lines.append(f"{idx}️⃣ {row[1]} | {row[0]} | {row[2]} | Owned: {row[3]}×")

    text_lines.append("\n━━━━━━━━━━━━━━━")
    text_lines.append(f"💖 Total Collected: {total_cards}")

    # ---------------- Pagination buttons ----------------
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"inventory_page:{page-1}"))
    if len(rows) == ITEMS_PER_PAGE:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"inventory_page:{page+1}"))
    markup = InlineKeyboardMarkup([buttons]) if buttons else None

    # ---------------- Send favorite media first ----------------
    if fav_media:
        media_type, media_file = fav_media
        if media_type == "photo":
            await client.send_photo(chat_id, media_file, caption="\n".join(text_lines), reply_markup=markup)
        elif media_type == "video":
            await client.send_video(chat_id, media_file, caption="\n".join(text_lines), reply_markup=markup)
    else:
        await client.send_message(chat_id, "\n".join(text_lines), reply_markup=markup)


# ---------------- Callback for pagination ----------------
@app.on_callback_query(filters.regex(r"^inventory_page:"))
async def inventory_page_callback(client, callback):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    await send_inventory_page(client, callback.message.chat.id, user_id, page)
    await callback.answer()
