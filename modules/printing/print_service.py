import asyncio
from datetime import datetime
from collections import deque
from .print_job import PrintJob
from modules.ui.messages import PRINT_START_TEXT
from modules.analytics.logger import error, info
from modules.ui.keyboards.tracker import send_managed_message
from modules.ui.keyboards.status import print_status_kb
from config import QUEUE_TIME_PER_PAGE, QUEUE_WARMUP_TIME, QUEUE_STATUS_UPDATE_INTERVAL

# The printing queue holds jobs waiting to be processed.  Jobs are appended
# as they arrive.  Only one job is printed at a time; other jobs remain
# in the queue until the current job finishes.
print_queue: deque[PrintJob] = deque()

# Flag indicating whether the worker is currently running.  Access is
# synchronized via the lock.
processing: bool = False

# Lock to prevent concurrent workers from starting.  Only one worker
# instance should run at a time.
lock = asyncio.Lock()

# Track the job currently being printed, along with timing information.
# These globals allow estimation of wait times for queued jobs.
current_job: PrintJob | None = None
current_job_start: datetime | None = None
current_job_total_time: float | None = None


def estimate_time_for_job(job: PrintJob) -> float:
    """Return the estimated duration (in seconds) required to print a job.

    The estimate is based on the number of pages to print and the
    configured per‑page time and warmup overhead.  If the job has a
    specific page selection, only those pages are counted; otherwise the
    full page_count is used.  The number of copies is also taken into
    account.
    """
    try:
        # Compute the list of pages to print.  Fallback to page_count on
        # error.  Multiplying by copies accounts for multiple outputs.
        pages_to_print = len(job.parse_page_ranges(job.pages or f"1-{job.page_count}")) * (job.copies or 1)
    except Exception:
        pages_to_print = job.page_count * (job.copies or 1)
    return pages_to_print * QUEUE_TIME_PER_PAGE + QUEUE_WARMUP_TIME


def compute_wait_time(job: PrintJob) -> float:
    """Compute how many seconds remain before the given job will start printing.

    The wait time is the sum of the remaining time on the current job (if
    any) and the estimated time for each job ahead of the given job in
    the queue.  If the job is not found in the queue, the returned time
    accounts for the current job only.  The value is always non‑negative.
    """
    wait_seconds = 0.0
    now = datetime.now()
    # Include remaining time for the job currently printing, if any
    if current_job and current_job_start and current_job_total_time:
        elapsed = (now - current_job_start).total_seconds()
        remaining = current_job_total_time - elapsed
        if remaining > 0:
            wait_seconds += remaining
    # Sum the durations of all jobs ahead of this job in the queue
    for queued_job in print_queue:
        if queued_job is job:
            break
        wait_seconds += estimate_time_for_job(queued_job)
    return max(wait_seconds, 0.0)


async def update_queue_messages() -> None:
    """Refresh the position and wait time displayed to each queued job.

    Iterates over all jobs in the queue and edits their existing messages
    with updated position numbers and estimated wait times.  Jobs that
    have not yet had a message sent (message_id is None) are skipped.
    """
    # Enumerate queued jobs and build messages
    for idx, job in enumerate(list(print_queue)):
        if job.message_id is None:
            continue
        # Compute position: all jobs ahead plus current job if printing
        position = (1 if current_job else 0) + idx + 1
        wait_seconds = compute_wait_time(job)
        minutes = int(wait_seconds // 60)
        seconds = int(wait_seconds % 60)
        text = (
            f"📄 Файл <b>{job.file_name}</b> поставлен в очередь на печать.\n"
            f"Позиция в очереди: <b>{position}</b>\n"
            f"⏱️ Примерное время ожидания: <b>{minutes} мин {seconds:02d} сек.</b>"
        )
        try:
            await job.bot.edit_message_text(
                chat_id=job.user_id,
                message_id=job.message_id,
                text=text,
                reply_markup=print_status_kb,
                parse_mode="HTML",
            )
            info(job.user_id, "print_queue", f"Queue status updated for {job.file_name}, position {position}, wait {minutes}m {seconds}s")
        except Exception as e:
            # Silently ignore errors when updating messages (e.g. message deleted)
            error(job.user_id, "print_queue", f"Failed to update queue message: {e}")


async def _notify_job_added(job: PrintJob, ahead_jobs: int) -> None:
    """Send an initial message to the user when their job is added to the queue.

    Depending on the state of the queue, the user is either notified that
    their document has begun printing immediately or that it has been
    queued.  A status button is attached to allow manual refreshes.  The
    message id is stored on the job object for future updates.
    """
    try:
        # If there are no jobs printing and no jobs ahead, start printing soon
        if ahead_jobs == 0 and not current_job:
            info(job.user_id, "queue", f"Job {job.file_name} will start immediately")
            msg = await send_managed_message(
                job.bot,
                job.user_id,
                text=PRINT_START_TEXT.format(file_name=job.file_name),
                reply_markup=print_status_kb,
            )
            job.message_id = msg.message_id
        else:
            # Compute wait time based on current queue
            wait_seconds = compute_wait_time(job)
            position = (1 if current_job else 0) + ahead_jobs + 1
            minutes = int(wait_seconds // 60)
            seconds = int(wait_seconds % 60)
            info(job.user_id, "queue", f"Job {job.file_name} queued at position {position}")
            text = (
                f"📄 Файл <b>{job.file_name}</b> поставлен в очередь на печать.\n"
                f"Позиция в очереди: <b>{position}</b>\n"
                f"⏱️ Примерное время ожидания: <b>{minutes} мин {seconds:02d} сек.</b>"
            )
            msg = await send_managed_message(
                job.bot,
                job.user_id,
                text=text,
                reply_markup=print_status_kb,
                parse_mode="HTML",
            )
            job.message_id = msg.message_id
    except Exception as e:
        error(job.user_id, "queue", f"Error notifying user about new job: {e}")
    # After notifying, refresh the queue messages for all other jobs
    await update_queue_messages()


async def print_worker() -> None:
    """Asynchronous worker that manages printing jobs sequentially.

    This coroutine ensures that only one job prints at a time and that
    queued users receive periodic updates about their wait time.  It
    continues running as long as there are jobs to process or a job is
    currently printing.
    """
    global processing, current_job, current_job_start, current_job_total_time
    async with lock:
        # If another worker is active or there are no queued jobs, do nothing
        if processing:
            return
        if not print_queue and not current_job:
            return
        processing = True

    # Main loop
    while True:
        # Start a new job if nothing is currently printing
        if current_job is None and print_queue:
            job = print_queue.popleft()
            current_job = job
            current_job_start = datetime.now()
            current_job_total_time = estimate_time_for_job(job)
            info(job.user_id, "print_worker", f"Starting print job: {job.file_name}")
            # Update the user's message to indicate printing has begun
            if job.message_id is not None:
                try:
                    await job.bot.edit_message_text(
                        chat_id=job.user_id,
                        message_id=job.message_id,
                        text=PRINT_START_TEXT.format(file_name=job.file_name),
                        reply_markup=None,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    error(job.user_id, "print_worker", f"Failed to update message for printing: {e}")
            # Run the job synchronously; this will block until printing finishes
            try:
                # Mark the job as printing in the database and set the start time
                try:
                    from db import get_connection  # Import here to avoid circular dependency at module load
                    with get_connection() as conn:
                        conn.execute(
                            "UPDATE print_jobs SET status = 'printing', started_at = ? WHERE user_id = ? AND file_name = ? AND status = 'queued'",
                            (datetime.now(), job.user_id, job.file_name),
                        )
                        conn.commit()
                except Exception:
                    pass
                await job.run()
            except Exception as e:
                error(job.user_id, "print_worker", f"Error in print job {job.file_name}: {e}")
            # Reset current job tracking after completion
            current_job = None
            current_job_start = None
            current_job_total_time = None
            # Refresh queue messages after finishing a job
            await update_queue_messages()
        # Exit condition: no current job and queue is empty
        if current_job is None and not print_queue:
            processing = False
            return
        # Sleep for a configured interval and update the queue messages
        await asyncio.sleep(QUEUE_STATUS_UPDATE_INTERVAL)
        await update_queue_messages()


def add_job(job: PrintJob) -> None:
    """Add a new print job to the queue and schedule worker and notifications.

    This function is safe to call from synchronous contexts.  It appends
    the job to the queue, schedules an asynchronous notification to the
    user, and ensures that the print worker is running.  The job's
    position is computed based on the number of jobs currently waiting
    plus any job that is already printing.
    """
    # Determine how many jobs are ahead of this one.  We compute this
    # before appending to ensure the count reflects the current queue.
    ahead_jobs = (1 if current_job else 0) + len(print_queue)
    print_queue.append(job)
    # Notify the user asynchronously about their job status
    asyncio.create_task(_notify_job_added(job, ahead_jobs))
    # Ensure the worker is running
    asyncio.create_task(print_worker())