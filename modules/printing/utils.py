import re

def parse_pages(input_str, max_pages=None):
    pages = set()
    input_str = input_str.replace(" ", "")
    parts = input_str.split(',')

    for part in parts:
        if re.fullmatch(r"\d+", part):
            page = int(part)
            if page < 1 or (max_pages and page > max_pages):
                raise ValueError(f"Неверный номер страницы: {page}")
            pages.add(page)
        elif re.fullmatch(r"\d+-\d+", part):
            start, end = map(int, part.split('-'))
            if start > end:
                raise ValueError(f"Неверный диапазон: {part}")
            if max_pages and (start < 1 or end > max_pages):
                raise ValueError(f"Диапазон вне допустимого диапазона: {part}")
            pages.update(range(start, end + 1))
        else:
            raise ValueError(f"Неправильный формат: {part}")

    return sorted(pages)
