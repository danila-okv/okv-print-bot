import os

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from modules.printing.pdf_utils import (
    get_page_count,
    is_supported_file,
    convert_docx_to_pdf,
    convert_image_to_pdf,
)
from modules.billing.services.calculate_price import calculate_price
from modules.billing.services.promo import get_user_discounts
from ..keyboards.review import details_review_kb, free_review_kb
from modules.admin.services.ban import is_banned
from .main_menu import send_main_menu
from states import UserStates
from ..messages import *
from modules.analytics.logger import action, warning, info, error
from ..keyboards.tracker import send_managed_message
from modules.decorators import check_paused

# Import configuration for upload paths and limits
from config import (
    UPLOAD_DIR,
    UPLOAD_DIR_STR,
    MAX_FILE_SIZE_MB,
    MAX_PAGES_PER_JOB,
)

router = Router()

# --- Media group support ---
#
# Some users may send multiple files (documents or images) in a single Telegram
# album (media group).  When this occurs, Telegram delivers each attachment as
# an individual message with the same ``media_group_id``.  Our standard
# handlers process each message immediately, which would override the
# FSMContext state for the user and confuse the user with multiple prompts.
# To handle albums gracefully, we collect all messages belonging to the same
# media group and process them together once the group is complete.  The
# resulting PDF is a merger of all uploaded files and pages; the user is
# presented with a single review step and a combined price.  This preserves
# consistency and avoids overwriting state between concurrent uploads.

from collections import defaultdict
import asyncio
from typing import Dict, Tuple, List, Any
from aiogram.types import File as TGFile
from aiogram.types import PhotoSize
from PyPDF2 import PdfReader, PdfWriter

# A registry for pending media groups.  The key is a tuple of (user_id,
# media_group_id) and the value is a dictionary containing:
#   messages: list of incoming Message objects belonging to the group
#   task:     the asyncio Task scheduled to process the group after a short
#             delay; when a new message arrives for the same group the
#             previous task is cancelled and rescheduled
#   bot:      reference to aiogram Bot instance
#   state:    the FSMContext to use for storing job data
pending_media_groups: Dict[Tuple[int, str], Dict[str, Any]] = {}


async def _process_media_group_after_delay(user_id: int, group_id: str) -> None:
    """Helper: wait briefly then process a media group if no new items arrive."""
    # The delay allows Telegram to deliver all parts of the album before we
    # process the group.  Without this delay we might process the group too
    # early and miss later parts.
    await asyncio.sleep(1.0)
    await process_media_group(user_id, group_id)


async def process_media_group(user_id: int, group_id: str) -> None:
    """
    Process all attachments in a media group for a given user.  This function
    downloads each document or photo, converts it to PDF if necessary,
    merges the resulting PDFs into a single file, calculates the total page
    count and price, and then updates the FSM context and sends the review
    message to the user.

    This function removes the group from the ``pending_media_groups`` registry
    once processing starts.  Errors encountered during processing will be
    reported to the user and logged using the logger functions.
    """
    key = (user_id, group_id)
    group = pending_media_groups.pop(key, None)
    if group is None:
        # Nothing to process
        return

    messages: List[Message] = group.get("messages", [])
    bot = group.get("bot")
    state: FSMContext = group.get("state")

    if not messages or bot is None or state is None:
        return

    # Compose the path to the user's upload folder.  Ensure it exists.
    user_folder = os.path.join(UPLOAD_DIR_STR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    # Send a processing message for the group
    file_names = []
    for msg in messages:
        if msg.document:
            file_names.append(msg.document.file_name)
        else:
            # photos don't have names; we assign them later
            file_names.append("photo")
    combined_name = ", ".join(file_names)

    processing_msg = await send_managed_message(
        bot=bot,
        user_id=user_id,
        text=FILE_PROCESSING_TEXT.format(file_name=combined_name)
    )

    # Prepare containers for processed PDF paths and page counts
    processed_pdf_paths: List[str] = []
    total_pages = 0
    global_error = False

    # Define inner helper to log and answer on failure
    async def handle_failure(err_msg: str) -> None:
        nonlocal global_error
        global_error = True
        await processing_msg.edit_text(err_msg)
        warning(user_id, "media_group", err_msg)
        # Send user back to main menu
        await send_main_menu(bot, user_id)

    # Process each message in the group
    for msg in messages:
        try:
            if msg.document:
                doc = msg.document
                # Check file size if configured (>0)
                if MAX_FILE_SIZE_MB and MAX_FILE_SIZE_MB > 0 and doc.file_size:
                    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
                    if doc.file_size > max_bytes:
                        await handle_failure(
                            f"📎 Файл '{doc.file_name}' слишком большой. Максимальный размер — {MAX_FILE_SIZE_MB} МБ."
                        )
                        break

                original_file_name = doc.file_name
                # Validate file type
                if not is_supported_file(original_file_name):
                    await handle_failure(FILE_TYPE_ERROR_TEXT)
                    break

                # Download file
                tg_file: TGFile = await bot.get_file(doc.file_id)
                file_data = await bot.download_file(tg_file.file_path)
                uploaded_file_path = os.path.join(user_folder, original_file_name)
                with open(uploaded_file_path, "wb") as f:
                    f.write(file_data.read())

                # Determine processing based on extension
                _, ext = os.path.splitext(original_file_name)
                ext = ext.lower()
                if ext == ".docx":
                    temp_pdf = await convert_docx_to_pdf(uploaded_file_path)
                    pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
                    final_pdf_path = os.path.join(user_folder, pdf_file_name)
                    os.replace(temp_pdf, final_pdf_path)
                    processed_path = final_pdf_path
                elif ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
                    temp_pdf = await convert_image_to_pdf(uploaded_file_path)
                    pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
                    final_pdf_path = os.path.join(user_folder, pdf_file_name)
                    os.replace(temp_pdf, final_pdf_path)
                    processed_path = final_pdf_path
                else:
                    # Already a PDF or other supported type
                    processed_path = uploaded_file_path

                # Count pages
                page_count, _ = await get_page_count(processed_path)
                # Enforce per-job page limit (if configured) on accumulation
                if MAX_PAGES_PER_JOB and MAX_PAGES_PER_JOB > 0 and (total_pages + page_count) > MAX_PAGES_PER_JOB:
                    await handle_failure(
                        f"❌ Слишком много страниц. Всего страниц после добавления '{original_file_name}' будет {total_pages + page_count}, "
                        f"что превышает допустимый лимит {MAX_PAGES_PER_JOB}."
                    )
                    break
                processed_pdf_paths.append(processed_path)
                total_pages += page_count

            elif msg.photo:
                # Photo (compressed)
                photo: PhotoSize = msg.photo[-1]
                file_size = photo.file_size
                if MAX_FILE_SIZE_MB and MAX_FILE_SIZE_MB > 0 and file_size:
                    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
                    if file_size > max_bytes:
                        await handle_failure(
                            f"📎 Изображение слишком большое. Максимальный размер — {MAX_FILE_SIZE_MB} МБ."
                        )
                        break
                # Compose a unique name for the photo
                file_unique_id = photo.file_unique_id
                original_file_name = f"photo_{file_unique_id}.jpg"
                # Download the photo
                tg_file: TGFile = await bot.get_file(photo.file_id)
                file_data = await bot.download_file(tg_file.file_path)
                uploaded_file_path = os.path.join(user_folder, original_file_name)
                with open(uploaded_file_path, "wb") as f:
                    f.write(file_data.read())
                # Convert to PDF
                temp_pdf = await convert_image_to_pdf(uploaded_file_path)
                pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
                final_pdf_path = os.path.join(user_folder, pdf_file_name)
                os.replace(temp_pdf, final_pdf_path)
                processed_path = final_pdf_path
                # Count pages (should be 1)
                page_count, _ = await get_page_count(processed_path)
                if MAX_PAGES_PER_JOB and MAX_PAGES_PER_JOB > 0 and (total_pages + page_count) > MAX_PAGES_PER_JOB:
                    await handle_failure(
                        f"❌ Слишком много страниц. Всего страниц после добавления изображения будет {total_pages + page_count}, "
                        f"что превышает допустимый лимит {MAX_PAGES_PER_JOB}."
                    )
                    break
                processed_pdf_paths.append(processed_path)
                total_pages += page_count
            else:
                # Unknown type; skip
                continue
        except Exception as err:
            await handle_failure(FILE_PROCESSING_FAILURE_TEXT.format(file_name=combined_name))
            error(user_id, "media_group", f"Error processing group item: {err}")
            break

    if global_error:
        # Already handled
        return

    # If no pages processed, nothing to do
    if total_pages == 0:
        await processing_msg.edit_text("❌ Не удалось обработать ни один файл.")
        warning(user_id, "media_group", "No pages processed")
        await send_main_menu(bot, user_id)
        return

    # Merge all processed PDFs into a single PDF
    try:
        # Name the merged PDF with the media_group_id for uniqueness
        merged_pdf_name = f"group_{group_id}.pdf"
        merged_pdf_path = os.path.join(user_folder, merged_pdf_name)
        pdf_writer = PdfWriter()
        for pdf_path in processed_pdf_paths:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                pdf_writer.add_page(page)
        with open(merged_pdf_path, "wb") as f_out:
            pdf_writer.write(f_out)
    except Exception as err:
        await processing_msg.edit_text(FILE_PROCESSING_FAILURE_TEXT.format(file_name=combined_name))
        error(user_id, "media_group", f"Error merging PDFs: {err}")
        await send_main_menu(bot, user_id)
        return

    # Apply user bonuses and discounts
    bonus_pages, discount_percent, promo_code = get_user_discounts(user_id)
    info(
        user_id,
        "media_group",
        f"User discounts: bonus_pages={bonus_pages}, discount_percent={discount_percent}, promo_code={promo_code}"
    )

    # Calculate price for total_pages
    price_data = calculate_price(
        page_range=f"1-{total_pages}",
        layout="1",
        copies=1,
        bonus_pages=bonus_pages,
        discount_percent=discount_percent
    )

    # Update FSM state with job details
    await state.update_data(
        price_data=price_data,
        file_path=merged_pdf_path,
        page_count=total_pages,
        file_name=combined_name,
        method="free" if price_data.get("final_price", 0) == 0 else None,
    )
    data = await state.get_data()

    # Choose keyboard based on the final price
    kb = free_review_kb if price_data.get("final_price", 0) == 0 else details_review_kb

    await processing_msg.edit_text(
        get_details_review_text(data),
        reply_markup=kb
    )
    info(
        user_id,
        "media_group",
        f"Group processed. pages: {total_pages}, price: {price_data['final_price']}"
    )

    await state.set_state(UserStates.reviewing_print_details)

# Ensure the upload directory exists.  The path comes from config.py.
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.message(F.document)
@check_paused
async def handle_document(message: Message, state: FSMContext):
    # If this document is part of a media group (album), defer processing to the
    # group handler.  We collect all attachments belonging to the same
    # media_group_id and process them together.  Without this check, each
    # document in an album would trigger a separate processing flow and
    # override the user's FSM state.  Note: we must place this check at
    # the very beginning of the handler before any side effects occur.
    if message.media_group_id:
        # Register the message into the pending media group and schedule
        # processing after a brief delay.  We use the current bot and state
        # objects; these will be reused when the group is processed.
        key = (message.from_user.id, message.media_group_id)
        group = pending_media_groups.get(key)
        if group is None:
            group = {"messages": [], "task": None, "bot": message.bot, "state": state}
            pending_media_groups[key] = group
        group["messages"].append(message)
        # Cancel the existing task if any and schedule a new one
        if group.get("task"):
            group["task"].cancel()
        loop = asyncio.get_running_loop()
        group["task"] = loop.create_task(_process_media_group_after_delay(message.from_user.id, message.media_group_id))
        return

    doc = message.document
    original_file_name = doc.file_name
    user_id = message.from_user.id

    info(
        message.from_user.id, 
        "handle_document", 
        f"User uploaded a document for printing, {original_file_name}, {doc.file_size} bytes"
    )

    # Validate file size if a maximum is configured (>0).  Some documents may
    # not provide a file_size attribute; handle missing values gracefully.
    if MAX_FILE_SIZE_MB and MAX_FILE_SIZE_MB > 0 and doc.file_size:
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if doc.file_size > max_bytes:
            await message.answer(
                f"📎 Файл слишком большой. Максимальный размер — {MAX_FILE_SIZE_MB} МБ."
            )
            warning(
                message.from_user.id,
                "handle_document",
                f"File size exceeds limit: {doc.file_size} bytes"
            )
            return

    if is_banned(user_id):
        await message.answer("🚫 Вы были заблокированы. Обратитесь к администратору.")
        warning(
        message.from_user.id, 
        "document_upload", 
        "Banned user: Access denied"
        )
        return

    if not is_supported_file(original_file_name):
        await message.answer(FILE_TYPE_ERROR_TEXT)
        warning(
        message.from_user.id, 
        "handle_document", 
        f"Unsupported file type {original_file_name}"
        )
        return

    user_id = message.from_user.id
    # Compose the path to the user's upload folder.  UPLOAD_DIR may be a
    # Path object; convert to string for os.path.join
    user_folder = os.path.join(UPLOAD_DIR_STR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    uploaded_file_path = os.path.join(user_folder, original_file_name)

    processing_msg = await send_managed_message(
        bot=message.bot,
        user_id=message.from_user.id,
        text=FILE_PROCESSING_TEXT.format(file_name=original_file_name)
    )

    await state.update_data(
        duplex=False,
        copies=1,
        layout=None,
        pages=None
    )
    
    info(
        message.from_user.id, 
        "handle_document", 
        f"Start file processing: {original_file_name}"
        )
    try:
        tg_file = await message.bot.get_file(doc.file_id)
        info(
        message.from_user.id, 
        "handle_document", 
        f"Downloading file: {tg_file.file_path}"
        )
        file_data = await message.bot.download_file(tg_file.file_path)
        info(
        message.from_user.id, 
        "handle_document", 
        f"File downloaded: {tg_file.file_path}"
        )
        with open(uploaded_file_path, "wb") as f:
            f.write(file_data.read())
        _, ext = os.path.splitext(original_file_name)
        ext = ext.lower()

        # Determine how to process the uploaded file based on its extension.
        if ext == ".docx":
            # Convert DOCX to PDF
            temp_pdf = await convert_docx_to_pdf(uploaded_file_path)
            info(
                user_id,
                "handle_document",
                f"Converted DOCX to PDF: {temp_pdf}"
            )
            pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
            final_pdf_path = os.path.join(user_folder, pdf_file_name)
            os.replace(temp_pdf, final_pdf_path)
            processed_pdf_path = final_pdf_path
        elif ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
            # Convert image to PDF
            temp_pdf = await convert_image_to_pdf(uploaded_file_path)
            info(
                user_id,
                "handle_document",
                f"Converted image to PDF: {temp_pdf}"
            )
            pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
            final_pdf_path = os.path.join(user_folder, pdf_file_name)
            os.replace(temp_pdf, final_pdf_path)
            processed_pdf_path = final_pdf_path
        else:
            # Already a PDF (or supported extension that doesn't need conversion)
            processed_pdf_path = uploaded_file_path

        # Count pages in the processed PDF
        page_count, _ = await get_page_count(processed_pdf_path)

        # Enforce maximum pages per job if configured (>0)
        if MAX_PAGES_PER_JOB and MAX_PAGES_PER_JOB > 0 and page_count > MAX_PAGES_PER_JOB:
            await processing_msg.edit_text(
                f"❌ Слишком много страниц ({page_count}). Максимально допустимо {MAX_PAGES_PER_JOB} страниц.\n"
                "Уменьши диапазон страниц или раздели документ."
            )
            warning(
                message.from_user.id,
                "handle_document",
                f"Document page count exceeds limit: {page_count}"
            )
            return

        bonus_pages, discount_percent, promo_code = get_user_discounts(message.from_user.id)
        info(
            message.from_user.id,
            "handle_document",
            f"User discounts: bonus_pages={bonus_pages}, discount_percent={discount_percent}, promo_code={promo_code}"
        )

        price_data = calculate_price(
            page_range=f"1-{page_count}",
            layout="1",
            copies=1,
            bonus_pages=bonus_pages,
            discount_percent=discount_percent
        )

        await state.update_data(
            price_data=price_data,
            file_path=processed_pdf_path,
            page_count=page_count,
            file_name=original_file_name,
            # метод free, если цена нулевая
            method="free" if price_data.get("final_price", 0) == 0 else None,
        )
        data = await state.get_data()

        # Выбираем клавиатуру в зависимости от итоговой цены
        kb = free_review_kb if price_data.get("final_price", 0) == 0 else details_review_kb

        await processing_msg.edit_text(
            get_details_review_text(data),
            reply_markup=kb
        )
        info(
            message.from_user.id,
            "handle_document",
            f'File processed. pages: {page_count}, price: {price_data["final_price"]}'
        )

        await state.set_state(UserStates.reviewing_print_details)
        

    except Exception as err:
        await processing_msg.edit_text(FILE_PROCESSING_FAILURE_TEXT.format(file_name=original_file_name))
        error(
            message.from_user.id,
            "handle_file",
            f"Failed document processing - {err}"
        )
        await send_main_menu(message.bot, message.chat.id)


@router.message(F.photo)
@check_paused
async def handle_photo(message: Message, state: FSMContext):
    """
    Handle images sent as compressed photos.  Telegram sends photos with
    multiple sizes; we select the highest resolution and process it like a
    document: validate size, convert to PDF, count pages (1), apply discounts
    and show review.  Supported image formats are defined in config.py.
    """
    user_id = message.from_user.id
    # If this photo is part of a media group (album), defer processing to the
    # group handler.  See ``handle_document`` for details.
    if message.media_group_id:
        key = (message.from_user.id, message.media_group_id)
        group = pending_media_groups.get(key)
        if group is None:
            group = {"messages": [], "task": None, "bot": message.bot, "state": state}
            pending_media_groups[key] = group
        group["messages"].append(message)
        if group.get("task"):
            group["task"].cancel()
        loop = asyncio.get_running_loop()
        group["task"] = loop.create_task(_process_media_group_after_delay(message.from_user.id, message.media_group_id))
        return

    # Take the largest available photo size for best quality
    photo = message.photo[-1]
    file_size = photo.file_size
    file_unique_id = photo.file_unique_id
    # Construct a file name using the unique ID with .jpg extension
    original_file_name = f"photo_{file_unique_id}.jpg"

    info(
        user_id,
        "handle_photo",
        f"User uploaded a photo for printing, {original_file_name}, {file_size} bytes"
    )

    # Validate file size if a maximum is configured (>0).  Some photos may
    # not provide a file_size attribute; handle missing values gracefully.
    if MAX_FILE_SIZE_MB and MAX_FILE_SIZE_MB > 0 and file_size:
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            await message.answer(
                f"📎 Изображение слишком большое. Максимальный размер — {MAX_FILE_SIZE_MB} МБ."
            )
            warning(
                user_id,
                "handle_photo",
                f"Photo size exceeds limit: {file_size} bytes"
            )
            return

    # Check if user is banned
    if is_banned(user_id):
        await message.answer("🚫 Вы были заблокированы. Обратитесь к администратору.")
        warning(
            user_id,
            "photo_upload",
            "Banned user: Access denied"
        )
        return

    # Compose the path to the user's upload folder
    user_folder = os.path.join(UPLOAD_DIR_STR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    uploaded_file_path = os.path.join(user_folder, original_file_name)

    # Notify the user that processing has started
    processing_msg = await send_managed_message(
        bot=message.bot,
        user_id=user_id,
        text=FILE_PROCESSING_TEXT.format(file_name=original_file_name)
    )

    # Initialise state defaults
    await state.update_data(
        duplex=False,
        copies=1,
        layout=None,
        pages=None
    )

    info(
        user_id,
        "handle_photo",
        f"Start photo processing: {original_file_name}"
    )
    try:
        # Download the photo from Telegram servers
        tg_file = await message.bot.get_file(photo.file_id)
        info(
            user_id,
            "handle_photo",
            f"Downloading photo: {tg_file.file_path}"
        )
        file_data = await message.bot.download_file(tg_file.file_path)
        info(
            user_id,
            "handle_photo",
            f"Photo downloaded: {tg_file.file_path}"
        )
        # Save the photo to the user's folder
        with open(uploaded_file_path, "wb") as f:
            f.write(file_data.read())

        # Convert image to PDF
        temp_pdf = await convert_image_to_pdf(uploaded_file_path)
        info(
            user_id,
            "handle_photo",
            f"Converted photo to PDF: {temp_pdf}"
        )
        pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
        final_pdf_path = os.path.join(user_folder, pdf_file_name)
        os.replace(temp_pdf, final_pdf_path)
        processed_pdf_path = final_pdf_path

        # Count pages in the resulting PDF (should be 1)
        page_count, _ = await get_page_count(processed_pdf_path)

        # Enforce maximum pages per job if configured (>0)
        if MAX_PAGES_PER_JOB and MAX_PAGES_PER_JOB > 0 and page_count > MAX_PAGES_PER_JOB:
            await processing_msg.edit_text(
                f"❌ Слишком много страниц ({page_count}). Максимально допустимо {MAX_PAGES_PER_JOB} страниц.\n"
                "Уменьши диапазон страниц или раздели документ."
            )
            warning(
                user_id,
                "handle_photo",
                f"Image page count exceeds limit: {page_count}"
            )
            return

        # Compute user bonuses and discounts
        bonus_pages, discount_percent, promo_code = get_user_discounts(user_id)
        info(
            user_id,
            "handle_photo",
            f"User discounts: bonus_pages={bonus_pages}, discount_percent={discount_percent}, promo_code={promo_code}"
        )

        # Calculate price for 1-page document (page_count)
        price_data = calculate_price(
            page_range=f"1-{page_count}",
            layout="1",
            copies=1,
            bonus_pages=bonus_pages,
            discount_percent=discount_percent
        )

        # Update state with job details
        await state.update_data(
            price_data=price_data,
            file_path=processed_pdf_path,
            page_count=page_count,
            file_name=original_file_name,
            method="free" if price_data.get("final_price", 0) == 0 else None,
        )
        data = await state.get_data()

        # Choose keyboard based on the final price
        kb = free_review_kb if price_data.get("final_price", 0) == 0 else details_review_kb

        await processing_msg.edit_text(
            get_details_review_text(data),
            reply_markup=kb
        )
        info(
            user_id,
            "handle_photo",
            f'Photo processed. pages: {page_count}, price: {price_data["final_price"]}'
        )

        await state.set_state(UserStates.reviewing_print_details)

    except Exception as err:
        await processing_msg.edit_text(FILE_PROCESSING_FAILURE_TEXT.format(file_name=original_file_name))
        error(
            user_id,
            "handle_photo",
            f"Failed photo processing - {err}"
        )
        await send_main_menu(message.bot, message.chat.id)
