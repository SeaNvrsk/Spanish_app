"""Calendar-based lesson unlock — one program day per calendar day from program start."""

from datetime import date, timedelta

from .config import get_settings
from .msk_time import msk_today


def program_start() -> date:
    return get_settings().program_start_date


def program_day_for_date(d: date, start: date | None = None) -> int:
    """1-based program day; 0 before the program starts."""
    start = start or program_start()
    if d < start:
        return 0
    return (d - start).days + 1


def unlock_date_for_day(global_day: int, start: date | None = None) -> date:
    start = start or program_start()
    return start + timedelta(days=global_day - 1)


def max_unlocked_global_day(today: date | None = None, start: date | None = None) -> int:
    """Highest lesson `day` index (1–365) unlocked on this calendar date."""
    today = today or msk_today()
    start = start or program_start()
    return program_day_for_date(today, start)


def is_lesson_unlocked(lesson_global_day: int, today: date | None = None, start: date | None = None) -> bool:
    today = today or msk_today()
    start = start or program_start()
    if today < start:
        return False
    return lesson_global_day <= max_unlocked_global_day(today, start)


def lesson_schedule_meta(lesson_global_day: int, today: date | None = None, start: date | None = None) -> dict:
    today = today or msk_today()
    start = start or program_start()
    unlocked = is_lesson_unlocked(lesson_global_day, today, start)
    prog_day = program_day_for_date(today, start)
    return {
        "unlocked": unlocked,
        "unlock_date": unlock_date_for_day(lesson_global_day, start).isoformat(),
        "is_today": unlocked and lesson_global_day == prog_day,
    }
