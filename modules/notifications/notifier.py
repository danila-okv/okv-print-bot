from aiogram import Bot
from modules.ui.keyboards.print import print_done_kb
from modules.ui.messages import PRINT_DONE_TEXT
from modules.analytics.logger import info, error
from modules.ui.keyboards.tracker import send_managed_message

async def notify_print_complete(user_id: int, bot: Bot, file_name: str):
    try:
        await send_managed_message(
            bot,
            user_id,
            PRINT_DONE_TEXT.format(file_name=file_name),
            print_done_kb
        )
        info(
            user_id,
            "notifier",
            f"User notified about print completion: {file_name}"
        )
    except Exception as e:
        error(
            user_id,
            "notifier",
            f"Error notifying user about print completion: {e}"
        )