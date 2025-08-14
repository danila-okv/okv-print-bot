import asyncio
from dataclasses import dataclass
from collections import deque
from .print_job import PrintJob
from modules.ui.messages import *
from modules.analytics.logger import error, info
from modules.ui.keyboards.tracker import send_managed_message

# Очередь и управление
print_queue = deque()
processing = False
lock = asyncio.Lock()

async def print_worker():
    global processing

    async with lock:
        if processing or not print_queue:
            return
        processing = True

    while print_queue:
        job = print_queue.popleft()
        position = len(print_queue) + 1
        try:
            if position > 1:
                info(job.user_id, "print_worker", f"Queued print job: {job.file_name}, position: {position}")
                await send_managed_message(
                    job.bot,
                    job.user_id,
                    text=f"📄 Файл {job.file_name} поставлен в очередь на печать. Позиция в очереди: {position}"
                )
            else:
                info(job.user_id, "print_worker", f"Starting print job: {job.file_name}")
                await send_managed_message(
                    job.bot,
                    job.user_id,
                    text=PRINT_START_TEXT.format(file_name=job.file_name)
                )
            await job.run()
        except Exception as e:
            error(job.user_id, "print_worker", f"Error in print job {job.file_name}: {e}")
        await asyncio.sleep(1)

    processing = False

def add_job(job: PrintJob):
    print_queue.append(job)
    asyncio.create_task(print_worker())