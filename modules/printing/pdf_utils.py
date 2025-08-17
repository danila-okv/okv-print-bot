import os
import asyncio
from PyPDF2 import PdfReader
from docx2pdf import convert
import shutil
import fitz  # PyMuPDF for image to PDF conversion

# Import configured temporary directory and allowed file types from config.  We
# import the string representation because os.path.join expects strings rather
# than Path objects.  See config.py for details.
from config import TMP_DIR_STR, ALLOWED_FILE_TYPES

# Copy the allowed types into SUPPORTED_EXTENSIONS for backwards compatibility.
SUPPORTED_EXTENSIONS = [ext.lower() for ext in ALLOWED_FILE_TYPES]

conversion_lock = asyncio.Lock()

def is_supported_file(filename: str) -> bool:
    """Return True if the file has an extension listed in the configuration."""
    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_EXTENSIONS

async def convert_docx_to_pdf(docx_path: str) -> str:
    """
    Safely converts a .docx document to .pdf and returns the path to the
    resulting PDF.  Uses a fixed filename inside the configured temporary
    directory for compatibility with environments like macOS.
    """
    tmp_dir = TMP_DIR_STR
    os.makedirs(tmp_dir, exist_ok=True)

    fixed_input_path = os.path.join(tmp_dir, "convert.docx")
    fixed_output_path = os.path.join(tmp_dir, "converted.pdf")

    # Copy the input docx to a fixed location
    shutil.copy(docx_path, fixed_input_path)

    async with conversion_lock:
        loop = asyncio.get_event_loop()
        # docx2pdf signature: convert(input, output, keep_active)
        await loop.run_in_executor(None, convert, fixed_input_path, fixed_output_path, True)

    return fixed_output_path

async def convert_image_to_pdf(image_path: str) -> str:
    """
    Convert a single image to a PDF.  Returns the path to the generated
    PDF file.  The output file will reside in the configured temporary
    directory and share the base name with the original image but with a
    .pdf extension.  Uses PyMuPDF (fitz) for conversion.
    """
    tmp_dir = TMP_DIR_STR
    os.makedirs(tmp_dir, exist_ok=True)
    base_name = os.path.basename(image_path)
    name_no_ext, _ = os.path.splitext(base_name)
    output_path = os.path.join(tmp_dir, f"{name_no_ext}.pdf")

    async with conversion_lock:
        # Open the image file
        image_doc = fitz.open(image_path)
        # Convert to PDF bytes
        pdf_bytes = image_doc.convert_to_pdf()
        # Open the PDF bytes as a new document
        pdf_doc = fitz.open("pdf", pdf_bytes)
        pdf_doc.save(output_path)
        pdf_doc.close()
        image_doc.close()
    return output_path

def count_pdf_pages(pdf_path: str) -> int:
    """Return the number of pages in a PDF file."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)

async def get_page_count(file_path: str) -> tuple[int, str]:
    """
    Return a tuple of (page_count, pdf_path) for the given file.

    If the file is already a PDF, count its pages directly.  If it's a DOCX,
    convert it to PDF using convert_docx_to_pdf() then count pages.  If it's
    an image (JPEG, PNG, GIF, BMP, TIFF, WEBP), convert it to PDF using
    convert_image_to_pdf().  Unsupported file types will raise a ValueError.
    """
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".pdf":
        return count_pdf_pages(file_path), file_path
    elif ext == ".docx":
        # Convert DOCX to PDF and count pages
        try:
            pdf_path = await convert_docx_to_pdf(file_path)
            page_count = count_pdf_pages(pdf_path)
            return page_count, pdf_path
        finally:
            # Remove temporary files used for conversion
            tmp_dir = TMP_DIR_STR
            for tmp_file in ["convert.docx", "converted.pdf"]:
                tmp_path = os.path.join(tmp_dir, tmp_file)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
    elif ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
        # Convert image to PDF and count pages (should be 1)
        try:
            pdf_path = await convert_image_to_pdf(file_path)
            page_count = count_pdf_pages(pdf_path)
            return page_count, pdf_path
        finally:
            # Remove temporary file for image conversion.  Remove only the
            # generated PDF file; the original image remains in place.
            name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
            tmp_pdf_path = os.path.join(TMP_DIR_STR, f"{name_no_ext}.pdf")
            if os.path.exists(tmp_pdf_path):
                os.remove(tmp_pdf_path)
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