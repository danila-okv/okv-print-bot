# modules/analytics/logger.py
import os
import logging
from logging import LoggerAdapter
from datetime import datetime
from config import LOG_DIR, LOG_DIR_STR, LOG_TO_CONSOLE

# Ensure the log directory exists (config.py should already do this, but
# performing it here makes the module self‑sufficient if imported alone).
os.makedirs(LOG_DIR, exist_ok=True)
date_str = datetime.now().strftime("%Y-%m-%d")
# Compose the path to today's log file.  Convert Path to string because
# logging API expects simple strings for file names.
LOG_PATH = os.path.join(LOG_DIR_STR, f"{date_str}.log")

# Базовый логгер
_base_logger = logging.getLogger("printer_bot")
_base_logger.setLevel(logging.DEBUG)

# File handler writes all log records to the daily log file.
file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# [14:05] [LEVEL] [12345] [cmd_print] Message
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(user_id)s] [%(handler)s] %(message)s",
    datefmt="%H:%M"
)
file_handler.setFormatter(formatter)
_base_logger.addHandler(file_handler)

# Optionally add a console handler.  When LOG_TO_CONSOLE is True, messages
# will be printed to stdout in the same format as the file handler.  This
# is useful during development but can be disabled in production to
# prevent noisy output.
if LOG_TO_CONSOLE:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    _base_logger.addHandler(console_handler)

# Обёртка, которая добавляет поля user_id и handler в каждый рекорд
class _ContextAdapter(LoggerAdapter):
    def process(self, msg, kwargs):
        # extra — это dict, который логгер добавит в рекорд
        extra = self.extra.copy()
        extra.update(kwargs.get("extra", {}))
        kwargs["extra"] = extra
        return msg, kwargs

# Экземпляр, в который подсовываем шаблонные поля
logger = _ContextAdapter(_base_logger, {"user_id": "-", "handler": "-"})

# Уровень ACTION между INFO и WARNING, если хочется выделить «важное действие»
ACTION_LEVEL = 25
logging.addLevelName(ACTION_LEVEL, "ACTION")
def action(self, message, *args, **kws):
    if self.isEnabledFor(ACTION_LEVEL):
        # вызываем внутренний метод log()
        self._log(ACTION_LEVEL, message, args, **kws)
# Добавляем метод в Logger и Adapter
logging.Logger.action = action
LoggerAdapter.action = lambda self, msg, **k: self.log(ACTION_LEVEL, msg, **k)

# Удобные врапперы для каждого уровня, чтобы не писать `.log(logging.ERROR, …)`
def error(user_id: int, handler: str, msg: str, **kwargs):
    logger.error(msg, extra={"user_id": user_id, "handler": handler}, **kwargs)

def warning(user_id: int, handler: str, msg: str, **kwargs):
    logger.warning(msg, extra={"user_id": user_id, "handler": handler}, **kwargs)

def info(user_id: int, handler: str, msg: str, **kwargs):
    logger.info(msg, extra={"user_id": user_id, "handler": handler}, **kwargs)

def action(user_id: int, handler: str, msg: str, **kwargs):
    logger.action(msg, extra={"user_id": user_id, "handler": handler}, **kwargs)
