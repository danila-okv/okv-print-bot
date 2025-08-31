from typing import Optional
from utils.parsers import extract_pages
from config import PRICE_PER_PAGE

def calculate_price(
    page_range: str,
    layout: str = "1",
    copies: int = 1,
    bonus_pages: int = 0,
    discount_percent: float = 0.0
) -> dict:
    pages = extract_pages(page_range)
    total_pages = len(pages) * copies

    pages_covered_by_bonus = min(bonus_pages, total_pages)
    pages_to_pay = total_pages - pages_covered_by_bonus

    # Use configured price per page
    price_per_page = PRICE_PER_PAGE
    raw_price = total_pages * price_per_page
    discounted_price = pages_to_pay * price_per_page * (1 - discount_percent / 100)

    return {
        "total_pages": total_pages,
        "pages_covered_by_bonus": pages_covered_by_bonus,
        "pages_to_pay": pages_to_pay,
        "price_per_page": price_per_page,
        "raw_price": raw_price,
        "final_price": round(discounted_price, 2),
        "discount_applied": discount_percent
    }