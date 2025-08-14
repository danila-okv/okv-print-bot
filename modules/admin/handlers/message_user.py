from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from modules.decorators import admin_only
from modules.analytics.logger import warning, error, action, info
from modules.ui.keyboards.tracker import send_managed_message
router = Router()

class MessageUserState(StatesGroup):
    waiting_for_text = State()
    waiting_for_confirmation = State()

@router.message(Command("m"))
@admin_only
async def start_message_to_user(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        # Экранируем угловые скобки в примере использования
        await message.answer("❌ Используй команду так: /m &lt;user_id&gt;")
        warning(
            message.from_user.id,
            "Command /m",
            "Wrong syntax"
        )
        return

    user_id = int(parts[1])
    await state.set_state(MessageUserState.waiting_for_text)
    await state.update_data(target_user_id=user_id)
    await message.answer(f"✉️ Напиши сообщение, которое хочешь отправить пользователю <code>{user_id}</code>.")
    action(
        message.from_user.id,
        "Command /m",
        f"Start texting to user {user_id}"
    )

@router.message(MessageUserState.waiting_for_text)
@admin_only
async def receive_message_text(message: Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    await state.set_state(MessageUserState.waiting_for_confirmation)
    await message.answer(
        f"📨 Твоё сообщение:\n\n{message.text}\n\n✅ Подтвердить отправку? Напиши <b>да</b> или <b>нет</b>."
    )
    info(
        message.from_user.id,
        "Command /m",
        f"Waiting for message confirmation"
    )
    

@router.message(MessageUserState.waiting_for_confirmation, F.text.lower() == "да")
@admin_only
async def confirm_and_send(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["target_user_id"]
    text = data["message_text"]

    try:
        await send_managed_message(
            message.bot,
            user_id,
            text
        )
        await message.answer("✅ Сообщение успешно отправлено.")
        action(
            message.from_user.id,
            "Command /m",
            f"Message sent to {user_id}: {text}"
        )
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить сообщение: {e}")
        await state.clear()
        error(
            message.from_user.id,
            "Command /m",
            f"Failed to send message to {user_id}: {e}"
        )
    await state.clear()

@router.message(MessageUserState.waiting_for_confirmation, F.text.lower() == "нет")
@admin_only
async def cancel_send(message: Message, state: FSMContext):
    await message.answer("❌ Отправка отменена.")
    action(
            message.from_user.id,
            "Command /m",
            f"Canceled message send"
        )
    await state.clear()
