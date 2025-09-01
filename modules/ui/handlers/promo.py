from aiogram import Router, F
from aiogram.types import Message
from modules.billing.services.promo import (
    promo_exists,
    promo_can_be_activated,
    has_activated_promo,
    record_promo_activation,
    add_user_bonus_pages,
    get_promo_info,
)
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.ui.keyboards.tracker import send_managed_message

router = Router()

@router.message(F.text.regexp(r"^[\w\dа-яА-ЯёЁ]{3,30}$"))
async def handle_promo_code_input(message: Message):
    code = message.text.strip()

    if not promo_exists(code):
        return  # Просто пропускаем — пусть другие обработчики ловят как обычный текст

    user_id = message.from_user.id

    if has_activated_promo(user_id, code):
        await message.answer("⚠️ Ты уже активировал этот промокод")
        return

    if not promo_can_be_activated(code):
        await message.answer("❌ Этот промокод больше не активен")
        return

    # Получаем полную информацию о промокоде, включая шаблон сообщения и срок действия
    info_data = get_promo_info(code)
    if not info_data:
        return

    reward_type = info_data["reward_type"]
    reward_value = info_data["reward_value"]
    duration_days = info_data.get("duration_days")
    message_template = info_data.get("message_template")
    expires_at = info_data.get("expires_at")

    # Фиксируем активацию промокода
    record_promo_activation(user_id, code)

    # Применяем бонусные страницы при необходимости
    if reward_type == "pages":
        add_user_bonus_pages(user_id, int(reward_value))

    # Формируем сообщение для пользователя
    if message_template:
        # Заполняем плейсхолдеры {value} и {date}
        # значение скидки/страниц
        value_str = str(int(reward_value)) if reward_type == "pages" else str(int(reward_value))
        # дата окончания действия
        expiry_str = ""
        if duration_days:
            try:
                from datetime import datetime, timedelta
                expiry_date = datetime.now() + timedelta(days=int(duration_days))
                expiry_str = expiry_date.strftime("%Y-%m-%d")
            except Exception:
                expiry_str = ""
        elif expires_at:
            expiry_str = expires_at.split("T")[0] if "T" in expires_at else expires_at
        else:
            expiry_str = ""

        try:
            text = message_template.format(value=value_str, date=expires_at.strftime("%d.%m.%Y"))
        except Exception:
            # Если форматирование не удалось — отправим шаблон как есть
            text = message_template
    else:
        # Стандартные сообщения, если шаблон не задан
        if reward_type == "pages":
            text = (
                f"🎉 Промокод <b>{code}</b> активирован!\n"
                f"Ты получил <b>{int(reward_value)}</b> бесплатных страниц"
            )
        else:
            text = (
                f"🎉 Промокод <b>{code}</b> активирован!\n"
                f"Ты получил скидку <b>{int(reward_value)}%</b>"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Понятно, спасибо!",
                    callback_data="main_menu"
                )
            ]
        ]
    )

    await send_managed_message(
        bot=message.bot,
        user_id=user_id,
        text=text,
        reply_markup=kb
    )