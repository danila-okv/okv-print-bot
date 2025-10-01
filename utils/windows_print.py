# utils/windows_print.py
import os
import time
import subprocess
import win32print
import win32api
from typing import Optional, Iterable
from config import SUMATRA_PATH, DEFAULT_PRINTER_NAME

def list_printers_win() -> list[str]:
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    # printers: [(flags, desc, name, comment), ...]
    return [p[2] for p in printers]

def get_default_printer_win() -> str:
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return ""

def get_queue_len(printer_name: Optional[str] = None) -> int:
    h = _open_printer_handle(printer_name)
    try:
        return len(win32print.EnumJobs(h, 0, 9999, 1))
    finally:
        win32print.ClosePrinter(h)

def enum_jobs(printer_name: Optional[str] = None):
    h = _open_printer_handle(printer_name)
    try:
        return win32print.EnumJobs(h, 0, 9999, 1)
    finally:
        win32print.ClosePrinter(h)

def _open_printer_handle(printer_name: Optional[str]):
    name = printer_name or DEFAULT_PRINTER_NAME or get_default_printer_win()
    if not name:
        raise RuntimeError("Нет доступного принтера: не задан и не найден принтер по умолчанию")
    return win32print.OpenPrinter(name)

# ---- Печать PDF через SumatraPDF ----

def print_pdf_win(
    pdf_path: str,
    printer_name: Optional[str] = None,
    copies: int = 1,
    duplex: bool = False,                 # two-sided-long-edge
    orientation: Optional[str] = None,    # "portrait" | "landscape" | None
    page_ranges: Optional[Iterable[int]] = None,  # например [1,2,3,7,8]
    number_up: int = 1,                   # 1 | 2 | 4 | 6 | 9 | 16
    fit: bool = True,                     # fit-to-page
    paper: str = "A4",
    silent: bool = True,
    wait: bool = False,                   # дождаться завершения (ждём пропадания job из очереди)
    wait_timeout_s: int = 300
) -> None:
    """
    Печатает PDF бесшумно через SumatraPDF.
    Требует установленный SumatraPDF.exe (portable OK).
    """
    exe = _resolve_sumatra()
    if not os.path.isfile(exe):
        raise RuntimeError(f"Не найден SumatraPDF.exe: {exe}")

    printer = printer_name or DEFAULT_PRINTER_NAME or get_default_printer_win()
    if not printer:
        raise RuntimeError("Не найден принтер по умолчанию и не задан явный printer_name")

    args = [exe, "-print-to", printer]

    # настройки печати
    settings = []
    if duplex:
        settings.append("duplex")  # long-edge по умолчанию
        # для короткого края: settings.append("duplex,short-edge")
    if fit:
        settings.append("fit")
    if paper:
        settings.append(f"paper={paper}")
    if number_up and number_up > 1:
        settings.append(f"n-up={number_up}")

    if settings:
        args += ["-print-settings", ";".join(settings)]

    # страницы (Sumatra понимает 1,2,4-6)
    if page_ranges:
        pages_str = _merge_pages_for_sumatra(page_ranges)  # "1,2,4-6"
        args += ["-print-pages", pages_str]

    # копии
    if copies and copies > 1:
        args += ["-print-settings", f"copies={copies}"]

    if silent:
        args.append("-silent")

    # ориентирование: для PDF это лучше задавать в driver, но можно попробовать "/orientation" нельзя — Sumatra не имеет явного флага
    # Обычно ориентация берётся из PDF-страницы, а не принудительно.

    # сам файл
    args.append(os.path.abspath(pdf_path))

    # Запускаем
    # подавим окно:
    creationflags = 0x08000000  # CREATE_NO_WINDOW
    proc = subprocess.Popen(args, creationflags=creationflags)

    if wait:
        # Сопоставим job по имени документа: у Sumatra документ обычно = имя файла
        _wait_for_job_disappear(doc_name=os.path.basename(pdf_path),
                                printer_name=printer,
                                timeout_s=wait_timeout_s)


def _merge_pages_for_sumatra(pages: Iterable[int]) -> str:
    """
    Превращаем [1,2,3,7,8] -> "1-3,7-8"
    """
    pages = sorted(set(int(p) for p in pages))
    if not pages:
        return ""
    ranges = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
        else:
            ranges.append(_fmt_range(start, prev))
            start = prev = p
    ranges.append(_fmt_range(start, prev))
    return ",".join(ranges)

def _fmt_range(a, b):
    return f"{a}-{b}" if a != b else f"{a}"

def _resolve_sumatra() -> str:
    """
    Пытаемся найти SumatraPDF.exe, если путь в конфиге пуст/не существует.
    """
    if SUMATRA_PATH and os.path.isfile(SUMATRA_PATH):
        return SUMATRA_PATH
    # автопоиск в Program Files
    candidates = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # последний шанс — окружение
    return SUMATRA_PATH or "SumatraPDF.exe"

def _wait_for_job_disappear(doc_name: str, printer_name: str, timeout_s: int):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        jobs = enum_jobs(printer_name)
        names = [j.get("pDocument", "") for j in jobs]
        if doc_name not in names:
            return
        time.sleep(1)
    # если нужно — можно бросить исключение
    # raise TimeoutError("Печать не завершилась вовремя")
