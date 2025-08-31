from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.decorators import admin_only
from modules.ui.keyboards.tracker import send_managed_message
from db import get_connection

SUPPLY_ALIASES: dict[str, str] = {
    # Paper synonyms
    "paper": "бумага",
    "бумага": "бумага",
    "лист": "бумага",
    "листы": "бумага",
    "a4": "бумага",
    # Ink/toner synonyms
    "ink": "чернила",
    "чернила": "чернила",
    "тонер": "чернила",
    "картридж": "чернила",
}

router = Router()

@admin_only
@router.message(Command("refill"))
async def cmd_refill(message: Message) -> None:
    parts = message.text.strip().split()
    parts.pop(0)

    if len(parts) < 2:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=
            "📚 Пример использования:\n"
            "<b>/refill [запас] [кол-во]</b> <i>[минимум]</i>\n\n"
            "Запасы: <b>бумага, чернила</b>"
        )
        return

    raw_name = parts[0].lower()
    supply_name = SUPPLY_ALIASES.get(raw_name)
    if supply_name is None:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=f"❌ Неизвестный расходник: {raw_name}\n"
            "Допустимые: <b>бумага, чернила</b>"
        )
        return

    # Parse quantity
    qty_str = parts[1].strip()
    if qty_str.isdigit() is False:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text="❌ Количество должно быть числом"
        )
        return
    quantity = int(qty_str)
    if quantity <= 0:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text="❌ Количество должно быть положительным"
        )
        return

    # Parse optional minimum
    min_val: int | None = None
    if len(parts) >= 3:
        min_str=parts[2].strip()
        if min_str.isdigit():
            min_val = int(min_str)
        else:
            await send_managed_message(
                bot=message.bot,
                user_id=message.from_user.id,
                text="❌ Минимум должен быть числом"
            )
            return

    with get_connection() as conn:
        row = conn.execute(
            "SELECT quantity, minimum FROM supplies WHERE name = ?",
            (supply_name,)
        ).fetchone()
        if row:
            # Existing supply: increment quantity and optionally update minimum
            new_minimum = min_val if min_val is not None else row["minimum"]
            conn.execute(
                "UPDATE supplies SET quantity = ?, minimum = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                (quantity, new_minimum, supply_name),
            )
        else:
            # New supply: insert with given quantity and minimum (or zero if omitted)
            new_minimum = min_val if min_val is not None else 0
            conn.execute(
                "INSERT INTO supplies (name, quantity, minimum, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (supply_name, quantity, new_minimum),
            )
        conn.commit()

    # Prepare a confirmation message.  We show both the increment and the
    # resulting total so the admin can verify the operation.
    note_parts: list[str] = [f"✅ Запас <b>{supply_name}</b> пополнен"]
    note_parts.append(f"Количество: <b>{quantity}</b>")
    old_min = row["minimum"] if row else 0
    if min_val is not None:
        note_parts.append(f"Новый минимум: <b>{new_minimum}</b>")
    else:
        note_parts.append(f"Минимум: <b>{old_min}</b> (без изменений)")

    await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text="\n".join(note_parts)
    )

