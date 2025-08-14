from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from ..callbacks import PROFILE
from .buttons import BUTTON_PROFILE, BUTTON_SUPPORT

main_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_PROFILE, callback_data=PROFILE),
            InlineKeyboardButton(text=BUTTON_SUPPORT, url="https://t.me/danila_okv")
        ]
    ] 
)