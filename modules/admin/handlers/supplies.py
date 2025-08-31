from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.decorators import admin_only
from modules.ui.keyboards.tracker import send_managed_message
from db import get_connection

router = Router()

@admin_only
@router.message(Command("supplies"))
async def cmd_supplies(message: Message) -> None:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT name, quantity, minimum, updated_at
            FROM supplies
            ORDER BY name
            """
        )
        rows = cur.fetchall()

    if not rows:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text="📦 Запасы не настроены."
        )
        return

    lines = ["📦 <b>Текущие запасы:</b>\n"]
    for row in rows:
        name = row["name"]
        quantity = row["quantity"]
        minimum = row["minimum"]
        updated_at = row["updated_at"]

        line = f"• <b>{name.capitalize()}</b>: {quantity}"
        if minimum > 0:
            line += f" (мин. {minimum})"
        if updated_at:
            line += f" — обновлено {updated_at}"
        lines.append(line)

    await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text="\n".join(lines)
    )