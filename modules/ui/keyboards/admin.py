from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .buttons import (
    BUTTON_ADMIN_DISCOUNT, BUTTON_ADMIN_BONUS_PAGES
)

from ..callbacks import (
    ADMIN_DISCOUNT, ADMIN_BONUS_PAGES
)

promo_type_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_ADMIN_BONUS_PAGES, callback_data=ADMIN_BONUS_PAGES),
            InlineKeyboardButton(text=BUTTON_ADMIN_DISCOUNT, callback_data=ADMIN_DISCOUNT)
        ],
    ]
)