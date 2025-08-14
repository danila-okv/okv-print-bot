from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup

from modules.ui.keyboards.admin import promo_type_kb
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.ui.keyboards.tracker import send_managed_message
from modules.admin.services.promo import create_promo, promo_exists
from modules.decorators import admin_only
from states import PromoStates
from datetime import datetime

router = Router()


@router.message(Command("promo"))
@admin_only
async def cmd_promo(message: Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        # Выводим параметр в угловых скобках, но экранируем его: &lt;код&gt;
        return await message.reply("⚠️ Использование: /promo &lt;код&gt;")

    code = parts[1].strip()

    if promo_exists(code):
        return await message.reply(f"❌ Промокод <b>{code}</b> уже существует")
    
    await state.update_data(code=code)
    await state.set_state(PromoStates.choosing_type)

    await send_managed_message(
        message.bot,
        message.from_user.id,
        f"Вы создали новый промокод: <b>{code}</b>\n"
             "Теперь выбери тип награды для этого промокода.",
        promo_type_kb
    )

@router.callback_query(PromoStates.choosing_type)
async def promo_choose_type(callback: CallbackQuery, state: FSMContext):
    """
    Сохраняет выбранный тип награды. Значения callback.data приходят из promo_type_kb:
    ADMIN_BONUS_PAGES или ADMIN_DISCOUNT. Преобразуем их в 'pages' или 'discount'.
    """
    reward_type_raw = callback.data
    reward_type = "pages" if reward_type_raw == "bonus_pages" else "discount"
    await state.update_data(reward_type=reward_type)
    await state.set_state(PromoStates.entering_activations)
    await callback.message.edit_text("Введи общее количество активаций промокода:")

@router.message(PromoStates.entering_activations)
async def promo_enter_activations(message: Message, state: FSMContext):
    """Обрабатывает ввод общего числа активаций промокода."""
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError()
    except Exception:
        return await message.reply("❌ Введи положительное число активаций")

    await state.update_data(activations_total=count)
    data = await state.get_data()
    if data['reward_type'] == 'pages':
        await message.answer("Введи количество страниц в качестве награды:")
    else:
        await message.answer("Введи процент скидки (от 1 до 100), который будет предоставляться:")
    await state.set_state(PromoStates.entering_reward_value)

@router.message(PromoStates.entering_reward_value)
async def promo_enter_reward_value(message: Message, state: FSMContext):
    """Обрабатывает ввод значения награды (количество страниц или процент скидки)."""
    text = message.text.strip().replace(",", ".").replace(" ", "")
    # Убираем знак процента, если он введён
    if text.endswith("%"):
        text = text[:-1]

    data = await state.get_data()
    reward_type = data.get('reward_type')
    try:
        value = float(text)
    except ValueError:
        await message.reply("❌ Введи корректное число")
        return

    if reward_type == 'discount':
        # Скидка должна быть от 1 до 100
        if value <= 0 or value > 100:
            await message.reply("❌ Скидка должна быть от 1 до 100")
            return
    else:
        # Количество страниц должно быть положительным целым
        if value <= 0 or int(value) != value:
            await message.reply("❌ Количество страниц должно быть положительным целым")
            return

    await state.update_data(reward_value=value)
    # Для скидки запрашиваем срок действия, для страниц срок не ограничен
    if reward_type == 'discount':
        await state.set_state(PromoStates.entering_duration)
        await message.answer(
            "Введите срок действия промокода в днях (например, 7)\n"
            "или напишите «нет», чтобы сделать его бессрочным:"
        )
    else:
        # Для страниц срок действия всегда бессрочный
        await state.update_data(duration_days=None)
        await state.set_state(PromoStates.entering_message)
        await message.answer(
            "Введите сообщение для пользователя, которое будет отправляться при активации промокода.\n"
            "Используйте {value} для подстановки значения награды.\n"
            "Если шаблон не нужен, напишите «нет»."
        )

@router.message(PromoStates.entering_duration)
async def promo_enter_duration(message: Message, state: FSMContext):
    """Обрабатывает ввод срока действия промокода (количество дней)."""
    text = message.text.strip().lower()
    if text in ("нет", "none", "-"):
        duration = None
    else:
        try:
            duration_int = int(text)
            if duration_int < 1:
                raise ValueError()
            duration = duration_int
        except Exception:
            return await message.reply("❌ Введи положительное число дней или 'нет'")

    await state.update_data(duration_days=duration)
    # Переходим к вводу шаблона сообщения
    await state.set_state(PromoStates.entering_message)
    await message.answer(
        "Введите сообщение для пользователя, которое будет отправляться при активации промокода.\n"
        "Используйте {value} для подстановки значения награды и {date} для даты окончания действия.\n"
        "Если шаблон не нужен, напишите «нет»."
    )

@router.message(PromoStates.entering_message)
async def promo_enter_message(message: Message, state: FSMContext):
    """Сохраняет текст шаблона сообщения и формирует подтверждение."""
    text = message.text
    if text.strip().lower() in ("нет", "none", "-"):
        template = None
    else:
        template = text
    await state.update_data(message_template=template)
    data = await state.get_data()
    # Формируем текст подтверждения
    type_text = 'Страницы' if data['reward_type'] == 'pages' else 'Скидка'
    value_text = data['reward_value']
    activations = data['activations_total']
    duration = data.get('duration_days')
    duration_text = f"{duration} дн." if duration else 'Бессрочный'
    template_text = template if template else 'Стандартное'
    confirm_text = (
        f"Подтверди создание промокода:\n\n"
        f"🔑 <b>{data['code']}</b>\n"
        f"🎁 Тип: {type_text}\n"
        f"📊 Значение: {value_text}\n"
        f"🔁 Активаций: {activations}\n"
        f"⏳ Срок действия: {duration_text}\n"
        f"📝 Шаблон сообщения: {template_text}\n\n"
        "Подтвердить?"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_promo")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_promo")],
        ]
    )
    await state.set_state(PromoStates.confirming)
    await message.answer(confirm_text, reply_markup=kb)



@router.callback_query(PromoStates.confirming)
async def promo_final_confirm(callback: CallbackQuery, state: FSMContext):
    # Если администратор нажал отмену — завершаем работу
    if callback.data == "cancel_promo":
        await state.clear()
        await callback.message.edit_text("🚫 Отменено.")
        return

    data = await state.get_data()
    # Создаём промокод с учётом новых полей: срок действия и шаблон сообщения
    create_promo(
        code=data['code'],
        activations_total=data['activations_total'],
        reward_type=data['reward_type'],
        reward_value=data['reward_value'],
        expires_at=None,
        duration_days=data.get('duration_days'),
        message_template=data.get('message_template'),
    )
    await state.clear()
    await callback.message.edit_text("🎉 Промокод успешно создан!")
