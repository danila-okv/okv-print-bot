from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from modules.billing.ledger import log_print_job
from modules.printing.print_job import PrintJob
from modules.decorators import ensure_data
from modules.printing.print_service import add_job
from modules.billing.services.promo import (
    consume_bonus_pages,
    get_user_bonus_pages,
    get_user_discounts,
    get_promo_reward,
)
from config import (
    IS_DEBUG, DEBUG_PRINT_FILE_PATH, DEBUG_PRINT_FILE_NAME, DEBUG_PAGE_COUNT,
    DEBUG_PRICE
)
from ..messages import *
from ..keyboards.payment import payment_methods_kb, payment_confirm_kb
from ..callbacks import *
from states import UserStates
from modules.analytics.logger import action, warning, error, info
from modules.decorators import check_paused

router = Router()

# Cash payment handler
@router.callback_query(F.data == PAY_CASH)
@check_paused
@ensure_data
async def handle_cash_payment(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.update_data(method="cash")
    await state.set_state(UserStates.confirming_cash_payment)

    await callback.message.edit_text(
        text=get_cash_payment_text(data),
        reply_markup=payment_confirm_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=PAY_CASH,
        msg="Selected Cash payment method"
    )
    await callback.answer()


# Card payment handler
@router.callback_query(F.data == PAY_CARD)
@check_paused
@ensure_data
async def handle_card_payment(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.set_state(UserStates.confirming_cash_payment)
    await state.update_data(method="card")

    await callback.message.edit_text(
        text=get_card_payment_text(data),
        reply_markup=payment_methods_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=PAY_CARD,
        msg="Selected Card payment method"
    )
    await callback.answer()


# Pay with Alfa
@router.callback_query(F.data == PAY_ALFA)
@check_paused
@ensure_data
async def handle_alfa_payment(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.update_data(method="alfa")
    await state.set_state(UserStates.confirming_card_payment)

    await callback.message.edit_text(
        text=get_alfa_payment_text(data),
        reply_markup=payment_confirm_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=PAY_ALFA,
        msg="Selected Alfa payment method"
    )
    await callback.answer()
    


# Pay with Belarusbank
@router.callback_query(F.data == PAY_BELARUSBANK)
@check_paused
@ensure_data
async def handle_belarusbank_payment(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.update_data(method="belarusbank")
    await state.set_state(UserStates.confirming_card_payment)

    await callback.message.edit_text(
        text=get_belarusbank_payment_text(data),
        reply_markup=payment_confirm_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=PAY_BELARUSBANK,
        msg="Selected Belarusbank payment method"
    )
    await callback.answer()

# Pay with Other bank
@router.callback_query(F.data == PAY_OTHER)
@check_paused
@ensure_data
async def handle_other_payment(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.update_data(method="other")
    await state.set_state(UserStates.confirming_card_payment)

    await callback.message.edit_text(
        text=get_other_payment_text(data),
        reply_markup=payment_confirm_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=PAY_OTHER,
        msg="Selected Other payment method"
    )
    await callback.answer()

# Pay confirm
@router.callback_query(F.data == PAY_CONFIRM)
@check_paused
@ensure_data
async def handle_pay_confirm(callback: CallbackQuery, state: FSMContext, data: dict):
    user_id = callback.from_user.id
    file_path = data.get("file_path")
    file_name = data.get("file_name")
    page_count = data.get("page_count")
    duplex = data.get("duplex", False)
    layout = data.get("layout", "1")
    price_data = data.get("price_data")
    pages = data.get("pages")
    copies = data.get("copies", 1)
    method = data.get("method", "cash")

    info(
        callback.from_user.id,
        PAY_CONFIRM,
        "Confirm payment"
    )

    log_print_job(
        user_id=user_id,
        file_name=file_name,
        page_count=page_count,
        price=price_data["final_price"],
        method=method
    )

    # После расчёта цены списываем использованные бонусные страницы из таблицы user_bonus.
    # pages_covered_by_bonus отражает общее количество страниц, покрытых бонусами
    # пользователя и промокодами на бесплатные страницы. Чтобы не списывать бонусы,
    # предоставленные промокодом, определяем их количество и вычитаем.
    try:
        pages_covered = int(price_data.get("pages_covered_by_bonus", 0))
    except Exception:
        pages_covered = 0

    if pages_covered > 0:
        # Текущее количество бонусных страниц у пользователя
        try:
            available_bonus = get_user_bonus_pages(user_id)
        except Exception:
            available_bonus = 0

        # Определяем промокод, который мог быть активирован
        try:
            _, _, used_code = get_user_discounts(user_id)
        except Exception:
            used_code = None

        # Количество страниц, предоставленных промокодом
        promo_pages = 0
        if used_code:
            try:
                reward_type, reward_value = get_promo_reward(used_code)
                if reward_type == "pages":
                    promo_pages = int(reward_value)
            except Exception:
                promo_pages = 0

        # Вычитаем промостраницы из общего покрытия, чтобы понять, сколько списать
        pages_from_user_bonus = max(pages_covered - promo_pages, 0)

        # Не списываем больше, чем есть на балансе
        to_consume = min(available_bonus, pages_from_user_bonus)
        if to_consume > 0:
            try:
                consume_bonus_pages(user_id, to_consume)
            except Exception:
                # Если не удалось списать, продолжаем без ошибки — печать не блокируем
                pass

    job = PrintJob(
        user_id,
        file_path,
        file_name,
        callback.bot,
        page_count,
        duplex,
        layout,
        pages,
        copies
    )
    
    add_job(job)
    info(
        user_id,
        PAY_CONFIRM,
        msg="Add Print Job"
    )

    await state.clear()
    await callback.answer(PAY_SUCCESS_TEXT)