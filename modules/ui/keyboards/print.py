from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..callbacks import (
    DONE, CANCEL
)
from .buttons import (
    BUTTON_SUPPORT, BUTTON_DONE, BUTTON_CANCEL
)

print_done_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_SUPPORT, url="https://t.me/danila_okv"),
            InlineKeyboardButton(text=BUTTON_DONE, callback_data=DONE)     
      ]
    ]
)

print_error_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_SUPPORT, url="https://t.me/danila_okv"),
            InlineKeyboardButton(text=BUTTON_CANCEL, callback_data=CANCEL)
        ]
    ]
)