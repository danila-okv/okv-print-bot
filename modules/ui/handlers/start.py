from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from ..messages import *
from ..keyboards.main_menu import main_menu_kb
from ..callbacks import MAIN_MENU, DONE
from modules.analytics.logger import action
from ..keyboards.tracker import send_managed_message
from config import FREE_PAGES_ON_REGISTER
from modules.billing.services.promo import add_user_bonus_pages
from db import get_connection

router = Router()

# Handle Bot state reset and send Main menu

@router.callback_query(F.data == DONE)
async def handle_done(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    # Award free pages on first interaction if configured
    
    await send_main_menu(callback.bot, user_id)
    action(
        user_id=user_id,
        handler="Command /start",
        msg="User started bot"
    )

    if FREE_PAGES_ON_REGISTER and FREE_PAGES_ON_REGISTER > 0:
        try:
            # Check whether the user already exists in the bonus table.  We only
            # insert when there's no record at all (so we don't award free pages
            # again after they are consumed).
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM user_bonus WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
            if row is None:
                add_user_bonus_pages(user_id, FREE_PAGES_ON_REGISTER)
                
                await callback.message.answer(
                    text=f"👋 Почему бы и нет? Лови <b>{FREE_PAGES_ON_REGISTER}</b> бесплатных страниц 🎁"
                )
        except Exception:
            # Silently ignore any errors when awarding free pages
            pass

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    # Award free pages on first interaction if configured
    
    await send_main_menu(message.bot, user_id)
    action(
        user_id=user_id,
        handler="Command /start",
        msg="User started bot"
    )

    if FREE_PAGES_ON_REGISTER and FREE_PAGES_ON_REGISTER > 0:
        try:
            # Check whether the user already exists in the bonus table.  We only
            # insert when there's no record at all (so we don't award free pages
            # again after they are consumed).
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM user_bonus WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
            if row is None:
                add_user_bonus_pages(user_id, FREE_PAGES_ON_REGISTER)
                
                await message.answer(
                    text=f"👋 Почему бы и нет? Лови <b>{FREE_PAGES_ON_REGISTER}</b> бесплатных страниц 🎁"
                )
        except Exception:
            # Silently ignore any errors when awarding free pages
            pass

# Handle Main menu callback
@router.callback_query(F.data == MAIN_MENU)
async def handle_main_menu(callback: CallbackQuery):
    await send_managed_message(
        bot=callback.bot,
        user_id=callback.from_user.id,
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_kb
    )
    action(
        user_id=callback.from_user.id,
        handler="Main menu",
        msg="Send main menu"
    )

async def send_main_menu(bot: Bot, user_id: int):
    await send_managed_message(
        bot=bot,
        user_id=user_id,
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_kb
    )
