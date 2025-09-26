import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from aiogram import Bot
from modules.ui.messages import PRINT_DONE_TEXT
from modules.ui.keyboards.print import print_done_kb, print_error_kb
from modules.ui.keyboards.tracker import send_managed_message
from modules.analytics.logger import info, error
from db import get_connection
from utils.pdf_utils import get_orientation_ranges

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

    async def run(self):
        try:
            orientation_blocks = get_orientation_ranges(self.file_path)
            selected_pages = self.parse_page_ranges(self.pages or f"1-{self.page_count}")

            blocks = []
            for block in orientation_blocks:
                block_pages = [p for p in range(block["start"], block["end"] + 1) if p in selected_pages]
                if block_pages:
                    blocks.append({
                        "pages": block_pages,
                        "orientation": block["type"]
                    })

            if not blocks:
                raise RuntimeError("Нет подходящих страниц для печати")

            cmds = []

            if len(blocks) == 1:
                block = blocks[0]
                page_range_str = self.merge_page_list(block["pages"])
                cmd = ["lp", "-o", "media=A4", "-o", "fit-to-page"]

                if self.layout:
                    cmd += ["-o", f"number-up={self.layout}"]
                cmd += ["-o", "sides=one-sided"]
                if self.duplex:
                    cmd += ["-o", "sides=two-sided-long-edge"]
                else:
                    cmd += ["-o", "sides=one-sided"]
                if self.copies > 1:
                    cmd += ["-n", str(self.copies)]

                orientation = block["orientation"]
                if orientation == "landscape":
                    cmd += ["-o", "orientation-requested=4"]
                else:
                    cmd += ["-o", "orientation-requested=3"]

                cmd += ["-P", page_range_str]
                cmd.append(self.file_path)
                cmds.append(cmd)
            else:
                for copy_num in range(self.copies):
                    for block in blocks:
                        page_range_str = self.merge_page_list(block["pages"])
                        cmd = ["lp", "-o", "sides=one-sided"]

                        if self.layout:
                            cmd += ["-o", f"number-up={self.layout}"]

                        orientation = block["orientation"]
                        if orientation == "landscape":
                            cmd += ["-o", "orientation-requested=4"]
                        else:
                            cmd += ["-o", "orientation-requested=3"]

                        cmd += ["-P", page_range_str]
                        cmd.append(self.file_path)
                        cmds.append(cmd)

            job_ids = []

            for cmd in cmds:
                info(self.user_id, "print_job", f"Run command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"lp error: {result.stderr.strip()}")

                job_id_str = result.stdout.strip()
                info(self.user_id, "print_job", f"Job started {self.file_name}: {job_id_str}")
                if "-" in job_id_str:
                    job_id = job_id_str.split("-")[1].split()[0]
                    self.save_to_db(status="queued", job_id=job_id)
                    job_ids.append(job_id)

            await consume_supply("бумага", self.page_count * self.copies, bot=self.bot)
            await consume_supply("чернила", self.page_count * self.copies, bot=self.bot)

            while True:
                lpstat = subprocess.run(["lpstat", "-W", "not-completed"], capture_output=True, text=True)
                output = lpstat.stdout
                if all(job_id not in output for job_id in job_ids):
                    break
                await asyncio.sleep(3)

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

    def parse_page_ranges(self, range_str):
        result = set()
        for part in range_str.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                result.update(range(start, end + 1))
            else:
                result.add(int(part))
        return result

    def merge_page_list(self, pages):
        pages = sorted(set(map(int, pages)))
        ranges = []
        start = prev = pages[0]

        for p in pages[1:]:
            if p == prev + 1:
                prev = p
            else:
                if start == prev:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{prev}")
                start = prev = p
        if start == prev:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{prev}")
        return ",".join(ranges)

def add_job(job: PrintJob):
    asyncio.create_task(job.run())
