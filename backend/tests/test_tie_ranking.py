"""Monthly ranking with tied scores."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.gamification import month_rankings, PLACE_SPEND_SHARE


class _U:
    def __init__(self, uid: int):
        self.id = uid


def test_three_way_tie_splits_all_places():
    users = [_U(1), _U(2), _U(3)]
    pesos = {1: 40, 2: 40, 3: 40}
    rows = month_rankings(users, pesos)
    assert len(rows) == 3
    assert all(r["rank"] == 1 for r in rows)
    assert all(r["tied"] for r in rows)
    pooled = PLACE_SPEND_SHARE[1] + PLACE_SPEND_SHARE[2] + PLACE_SPEND_SHARE[3]
    share = pooled / 3
    assert all(abs(r["spend_share"] - share) < 0.001 for r in rows)
    assert all(r["spendable"] == int(40 * share) for r in rows)


def test_two_tie_first_third_alone():
    users = [_U(1), _U(2), _U(3)]
    pesos = {1: 50, 2: 50, 3: 30}
    rows = month_rankings(users, pesos)
    assert rows[0]["rank"] == 1 and rows[1]["rank"] == 1
    assert rows[0]["tied"] and rows[1]["tied"]
    pooled = PLACE_SPEND_SHARE[1] + PLACE_SPEND_SHARE[2]
    share = pooled / 2
    assert rows[0]["spendable"] == int(50 * share)
    assert rows[2]["rank"] == 3
    assert rows[2]["spendable"] == int(30 * PLACE_SPEND_SHARE[3])


def test_two_tie_second_first_alone():
    users = [_U(1), _U(2), _U(3)]
    pesos = {1: 60, 2: 40, 3: 40}
    rows = month_rankings(users, pesos)
    assert rows[0]["rank"] == 1 and not rows[0]["tied"]
    assert rows[0]["spendable"] == 60
    assert rows[1]["rank"] == 2 and rows[2]["rank"] == 2
    pooled = PLACE_SPEND_SHARE[2] + PLACE_SPEND_SHARE[3]
    share = pooled / 2
    assert rows[1]["spendable"] == int(40 * share)
