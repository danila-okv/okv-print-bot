import re
from typing import List

def parse_pages_str(input_str, max_pages: int = None, offset: int = 0) -> str:
    input_str = input_str.replace(" ", "")
    if not input_str:
        raise ValueError("Пустой ввод")

    parts = input_str.split(',')
    for part in parts:
        if re.fullmatch(r"\d+", part):
            page = int(part) - offset
            if page < 1 or (max_pages and page > max_pages):
                raise ValueError(f"Неверный номер страницы: {part}")
        elif re.fullmatch(r"\d+-\d+", part):
            start, end = map(int, part.split('-'))
            start -= offset
            end -= offset
            if start > end:
                raise ValueError(f"Неверный диапазон: {part}")
            if max_pages and (start < 1 or end > max_pages):
                raise ValueError(f"Диапазон вне допустимого диапазона: {part}")
        else:
            raise ValueError(f"Неправильный формат: {part}")

    return input_str

def extract_pages(range_str: str) -> List[int]:
    result = set()
    for part in range_str.replace(" ", "").split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            result.update(range(start, end + 1))
        else:
            result.add(int(part))
    return sorted(result)

def merge_pages(pages: List[int]) -> str:
    if not pages:
        return ""

    pages = sorted(set(pages))
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


def calculate_pages_count(range_str: str) -> int:
    return len(extract_pages(range_str))


def is_valid_page_range(range_str: str, max_pages: int) -> bool:
    try:
        parse_pages_str(range_str, max_pages)
        return True
    except ValueError:
        return False


def normalize_page_range(range_str: str) -> str:
    return merge_pages(extract_pages(range_str))