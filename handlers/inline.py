# inline.py
import sqlite3
from aiogram import types, Dispatcher
from aiogram.types import (
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InlineQueryResultVideo,
    InputTextMessageContent
)
from uuid import uuid4

DB_PATH = "waifu_bot.db"

def search_waifus(query: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "SELECT id, name, anime, rarity, file_id FROM waifus "
            "WHERE name LIKE ? OR anime LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        results = c.fetchall()
        print(f"[DEBUG] Found {len(results)} results for query '{query}'")  # DEBUG
    except Exception as e:
        print("[DB ERROR]", e)
        results = []
    conn.close()
    return results


async def inline_search(inline_query: types.InlineQuery):
    query = inline_query.query.strip()
    print(f"[DEBUG] Inline query received: '{query}'")  # DEBUG

    if not query:
        await inline_query.answer([], cache_time=1)
        return

    waifus = search_waifus(query)
    results = []

    for wid, name, anime, rarity, file_id in waifus:
        caption = (
            f"🔮✨ CARD COLLECTED! ✨🔮\n\n"
            f"🆔 ID: {wid}\n"
            f"👤 Name: {name}\n"
            f"🤝 Anime: {anime}\n"
            f"❄️ Rarity: {rarity}\n\n"
            f"Type /inventory to view your collection! 📚"
        )

        # If no file_id saved → fallback to text card
        if not file_id:
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"{name} ({anime})",
                    description=f"Rarity: {rarity}",
                    input_message_content=InputTextMessageContent(caption)
                )
            )
        elif file_id.startswith("AgAC") or file_id.startswith("BAAC"):  # photo
            results.append(
                InlineQueryResultPhoto(
                    id=str(uuid4()),
                    photo_file_id=file_id,
                    caption=caption
                )
            )
        else:  # fallback as video
            results.append(
                InlineQueryResultVideo(
                    id=str(uuid4()),
                    video_file_id=file_id,
                    title=name,
                    caption=caption,
                    mime_type="video/mp4"
                )
            )

    if not results:
        # fallback "no result" card
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="No results",
                input_message_content=InputTextMessageContent(
                    "❌ No waifu found for your search."
                )
            )
        )

    await inline_query.answer(results, cache_time=1)


def register_inline(dp: Dispatcher):
    dp.register_inline_handler(inline_search)
