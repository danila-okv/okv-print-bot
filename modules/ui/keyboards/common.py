
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from ..callbacks import BACK, CANCEL
from .buttons import BUTTON_BACK, BUTTON_CANCEL

back_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_BACK, callback_data=BACK)
        ]
    ] 
)

cancel_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_CANCEL, callback_data=CANCEL)
        ]
    ]
)