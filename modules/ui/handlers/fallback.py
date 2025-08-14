from aiogram import Router
from aiogram.types import Message
from ..messages import UNKNOWN_COMMAND_TEXT
from modules.analytics.logger import warning

router = Router()

@router.message()
async def unknown_message_handler(message: Message):
    await message.answer(UNKNOWN_COMMAND_TEXT)
    warning(
        message.from_user.id,
        "unknown_command",
        message.text
    )   