# modules/admin/handlers/control.py

from aiogram import Router, types
from modules.decorators import admin_only
from modules.ui.keyboards.tracker import send_managed_message
from aiogram.filters import Command
from ..services.control import (
    set_pause, clear_pause,
    pop_all_queued_actions,
    backup_database
)

from config import BACKUP_PATH_STR

router = Router()

@router.message(Command("pause"))
@admin_only
async def cmd_pause(message: types.Message):
    # извлекаем причину (всё, что после команды)
    reason = message.text.partition(' ')[2].strip() or "🤖 Технические работы"
    set_pause(reason)
    await message.reply(f"⏸️ Бот поставлен на пауза.\nПричина: <i>{reason}</i>")

@router.message(Command("resume"))
@admin_only
async def cmd_resume(message: types.Message):
    clear_pause()
    await message.reply("▶️ Бот возобновил работу.")

    # Вытягиваем все отложенные действия и сразу удаляем их из БД
    actions = pop_all_queued_actions()

    # Определяем всех уникальных пользователей, которые выполняли любые действия во время паузы.
    target_user_ids = {act['user_id'] for act in actions}

    # Импортируем функцию начисления бонусных страниц здесь, чтобы избежать циклических импортов.
    from modules.billing.services.promo import add_user_bonus_pages

    # Начисляем 5 бонусных страниц каждому пользователю и уведомляем его о возобновлении работы.
    for uid in target_user_ids:
        try:
            add_user_bonus_pages(uid, 5)
        except Exception:
            # Если по какой-то причине начислить не удалось, игнорируем ошибку
            pass
        await send_managed_message(
            message.bot,
            uid,
            text="✅ Бот снова в деле!\nСпасибо за терпение — дарю тебе 5 бесплатных страниц 🎉"
        )


# ---------------------------------------------------------------------------
# Backup command
# ---------------------------------------------------------------------------
@router.message(Command("backup"))
@admin_only
async def cmd_backup(message: types.Message) -> None:
    """
    Административная команда для создания резервной копии базы данных.
    При вызове сохраняет текущий файл базы данных в каталог BACKUP_PATH с
    временной меткой в имени и отправляет его администратору в чат.

    Требуется уровень admin, обеспечивается декоратором admin_only.
    """
    # Create the backup file
    try:
        backup_path = backup_database()
    except Exception as err:
        await message.answer(f"❌ Ошибка при создании резервной копии: {err}")
        return

    # Attempt to send the backup file to the admin.  If FSInputFile is not
    # available (older aiogram), fall back to reading bytes into BufferedInputFile.
    try:
        # Determine file name for caption
        file_name = backup_path.name
        try:
            # aiogram v3 exports FSInputFile under aiogram.types, fallback gracefully
            from aiogram.types import FSInputFile
            file = FSInputFile(path=str(backup_path), filename=file_name)
        except Exception:
            from aiogram.types import BufferedInputFile
            file_bytes = backup_path.read_bytes()  # type: ignore[attr-defined]
            file = BufferedInputFile(file_bytes, filename=file_name)
        await message.answer_document(file, caption=f"🗄️ Резервная копия создана: {file_name}")
    except Exception as err:
        # If sending the file fails, inform the admin about the location
        await message.answer(
            f"✅ Резервная копия базы данных создана: {backup_path}\n"
            f"Не удалось отправить файл автоматически (ошибка: {err}).\n"
            f"Вы можете скачать копию вручную из каталога {BACKUP_PATH_STR}."
        )
