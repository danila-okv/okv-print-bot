from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from ..messages import *
from ..keyboards.main_menu import main_menu_kb
from ..callbacks import MAIN_MENU
from modules.analytics.logger import action
from ..keyboards.tracker import send_managed_message

router = Router()

# Handle Bot state reset and send Main menu
@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    
    await send_main_menu(message.bot, message.from_user.id)
    action(
        user_id=message.from_user.id,
        handler="Command /start",
        msg="User started bot"
    )

# Handle Main menu callback
@router.callback_query(F.data == MAIN_MENU)
async def handle_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_kb
    )
    action(
        user_id=callback.from_user.id,
        handler="Main menu",
        msg="Send main menu"
    )

async def send_main_menu(bot: Bot, user_id: int, total_pages: int = 0):
    await send_managed_message(
        bot=bot,
        user_id=user_id,
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_kb
    )
