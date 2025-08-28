from db import get_connection
from datetime import datetime, timedelta

def add_expense(
    category: str,
    amount: float,
    quantity: int = 1,
    note: str | None = None
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO expenses (category, amount, quantity, note)
            VALUES (?, ?, ?, ?)
            """,
            (category, amount, quantity, note),
        )
        conn.commit()

def list_expenses() -> list[dict]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT id, category, amount, quantity, note, created_at
            FROM expenses
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]