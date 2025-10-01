# utils/pdf_utils.py
import os
import asyncio
from PyPDF2 import PdfReader
import fitz  # PyMuPDF

from config import ALLOWED_FILE_TYPES
from utils.word_utils import init_word, run_on_word_thread

SUPPORTED_EXTENSIONS = [ext.lower() for ext in ALLOWED_FILE_TYPES]
conversion_lock = asyncio.Lock()


def is_supported_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_EXTENSIONS


async def convert_docx_to_pdf(docx_path: str) -> str:
    """
    DOCX → PDF через COM Word. PDF сохраняется рядом с DOCX.
    ВАЖНО: все COM-вызовы идут в один выделенный поток.
    """
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    abs_docx = os.path.abspath(docx_path)
    abs_pdf = os.path.abspath(pdf_path)

    async with conversion_lock:
        # убеждаемся, что Word и поток инициализированы
        init_word()
        loop = asyncio.get_running_loop()
        # выполняем экспорт СИНХРОННО в том же COM-потоке через run_on_word_thread
        await loop.run_in_executor(None, run_on_word_thread, _export_docx_to_pdf, abs_docx, abs_pdf)

    return pdf_path

def get_orientation_ranges(file_path):
    """
    Возвращает список диапазонов страниц с одинаковой ориентацией
    (portrait/landscape) для PDF-документа.

    Пример возвращаемой структуры:
    [
        {"type": "portrait", "start": 1, "end": 3},
        {"type": "landscape", "start": 4, "end": 5},
        {"type": "portrait", "start": 6, "end": 10},
    ]
    """
    reader = PdfReader(file_path)
    result = []

    current = None
    for i, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        orientation = "landscape" if width > height else "portrait"

        if current is None or current["type"] != orientation:
            if current:
                result.append(current)
            current = {"type": orientation, "start": i + 1, "end": i + 1}
        else:
            current["end"] = i + 1

    if current:
        result.append(current)

    return result


def _export_docx_to_pdf(docx_path: str, pdf_path: str):
    """
    Эта функция выполняется внутри COM-потока (run_on_word_thread -> _safe_call).
    Здесь уже гарантированно есть CoInitialize и один общий _APP.
    """
    import pythoncom
    import win32com.client
    # Получаем объект Word в текущем (COM) потоке
    # (он был создан в bootstrap; доступ — через глобал в word_utils._APP)
    # Чтобы не лезть в приватные переменные, просто используем GetActiveObject/Dispatch:
    try:
        app = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        app = win32com.client.Dispatch("Word.Application")

    doc = app.Documents.Open(docx_path, ReadOnly=True)
    try:
        # 17 = wdExportFormatPDF
        doc.ExportAsFixedFormat(OutputFileName=pdf_path, ExportFormat=17)
    finally:
        doc.Close(False)


async def convert_image_to_pdf(image_path: str) -> str:
    output_path = os.path.splitext(image_path)[0] + ".pdf"
    async with conversion_lock:
        img_doc = fitz.open(image_path)
        try:
            pdf_bytes = img_doc.convert_to_pdf()
            pdf_doc = fitz.open("pdf", pdf_bytes)
            try:
                pdf_doc.save(output_path)
            finally:
                pdf_doc.close()
        finally:
            img_doc.close()
    return output_path


def count_pdf_pages(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


async def get_page_count(file_path: str) -> tuple[int, str]:
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".pdf":
        return count_pdf_pages(file_path), file_path

    if ext in {".docx", ".doc"}:
        pdf_path = await convert_docx_to_pdf(file_path)
        return count_pdf_pages(pdf_path), pdf_path

    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
        pdf_path = await convert_image_to_pdf(file_path)
        return count_pdf_pages(pdf_path), pdf_path

    raise ValueError("Unsupported file type")
