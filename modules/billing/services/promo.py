from datetime import datetime
from db import get_connection

def get_active_promos_for_user(user_id: int) -> list[dict]:
    now = datetime.now().isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.code, p.reward_type, p.reward_value
            FROM promos p
            JOIN promo_activations pa USING(code)
            WHERE pa.user_id = ?
              AND (p.expires_at IS NULL OR p.expires_at > ?)
              AND p.activations_used <= p.activations_total
        """, (user_id, now)).fetchall()
    return [dict(row) for row in rows]

def get_user_bonus_pages(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT bonus_pages FROM user_bonus WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    return row["bonus_pages"] if row else 0

def get_user_discounts(user_id: int) -> tuple[int, float, str]:
    # бонусы из таблицы
    bonus = get_user_bonus_pages(user_id)

    promos = get_active_promos_for_user(user_id)
    pages_promos = [(p["reward_value"], p["code"]) for p in promos if p["reward_type"] == "pages"]
    discs_promos = [(p["reward_value"], p["code"]) for p in promos if p["reward_type"] == "discount"]

    # наименьший индекс промокода единым: либо страницы, если больше или скидка, если она дает больше выгоды
    best_pages = max(pages_promos, default=(0, None))
    best_disc = max(discs_promos, default=(0.0, None))

    # объединяем бонус от таблицы + промокод
    total_bonus_pages = bonus + int(best_pages[0])
    # при выборе нужно решить — использовать либо бонус, либо процент?
    # допустим, мы сразу сделаем так: применяем оба (бонус + скидка),
    # но логика выбора промокода — только один скидочный используется.

    discount_percent = float(best_disc[0])
    used_code = best_disc[1] or best_pages[1]
    return total_bonus_pages, discount_percent, used_code

def record_promo_activation(user_id: int, code: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO promo_activations(user_id, code) VALUES(?, ?)",
            (user_id, code)
        )
        conn.execute(
            "UPDATE promos SET activations_used = activations_used + 1 WHERE code = ?",
            (code,)
        )
        conn.commit()

def consume_bonus_pages(user_id: int, pages_used: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE user_bonus SET bonus_pages = bonus_pages - ? WHERE user_id = ?",
            (pages_used, user_id)
        )
        conn.commit()

def promo_exists(code: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM promos WHERE code = ?", (code,)).fetchone()
    return bool(row)

def promo_can_be_activated(code: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT 1
            FROM promos
            WHERE code = ?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
              AND activations_used < activations_total
        """, (code,)).fetchone()
    return bool(row)

def has_activated_promo(user_id: int, code: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT 1 FROM promo_activations
            WHERE user_id = ? AND code = ?
        """, (user_id, code)).fetchone()
    return bool(row)

def get_promo_reward(code: str) -> tuple[str, float]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT reward_type, reward_value FROM promos
            WHERE code = ?
        """, (code,)).fetchone()
    return (row["reward_type"], row["reward_value"]) if row else (None, 0)

def add_user_bonus_pages(user_id: int, pages: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_bonus(user_id, bonus_pages)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET bonus_pages = bonus_pages + ?
        """, (user_id, pages, pages))
        conn.commit()