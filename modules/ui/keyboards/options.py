from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..callbacks import (
    CONFIRM, BACK, LAYOUTS,OPTION_DUPLEX, OPTION_LAYOUT, OPTION_PAGES
)
from .buttons import (
    BUTTON_CONFIRM, BUTTON_EDIT, BUTTON_RETURN, BUTTONS_LAYOUT,
    BUTTON_OPTIONS_DUPLEX, BUTTON_OPTIONS_LAYOUT, BUTTON_OPTIONS_PAGES
)

confim_pages_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_CONFIRM, callback_data=CONFIRM),
            InlineKeyboardButton(text=BUTTON_EDIT, callback_data=BACK)
        ]
    ]
)

def get_print_options_kb(duplex: bool) -> InlineKeyboardMarkup:
    duplex_text = f"✅ {BUTTON_OPTIONS_DUPLEX}" if duplex else f"❌ {BUTTON_OPTIONS_DUPLEX}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=BUTTON_OPTIONS_LAYOUT, callback_data=OPTION_LAYOUT),
                InlineKeyboardButton(text=duplex_text, callback_data=OPTION_DUPLEX)
            ],
            [
                InlineKeyboardButton(text=BUTTON_RETURN, callback_data=BACK),
                InlineKeyboardButton(text=BUTTON_OPTIONS_PAGES, callback_data=OPTION_PAGES)
            ]
        ]
    )
    return markup

def get_print_layouts_kb(selected_layout: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []

    for layout in LAYOUTS:
        layout_text = BUTTONS_LAYOUT.get(layout, "Unknown layout")
        text = f"✅ {layout_text}" if layout == selected_layout else f"📄 {layout_text}"

        button = InlineKeyboardButton(
            text=text,
            callback_data=layout
        )
        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Добавляем последнюю неполную строку кнопок (если осталась одна)
    if row:
        keyboard.append(row)
        row = []

    # Добавляем кнопку "Назад"
    back_button = InlineKeyboardButton(
        text=BUTTON_RETURN,
        callback_data=BACK
    )

    # Если последняя строка пустая — создаём новую строку, иначе — добавляем в текущую
    if not keyboard or len(keyboard[-1]) == 2:
        keyboard.append([back_button])
    else:
        keyboard[-1].append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)