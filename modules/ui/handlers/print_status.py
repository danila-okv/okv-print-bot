"""
Handler for the print status callback.

This module defines a callback handler that updates a user's print queue
status when they press the "Статус печати" button.  The handler looks up
the user's pending job in the queue, computes the current position and
remaining wait time, and edits the existing message with the new
information.  If the user's job is currently printing or has already
been removed from the queue, a corresponding notice is displayed.
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime

from modules.ui.callbacks import PRINT_STATUS
from modules.ui.keyboards.status import print_status_kb
from modules.printing.print_service import compute_wait_time, print_queue, current_job
from modules.analytics.logger import info, error

router = Router()


@router.callback_query(F.data == PRINT_STATUS)
async def handle_print_status(callback: CallbackQuery) -> None:
    """Respond to the print status button press.

    Looks up the first pending job for the user and updates the message
    with a fresh estimate of their position and wait time.  If the job
    cannot be found, informs the user that printing is underway or
    completed.
    """
    user_id = callback.from_user.id
    # Find the user's first job in the queue
    target_job = None
    for job in list(print_queue):
        try:
            if job.user_id == user_id:
                target_job = job
                break
        except AttributeError:
            # Ignore jobs without expected attributes
            continue
    # If not found in queue, check if currently printing
    if target_job is None:
        if current_job and getattr(current_job, "user_id", None) == user_id:
            # User's job is currently printing
            text = "🖨️ Твой документ сейчас печатается…"
        else:
            # Job not in queue — likely printed or cancelled
            text = "ℹ️ Похоже, твой документ уже распечатан или не найден в очереди."
        # Attempt to edit the existing message.  If that fails (e.g. message
        # deleted), fall back to answering the callback
        try:
            await callback.message.edit_text(text=text)
        except Exception:
            await callback.answer(text)
        else:
            await callback.answer()
        return
    # Compute updated wait time and position
    wait_seconds = compute_wait_time(target_job)
    minutes = int(wait_seconds // 60)
    seconds = int(wait_seconds % 60)
    # Determine position including current job
    ahead_count = (1 if current_job else 0) + list(print_queue).index(target_job)
    position = ahead_count + 1
    update_time = datetime.now().strftime("%H:%M:%S")
    text = (
        f"📄 Файл <b>{target_job.file_name}</b>\n"
        f"Позиция в очереди: <b>{position}</b>\n"
        f"⏱️ Осталось: <b>{minutes} мин {seconds:02d} сек.</b>\n"
        f"Обновлено: {update_time}"
    )
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=print_status_kb,
            parse_mode="HTML",
        )
        info(user_id, "print_status", f"Status updated: position {position}, wait {minutes}m {seconds}s")
    except Exception as e:
        error(user_id, "print_status", f"Failed to edit status message: {e}")
    await callback.answer()