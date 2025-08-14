import os

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from modules.printing.pdf_utils import get_page_count, is_supported_file, convert_docx_to_pdf
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

router = Router()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.message(F.document)
@check_paused
async def handle_document(message: Message, state: FSMContext):
    doc = message.document
    original_file_name = doc.file_name
    user_id = message.from_user.id

    info(
        message.from_user.id, 
        "handle_document", 
        f"User uploaded a document for printing, {original_file_name}, {doc.file_size} bytes"
    )

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
    user_folder = os.path.join(UPLOAD_DIR, str(user_id))
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

        if ext == ".docx":

            temp_pdf = await convert_docx_to_pdf(uploaded_file_path)
            info(user_id,
                 "handle_document",
                 f"Converted DOCX to PDF: {temp_pdf}"
            )
            pdf_file_name = os.path.splitext(original_file_name)[0] + ".pdf"
            final_pdf_path = os.path.join(user_folder, pdf_file_name)
            os.replace(temp_pdf, final_pdf_path)
            processed_pdf_path = final_pdf_path
        else:
            processed_pdf_path = uploaded_file_path

        page_count, _ = await get_page_count(processed_pdf_path)

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
