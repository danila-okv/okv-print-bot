from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import UserStates
from modules.decorators import ensure_data
from modules.decorators import check_paused
from ..keyboards.review import review_kb
from ..keyboards.payment import payment_methods_kb
from ..keyboards.options import get_print_options_kb
from ..messages import *
from ..callbacks import BACK
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(F.data == BACK)
@check_paused
@ensure_data
async def handle_back(callback: CallbackQuery, state: FSMContext, data: dict):
    current = await state.get_state()

    if current == UserStates.setting_print_options:
        await state.set_state(UserStates.reviewing_print_details)

        await callback.message.edit_text(
            text=format_print_text(data),
            reply_markup=review_kb(data)
        )
        return await callback.answer()
    
    # Handle return from Page range or Layout options
    if current == UserStates.inputting_pages or current == UserStates.selecting_print_layout:
        await state.set_state(UserStates.setting_print_options)
        duplex = data.get("duplex", False)

        await callback.message.edit_text(
            text=get_print_options_text(data),
            reply_markup=get_print_options_kb(duplex)
        )
        return await callback.answer()
    
    # Handle return from Cash confirmation
    if current == UserStates.confirming_cash_payment:
        await state.set_state(UserStates.reviewing_print_details)

        await callback.message.edit_text(
            text=get_details_review_text(data),
            reply_markup=review_kb(data)
        )
        return await callback.answer()
    
    if current == UserStates.confirming_card_payment and data["method"] == "card":
        await state.set_state(UserStates.reviewing_print_details)

        await callback.message.edit_text(
            text=get_details_review_text(data),
            reply_markup=review_kb(data)
        )
        return await callback.answer()
    
    if current == UserStates.confirming_card_payment and data["method"] != "card":
        await state.update_data(method="card")

        await callback.message.edit_text(
            text=get_card_payment_text(data),
            reply_markup=payment_methods_kb
        )
        return await callback.answer()

    if current == UserStates.inputting_copies_count:

        await state.update_data(copies=1)
        await callback.message.edit_text(
            text=get_print_options_text(data),
            reply_markup=get_print_options_kb(data.get("duplex", False))
        )
        return await callback.answer()