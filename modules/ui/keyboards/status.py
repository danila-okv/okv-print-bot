"""
Inline keyboard for querying the status of a print job.

This keyboard contains a single button that triggers a callback when
pressed.  The callback will update the user's message with the latest
position in the queue and an updated estimate of the time remaining until
printing begins.  See modules/ui/handlers/print_status.py for the
corresponding handler.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..callbacks import PRINT_STATUS


# Label for the status button.  Translated as “Print status” so users know
# they can check how much longer they need to wait.
BUTTON_PRINT_STATUS = "🔄 Статус печати"


print_status_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=BUTTON_PRINT_STATUS, callback_data=PRINT_STATUS)]
    ]
)

__all__ = ["print_status_kb", "BUTTON_PRINT_STATUS"]