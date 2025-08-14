from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from modules.decorators import ensure_data
from states import UserStates
from ..keyboards.common import back_kb
from ..keyboards.options import get_print_options_kb, get_print_layouts_kb, confirm_kb
from ..keyboards.tracker import send_managed_message
from modules.printing.pdf_utils import get_orientation_ranges
from modules.analytics.logger import action, warning, error, info
from modules.billing.services.calculate_price import calculate_price
from modules.billing.services.promo import get_user_discounts
from modules.decorators import check_paused
from utils.parsers import parse_pages_str


from ..messages import (
    get_print_options_text, get_layout_selection_text, get_pages_input_text,
    get_copies_input_text

)
from ..callbacks import (
    PRINT_OPTIONS, OPTION_DUPLEX, OPTION_LAYOUT, OPTION_PAGES,
    OPTION_COPIES, LAYOUTS
)

router = Router()

# Handle Options
@router.callback_query(F.data == PRINT_OPTIONS)
@check_paused
@ensure_data
async def handle_print_options(callback: CallbackQuery, state: FSMContext, data: dict):    
    await state.set_state(UserStates.setting_print_options)
    duplex = data.get("duplex", False)

    await callback.message.edit_text(
        text = get_print_options_text(data),
        reply_markup=get_print_options_kb(duplex)
    )
    action(
        user_id=callback.from_user.id,
        handler=PRINT_OPTIONS,
        msg="Started Option selection"
    )
    await callback.answer()

# Handle Duplex option
@router.callback_query(F.data == OPTION_DUPLEX)
@check_paused
@ensure_data
async def handle_option_duplex(callback: CallbackQuery, state: FSMContext, data: dict):
    new = not data.get("duplex", False)

    orientation_ranges = get_orientation_ranges(data.get("file_path", ""))
    if len(orientation_ranges) > 1:
        await callback.message.answer(
            "❗️ Твой файл содержит страницы с разной ориентацией\n"
            "Из-за чего двусторонняя печать не работает"
        )
        return


    await state.update_data(duplex=new)
    data["duplex"] = new

    
    await callback.message.edit_text(
        text=get_print_options_text(data),
        reply_markup=get_print_options_kb(new)
        )
    action(
        user_id=callback.from_user.id,
        handler=OPTION_DUPLEX,
        msg="Switched duplex option"
    )
    await callback.answer()

# Handle Layout option
@router.callback_query(F.data == OPTION_LAYOUT)
@check_paused
@ensure_data
async def handle_option_layout(callback: CallbackQuery, state: FSMContext, data: dict):
    layout = data.get("layout", "1")
    await callback.message.edit_text(
        text = get_layout_selection_text(data),
        reply_markup=get_print_layouts_kb(layout)
    )
    action(
        user_id=callback.from_user.id,
        handler=OPTION_LAYOUT,
        msg="Show layouts"
    )
    await callback.answer()

# Handle Layouts selection
@router.callback_query(F.data.in_(LAYOUTS))
@check_paused
@ensure_data
async def handle_layout_selection(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.update_data(layout=callback.data)
    data = await state.get_data()

    bonus_pages, discount_percent, promo_code = get_user_discounts(callback.from_user.id)

    page_range = data.get("pages") or f"1-{data['page_count']}"
    layout = int(data.get("layout"), "1")
    copies = data.get("copies", 1)

    price_data = calculate_price(
        page_range=page_range,
        layout=layout,
        copies=copies,
        bonus_pages=bonus_pages,
        discount_percent=discount_percent
    )

    await state.update_data(price_data=price_data)


    await callback.message.edit_text(
        text=get_layout_selection_text(data),
        reply_markup=get_print_layouts_kb(callback.data)
    )
    await callback.answer()

    action(
        callback.from_user.id,
        "print_layout",
        f"Select layout - {callback.data}"
    )

# Handle Copies option
@router.callback_query(F.data == OPTION_COPIES)
@check_paused
@ensure_data
async def handle_copies_selection(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.set_state(UserStates.inputting_copies_count)

    await callback.message.edit_text(
        text=get_copies_input_text(data),
        reply_markup=back_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=OPTION_COPIES,
        msg="Select Copies option"
    )

    await callback.answer()

# Handle Copies input
@router.message(UserStates.inputting_copies_count)
@check_paused
@ensure_data
async def handle_copies_input(message: Message, state: FSMContext, data: dict):
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("❌ Введите только число, например: 2")
        warning(
            message.from_user.id,
            "copies_input",
            f"Invalid input for copies: {text} (expected a number)",
            f"Input: {text}"
        )
        return

    copies = int(text)
    if copies < 1 or copies > 50:
        await message.answer("❌ Количество копий должно быть от 1 до 50")
        warning(
            message.from_user.id,
            "copies_input",
            f"Invalid copies count: {copies} (expected 1-50)",
            f"Input: {text}"
        )
        return

    await state.update_data(copies=copies)

    await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text=f"Количество копий установлено: {copies}",
        reply_markup=confirm_kb
    )
    
    action(
        message.from_user.id,
        "copies_input",
        f"Set copies count: {copies}"
    )
    

# Handle Pages option
@router.callback_query(F.data == OPTION_PAGES)
@check_paused
@ensure_data
async def handle_pages_selection(callback: CallbackQuery, state: FSMContext, data: dict):
    await state.set_state(UserStates.inputting_pages)

    await callback.message.edit_text(
        text=get_pages_input_text(data),
        reply_markup=back_kb
    )
    action(
        user_id=callback.from_user.id,
        handler=OPTION_PAGES,
        msg="Select Pages option"
    )

    callback.answer()

# Handle Page ranges input
@router.message(UserStates.inputting_pages)
@check_paused
@ensure_data
async def handle_pages_input(message: Message, state: FSMContext, data: dict):
    text = message.text.strip()

    page_count = data.get("page_count", 0)

    try:
        pages = parse_pages_str(text, page_count)
        await state.update_data(pages=pages)
        
        await send_managed_message(
            bot=message.bot,
            user_id=message.from_user.id,
            text=f"Приняты страницы: {pages}",
            reply_markup=confirm_kb
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")