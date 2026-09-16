"""Monthly place-share credits go into the piggy bank (not full month pesos)."""

from datetime import date

from app.gamification import month_rankings
from app.prize_bank import closed_months, quarter_window


class U:
    def __init__(self, id, name="x"):
        self.id = id
        self.name = name


def test_closed_months_before_august():
    start = date(2026, 7, 1)
    assert closed_months(date(2026, 7, 15), start) == []
    assert closed_months(date(2026, 8, 1), start) == [date(2026, 7, 1)]
    assert closed_months(date(2026, 10, 5), start) == [
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 9, 1),
    ]


def test_quarter_window_from_program_start():
    start = date(2026, 7, 1)
    q1 = quarter_window(date(2026, 8, 1), start)
    assert q1["label"] == "2026-07 … 2026-09"
    assert q1["order_after"] == "2026-09-30"
    q2 = quarter_window(date(2026, 10, 1), start)
    assert q2["label"] == "2026-10 … 2026-12"


def test_july_place_shares_not_full_balance():
    users = [U(3, "Kristina"), U(4, "Veronika"), U(5, "Eva")]
    pesos = {3: 306, 4: 302, 5: 223}
    ranked = month_rankings(users, pesos)
    by_id = {r["user_id"]: r for r in ranked}
    assert by_id[3]["rank"] == 1 and by_id[3]["spendable"] == 306  # 100%
    assert by_id[4]["rank"] == 2 and by_id[4]["spendable"] == 226  # 75% of 302
    assert by_id[5]["rank"] == 3 and by_id[5]["spendable"] == 111  # 50% of 223
    assert by_id[3]["spendable"] + by_id[4]["spendable"] + by_id[5]["spendable"] < 306 + 302 + 223
