# handlers/gift.py
import sqlite3
import time
import random
import traceback
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import app

DB_PATH = "waifu_bot.db"
pending_gifts = {}  # nonce -> {"giver": int, "receiver": int, "wid": int, "chat_id": int, "created": float}

print("[gift.py] handler loaded")


# ---------- DB helpers ----------
def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _table_columns(table_name: str):
    """Return list of column names for a table (empty list if table missing)."""
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        rows = cur.fetchall()
        conn.close()
        return [r[1] for r in rows]
    except Exception:
        return []


def get_card(wid: int):
    """
    Return a dict with available card fields from waifu_cards or None.
    Will adapt to missing columns.
    """
    cols = _table_columns("waifu_cards")
    # preferred fields in order
    desired = ["id", "name", "anime", "rarity", "event", "theme", "media_type", "media_file"]
    use = [c for c in desired if c in cols]
    if not use:
        return None
    sql = f"SELECT {', '.join(use)} FROM waifu_cards WHERE id = ?"
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, (wid,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {use[i]: row[i] for i in range(len(use))}


def user_card_amount(user_id: int, wid: int) -> int:
    """
    Return how many of a card the user has.
    If user_waifus has 'amount' column, uses it; otherwise returns 1 if a row exists.
    """
    cols = _table_columns("user_waifus")
    conn = _conn()
    cur = conn.cursor()
    try:
        if "amount" in cols:
            cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (user_id, wid))
            r = cur.fetchone()
            return r[0] if r else 0
        else:
            cur.execute("SELECT 1 FROM user_waifus WHERE user_id=? AND waifu_id=? LIMIT 1", (user_id, wid))
            r = cur.fetchone()
            return 1 if r else 0
    finally:
        conn.close()


def transfer_one_card_atomic(giver: int, receiver: int, wid: int) -> bool:
    """
    Atomically remove 1 from giver and add 1 to receiver.
    Supports user_waifus with 'amount' column, otherwise uses rowid delete/insert fallback.
    Returns True on success, False on failure.
    """
    cols = _table_columns("user_waifus")
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        if "amount" in cols:
            # check giver amount
            cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (giver, wid))
            r = cur.fetchone()
            if not r or r[0] <= 0:
                conn.rollback()
                return False
            g_amt = r[0]
            # decrement giver
            if g_amt > 1:
                cur.execute("UPDATE user_waifus SET amount=amount-1 WHERE user_id=? AND waifu_id=?", (giver, wid))
            else:
                cur.execute("DELETE FROM user_waifus WHERE user_id=? AND waifu_id=?", (giver, wid))
            # increment receiver
            cur.execute("SELECT amount FROM user_waifus WHERE user_id=? AND waifu_id=?", (receiver, wid))
            r2 = cur.fetchone()
            if r2:
                cur.execute("UPDATE user_waifus SET amount=amount+1 WHERE user_id=? AND waifu_id=?", (receiver, wid))
            else:
                cur.execute("INSERT INTO user_waifus (user_id, waifu_id, amount) VALUES (?, ?, 1)", (receiver, wid))
        else:
            # fallback: delete one row by rowid from giver, insert new for receiver
            # select a rowid to delete
            cur.execute("SELECT rowid FROM user_waifus WHERE user_id=? AND waifu_id=? LIMIT 1", (giver, wid))
            r = cur.fetchone()
            if not r:
                conn.rollback()
                return False
            rowid = r[0]
            cur.execute("DELETE FROM user_waifus WHERE rowid=?", (rowid,))
            # insert into receiver
            cur.execute("INSERT INTO user_waifus (user_id, waifu_id) VALUES (?, ?)", (receiver, wid))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        traceback.print_exc()
        return False
    finally:
        conn.close()


# ---------- /gift command ----------
@app.on_message(filters.command("gift") & filters.reply)
async def cmd_gift(client, message: Message):
    try:
        print("[gift] /gift triggered by", getattr(message.from_user, "id", None), "text:", message.text)

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("❌ Usage: Reply to a user with: /gift <waifu_id>", parse_mode=None)
            return

        try:
            wid = int(parts[1])
        except ValueError:
            await message.reply_text("❌ Waifu ID must be a number.", parse_mode=None)
            return

        giver = message.from_user.id
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply_text("❌ Reply to the recipient's message.", parse_mode=None)
            return
        receiver_user = message.reply_to_message.from_user
        receiver = receiver_user.id

        if giver == receiver:
            await message.reply_text("❌ You cannot gift to yourself.", parse_mode=None)
            return

        # check giver owns card
        amt = user_card_amount(giver, wid)
        if amt <= 0:
            await message.reply_text("❌ You don't own that waifu card.", parse_mode=None)
            return

        # fetch card
        card = get_card(wid)
        if not card:
            await message.reply_text("❌ Waifu card not found in database.", parse_mode=None)
            return

        # Build safe caption (plain text, no special markup)
        lines = []
        lines.append("🎁 Gift Offer 🎁")
        lines.append("")
        lines.append("ID: " + str(card.get("id", wid)))
        lines.append("Name: " + str(card.get("name", "—")))
        lines.append("Anime: " + str(card.get("anime", "—")))
        lines.append("Rarity: " + str(card.get("rarity", "—")))
        if "event" in card:
            lines.append("Event: " + str(card.get("event") or "—"))
        if "theme" in card:
            lines.append("Theme: " + str(card.get("theme") or "—"))
        lines.append("")
        lines.append("From: " + (message.from_user.first_name or str(giver)) + f" (id:{giver})")
        lines.append("To: " + (receiver_user.first_name or str(receiver)) + f" (id:{receiver})")
        lines.append("")
        lines.append("Do you accept this gift?")

        caption = "\n".join(lines)

        nonce = str(int(time.time() * 1000)) + str(random.randint(1000, 9999))
        pending_gifts[nonce] = {"giver": giver, "receiver": receiver, "wid": wid, "chat_id": message.chat.id, "created": time.time()}

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"gift_confirm:{nonce}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"gift_decline:{nonce}")
            ]
        ])

        media_type = card.get("media_type")
        media_file = card.get("media_file")

        # Try to preview under recipient's message (so they notice it)
        try:
            if media_type and media_file:
                if media_type.lower() in ("photo", "image", "photo_file"):
                    await message.reply_to_message.reply_photo(photo=media_file, caption=caption, reply_markup=kb, parse_mode=None)
                elif media_type.lower() in ("video", "animation", "mp4"):
                    await message.reply_to_message.reply_video(video=media_file, caption=caption, reply_markup=kb, parse_mode=None)
                else:
                    # unknown media type - send text preview
                    await message.reply_text(caption, reply_markup=kb, parse_mode=None)
            else:
                await message.reply_text(caption, reply_markup=kb, parse_mode=None)
        except Exception as e:
            print("[gift] preview send failed:", e)
            # fallback
            await message.reply_text(caption, reply_markup=kb, parse_mode=None)

        print(f"[gift] pending {nonce} -> giver={giver}, receiver={receiver}, wid={wid}")

    except Exception as e:
        print("[gift] exception:", e)
        traceback.print_exc()
        try:
            await message.reply_text("❌ Internal error processing /gift. Check logs.", parse_mode=None)
        except:
            pass


# ---------- Callback handler ----------
@app.on_callback_query(filters.regex(r"^gift_(confirm|decline):"))
async def cb_gift(client, callback: CallbackQuery):
    try:
        print("[gift cb] received:", callback.data, "from:", callback.from_user.id)
        action, nonce = callback.data.split(":", 1)
        info = pending_gifts.get(nonce)
        if not info:
            await callback.answer("⚠️ This gift has expired or is invalid.", show_alert=True)
            return

        giver = info["giver"]
        receiver = info["receiver"]
        wid = info["wid"]

        # Only recipient may act
        if callback.from_user.id != receiver:
            await callback.answer("⛔ Only the recipient can accept/decline this gift.", show_alert=True)
            return

        if action == "gift_decline":
            # edit preview
            try:
                await callback.message.edit_caption("❌ Gift declined by recipient.", reply_markup=None)
            except:
                try:
                    await callback.message.edit_text("❌ Gift declined by recipient.", reply_markup=None)
                except:
                    pass
            pending_gifts.pop(nonce, None)
            await callback.answer("Gift declined.", show_alert=False)
            return

        # action == gift_confirm
        # verify giver still has the card
        cur_amt = user_card_amount(giver, wid)
        if cur_amt <= 0:
            try:
                await callback.message.edit_caption("❌ Gift failed: giver no longer owns the card.", reply_markup=None)
            except:
                try:
                    await callback.message.edit_text("❌ Gift failed: giver no longer owns the card.", reply_markup=None)
                except:
                    pass
            pending_gifts.pop(nonce, None)
            await callback.answer("Gift failed.", show_alert=True)
            return

        ok = transfer_one_card_atomic(giver, receiver, wid)
        if not ok:
            try:
                await callback.message.edit_caption("❌ Gift failed during DB update.", reply_markup=None)
            except:
                try:
                    await callback.message.edit_text("❌ Gift failed during DB update.", reply_markup=None)
                except:
                    pass
            pending_gifts.pop(nonce, None)
            await callback.answer("Gift failed.", show_alert=True)
            return

        # success
        try:
            await callback.message.edit_caption(f"✅ Gift accepted! Waifu ID {wid} moved from user {giver} → user {receiver}.", reply_markup=None)
        except:
            try:
                await callback.message.edit_text(f"✅ Gift accepted! Waifu ID {wid} moved from user {giver} → user {receiver}.", reply_markup=None)
            except:
                pass

        # notify both users privately (best-effort)
        try:
            await app.send_message(giver, f"✅ Your gift (ID {wid}) was accepted and removed from your inventory.")
        except:
            pass
        try:
            await app.send_message(receiver, f"🎉 You received a gift! Waifu ID {wid} has been added to your inventory.")
        except:
            pass

        pending_gifts.pop(nonce, None)
        await callback.answer("Gift completed!", show_alert=False)

    except Exception as e:
        print("[gift cb] exception:", e)
        traceback.print_exc()
        try:
            await callback.answer("Internal error processing gift.", show_alert=True)
        except:
            pass
