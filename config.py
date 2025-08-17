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

###############################################################################
# Basic bot configuration
###############################################################################

# Price per single printed page (in your local currency).  When adjusting this
# value, remember that downstream calculations may perform rounding; see
# modules/billing/services/calculate_price.py for details.
PRICE_PER_PAGE: float = 0.20

# A set of Telegram user IDs who have administrative privileges.  Only these
# users may access admin-only commands such as statistics, logs and gifts.
ADMIN_IDS: set[int] = {7676096317}

# The SQLite database file name used to store state.  It will be created
# automatically when first accessed.  You can change this filename if you wish
# to store the database in a different location within the project root.
DB_FILE_NAME: str = "bot.db"

###############################################################################
# File system paths
###############################################################################

# Determine the base directory of the project (the directory containing this
# config file).  All other relative paths are derived from this location.
_BASE_DIR: Path = Path(__file__).resolve().parent

# Directory for persistent user data, such as uploads and temporary files.
# Under this folder you will find subdirectories for uploads, temporary
# conversion files and debugging resources.  Feel free to relocate the
# top‑level data directory by changing DATA_DIR; the subdirectories will
# follow automatically.  When this module is imported the directories will
# be created if they do not already exist.
DATA_DIR: Path = _BASE_DIR / "data"
UPLOAD_DIR: Path = DATA_DIR / "uploads"
TMP_DIR: Path = DATA_DIR / "tmp"
DEBUG_DIR: Path = DATA_DIR / "debug"

# Directory for log files.  Each log file is named according to the
# current date (YYYY‑MM‑DD.log).  See modules/analytics/logger.py for
# implementation.
LOG_DIR: Path = _BASE_DIR / "logs"

# Directory where periodic backups of the database and other important data
# should be stored.  See modules/admin/services/control.py for a backup helper.
BACKUP_PATH: Path = _BASE_DIR / "backups"

# Ensure that all necessary directories exist.  We suppress any
# FileExistsError by using exist_ok=True.  Other errors (e.g. permission
# denied) will propagate.
for _dir in (DATA_DIR, UPLOAD_DIR, TMP_DIR, DEBUG_DIR, LOG_DIR, BACKUP_PATH):
    os.makedirs(_dir, exist_ok=True)

###############################################################################
# Debugging configuration
###############################################################################

# Flag indicating whether the bot is running in debug mode.  When True,
# commands such as /debug_print may behave differently (e.g. using the
# DEBUG_PRINT_FILE instead of requiring a user upload).  Leave False for
# production.
IS_DEBUG: bool = False

# Name of the PDF used for debug printing.  Only relevant if IS_DEBUG
# is enabled.
DEBUG_PRINT_FILE_NAME: str = "debug.pdf"

# Full path to the debug PDF file.  Stored inside the dedicated debug
# directory.  You may replace the file in this location to change the
# default debug print document.
DEBUG_PRINT_FILE_PATH: Path = DEBUG_DIR / DEBUG_PRINT_FILE_NAME

# The default number of pages assumed for the debug document if the actual
# document is unavailable.  Adjust this if your debug PDF has a different
# length.
DEBUG_PAGE_COUNT: int = 4

# The default cost (in your local currency) for printing the entire debug
# document.  Combined with DEBUG_PAGE_COUNT this allows the bot to
# simulate printing costs without reading a file.
DEBUG_PRICE: float = 0.80

###############################################################################
# Logging configuration
###############################################################################

# When True, log records will be sent to the console (stdout) in addition
# to being written to the daily log file.  This is helpful during
# development but can be noisy in production.  modules/analytics/logger.py
# reads this value when configuring its loggers.
LOG_TO_CONSOLE: bool = False

###############################################################################
# User and job limits / promotional settings
###############################################################################

# Number of free pages to credit to a user upon their first interaction with the
# bot.  A value of 0 disables this feature.  See modules/ui/handlers/main_menu.py
# for implementation.
FREE_PAGES_ON_REGISTER: int = 5

# Default discount percentage applied to every print job.  This acts as a
# baseline discount for all users and stacks with any discount codes they may
# activate.  For example, if DISCOUNT_PERCENT is 5.0 and a promo code gives
# another 10%, the user will receive the larger of the two discounts.  Set to
# 0.0 to disable a default discount.
DISCOUNT_PERCENT: float = 0.0

# List of allowed file extensions (lower‑case, with leading dot) that users may
# upload for printing.  Include both documents and images.  Modify this list
# to permit additional formats.  The pdf_utils module reads this value.
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

# Maximum size of an uploaded file in megabytes.  Files exceeding this limit
# will be rejected by the upload handler.  A value of 0 disables this check.
MAX_FILE_SIZE_MB: int = 20

# Maximum number of pages allowed per print job.  If a document exceeds this
# limit, the user will be asked to reduce the page range or split the job.  A
# value of 0 disables this check.
MAX_PAGES_PER_JOB: int = 100

###############################################################################
# Derived values for convenience
###############################################################################

# Derived database path relative to the base directory
DB_PATH: Path = _BASE_DIR / DB_FILE_NAME

# Convenience string versions of some paths for legacy code.  Older modules
# in the project expect plain strings rather than Path objects.  You can
# refactor them to use Path objects in the future.
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