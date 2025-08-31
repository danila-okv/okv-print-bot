from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import UserStates
from modules.decorators import ensure_data
from modules.decorators import check_paused
from modules.analytics.logger import action, warning, error
from ..keyboards.review import review_kb
from ..keyboards.payment import payment_methods_kb
from ..keyboards.options import get_print_options_kb
from ..messages import (
    get_print_options_text
)
from modules.billing.services.calculate_price import calculate_price
from modules.billing.services.promo import get_user_discounts
from ..callbacks import CONFIRM
from utils.parsers import parse_pages_str
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(F.data == CONFIRM)
@check_paused
@ensure_data
async def handle_confirm(callback: CallbackQuery, state: FSMContext, data: dict):
    current = await state.get_state()
    print(f"Current state: {current}")
    if current == UserStates.inputting_copies_count:
        copies = data.get("copies", 1)
        if not isinstance(copies, int) or copies <= 0:
            await callback.answer("Количество копий должно быть положительным числом.")
            warning(
                callback.from_user.id,
                handler=CONFIRM,
                msg=f"Invalid copies count: {copies}"
            )
            return

        await state.update_data(copies=copies)

        bonus_pages, discount_percent, promo_code = get_user_discounts(callback.from_user.id)

        page_range = data.get("pages") or f"1-{data['page_count']}"
        layout = data.get("layout", "1")

        price_data = calculate_price(
            page_range=page_range,
            layout=layout,
            copies=copies,
            bonus_pages=bonus_pages,
            discount_percent=discount_percent
        )

        await state.update_data(price_data=price_data)
        data = await state.get_data()

        try:
            if price_data.get("final_price", 0) == 0:
                await state.update_data(method="free")
            else:
                await state.update_data(method=None)

            await callback.message.edit_text(
                text=get_print_options_text(data),
                reply_markup=review_kb(data)
            )
        except TelegramBadRequest as e:
            await callback.message.answer(f"Ошибка при обновлении текста: {e}")
            error(
                callback.from_user.id,
                CONFIRM,
                f"Error updating text: {e}"
            )
            return

        await state.set_state(UserStates.setting_print_options)
        action(
            callback.from_user.id,
            CONFIRM,
            f"Copies count confirmed: {copies}"
        )
        return await callback.answer()
    
    if current == UserStates.inputting_pages:
        pages = data.get("pages", "")
        if not parse_pages_str(pages):
            await callback.message.answer("Некорректный диапазон страниц.")
            warning(
                callback.from_user.id,
                handler=CONFIRM,
                msg=f"Invalid page range: {pages}"
            )
            return

        await state.update_data(pages=pages)
        data = await state.get_data()

        bonus_pages, discount_percent, promo_code = get_user_discounts(callback.from_user.id)

        page_range = data.get("pages") or f"1-{data['page_count']}"
        layout = data.get("layout", "1")
        copies = data.get("copies", 1)

        price_data = calculate_price(
            page_range=page_range,
            layout=layout,
            copies=copies,
            bonus_pages=bonus_pages,
            discount_percent=discount_percent
        )

        await state.update_data(price_data=price_data)
        data = await state.get_data()

        try:
            if price_data.get("final_price", 0) == 0:
                await state.update_data(method="free")
            else:
                await state.update_data(method=None)
            await callback.message.edit_text(
                text=get_print_options_text(data),
                reply_markup=review_kb(data)
            )
        except TelegramBadRequest as e:
            await callback.message.answer(f"Ошибка при обновлении текста: {e}")
            error(
                callback.from_user.id,
                handler=CONFIRM,
                msg=f"Error updating text: {e}"
            )
            return

        await state.set_state(UserStates.setting_print_options)
        action(
            callback.from_user.id,
            CONFIRM,
            f"Pages confirmed: {pages}"
        )
        return await callback.answer()