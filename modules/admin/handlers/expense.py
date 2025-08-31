from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from modules.decorators import admin_only
from modules.ui.keyboards.tracker import send_managed_message

from ..services.expense import add_expense

# Define a human‑readable command syntax to display on errors.  The syntax
# now supports an optional quantity and note after the amount.  Examples:
#   /expense paper 12.50 500 "A4, 80 g/m²"
#   /expense ink 5.99
cmd_syntax = "/expense [категория] [сумма] [кол-во] [примечание]"

# Map various aliases and Russian terms to canonical expense categories.
# Only these canonical values are stored in the database (paper, ink,
# service or other).  Unknown aliases fall back to "other".
CATEGORY_ALIASES: dict[str, str] = {
    # Paper synonyms
    "paper": "paper",
    "бумага": "paper",
    "лист": "paper",
    "листы": "paper",
    "a4": "paper",
    # Ink/toner synonyms
    "ink": "ink",
    "чернила": "ink",
    "тонер": "ink",
    "картридж": "ink",
    # Service/maintenance synonyms
    "service": "service",
    "сервис": "service",
    "обслуживание": "service",
    "ремонт": "service",
    # Fallback; note that other categories will be saved as "other"
}

router = Router()

@admin_only
@router.message(Command("expense"))
async def cmd_expense(message: Message):
    """Handle the /expense command for administrators.

    Syntax: /expense <категория> <сумма> [кол-во] [примечание]

    * категория – одно из: paper/бумага, ink/чернила, service/обслуживание.
      Неизвестные категории сохраняются как «other».
    * сумма – стоимость расхода в валюте (число с точкой или запятой).
    * кол-во – (опционально) количество закупленных единиц; по умолчанию 1.
    * примечание – (опционально) произвольный текст, описывающий расход.

    Пример: /expense бумага 1500 500 "A4, 80 г/м²"
    """
    # Split the incoming message by whitespace.  The first element is
    # always the command itself (e.g. '/expense'), which we discard.
    parts = message.text.strip().split()
    if not parts:
        return
    parts.pop(0)

    # Ensure at least a category and amount are provided
    if len(parts) < 2:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=f"❌ Недостаточно аргументов. Ожидаю: {cmd_syntax}"
        )
        return

    raw_category = parts[0].lower()
    # Determine canonical category; fall back to "other" if unknown
    category = CATEGORY_ALIASES.get(raw_category, "other")

    # Normalize decimal separator and validate the amount
    amount_str = parts[1].replace(",", ".")
    if amount_str.replace(".", "", 1).isdigit() is False:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=(f"❌ Некорректная сумма, должна быть числом.\n"
                  f"Синтаксис: {cmd_syntax}")
        )
        return
    amount = float(amount_str)

    # Defaults for optional fields
    quantity: int = 1
    note: str | None = None

    # Parse optional third token as quantity if it looks numeric.
    # If it is not numeric, treat the remainder of the message as the note.
    if len(parts) >= 3:
        third = parts[2]
        # Try to parse numeric quantity (integer).  Accept decimal but convert to int.
        quant_candidate = third.replace(",", ".")
        if quant_candidate.replace(".", "", 1).isdigit():
            quantity = int(float(quant_candidate))
            # Any further tokens constitute the note
            if len(parts) > 3:
                note = " ".join(parts[3:])
        else:
            # No numeric quantity; treat everything from the third token as a note
            note = " ".join(parts[2:])

    # Record the expense in the database
    add_expense(
        category=category,
        amount=amount,
        quantity=quantity,
        note=note
    )

    # Compose a confirmation message for the administrator.  We display
    # the original category string (raw_category) so that admins see what
    # they typed, but the data is saved under the canonical key.
    response_lines = [
        "✅ Добавлен расход:",
        f"Категория: <b>{raw_category}</b>",
        f"Сумма: <b>{amount}</b>"
    ]
    if quantity != 1:
        response_lines.append(f"Количество: <b>{quantity}</b>")
    if note:
        response_lines.append(f"Примечание: {note}")

    await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text="\n".join(response_lines)
    )