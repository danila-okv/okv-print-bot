from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..callbacks import (
    CONFIRM, BACK, LAYOUTS,OPTION_DUPLEX, OPTION_LAYOUT, OPTION_PAGES,
    OPTION_COPIES
)
from .buttons import (
    BUTTON_CONFIRM, BUTTON_EDIT, BUTTON_BACK, BUTTONS_LAYOUT,
    BUTTON_OPTION_DUPLEX, BUTTON_OPTION_LAYOUT, BUTTON_OPTION_PAGES,
    BUTTON_OPTION_COPIES
)

confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_CONFIRM, callback_data=CONFIRM),
            InlineKeyboardButton(text=BUTTON_EDIT, callback_data=BACK)
        ]
    ]
)

def get_print_options_kb(duplex: bool) -> InlineKeyboardMarkup:
    duplex_text = f"✅ {BUTTON_OPTION_DUPLEX}" if duplex else f"❌ {BUTTON_OPTION_DUPLEX}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=BUTTON_OPTION_LAYOUT, callback_data=OPTION_LAYOUT),
                InlineKeyboardButton(text=duplex_text, callback_data=OPTION_DUPLEX)
            ],
            [
                InlineKeyboardButton(text=BUTTON_OPTION_COPIES, callback_data=OPTION_COPIES),
                InlineKeyboardButton(text=BUTTON_OPTION_PAGES, callback_data=OPTION_PAGES)
            ],
            [
                InlineKeyboardButton(text=BUTTON_BACK, callback_data=BACK)
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

    if row:
        keyboard.append(row)
        row = []

    back_button = InlineKeyboardButton(
        text=BUTTON_BACK,
        callback_data=BACK
    )

    if not keyboard or len(keyboard[-1]) == 2:
        keyboard.append([back_button])
    else:
        keyboard[-1].append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)