# modules/printing/print_job.py
import asyncio
from dataclasses import dataclass
from datetime import datetime
from aiogram import Bot
from modules.ui.messages import PRINT_DONE_TEXT
from modules.ui.keyboards.print import print_done_kb, print_error_kb
from modules.ui.keyboards.tracker import send_managed_message
from modules.analytics.logger import info, error
from db import get_connection
from utils.pdf_utils import get_orientation_ranges
from utils.windows_print import print_pdf_win 

from modules.analytics.supplies import consume_supply

@dataclass
class PrintJob:
    user_id: int
    file_path: str
    file_name: str
    bot: Bot
    page_count: int = 0
    duplex: bool = False
    layout: str = "1"
    pages: str = ""
    copies: int = 1

    message_id: int | None = None

    def _parse_pages(self):
        result = set()
        s = (self.pages or f"1-{self.page_count}").replace(" ", "")
        for part in s.split(","):
            if "-" in part:
                a, b = map(int, part.split("-"))
                result.update(range(a, b+1))
            else:
                result.add(int(part))
        return sorted(result)

    async def run(self):
        try:
            selected_pages = self._parse_pages()
            try:
                nup = int(self.layout)
            except Exception:
                nup = 1

            info(self.user_id, "print_job", f"Printing via Sumatra: {self.file_name}")
            print_pdf_win(
                pdf_path=self.file_path,
                copies=self.copies,
                duplex=self.duplex,
                page_ranges=selected_pages,
                number_up=nup,
                paper="A4",
                fit=True,
                silent=True,
                wait=True, 
            )

            await consume_supply("бумага", self.page_count * self.copies, bot=self.bot)
            await consume_supply("чернила", self.page_count * self.copies, bot=self.bot)

            info(self.user_id, "print_job", f"Printing ended: {self.file_name}")
            self.update_status("done")
            await send_managed_message(self.bot, self.user_id, PRINT_DONE_TEXT, print_done_kb)

        except Exception as e:
            error(self.user_id, "print_job", f"Printing error: {e}")
            self.update_status("error")
            await send_managed_message(
                self.bot,
                self.user_id,
                f"❌ Ошибка при печати файла «{self.file_name}». {str(e)}",
                print_error_kb
            )

    def save_to_db(self, status: str = "queued", job_id: str | None = None):
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO print_jobs (
                    user_id, file_name, page_count, layout,
                    pages, copies, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id, self.file_name, self.page_count,
                self.layout, self.pages, self.copies,
                status, datetime.now()
            ))
            conn.commit()

    def update_status(self, status: str):
        with get_connection() as conn:
            conn.execute("""
                UPDATE print_jobs
                SET status = ?, completed_at = ?
                WHERE user_id = ? AND file_name = ? AND status != 'done'
            """, (
                status, datetime.now(), self.user_id, self.file_name
            ))
            conn.commit()
