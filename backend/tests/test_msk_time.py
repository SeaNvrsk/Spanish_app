from datetime import date
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.msk_time import msk_today, msk_month_start, msk_month_end, TZ_MSK


def test_msk_today_follows_moscow_clock():
    fake = date(2026, 7, 15)
    with patch("app.msk_time.msk_now", return_value=__import__("datetime").datetime(2026, 7, 15, 23, 30, tzinfo=TZ_MSK)):
        assert msk_today() == fake


def test_msk_month_end_july():
    assert msk_month_end(date(2026, 7, 10)) == date(2026, 7, 31)


def test_msk_month_start():
    assert msk_month_start(date(2026, 7, 10)) == date(2026, 7, 1)
