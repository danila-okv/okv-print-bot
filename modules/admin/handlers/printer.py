# modules/admin/printer.py

from aiogram import Router, types
from aiogram.filters import Command
from modules.decorators import admin_only
from modules.printing.printer_status import (
    get_printer_status,
    get_printer_latency,
    get_printer_diagnostics,
    list_printers,
    get_printer_ips
)

router = Router()

@router.message(Command("printer"))
@admin_only
async def cmd_printer(message: types.Message):
    """
    /printer <list|ping|status|diagnostic>
    """
    arg = message.text.removeprefix("/printer").strip().lower()

    if not arg or arg == "help":
        return await message.reply(
            "Использование:\n"
            "/printer list       — показать всех принтеров и их IP\n"
            "/printer ping       — проверить задержку до принтера по умолчанию\n"
            "/printer status     — узнать статус принтера по умолчанию\n"
            "/printer diagnostic — расширенная диагностика принтера"
        )

    if arg == "list":
        printers = list_printers()
        ips = get_printer_ips()
        if not printers:
            return await message.reply("❌ Не найдено ни одного принтера.")
        lines = []
        for name, uri in printers.items():
            ip = ips.get(name) or "–"
            lines.append(f"• <b>{name}</b>\n  URI: <code>{uri}</code>\n  IP: <code>{ip}</code>")
        return await message.reply("🖨️ <b>Список принтеров:</b>\n" + "\n\n".join(lines))

    if arg == "ping":
        lat = get_printer_latency()
        if lat is None:
            return await message.reply("❌ Не удалось пинговать принтер.")
        return await message.reply(f"🏓 Средняя задержка: {lat:.1f} ms")

    if arg == "status":
        status = get_printer_status()
        icons = {"idle": "🟢", "printing": "🟡", "disabled": "❌"}
        icon = icons.get(status, "❓")
        return await message.reply(f"{icon} Статус: <b>{status}</b>")

    if arg == "diagnostic":
        diag = get_printer_diagnostics()
        lines = [
            f"🖨 Принтер: {diag['default_printer']}",
            f"📶 Статус CUPS: {diag['status']}",
            f"🏓 Пинг: {diag['latency_ms']} ms",
            f"📋 Очередь: {diag['queue_length']} задач",
            f"🔗 Device URI: <code>{diag['device_uri']}</code>"
        ]
        return await message.reply("<b>🛠 Диагностика принтера:</b>\n" + "\n".join(lines))

    # неизвестная подкоманда
    # Экран угловых скобок для списка параметров
    return await message.reply("Неизвестная подкоманда. /printer &lt;list|ping|status|diagnostic&gt;")
