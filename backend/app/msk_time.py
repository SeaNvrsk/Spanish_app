"""Learner-facing calendar boundaries — Europe/Moscow (UTC+3).

Daily streaks, review caps, lesson unlocks and monthly rankings all use
the Moscow calendar day (00:00–23:59 MSK).
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ_MSK = ZoneInfo("Europe/Moscow")


def msk_now() -> datetime:
    return datetime.now(TZ_MSK)


def msk_today() -> date:
    return msk_now().date()


def msk_month_start(d: date | None = None) -> date:
    d = d or msk_today()
    return d.replace(day=1)


def msk_month_end(d: date | None = None) -> date:
    d = d or msk_today()
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def msk_days_left_in_month(d: date | None = None) -> int:
    d = d or msk_today()
    return (msk_month_end(d) - d).days
