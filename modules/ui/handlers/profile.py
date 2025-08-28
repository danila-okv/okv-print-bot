from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict
from datetime import datetime, timedelta

from modules.ui.keyboards.profile import profile_kb
from modules.ui.keyboards.tracker import send_managed_message
from modules.ui.callbacks import PROFILE, ORDERS, MAIN_MENU
from modules.billing.services.promo import (
    get_user_bonus_pages,
    get_active_promos_for_user,
)
from utils.parsers import extract_pages
from db import get_connection


router = Router()


def _calculate_user_total_pages(user_id: int) -> int:
    """Return the total number of pages printed by the user across all completed jobs.

    Pages are multiplied by the number of copies. If a custom page range
    was selected for a job, only those pages are counted.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT page_count, pages, copies
            FROM print_jobs
            WHERE user_id = ? AND status = 'done'
            """,
            (user_id,),
        ).fetchall()

    total = 0
    for row in rows:
        copies = row["copies"] or 1
        if row["pages"]:
            try:
                pages_list = extract_pages(row["pages"])
                pages_count = len(pages_list)
            except Exception:
                # Fall back to stored page_count if parsing fails
                pages_count = row["page_count"]
        else:
            pages_count = row["page_count"]
        total += pages_count * copies
    return total


def _get_user_jobs(user_id: int) -> List[Dict]:
    """Retrieve a list of user's print jobs ordered by creation date descending.

    Each element contains file_name, printed_pages (pages * copies) and
    created_at timestamp. Jobs of any status are returned. If a job has a
    custom page range, only those pages are counted.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT file_name, page_count, pages, copies, created_at, status
            FROM print_jobs
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    jobs: List[Dict] = []
    for row in rows:
        copies = row["copies"] or 1
        if row["pages"]:
            try:
                pages_list = extract_pages(row["pages"])
                pages_count = len(pages_list)
            except Exception:
                pages_count = row["page_count"]
        else:
            pages_count = row["page_count"]
        printed_pages = pages_count * copies
        jobs.append(
            {
                "file_name": row["file_name"],
                "printed_pages": printed_pages,
                "created_at": row["created_at"],
                "status": row["status"],
            }
        )
    return jobs


def _build_orders_kb(page: int, total_items: int, per_page: int) -> InlineKeyboardMarkup:
    """Construct an inline keyboard for navigating order history.

    Adds "previous" and "next" buttons when appropriate, along with a
    button to return to the profile summary.
    """
    buttons: List[List[InlineKeyboardButton]] = []
    max_page = (total_items + per_page - 1) // per_page

    nav_row: List[InlineKeyboardButton] = []
    # Previous page button
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"orders:{page - 1}"
            )
        )
    # Next page button
    if page < max_page:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Далее", callback_data=f"orders:{page + 1}"
            )
        )
    if nav_row:
        buttons.append(nav_row)

    # Return to profile button
    buttons.append(
        [InlineKeyboardButton(text="👤 Профиль", callback_data=PROFILE)]
    )
    # Return to main menu
    buttons.append(
        [InlineKeyboardButton(text="🏠 Меню", callback_data=MAIN_MENU)]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)



@router.callback_query(F.data == PROFILE)
async def handle_profile(callback: CallbackQuery) -> None:
    """Show user's profile summary when the profile button is pressed."""
    user_id = callback.from_user.id

    total_pages = _calculate_user_total_pages(user_id)
    bonus_pages = get_user_bonus_pages(user_id)

    # Personal discount and progress calculation
    # Import tiers lazily to avoid circular dependencies
    from config import PERSONAL_DISCOUNT_TIERS
    # Determine current and next discount thresholds
    sorted_tiers = sorted(PERSONAL_DISCOUNT_TIERS.items()) if PERSONAL_DISCOUNT_TIERS else []
    current_discount: float = 0.0
    prev_threshold: int = 0
    next_threshold: int | None = None
    next_discount: float | None = None
    for threshold, discount in sorted_tiers:
        if total_pages >= threshold:
            current_discount = discount
            prev_threshold = threshold
        else:
            next_threshold = threshold
            next_discount = discount
            break
    pages_to_next = (next_threshold - total_pages) if next_threshold is not None else None
    # Build progress bar across the current tier (or filled if no next tier)
    if next_threshold is not None and next_threshold > prev_threshold:
        progress_ratio = (total_pages - prev_threshold) / (next_threshold - prev_threshold)
    else:
        progress_ratio = 1.0
    bar_length = 14
    filled_segments = int(progress_ratio * bar_length)
    if filled_segments > bar_length:
        filled_segments = bar_length
    bar = "".join(["█" if i < filled_segments else "-" for i in range(bar_length)])
    # Compose discount block lines
    discount_lines: list[str] = []
    # Always display current discount tier (0 if none reached)
    discount_lines.append(f"💸 Личная скидка: <b>{int(current_discount)}</b>%")
    if next_threshold is not None and next_discount is not None:
        discount_lines.append(
            f"🚀 До скидки <b>{int(next_discount)}</b>% осталось <b>{pages_to_next}</b> стр."
        )
    elif sorted_tiers:
        # User has reached the highest tier if tiers are defined
        discount_lines.append("🎉 Ты достиг максимальной скидки!")
    # Append visual progress bar
    discount_lines.append(f"Прогресс: <code>[{bar}]</code>")
    discount_block = "\n".join(discount_lines)

    # Collect active promos and format them
    promos = get_active_promos_for_user(user_id)
    promo_lines: List[str] = []
    for promo in promos:
        code = promo["code"]
        reward_type = promo["reward_type"]
        reward_value = promo["reward_value"]
        dur = promo.get("duration_days")
        activated_at = promo.get("activated_at")
        # Compute expiry date if duration is set
        if dur is not None and activated_at:
            try:
                act_dt = datetime.fromisoformat(activated_at)
            except Exception:
                try:
                    act_dt = datetime.strptime(activated_at, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    act_dt = None
            if act_dt:
                expiry_dt = act_dt + timedelta(days=dur)
                expiry_str = expiry_dt.strftime("%Y-%m-%d")
            else:
                expiry_str = ""
        else:
            # No duration specified — treat as perpetual
            expiry_str = ""
        if "GIFT" in code:
            code="Подарок"

        if reward_type == "pages":
            reward_text = f"{int(reward_value)} стр."
        else:
            reward_text = f"{int(reward_value)}%"

        if expiry_str:
            promo_lines.append(f"• <b>{code}</b>: {reward_text}, до {expiry_str}")
        else:
            promo_lines.append(f"• <b>{code}</b>: {reward_text}, навсегда")

    promos_block = "\n".join(promo_lines) if promo_lines else "Нет"

    bonus_line = f"🎁 Бесплатных страниц: <b>{bonus_pages}</b>\n" if bonus_pages > 0 else ""
    promo_line = f"🎟 <b>Активные промокоды:</b>\n{promos_block}" if promo_lines else ""

    profile_text = (
        "👤 <b>Твой профиль</b>\n\n"
        f"📄 Напечатано страниц: <b>{total_pages}</b>\n"
        f"{bonus_line}\n"
        f"{promo_line}\n\n"
        f"{discount_block}"
    )

    await send_managed_message(
        bot=callback.bot,
        user_id=user_id,
        text=profile_text,
        reply_markup=profile_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orders"))
async def handle_orders(callback: CallbackQuery) -> None:
    """Show paginated order history when the user selects the orders button."""
    user_id = callback.from_user.id
    # Determine which page we are on. The callback data may be "orders" or "orders:N".
    page = 1
    data = callback.data
    if ":" in data:
        try:
            page_str = data.split(":", 1)[1]
            page = int(page_str)
        except ValueError:
            page = 1
    if page < 1:
        page = 1

    jobs = _get_user_jobs(user_id)
    per_page = 5
    total_items = len(jobs)

    # Compute slice bounds
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_jobs = jobs[start_idx:end_idx]

    if not page_jobs:
        orders_text = "Ты пока ничего не печатал."
    else:
        lines: List[str] = []
        for idx, job in enumerate(page_jobs, start=start_idx + 1):
            # Format each job line: index. file_name — printed_pages стр.
            lines.append(
                f"{idx}. {job['file_name']} — <b>{job['printed_pages']}</b> стр."
            )
        orders_text = "\n".join(lines)

    header = f"📑 <b>История заказов</b> (страница {page})\n\n"
    text = header + orders_text

    kb = _build_orders_kb(page, total_items, per_page)

    # Update or send a new message. We choose to edit the existing message if
    # possible, but fall back to sending a managed message. Editing maintains
    # continuity when navigating pages.
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=kb
        )
    except Exception:
        await send_managed_message(
            bot=callback.bot,
            user_id=user_id,
            text=text,
            reply_markup=kb
        )
    await callback.answer()