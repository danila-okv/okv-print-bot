"""
Centralized configuration for the Telegram printing bot.

This module defines all configurable parameters in one place, making it
easy to adjust bot behaviour without digging through the rest of
the codebase. Settings include pricing, administrative IDs, file
system paths, debugging toggles and user/job limits. When imported,
it ensures relevant directories exist so that other modules don't
need to explicitly create them.

If you modify these values, restart the bot to apply changes.
"""

from __future__ import annotations

import os
from pathlib import Path

# Basic bot configuration
PRICE_PER_PAGE: float = 0.20

ADMIN_IDS: set[int] = {7676096317}
CONTACT_USERNAME: str = "danila_okv"

DB_FILE_NAME: str = "bot.db"

# File system paths
_BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = _BASE_DIR / "data"
UPLOAD_DIR: Path = DATA_DIR / "uploads"
TMP_DIR: Path = DATA_DIR / "tmp"
DEBUG_DIR: Path = DATA_DIR / "debug"
LOG_DIR: Path = _BASE_DIR / "logs"
BACKUP_PATH: Path = _BASE_DIR / "backups"

for _dir in (DATA_DIR, UPLOAD_DIR, TMP_DIR, DEBUG_DIR, LOG_DIR, BACKUP_PATH):
    os.makedirs(_dir, exist_ok=True)


# Debugging configuration
IS_DEBUG: bool = False

DEBUG_PRINT_FILE_NAME: str = "debug.pdf"
DEBUG_PRINT_FILE_PATH: Path = DEBUG_DIR / DEBUG_PRINT_FILE_NAME
DEBUG_PAGE_COUNT: int = 4
DEBUG_PRICE: float = 0.01

# Logging configuration
LOG_TO_CONSOLE: bool = False

# Printing queue configuration
QUEUE_TIME_PER_PAGE: float = 5.0
QUEUE_WARMUP_TIME: float = 10.0
QUEUE_STATUS_UPDATE_INTERVAL: float = 30.0

# Promotional settings
PERSONAL_DISCOUNT_TIERS: dict[int, float] = {
    100: 5.0,
    300: 10.0,
    600: 15.0,
} 
FREE_PAGES_ON_REGISTER: int = 5
DISCOUNT_PERCENT: float = 0.0

ALLOWED_FILE_TYPES: list[str] = [
    ".pdf",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
]

MAX_FILE_SIZE_MB: int = 20
MAX_PAGES_PER_JOB: int = 100

# Derived values for convenience
DB_PATH: Path = _BASE_DIR / DB_FILE_NAME

UPLOAD_DIR_STR: str = str(UPLOAD_DIR)
TMP_DIR_STR: str = str(TMP_DIR)
LOG_DIR_STR: str = str(LOG_DIR)
DEBUG_PRINT_FILE_PATH_STR: str = str(DEBUG_PRINT_FILE_PATH)
BACKUP_PATH_STR: str = str(BACKUP_PATH)

__all__ = [
    # fundamental values
    "PRICE_PER_PAGE",
    "ADMIN_IDS",
    "DB_FILE_NAME",
    "DATA_DIR",
    "UPLOAD_DIR",
    "TMP_DIR",
    "DEBUG_DIR",
    "LOG_DIR",
    "IS_DEBUG",
    "DEBUG_PRINT_FILE_NAME",
    "DEBUG_PRINT_FILE_PATH",
    "DEBUG_PAGE_COUNT",
    "DEBUG_PRICE",
    "LOG_TO_CONSOLE",
    "FREE_PAGES_ON_REGISTER",
    "DISCOUNT_PERCENT",
    "QUEUE_TIME_PER_PAGE",
    "QUEUE_WARMUP_TIME",
    "QUEUE_STATUS_UPDATE_INTERVAL",
    "PERSONAL_DISCOUNT_TIERS",
    "ALLOWED_FILE_TYPES",
    "MAX_FILE_SIZE_MB",
    "MAX_PAGES_PER_JOB",
    "BACKUP_PATH",
    "DB_PATH",
    "UPLOAD_DIR_STR",
    "TMP_DIR_STR",
    "LOG_DIR_STR",
    "DEBUG_PRINT_FILE_PATH_STR",
    "BACKUP_PATH_STR",
]
