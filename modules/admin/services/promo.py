from db import get_connection
from datetime import datetime, timedelta

def create_promo(
    code: str,
    activations_total: int,
    reward_type: str,
    reward_value: float,
    expires_at: str | None = None,
    duration_days: int | None = None,
    message_template: str | None = None,
) -> None:
    """
    Создаёт промокод в базе данных.

    Аргументы:
        code: текст промокода.
        activations_total: общее число активаций.
        reward_type: "pages" или "discount".
        reward_value: количество страниц или процент скидки.
        expires_at: абсолютная дата истечения действия промокода (ГГГГ-ММ-ДД) или None.
        duration_days: срок действия в днях после активации или None для бессрочных.
        message_template: пользовательский текст, который будет отправлен при активации. В нём можно
            использовать {value} и {date}.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO promos (
                code, activations_total, reward_type, reward_value,
                expires_at, duration_days, message_template
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (code, activations_total, reward_type, reward_value, expires_at, duration_days, message_template),
        )
        conn.commit()

def list_promos() -> list[dict]:
    """
    Возвращает список промокодов со всеми полями.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT code, activations_total, activations_used, reward_type, reward_value,
                   expires_at, duration_days, message_template, created_at
            FROM promos
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]

def get_promo_details(code: str) -> dict | None:
    """
    Возвращает подробную информацию о промокоде по его коду.
    Включает срок действия, длительность и шаблон сообщения.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT code, activations_total, activations_used, reward_type, reward_value,
                   created_at, expires_at, duration_days, message_template
            FROM promos
            WHERE code = ?
            """,
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

def promo_exists(code: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("SELECT 1 FROM promos WHERE code = ?", (code,))
        return cur.fetchone() is not None