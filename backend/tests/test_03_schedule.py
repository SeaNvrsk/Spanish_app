"""Test 3/5 — Calendar unlock (fair start, catch-up allowed)."""

from datetime import date

from app.schedule import (
    is_lesson_unlocked,
    lesson_schedule_meta,
    max_unlocked_global_day,
    program_day_for_date,
    program_start,
    unlock_date_for_day,
)


def test_program_starts_july_first():
    assert program_start() == date(2026, 7, 1)


def test_one_new_slot_per_calendar_day():
    start = program_start()
    day1 = date(2026, 7, 1)
    day3 = date(2026, 7, 3)
    assert program_day_for_date(day1, start) == 1
    assert program_day_for_date(day3, start) == 3
    assert max_unlocked_global_day(day1, start) == 1
    assert max_unlocked_global_day(day3, start) == 3


def test_today_unlocked_catchup_yesterday():
    """On day 3, lessons 1–3 are open; lesson 4 is still locked."""
    start = program_start()
    today = date(2026, 7, 3)
    assert is_lesson_unlocked(1, today, start)
    assert is_lesson_unlocked(2, today, start)
    assert is_lesson_unlocked(3, today, start)
    assert not is_lesson_unlocked(4, today, start)


def test_future_lesson_has_unlock_date():
    meta = lesson_schedule_meta(10, date(2026, 7, 1))
    assert not meta["unlocked"]
    assert meta["unlock_date"] == unlock_date_for_day(10).isoformat()


def test_today_flag_on_matching_day():
    meta = lesson_schedule_meta(5, date(2026, 7, 5))
    assert meta["unlocked"]
    assert meta["is_today"]
