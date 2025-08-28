from datetime import datetime, timedelta
from db import get_connection

def get_active_promos_for_user(user_id: int) -> list[dict]:
    """
    Возвращает список активных промокодов для пользователя. Промокод считается активным,
    если его общий срок действия не истёк (expires_at) и, при наличии
    duration_days, прошло не больше duration_days дней с момента активации. Также
    проверяется, что число активаций не превышает activations_total.
    """
    now_iso = datetime.now().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.code, p.reward_type, p.reward_value, p.duration_days, pa.activated_at
            FROM promos p
            JOIN promo_activations pa USING(code)
            WHERE pa.user_id = ?
              AND (p.expires_at IS NULL OR p.expires_at > ?)
              AND p.activations_used <= p.activations_total
            """,
            (user_id, now_iso),
        ).fetchall()
        result = []
        for row in rows:
            # Check per‑activation duration: if duration_days is not null, ensure still valid
            dur = row["duration_days"]
            if dur is not None:
                # Compute expiry for this activation
                # activated_at is stored as ISO timestamp
                try:
                    act_time = datetime.fromisoformat(row["activated_at"])
                except Exception:
                    act_time = datetime.strptime(row["activated_at"], "%Y-%m-%d %H:%M:%S")
                expiry = act_time + timedelta(days=dur)
                if expiry <= datetime.now():
                    continue
            result.append({
                "code": row["code"],
                "reward_type": row["reward_type"],
                "reward_value": row["reward_value"],
                "duration_days": row["duration_days"],
                "activated_at": row["activated_at"],
            })
    return result

def get_user_bonus_pages(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT bonus_pages FROM user_bonus WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    return row["bonus_pages"] if row else 0

from config import DISCOUNT_PERCENT, PERSONAL_DISCOUNT_TIERS
from utils.parsers import extract_pages

# Helper functions for personal discount calculation
def _calculate_user_total_pages_for_discount(user_id: int) -> int:
    """
    Compute the total number of pages a user has printed across all completed
    jobs.  This replicates the logic in the profile handler but is kept here
    to avoid circular imports and so that the discount engine can be
    self‑contained.  Pages are multiplied by the number of copies.  If a
    custom page range was selected for a job, only those pages are counted.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT page_count, pages, copies
            FROM print_jobs
            WHERE user_id = ? AND status = 'done'
            """,
            (user_id,),
        ).fetchall()

    total = 0
    for row in rows:
        copies = row["copies"] or 1
        # If a custom page range exists, count only those pages
        if row["pages"]:
            try:
                pages_list = extract_pages(row["pages"])
                pages_count = len(pages_list)
            except Exception:
                # Fall back to stored page_count if parsing fails
                pages_count = row["page_count"]
        else:
            pages_count = row["page_count"]
        total += pages_count * copies
    return total


def _get_personal_discount(user_id: int) -> float:
    """
    Determine the appropriate personal discount percentage for a user
    based on how many pages they have printed.  The PERSONAL_DISCOUNT_TIERS
    dictionary defines thresholds and corresponding discount percentages.
    The highest tier that the user has reached is returned.  If no tiers
    are defined or the user hasn't met any threshold, 0.0 is returned.
    """
    if not PERSONAL_DISCOUNT_TIERS:
        return 0.0
    try:
        total_pages = _calculate_user_total_pages_for_discount(user_id)
    except Exception:
        # In case of database issues, do not apply a personal discount
        return 0.0
    # Find the maximum tier threshold less than or equal to total_pages
    eligible = [pct for pages, pct in PERSONAL_DISCOUNT_TIERS.items() if total_pages >= pages]
    return max(eligible) if eligible else 0.0

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

    # Apply personal discount based on total pages printed.  This will override
    # promo‑based discounts only if it is larger.  An empty PERSONAL_DISCOUNT_TIERS
    # dictionary disables this feature completely.
    try:
        personal_discount = _get_personal_discount(user_id)
        if personal_discount > discount_percent:
            discount_percent = personal_discount
    except Exception:
        # Ignore errors when computing personal discounts
        pass

    # Apply default discount from configuration if greater than existing discount
    try:
        if DISCOUNT_PERCENT > discount_percent:
            discount_percent = DISCOUNT_PERCENT
    except Exception:
        # If config import fails or attribute missing, ignore and use current value
        pass
    return total_bonus_pages, discount_percent, used_code


def get_promo_info(code: str) -> dict | None:
    """
    Возвращает полную информацию о промокоде: тип, значение награды,
    срок действия (expires_at), продолжительность в днях (duration_days),
    и шаблон сообщения (message_template). Если промокод не найден — None.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT code, reward_type, reward_value, expires_at, duration_days, message_template
            FROM promos
            WHERE code = ?
            """,
            (code,),
        ).fetchone()
        return dict(row) if row else None


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