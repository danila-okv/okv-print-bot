# modules/admin/shell.py

import subprocess
from aiogram import Router, types
from aiogram.filters import Command
from modules.decorators import admin_only

router = Router()

@router.message(Command("shell"))
@admin_only
async def cmd_admin_shell(message: types.Message):
    # отрезаем префикс и пробел
    cmd = message.text.removeprefix("/shell").strip()
    if not cmd:
        # Экран угловых скобок в инструкции
        return await message.reply("Использование: /shell &lt;команда&gt;")

    # запускаем команду с таймаутом
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15  # сек
        )
        output = proc.stdout or proc.stderr or "Команда выполнилась, но вывода нет."
    except subprocess.TimeoutExpired:
        output = "❗ Время выполнения команды истекло (15 сек)."

    # отвечаем администратору, экранируя вывод
    await message.reply(f"<pre>{output}</pre>")
