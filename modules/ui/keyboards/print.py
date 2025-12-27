from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CONTACT_USERNAME

from ..callbacks import (
    DONE, CANCEL
)
from .buttons import (
    BUTTON_SUPPORT, BUTTON_DONE, BUTTON_CANCEL
)

print_done_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_SUPPORT, url=f"https://t.me/{CONTACT_USERNAME}"),
            InlineKeyboardButton(text=BUTTON_DONE, callback_data=DONE)     
      ]
    ]
)

print_error_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_SUPPORT, url=f"https://t.me/{CONTACT_USERNAME}"),
            InlineKeyboardButton(text=BUTTON_CANCEL, callback_data=CANCEL)
        ]
    ]
)