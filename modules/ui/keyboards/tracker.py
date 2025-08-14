# modules/ui/keyboard_tracker.py

from db import get_connection
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from modules.analytics.logger import info

def get_active_message_id(user_id: int) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT message_id FROM active_keyboards WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return row["message_id"] if row else None

def update_active_message(user_id: int, message_id: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO active_keyboards(user_id, message_id)
            VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE SET message_id = excluded.message_id
        """, (user_id, message_id)
        )
        conn.commit()

async def send_managed_message(
    bot: Bot,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML"
) -> Message:
    old_msg_id = get_active_message_id(user_id)

    if old_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=old_msg_id,
                reply_markup=None
            )
            info(
                user_id=user_id,
                handler="keyboard_tracker",
                msg="Old markup removed"
            )
        except Exception:
            pass
        
    new_msg = await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    info(
        user_id=user_id,
        handler="keyboard_tracker",
        msg=f"Manage message sent: {text}"
    )

    update_active_message(user_id, new_msg.message_id)
    return new_msg
