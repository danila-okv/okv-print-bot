# modules/admin/services/ban.py

from db import get_connection
from modules.analytics.logger import info

def ban_user(user_id: int, reason: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bans(user_id, reason) VALUES(?, ?)",
            (user_id, reason)
        )
        conn.commit()
        info(
            user_id,
            "user_banned",
            f"User {user_id} banned for reason: {reason}"
        )

def unban_user(user_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        conn.commit()
        info(
            user_id,
            "user_unbanned",
            f"User {user_id} unbanned"
        )

def is_banned(user_id: int) -> bool:
    cur = get_connection().execute(
        "SELECT 1 FROM bans WHERE user_id = ?",
        (user_id,)
    )
    return cur.fetchone() is not None
