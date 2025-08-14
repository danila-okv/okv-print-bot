"""
Handler for /gift command allowing an administrator to grant a user either
free print pages or a discount. After selecting the type and amount,
the admin can optionally send a custom notification to the user.

Usage: /gift <user_id>
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

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
    parts = message.text.strip().split()

    if len(parts) < 2:
        await message.reply("⚠️ Использование: /gift &lt;user_id&gt; (перечисление через запятую)")
        warning(
            message.from_user.id,
            "/gift",
            "Missing user ID"
        )
        return
    
    parts.pop(0)
    parts = list(set(parts))

    for part in parts:
        if not part.isdigit():
            await message.reply("⚠️ Использование: /gift &lt;user_id&gt;")
            warning(
                message.from_user.id,
                "/gift",
                f"Invalid user ID: {part}"
            )
            return

    await state.clear()
    await state.update_data(gift_targets=parts)
    await state.set_state(GiftStates.choosing_type)

    # Ask admin which type of gift to grant
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Страницы", callback_data="gift_pages"),
                InlineKeyboardButton(text="💸 Скидка", callback_data="gift_discount")
            ]
        ]
    )

    
    await message.answer(
        f"Выдача подарка пользователю: <code>{parts[0]}</code>.\n" if len(parts) == 1 else f"Выдача подарков пользователям: <code>{", ".join(parts)}</code>.\n"
        "Выберите тип подарка:",
        reply_markup=kb
    )
    action(
        message.from_user.id,
        "/gift",
        f"Select gift type for users {parts.join(', ')}"
    )


# Gift type selection
@router.callback_query(GiftStates.choosing_type, F.data.in_({"gift_pages", "gift_discount"}))
@admin_only
async def gift_choose_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    reward_type = "pages" if callback.data == "gift_pages" else "discount"
    await state.update_data(reward_type=reward_type)
    await state.set_state(GiftStates.entering_value)

    prompt = (
        "Введи количество бесплатных страниц к выдаче:" if reward_type == "pages"
        else "Введи процент скидки (от 1 до 100):"
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
    gift_targets = data["gift_targets"]

    for target_user_id in gift_targets:
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

    gift_targets = data.get("gift_targets", [])
    text = message.text
    
    for target_user_id in gift_targets:
        if not target_user_id.isdigit():
            await message.reply(f"❌ Некорректный user_id: {target_user_id}")
            warning(
                message.from_user.id,
                "/gift",
                f"Invalid user ID in targets: {target_user_id}"
            )
            return

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