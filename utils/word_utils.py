# utils/word_utils.py
import pythoncom
import win32com.client
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional

# Исполнитель с одним потоком — все COM-вызовы идут сюда
_executor: Optional[ThreadPoolExecutor] = None
# Объект Word живёт ТОЛЬКО внутри потока _executor
_APP = None
_initialized_in_thread = False


def _thread_bootstrap():
    """Выполняется внутри COM-потока один раз: CoInitialize + создание Word."""
    global _APP, _initialized_in_thread
    if _initialized_in_thread:
        return
    pythoncom.CoInitialize()
    _APP = win32com.client.Dispatch("Word.Application")
    _APP.Visible = False
    _APP.DisplayAlerts = 0
    _initialized_in_thread = True
    logging.info("[word_utils] Word initialized in dedicated thread")


def init_word():
    """
    Готовит executor и инициализирует Word в его единственном потоке.
    Вызывать один раз при старте бота.
    """
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="WORD_COM")
        # Запускаем bootstrap в том самом потоке
        _executor.submit(_thread_bootstrap).result()
    return True


def close_word():
    """Закрывает Word и останавливает поток-исполнитель."""
    global _executor, _APP, _initialized_in_thread
    if _executor is None:
        return
    try:
        def _shutdown():
            global _APP, _initialized_in_thread
            try:
                if _APP is not None:
                    _APP.Quit()
            except Exception:
                pass
            finally:
                _APP = None
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
                _initialized_in_thread = False

        _executor.submit(_shutdown).result(timeout=15)
    finally:
        _executor.shutdown(wait=True, cancel_futures=False)
        _executor = None
        logging.info("[word_utils] Word closed and executor stopped")


def reload_word():
    close_word()
    return init_word()


def run_on_word_thread(func: Callable[..., Any], *args, **kwargs):
    """
    Синхронно выполняет func(*args, **kwargs) в COM-потоке Word и возвращает результат.
    Использовать из НЕ-async кода (или через loop.run_in_executor, если нужно).
    """
    if _executor is None:
        raise RuntimeError("Word is not initialized. Call init_word() first.")
    return _executor.submit(_safe_call, func, *args, **kwargs).result()


def _safe_call(func: Callable[..., Any], *args, **kwargs):
    """
    Обёртка, которая гарантирует, что bootstrap выполнен и ловит исключения
    с подробным логом стека.
    """
    try:
        _thread_bootstrap()
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"[word_utils] COM call failed: {e}\n{traceback.format_exc()}")
        raise
