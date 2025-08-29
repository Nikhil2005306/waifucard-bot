# handlers/trade.py
import sqlite3
import time
import traceback
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import app

DB_PATH = "waifu_bot.db"

print("[trade.py] module loaded")

# ----------------- DB helpers -----------------
def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def card_info(wid: int):
    """Return card info from waifu_cards table (id, name, anime, rarity, media_type, media_file) or None."""
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, anime, rarity, media_type, media_file FROM waifu_cards WHERE id = ?", (wid,))
        row = cur.fetchone()
    finally:
        conn.close()
    return row

def user_card_amount(user_id: int, wid: int) -> int:
    """Return how many of a card the user has (0 if none)."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_id, wid))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else 0

def _swap_cards_atomic(user_a: int, wid_a: int, user_b: int, wid_b: int) -> bool:
    """
    Swap one unit of wid_a from user_a with one unit of wid_b from user_b.
    Returns True on success, False on failure (e.g., insufficient amounts).
    """
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        # re-check ownership/amounts
        cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_a, wid_a))
        r1 = cur.fetchone()
        cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_b, wid_b))
        r2 = cur.fetchone()
        if not r1 or not r2:
            conn.rollback()
            return False
        a_amt = r1[0]
        b_amt = r2[0]
        if a_amt <= 0 or b_amt <= 0:
            conn.rollback()
            return False

        # decrement user_a's wid_a
        if a_amt > 1:
            cur.execute("UPDATE user_waifus SET amount=amount-1 WHERE user_id=? AND waifu_id=?", (user_a, wid_a))
        else:
            cur.execute("DELETE FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_a, wid_a))

        # increment user_b with wid_a
        cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_b, wid_a))
        if cur.fetchone():
            cur.execute("UPDATE user_waifus SET amount=amount+1 WHERE user_id=? AND waifu_id=?", (user_b, wid_a))
        else:
            cur.execute("INSERT INTO user_waifus (user_id, waifu_id, amount) VALUES (?, ?, 1)", (user_b, wid_a))

        # decrement user_b's wid_b
        if b_amt > 1:
            cur.execute("UPDATE user_waifus SET amount=amount-1 WHERE user_id=? AND waifu_id=?", (user_b, wid_b))
        else:
            cur.execute("DELETE FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_b, wid_b))

        # increment user_a with wid_b
        cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_a, wid_b))
        if cur.fetchone():
            cur.execute("UPDATE user_waifus SET amount=amount+1 WHERE user_id=? AND waifu_id=?", (user_a, wid_b))
        else:
            cur.execute("INSERT INTO user_waifus (user_id, waifu_id, amount) VALUES (?, ?, 1)", (user_a, wid_b))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        traceback.print_exc()
        return False
    finally:
        conn.close()

# ----------------- Command handler -----------------
@app.on_message(filters.command("trade"))
async def cmd_trade(client, message: Message):
    try:
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply_text("❌ You must reply to the partner's message.\nUsage: `/trade <your_waifu_id> <their_waifu_id>`", parse_mode=None)
            return

        parts = message.text.split()
        if len(parts) < 3:
            await message.reply_text("❌ Usage: `/trade <your_waifu_id> <their_waifu_id>` (reply to the partner's message).", parse_mode=None)
            return

        try:
            my_wid = int(parts[1])
            their_wid = int(parts[2])
        except ValueError:
            await message.reply_text("❌ Waifu IDs must be numbers.", parse_mode=None)
            return

        user_a = message.from_user.id
        user_b = message.reply_to_message.from_user.id
        if user_a == user_b:
            await message.reply_text("❌ You cannot trade with yourself.", parse_mode=None)
            return

        # Check both have the cards
        a_amt = user_card_amount(user_a, my_wid)
        b_amt = user_card_amount(user_b, their_wid)
        if a_amt <= 0:
            await message.reply_text("❌ You don't own the card you're offering.", parse_mode=None)
            return
        if b_amt <= 0:
            await message.reply_text("❌ The partner doesn't own the card you requested.", parse_mode=None)
            return

        # Fetch card details
        my_card = card_info(my_wid)
        their_card = card_info(their_wid)

        if not my_card or not their_card:
            await message.reply_text("❌ One of the cards does not exist in the database.")
            return

        my_name, my_media_type, my_media_file = my_card[1], my_card[4], my_card[5]
        their_name, their_media_type, their_media_file = their_card[1], their_card[4], their_card[5]

        nonce = int(time.time())
        cbdata_accept = f"trade_accept:{user_a}:{user_b}:{my_wid}:{their_wid}:{nonce}"
        cbdata_decline = f"trade_decline:{user_a}:{user_b}:{my_wid}:{their_wid}:{nonce}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Accept", callback_data=cbdata_accept),
             InlineKeyboardButton("❌ Decline", callback_data=cbdata_decline)]
        ])

        caption = (
            "🔄 **Trade Request** 🔄\n\n"
            f"👤 From: {message.from_user.mention}\n"
            f"✨ Offering: **{my_name}** (ID {my_wid})\n\n"
            f"👤 To: {message.reply_to_message.from_user.mention}\n"
            f"✨ Requested: **{their_name}** (ID {their_wid})\n\n"
            f"{message.reply_to_message.from_user.mention}, do you accept this trade?"
        )

        # send card preview (photo/video for offered card)
        try:
            if my_media_type == "photo":
                await message.reply_photo(my_media_file, caption=caption, reply_markup=keyboard, parse_mode=None)
            elif my_media_type == "video":
                await message.reply_video(my_media_file, caption=caption, reply_markup=keyboard, parse_mode=None)
            else:
                await message.reply_text(caption, reply_markup=keyboard, parse_mode=None)
        except:
            await message.reply_text(caption, reply_markup=keyboard, parse_mode=None)

    except Exception as e:
        print("[trade] exception:", e)
        traceback.print_exc()
        try:
            await message.reply_text("❌ Internal error handling /trade. Check logs.", parse_mode=None)
        except:
            pass

# ----------------- Callback handler -----------------
@app.on_callback_query(filters.regex(r"^trade_(accept|decline):"))
async def cb_trade(client, callback: CallbackQuery):
    try:
        data = callback.data.split(":")
        action = data[0].split("_")[1]  # accept or decline
        user_a = int(data[1])
        user_b = int(data[2])
        my_wid = int(data[3])
        their_wid = int(data[4])

        # only partner (user_b) may accept/decline
        if callback.from_user.id != user_b:
            await callback.answer("⛔ Only the requested partner can respond to this trade.", show_alert=True)
            return

        if action == "decline":
            try:
                await callback.message.edit_text("❌ Trade declined by the partner.")
            except:
                pass
            await callback.answer("Trade declined.", show_alert=False)
            return

        # accept: perform atomic swap
        success = _swap_cards_atomic(user_a, my_wid, user_b, their_wid)
        if not success:
            try:
                await callback.message.edit_text("❌ Trade failed: one of the users no longer owns the required card(s).")
            except:
                pass
            await callback.answer("Trade failed.", show_alert=True)
            return

        # success
        try:
            await callback.message.edit_text(
                f"✅ Trade completed!\n\n"
                f"User [{user_a}](tg://user?id={user_a}) ⇄ User [{user_b}](tg://user?id={user_b})\n"
                f"Swapped: ID {my_wid} ⇄ ID {their_wid}"
            , parse_mode=None)
        except:
            pass

        # notify both users
        try:
            await app.send_message(user_a, f"✅ Your trade completed: you gave ID {my_wid} and received ID {their_wid}.")
        except:
            pass
        try:
            await app.send_message(user_b, f"✅ Trade completed: you gave ID {their_wid} and received ID {my_wid}.")
        except:
            pass

        await callback.answer("Trade completed!", show_alert=False)

    except Exception as e:
        print("[trade cb] exception:", e)
        traceback.print_exc()
        try:
            await callback.answer("Internal error processing trade.", show_alert=True)
        except:
            pass
