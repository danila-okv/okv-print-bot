"""
Handler for the /gift command.

Originally this handler allowed an administrator to grant a single user
either free print pages or a discount. After selecting the type and
amount, the admin could optionally send a custom notification to the
user.

This implementation has been extended to support granting gifts to
multiple users at once. When the command is invoked without specifying
a user ID (e.g. ``/gift``), the bot will prompt the administrator to
enter a list of user IDs separated by commas or newlines. Valid formats
include:

    ``123, 456, 789`` – commas with optional spaces
    ``123,456,789`` – commas with no spaces
    ``123\n456\n789`` – each ID on a separate line

After receiving the list, the flow proceeds exactly like the single‑user
scenario: the admin chooses a gift type, enters the value, and decides
whether to notify the recipients. The notification message, if sent,
will be delivered to every user in the provided list.

Usage:
    ``/gift <user_id>`` – issue a gift to a single user (legacy behaviour)
    ``/gift`` – prompt for a list of user IDs and issue a gift to all of them
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
import re

from modules.decorators import admin_only
from modules.analytics.logger import action, warning, error, info
from modules.ui.keyboards.tracker import send_managed_message
from states import GiftStates

# Services for updating user bonuses and creating one‑off promo codes
from modules.billing.services.promo import add_user_bonus_pages, record_promo_activation
from modules.admin.services.promo import create_promo

router = Router()

# Gift Command Handler
@router.message(Command("gift"))
@admin_only
async def cmd_gift(message: Message, state: FSMContext):
    """
    Entry point for the /gift command.

    Depending on how the command is invoked, this function will either:

    * Expect a single user ID immediately after the command (legacy usage) and
      proceed directly to the gift type selection; or
    * Prompt the administrator to provide a comma‑ or newline‑separated list
      of user IDs when no ID is supplied, or when a list of IDs is supplied
      inline after the command.

    The FSM state is always cleared at the beginning of this handler to avoid
    interference from previous interactions.
    """
    # Reset any previous state to avoid confusion
    await state.clear()

    # Split the command into the command itself and the remainder
    parts = message.text.strip().split(maxsplit=1)

    # Helper to parse a string of IDs into a list of integers. Returns None on error.
    def parse_id_list(text: str) -> list[int] | None:
        # Normalize semicolons into commas for convenience
        cleaned = text.replace(';', ',')
        # Split by comma or newline
        raw_ids = re.split(r'[\n,]+', cleaned)
        ids: list[int] = []
        for item in raw_ids:
            token = item.strip()
            if not token:
                continue
            if not token.isdigit():
                return None
            ids.append(int(token))
        return ids if ids else None

    # If no additional arguments were provided (e.g. "/gift"), prompt for a list
    if len(parts) < 2:
        await state.set_state(GiftStates.entering_users)
        await message.reply(
            "💬 Введите список ID пользователей, которым хотите выдать подарок.\n"
            "Используйте запятую или перевод строки в качестве разделителя, например:\n"
            "<code>123, 456, 789</code> или <code>123\n456\n789</code>"
        )
        action(
            message.from_user.id,
            "/gift",
            "Prompted admin to enter list of user IDs"
        )
        return

    # Otherwise we have some text after the command; treat pure digits as a single ID
    remainder = parts[1].strip()
    target_user_ids: list[int] | None = None
    if remainder.isdigit():
        # Legacy single‑user behaviour
        target_user_ids = [int(remainder)]
    else:
        # Attempt to parse as a list of IDs
        target_user_ids = parse_id_list(remainder)
        if target_user_ids is None:
            # Could not parse; ask admin to re‑enter list in the next message
            await state.set_state(GiftStates.entering_users)
            await message.reply(
                "❌ Не удалось распознать список ID.\n"
                "Пожалуйста, введи их через запятую или перевод строки, например:\n"
                "<code>123, 456, 789</code> или <code>123\n456\n789</code>"
            )
            warning(
                message.from_user.id,
                "/gift",
                f"Invalid ID list provided: {remainder}"
            )
            return

    # Store the list and also the first ID for backwards compatibility
    await state.update_data(target_user_ids=target_user_ids, target_user_id=target_user_ids[0])
    await state.set_state(GiftStates.choosing_type)

    # Prepare inline keyboard for gift type selection
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Страницы", callback_data="gift_pages"),
                InlineKeyboardButton(text="💸 Скидка", callback_data="gift_discount")
            ]
        ]
    )

    # Compose recipient summary: list IDs if there are few, otherwise summarise count
    if len(target_user_ids) == 1:
        recipients_text = f"пользователю <code>{target_user_ids[0]}</code>"
    elif len(target_user_ids) <= 5:
        formatted = ', '.join(f"<code>{uid}</code>" for uid in target_user_ids)
        recipients_text = f"пользователям {formatted}"
    else:
        recipients_text = f"{len(target_user_ids)} пользователям"

    await message.answer(
        f"Вы выдаёте подарок {recipients_text}.\n"
        "Выберите тип подарка:",
        reply_markup=kb
    )
    action(
        message.from_user.id,
        "/gift",
        f"Select gift type for users {target_user_ids}"
    )

# --- New handler: entering list of users ---
@router.message(GiftStates.entering_users)
@admin_only
async def gift_enter_users(message: Message, state: FSMContext):
    """
    Handler for the state where an administrator enters a list of user IDs.

    This state is entered when the /gift command is issued without specifying
    any user IDs. The admin is expected to provide a comma‑ or newline‑separated
    list of numeric IDs. Upon successful parsing, the FSM transitions to
    ``choosing_type`` and displays the gift type selection inline keyboard.
    """
    text = message.text.strip()

    # Helper to parse the provided list into integers
    def parse_id_list(text: str) -> list[int] | None:
        cleaned = text.replace(';', ',')
        raw_ids = re.split(r'[\n,]+', cleaned)
        ids: list[int] = []
        for item in raw_ids:
            token = item.strip()
            if not token:
                continue
            if not token.isdigit():
                return None
            ids.append(int(token))
        return ids if ids else None

    user_ids = parse_id_list(text)
    if user_ids is None:
        await message.reply(
            "❌ Не удалось распознать список ID.\n"
            "Пожалуйста, введи их через запятую или перевод строки, например:\n"
            "<code>123, 456, 789</code> или <code>123\n456\n789</code>"
        )
        warning(
            message.from_user.id,
            "/gift",
            f"Invalid ID list provided: {text}"
        )
        return

    # Store the parsed IDs and first ID for compatibility
    await state.update_data(target_user_ids=user_ids, target_user_id=user_ids[0])
    await state.set_state(GiftStates.choosing_type)

    # Prepare gift type selection keyboard
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Страницы", callback_data="gift_pages"),
                InlineKeyboardButton(text="💸 Скидка", callback_data="gift_discount")
            ]
        ]
    )

    # Compose summary similar to cmd_gift
    if len(user_ids) == 1:
        recipients_text = f"пользователю <code>{user_ids[0]}</code>"
    elif len(user_ids) <= 5:
        formatted = ', '.join(f"<code>{uid}</code>" for uid in user_ids)
        recipients_text = f"пользователям {formatted}"
    else:
        recipients_text = f"{len(user_ids)} пользователям"

    await message.reply(
        f"Вы выдаёте подарок {recipients_text}.\n"
        "Выберите тип подарка:",
        reply_markup=kb
    )
    action(
        message.from_user.id,
        "/gift",
        f"Select gift type for users {user_ids}"
    )


# Gift type selection
@router.callback_query(GiftStates.choosing_type, F.data.in_({"gift_pages", "gift_discount"}))
@admin_only
async def gift_choose_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    reward_type = "pages" if callback.data == "gift_pages" else "discount"
    await state.update_data(reward_type=reward_type)
    await state.set_state(GiftStates.entering_value)

    # When prompting for the value we avoid mentioning "пользователю", because
    # the gift may be applied to multiple recipients.
    prompt = (
        "Введите количество бесплатных страниц, которые хотите выдать:" if reward_type == "pages"
        else "Введите процент скидки (от 1 до 100), который хотите выдать:"
    )
    await callback.message.edit_text(prompt)
    info(
        callback.from_user.id,
        "/gift",
        f"Gift type selected: {reward_type}"
    )
    await callback.answer()


# Gift enter value
@router.message(GiftStates.entering_value)
@admin_only
async def gift_enter_value(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", ".").replace(" ", "")
    data = await state.get_data()
    reward_type = data.get("reward_type")

    # Parse the number
    try:
        value = float(text.rstrip("%"))
    except ValueError:
        await message.reply("❌ Введи корректное число")
        warning(
            message.from_user.id,
            "/gift",
            f"Invalid value input: {text}"
        )
        return

    if reward_type == "discount":
        # Discount should be between 1 and 100
        if value <= 0 or value > 100:
            await message.reply("❌ Скидка должна быть в диапазоне от 1 до 100")
            warning(
                message.from_user.id,
                "/gift",
                f"Discount out of range: {value}"
            )
            return
    else:
        # Pages should be positive integer
        if value <= 0 or int(value) != value:
            await message.reply("❌ Количество страниц должно быть положительным целым числом")
            warning(
                message.from_user.id,
                "/gift",
                f"Invalid pages count: {value}"
            )
            return

    await state.update_data(reward_value=value)
    target_user_id = data["target_user_id"]

    # Apply the gift immediately
    try:
        if reward_type == "pages":
            add_user_bonus_pages(target_user_id, int(value))
            info(
                message.from_user.id,
                "/gift",
                f"Granted {int(value)} bonus pages to {target_user_id}"
            )
        else:
            # Create a one‑off promo code and activate it for the user
            # Use timestamp to ensure uniqueness
            code = f"GIFT{datetime.now().strftime('%Y%m%d%H%M%S')}{target_user_id}"
            # One activation only; no global expiry; no duration
            create_promo(
                code=code,
                activations_total=1,
                reward_type="discount",
                reward_value=value,
                expires_at=None,
                duration_days=None,
                message_template=None,
            )
            record_promo_activation(target_user_id, code)
            info(
                message.from_user.id,
                "/gift",
                f"Granted {value}% discount to {target_user_id} via promo {code}"
            )
    except Exception as e:
        await message.reply(f"❌ Не удалось выдать подарок: {e}")
        error(
            message.from_user.id,
            "/gift",
            f"Failed to apply gift: {e}"
        )
        await state.clear()
        return

    # Ask whether to notify user
    await state.set_state(GiftStates.notify_choice)
    notify_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔔 Уведомить", callback_data="gift_notify_yes"),
                InlineKeyboardButton(text="🚫 Не уведомлять", callback_data="gift_notify_no")
            ]
        ]
    )
    await message.reply(
        "✅ Подарок успешно начислен! Нужно ли отправить уведомление пользователю?",
        reply_markup=notify_kb
    )
    action(
        message.from_user.id,
        "/gift",
        f"Gift applied to {target_user_id}, awaiting notify choice"
    )


@router.callback_query(GiftStates.notify_choice, F.data == "gift_notify_no")
@admin_only
async def gift_notify_skip(callback: CallbackQuery, state: FSMContext):
    """
    Admin chose not to notify the user. End the FSM.
    """
    await callback.message.edit_text("✅ Подарок начислен.")
    await state.clear()
    action(
        callback.from_user.id,
        "/gift",
        "Gift process finished without notification"
    )
    await callback.answer()


@router.callback_query(GiftStates.notify_choice, F.data == "gift_notify_yes")
@admin_only
async def gift_notify_yes(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiftStates.entering_message)
    await callback.message.edit_text(
        "Введите текст сообщения, которое отправится пользователю."
    )
    action(
        callback.from_user.id,
        "/gift",
        "Admin will enter custom notify message"
    )
    await callback.answer()


@router.message(GiftStates.entering_message)
@admin_only
async def gift_notify_send(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    text = message.text
    try:
        await send_managed_message(
            bot=message.bot,
            user_id=target_user_id,
            text=text
        )
        await message.reply("✅ Уведомление отправлено.")
        action(
            message.from_user.id,
            "/gift",
            f"Notification sent to {target_user_id}: {text}"
        )
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить уведомление: {e}")
        error(
            message.from_user.id,
            "/gift",
            f"Failed to notify user {target_user_id}: {e}"
        )
    await state.clear()