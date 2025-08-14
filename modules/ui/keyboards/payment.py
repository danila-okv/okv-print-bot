from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..callbacks import (PAY_ALFA, PAY_BELARUSBANK, PAY_OTHER, PAY_CONFIRM, BACK)
from .buttons import (BUTTON_PAY_ALFA, BUTTON_PAY_BELARUSBANK, BUTTON_PAY_OTHER, BUTTON_PRINT, BUTTON_BACK)

payment_methods_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_PAY_ALFA, callback_data=PAY_ALFA),
            InlineKeyboardButton(text=BUTTON_PAY_BELARUSBANK, callback_data=PAY_BELARUSBANK)
        ],
        [   
            InlineKeyboardButton(text=BUTTON_BACK, callback_data=BACK),
            InlineKeyboardButton(text=BUTTON_PAY_OTHER, callback_data=PAY_OTHER)
        ]
    ]
)

payment_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_BACK, callback_data=BACK),
            InlineKeyboardButton(text=BUTTON_PRINT, callback_data=PAY_CONFIRM)
        ]
    ]
)