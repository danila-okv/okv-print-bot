from config import PRICE_PER_PAGE
from config import ALLOWED_DOCUMENT_TYPES, ALLOWED_IMAGE_TYPES

# Messages for the Telegram bot
MAIN_MENU_TEXT = f"""
📤 Присылай свой файл — я распечатаю его в комнате <b>1708А</b>

🖨 ЧБ-печать — <b>{int(PRICE_PER_PAGE*100)} коп/страница</b>  
"""
UNKNOWN_COMMAND_TEXT = "❓ Я пока что не выучил такой команды. Напиши /start, чтобы вызвать главное меню"
ACCESS_DENIED_TEXT = "🚫 Отсутствует доступ"


# File processing messages
FILE_PROCESSING_TEXT = "🔄 Файл <b>{file_name}</b> получил. Считаю страницы..."
FILE_TYPE_ERROR_TEXT = (
"⚠️ Ух, пока что не перевариваю файлы <b>{ext}</b>\n\n"
f"<b>документы:</b> {", ".join(ALLOWED_DOCUMENT_TYPES)}\n"
f"<b>изображения:</b> {", ".join(ALLOWED_IMAGE_TYPES)}\n\n"
"🎁 Перешли файл мне, распечатаю <b>со скидкой 25%</b> — @danila_okv"
)

FILE_PROCESSING_FAILURE_TEXT = "❌ Что-то пошло не так с файлом <b>{file_name}</b>. Попробуй ещё раз или пришли другой"

# Payment messages
PAY_CASH_TEXT = """
💵 Наличные: 
Оставляй в коробке на принтере, когда придешь забирать
"""
PAY_CARD_TEXT = """
💳 Куда удобнее перевести?
"""
PAY_ALFA_TEXT = """
💵 <b>Альфа-банк</b>  
Переводи по номеру телефона - +375 (25) 727-07-03
"""
PAY_BELARUSBANK_TEXT = """
💵 <b>Беларусбанк</b>  
Платежи → Перевод по номеру телефона
+375 (29) 277-07-03
"""
PAY_OTHER_TEXT = """ 
💵 Переводи через ЕРИП чбез комиссии:
1. Банковские, финансовые и услуги - Альфа-Банк
2. Пополнение счета, <code>375257270703</code> (нажми, чтобы скопировать)
"""
PAY_TIMEOUT_TEXT = """
😌 Ты не подтвердил печать
Если передумал — все ок. Если нет — пришли файл заново
"""
PAY_SUCCESS_TEXT = "✅ Ты подтвердил оплату"
PAY_FAILURE_TEXT = "❌ Платёж не найден. Проверь перевод и попробуй снова"

# Print messages
PRINT_HEADER_TEXT = """
✅ Файл <b>{file_name}</b> обработан

📄 Страниц: <b>{page_count}</b>
💰 К оплате: <b>{price:.2f} руб.</b>
"""
PRINT_OPTIONS_TEXT = """
⚙️ <b>Выбери опции:</b>
"""
PRINT_START_TEXT = "🖨️ Печатаю <b>{file_name}</b>..."
PRINT_QUEUE_TEXT = "📑 Файл <b>{file_name}</b> поставлен в очередь. Жди - скоро распечатаю..."
PRINT_LAYOUT_SELECTION_TEXT = """
📐 <b>Выбери макет печати:</b>
"""
PRINT_PAGES_INPUT_TEXT = """
📄 Введи страницы для печати (например, 1,2-5,10)
"""
PRINT_COPIES_INPUT_TEXT = """
🔄 Введи количество копий (по умолчанию 1)
"""
PRINT_DONE_TEXT = """✅ Готово!\n Можешь забрать свой файл в комнате <b>1708А</b> (2-я секция)
Заходи без стука
"""
PRINT_CANCELLED_TEXT = "❌ Печать отменена. Если что-то не так, пиши - @danila_okv"

def get_details_review_text(data: dict) -> str:
    header = format_print_text(data)
    return header

def get_print_options_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PRINT_OPTIONS_TEXT

def get_cash_payment_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PAY_CASH_TEXT

def get_card_payment_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PAY_CARD_TEXT

def get_copies_input_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PRINT_COPIES_INPUT_TEXT

def get_pages_input_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PRINT_PAGES_INPUT_TEXT

def get_layout_selection_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PRINT_LAYOUT_SELECTION_TEXT

def get_alfa_payment_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PAY_ALFA_TEXT

def get_belarusbank_payment_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PAY_BELARUSBANK_TEXT

def get_other_payment_text(data: dict) -> str:
    header = format_print_text(data)
    return header + PAY_OTHER_TEXT

def format_print_text(data: dict) -> str:
    price = data.get("price_data", {})
    price_block = f"\n💰 К оплате: <s>{price.get('raw_price', 0):.2f}</s> → <b>{price.get('final_price', 0):.2f} руб.</b>"

    if price.get("discount_applied", 0):
        price_block += f" (скидка {price['discount_applied']:.0f}%)"
    if price.get("pages_covered_by_bonus", 0):
        price_block += f"\n🎁 Использовано бесплатных страниц: {price['pages_covered_by_bonus']}"

    header = f"""
✅ Файл <b>{data['file_name']}</b> обработан
📄 Страниц: <b>{data['page_count']}</b>{price_block}
"""
    if "group" in data["file_path"]:
        header = f"""
✅ Файлы <b>{data['file_name']}</b> обработаны
📄 Страниц: <b>{data['page_count']}</b>{price_block}
"""
    

    options = []
    
    duplex = data.get("duplex", False)
    if duplex:
        options.append(f"Двусторонняя печать")

    pages = data.get("pages")
    if pages:
        options.append(f"Страницы - <i>{pages}</i>")
    
    copies = data.get("copies", 1)
    if copies > 1:
        options.append(f"Копий - <i>{copies}</i>")
        
    layout = data.get("layout")
    if layout and layout != "1":
        options.append(f"Макет - {layout} на лист")

    if not options:
        return header

    options_block = "\n".join(["", "‼️ <b>Опции печати:</b>"] + options)
    return header + options_block + "\n"
