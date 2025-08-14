# modules/admin/cups.py

import subprocess
from aiogram import Router, types
from aiogram.filters import Command
from modules.decorators import admin_only

router = Router()

@router.message(Command("jobs"))
@admin_only
async def cmd_jobs(message: types.Message):
    """
    Показывает актуальную очередь печати из CUPS (lpstat -o).
    """
    try:
        # lpstat -o выводит список очереди в формате:
        # printer-name-jobid  username  size  date  ...
        proc = subprocess.run(
            "lpstat -o",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        out = proc.stdout.strip()
        if not out:
            out = "✅ Очередь печати пуста."
        # Отправляем в блоке pre, чтобы сохранился формат
        await message.reply(f"<pre>{out}</pre>")
    except subprocess.TimeoutExpired:
        await message.reply("❗ Не удалось получить список задач: время ожидания истекло.")
    except Exception as e:
        # на всякий случай отлавливаем другие ошибки
        await message.reply(f"❗ Ошибка при запросе очереди: {e}")
