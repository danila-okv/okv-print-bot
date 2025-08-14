from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, date
from modules.decorators import admin_only

router = Router()

class Stats:
    def __init__(self, pages, users, files):
        self.pages = pages
        self.users = users
        self.files = files

# TODO: Use SQLite
def get_stats_for_interval(from_date: date, to_date: date) -> Stats:
    return Stats(
        pages=123,
        users=17,
        files=29
    )

@router.message(Command("stats"))
@admin_only
async def stats_handler(message: Message):
    parts = message.text.strip().split()

    from_date = to_date = date.today()

    if len(parts) == 2:
        if parts[1].lower() == "day":
            from_date = to_date = date.today()
        elif parts[1].lower() == "month":
            from_date = date.today().replace(day=1)
            to_date = date.today()

    elif len(parts) == 3:
        try:
            from_date = datetime.strptime(parts[1], "%d.%m.%Y").date()
            to_date = datetime.strptime(parts[2], "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используй: /stats 01.05.2025 01.06.2025")
            return

    stats = get_stats_for_interval(from_date, to_date)

    await message.answer(
        f"📊 Статистика с {from_date.strftime('%d.%m.%Y')} по {to_date.strftime('%d.%m.%Y')}:\n\n"
        f"🖨 Листов: {stats.pages}\n"
        f"👥 Пользователей: {stats.users}\n"
        f"📂 Файлов: {stats.files}"
    )
