from aiogram import Router, F
from aiogram.types import CallbackQuery
from .start import send_main_menu
from ..callbacks import CANCEL
from ..messages import PRINT_CANCELLED_TEXT
from modules.analytics.logger import action

router = Router()

@router.callback_query(F.data == CANCEL)
async def start_command(callback: CallbackQuery):
    await callback.message.edit_text(text=PRINT_CANCELLED_TEXT)
    action(
        callback.from_user.id,
        CANCEL,
        "Cancelled order"
    )
    await send_main_menu(callback.bot, callback.from_user.id)