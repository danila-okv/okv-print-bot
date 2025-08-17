# modules/admin/services/control.py

from db import get_connection
from typing import Optional, List, Dict
from pathlib import Path
import shutil
from datetime import datetime
from config import DB_PATH, BACKUP_PATH

PAUSE_KEY = 'paused'

def set_pause(reason: str) -> None:
    """Установить флаг паузы с причиной."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bot_state(key, value) VALUES (?, ?)",
            (PAUSE_KEY, reason)
        )
        conn.commit()

def clear_pause() -> None:
    """Снять флаг паузы."""
    with get_connection() as conn:
        conn.execute("DELETE FROM bot_state WHERE key = ?", (PAUSE_KEY,))
        conn.commit()

def is_paused() -> bool:
    """Проверить, стоит ли флаг паузы."""
    cur = get_connection().execute(
        "SELECT 1 FROM bot_state WHERE key = ?", (PAUSE_KEY,)
    )
    return cur.fetchone() is not None

def get_pause_reason() -> Optional[str]:
    """Получить текст причины паузы."""
    cur = get_connection().execute(
        "SELECT value FROM bot_state WHERE key = ?", (PAUSE_KEY,)
    )
    row = cur.fetchone()
    return row['value'] if row else None

def queue_action(user_id: int, action: str) -> None:
    """Сохранить попытку пользователя сделать что-то во время паузы."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO paused_actions(user_id, action) VALUES (?, ?)",
            (user_id, action)
        )
        conn.commit()

def pop_all_queued_actions() -> List[Dict]:
    """
    Вытянуть и удалить из очереди все отложенные действия.
    Возвращает список dict-ов с полями id, user_id, action.
    """
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT id, user_id, action FROM paused_actions ORDER BY created_at"
        )
        rows = [dict(row) for row in cur.fetchall()]
        conn.execute("DELETE FROM paused_actions;")
        conn.commit()
    return rows


def backup_database() -> Path:
    """
    Create a backup copy of the SQLite database in the configured backup directory.

    The backup file is named using the current timestamp to avoid collisions.
    Returns the Path to the created backup file.
    """
    # Ensure the backup directory exists (should already be created by config)
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_PATH / f"bot_backup_{timestamp}.db"
    shutil.copy2(DB_PATH, dest)
    return dest