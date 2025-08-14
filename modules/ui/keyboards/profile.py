from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..callbacks import ORDERS, MAIN_MENU, PROFILE
from .buttons import BUTTON_ORDERDS, BUTTON_BACK

"""
Клавиатура профиля содержит кнопку для просмотра истории заказов и кнопку возврата
в главное меню. Для возврата используем callback MAIN_MENU, чтобы сработал
обработчик главного меню и корректно обновил сообщение. SECOND button text uses
standard BACK caption from buttons, но в этом контексте он возвращает в
главное меню, а не в предыдущий шаг печати.
"""

profile_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_ORDERDS, callback_data=ORDERS),
            InlineKeyboardButton(text=BUTTON_BACK, callback_data=MAIN_MENU)
        ]
    ]
)
