from db import get_connection
from datetime import datetime, timedelta

from aiogram import Bot

from config import ADMIN_IDS

def all_supplies() -> list[dict]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT name, quantity, minimum, unit, updated_at
            FROM supplies
            ORDER BY name
            """
        )
        return [dict(row) for row in cur.fetchall()]
    

def update_supply(
    name: str,
    quantity: float,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO supplies (name, quantity, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                quantity = excluded.quantity,
                updated_at = excluded.updated_at
            """,
            (name, quantity),
        )
        conn.commit()


async def consume_supply(
    name: str,
    quantity: int,
    bot: Bot | None = None
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE supplies
            SET quantity = quantity - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
            """,
            (quantity, name),
        )
        conn.commit()

        row = conn.execute(
        
            "SELECT quantity, minimum FROM supplies WHERE name = ?",
            (name,)
        ).fetchone()

        conn.commit()

        if row and row["quantity"] < row["minimum"] and bot:
            for admin_id in ADMIN_IDS:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ Запас '{name}' ниже минимального уровня ({row['quantity']} {row['minimum']}). Пора пополнить!"
                )