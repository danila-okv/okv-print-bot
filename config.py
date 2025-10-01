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

DEFAULT_PRINTER_NAME = "Pantum_P3010DW"
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
SUMATRA_FILE_NAME: str = "SumatraPDF-3.5.2-64.exe"

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
TOOLS_DIR: Path = _BASE_DIR / "tools"

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
# Printing queue configuration
###############################################################################

# Estimated time in seconds that it takes the printer to output a single page.
# This value is used to predict how long a job will spend in the queue and
# therefore how long a user may need to wait.  Adjust this based on the
# actual throughput of your printer.  For example, if your printer can
# reliably produce about 12 pages per minute, set this value to 5.0 (seconds).
QUEUE_TIME_PER_PAGE: float = 5.0

# Fixed overhead in seconds before a job begins printing.  This accounts for
# warm‑up time, spooling and any mechanical delays prior to the first page
# being produced.  It is added once per job when calculating the expected
# duration.  Increase this if your printer takes a long time to start
# printing after receiving data.
QUEUE_WARMUP_TIME: float = 10.0

# How frequently (in seconds) the bot should refresh the estimated wait
# times for queued print jobs.  When users are waiting in the queue, their
# status messages can be automatically updated at this interval to reflect
# progress.  Lower values result in more frequent updates but may increase
# message editing load.
QUEUE_STATUS_UPDATE_INTERVAL: float = 30.0

# Personal discount tiers define how many pages a user must print to unlock a
# percentage discount on future print jobs.  The keys represent the
# cumulative number of pages a user has printed (counting duplicates when
# multiple copies are produced), and the values represent the discount
# percentage that will be applied once that threshold has been reached.
# Tiers should be defined in ascending order; the bot will always apply
# the highest tier that the user qualifies for.  For example:
#     {100: 5.0, 300: 10.0, 600: 15.0}
# means that users receive a 5% discount after printing 100 pages in total,
# 10% after 300 pages, and 15% after 600 pages.  You can adjust the
# thresholds and percentages to suit your use case.  An empty dict disables
# the personal discount feature.
PERSONAL_DISCOUNT_TIERS: dict[int, float] = {
    100: 5.0,
    300: 10.0,
    600: 15.0,
}

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
    ".doc",
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

###############################################################################
# Derived values for convenience
###############################################################################

# Derived database path relative to the base directory
DB_PATH: Path = _BASE_DIR / DB_FILE_NAME
SUMATRA_PATH: Path = TOOLS_DIR / SUMATRA_FILE_NAME

# Convenience string versions of some paths for legacy code.  Older modules
# in the project expect plain strings rather than Path objects.  You can
# refactor them to use Path objects in the future.
UPLOAD_DIR_STR: str = str(UPLOAD_DIR)
TMP_DIR_STR: str = str(TMP_DIR)
LOG_DIR_STR: str = str(LOG_DIR)
DEBUG_PRINT_FILE_PATH_STR: str = str(DEBUG_PRINT_FILE_PATH)
BACKUP_PATH_STR: str = str(BACKUP_PATH)
SUMATRA_PATH_STR: str = str(SUMATRA_PATH)

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