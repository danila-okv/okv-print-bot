# handlers/payment.py

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from messages import *
from keyboards import main_menu_keyboard
from callbacks import *

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Состояния FSM
# ─────────────────────────────────────────────────────────────────────────────
class PaymentMethod(StatesGroup):
    waiting_for_method = State()


# ─────────────────────────────────────────────────────────────────────────────
# Кнопки первого выбора: наличные / карта / отмена
# ─────────────────────────────────────────────────────────────────────────────
def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_METHOD_CASH, callback_data=PAY_CASH),
            InlineKeyboardButton(text=BUTTON_METHOD_CARD, callback_data="pay_card")
        ],
        [
            InlineKeyboardButton(text=BUTTON_CANCEL, callback_data="cancel")
        ]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Кнопка: Я оплатил (для карты)
# ─────────────────────────────────────────────────────────────────────────────
def get_card_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BUTTON_CONFIRM_PAYMENT, callback_data="confirm_payment")]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Кнопка: Подтвердить (для наличных)
# ─────────────────────────────────────────────────────────────────────────────
def get_cash_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_payment")]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# 💳 Выбран способ: Перевод на счёт
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == PAY_CARD)
async def handle_card_payment(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        text=PAYMENT_CARD_TEXT,
        reply_markup=get_card_confirm_keyboard()
    )


# ─────────────────────────────────────────────────────────────────────────────
# 💵 Выбран способ: Наличные
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == PAY_CASH)
async def handle_cash_payment(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        text=PAYMENT_CASH_TEXT,
        reply_markup=get_cash_confirm_keyboard()
    )