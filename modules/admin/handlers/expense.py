from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from modules.decorators import admin_only
from modules.ui.keyboards.tracker import send_managed_message

from ..services.expense import add_expense

cmd_syntax = "/expense &lt;название&gt; &lt;сумма&gt;" # TODO: &lt;кол-во&gt; [примечание]

router = Router()

@admin_only
@router.message(Command("expense"))
async def cmd_expense(message: Message):
    parts = message.text.strip().split()
    parts.pop(0)

    if len(parts) < 2:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=f"❌ Недостаточно аргументов, cинтаксис:\n {cmd_syntax}"
        )
        return
    
    if parts[1].replace('.', '', 1).isdigit() is False:
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=f"❌ Некорректная сумма, должна быть числом.\nСинтаксис:\n {cmd_syntax}"
        )
        return

    name = parts[0].lower()
    amount = float(parts[1])

    add_expense(
        category=name,
        amount=amount,
        quantity=1,
        note=None
    )

    await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text="✅ Добавлен расход:\n"
        f"Название: <b>{name}</b>\n"
        f"Сумма: <b>{amount}</b>\n"
    )