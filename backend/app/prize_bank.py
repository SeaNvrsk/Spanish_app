"""Monthly prize-share settlement into the family piggy bank (carryover)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import get_settings
from .family import competitors
from .gamification import month_rankings
from .models import User, DailyActivity, MonthPrizeCredit
from .msk_time import msk_today, msk_month_start


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _month_end(d: date) -> date:
    return d.replace(day=monthrange(d.year, d.month)[1])


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def closed_months(today: date | None = None, start: date | None = None) -> list[date]:
    """First day of each fully closed month from program start through last month."""
    today = today or msk_today()
    start = start or get_settings().program_start_date
    start_month = start.replace(day=1)
    last_closed = msk_month_start(today) - timedelta(days=1)
    last_closed = last_closed.replace(day=1)
    if last_closed < start_month:
        return []
    out: list[date] = []
    cursor = start_month
    while cursor <= last_closed:
        out.append(cursor)
        cursor = _add_months(cursor, 1)
    return out


def quarter_window(today: date | None = None, start: date | None = None) -> dict:
    """Current 3-month prize window aligned to program start (Jul–Sep, Oct–Dec, …)."""
    today = today or msk_today()
    start = start or get_settings().program_start_date
    start_month = start.replace(day=1)
    months_since = (today.year - start_month.year) * 12 + (today.month - start_month.month)
    q_index = max(0, months_since // 3)
    q_start = _add_months(start_month, q_index * 3)
    q_end_month = _add_months(q_start, 2)
    q_end = _month_end(q_end_month)
    months_done_in_q = min(3, max(0, months_since - q_index * 3 + 1))
    return {
        "quarter_index": q_index + 1,
        "start": q_start.isoformat(),
        "end": q_end.isoformat(),
        "order_after": q_end.isoformat(),
        "months_in_window": 3,
        "label": f"{q_start.strftime('%Y-%m')} … {q_end_month.strftime('%Y-%m')}",
    }


def _month_pesos_map(db: Session, month_start: date) -> dict[int, int]:
    month_end = _month_end(month_start)
    rows = (
        db.query(DailyActivity.user_id, func.sum(DailyActivity.pesos))
        .filter(DailyActivity.day >= month_start, DailyActivity.day <= month_end)
        .group_by(DailyActivity.user_id)
        .all()
    )
    return {uid: int(x or 0) for uid, x in rows}


def settle_closed_months(db: Session, today: date | None = None) -> list[dict]:
    """Credit each competitor's place share for every unsettled closed month."""
    today = today or msk_today()
    credited_rows: list[dict] = []
    comp = competitors(db)
    if not comp:
        return credited_rows

    for month_start in closed_months(today):
        key = month_key(month_start)
        already = {
            r.user_id
            for r in db.query(MonthPrizeCredit.user_id).filter(MonthPrizeCredit.month == key).all()
        }
        if len(already) >= len(comp):
            continue

        pesos_map = _month_pesos_map(db, month_start)
        ranked = month_rankings(comp, pesos_map)
        by_id = {u.id: u for u in comp}

        for row in ranked:
            uid = row["user_id"]
            if uid in already:
                continue
            u = by_id[uid]
            amount = int(row["spendable"] or 0)
            credit = MonthPrizeCredit(
                user_id=uid,
                month=key,
                rank=int(row["rank"]),
                month_pesos=int(row["month_pesos"] or 0),
                spend_share=float(row["spend_share"] or 0.0),
                credited=amount,
            )
            db.add(credit)
            if amount > 0:
                u.carryover_pesos = (u.carryover_pesos or 0) + amount
            credited_rows.append({
                "month": key,
                "user_id": uid,
                "name": u.name,
                "rank": row["rank"],
                "month_pesos": row["month_pesos"],
                "credited": amount,
            })

        db.flush()

    return credited_rows


def piggy_bank_by_user(db: Session) -> dict[int, int]:
    rows = db.query(User.id, User.carryover_pesos).all()
    return {uid: int(c or 0) for uid, c in rows}
