import os
import asyncio
from PyPDF2 import PdfReader
from docx2pdf import convert
import shutil

SUPPORTED_EXTENSIONS = [".pdf", ".docx"]
conversion_lock = asyncio.Lock()

def is_supported_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_EXTENSIONS

async def convert_docx_to_pdf(docx_path: str) -> str:
    """
    Безопасно конвертирует .docx в .pdf и возвращает путь к pdf-файлу.
    Использует фиксированное имя для macOS совместимости.
    """
    tmp_dir = "data/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    fixed_input_path = os.path.join(tmp_dir, "convert.docx")
    fixed_output_path = os.path.join(tmp_dir, "converted.pdf")

    # Перезаписываем фиксированный input-файл
    shutil.copy(docx_path, fixed_input_path)

    async with conversion_lock:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, convert, fixed_input_path, fixed_output_path, True)

    return fixed_output_path

def count_pdf_pages(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)

async def get_page_count(file_path: str) -> tuple[int, str]:
    """
    Возвращает (количество_страниц, путь_к_pdf)
    Если файл .docx — конвертирует его, потом удаляет временные файлы
    """
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".pdf":
        return count_pdf_pages(file_path), file_path

    elif ext == ".docx":
        try:
            pdf_path = await convert_docx_to_pdf(file_path)
            page_count = count_pdf_pages(pdf_path)
            return page_count, pdf_path
        finally:
            # Удаляем временные файлы после подсчёта
            tmp_dir = "data/tmp"
            for tmp_file in ["convert.docx", "converted.pdf"]:
                tmp_path = os.path.join(tmp_dir, tmp_file)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
    else:
        raise ValueError("Unsupported file type")

def get_orientation_ranges(file_path):
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
            current = {"type": orientation, "start": i+1, "end": i+1}
        else:
            current["end"] = i+1

    if current:
        result.append(current)

    return result