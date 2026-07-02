import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.gamification import apply_review_award, REVIEW_DAILY_CAP_TENTHS
from app.models import User


def _user(tenths=0, pesos=0):
    u = User(email="t@t.com", name="T", hashed_password="x")
    u.peso_tenths = tenths
    u.pesos = pesos
    return u


def test_review_award_tenth_per_correct():
    u = _user()
    a = apply_review_award(u, 3, 0)
    assert a["earned_tenths"] == 3
    assert a["pesos_display"] == 0.3
    assert u.peso_tenths == 3
    assert u.pesos == 0


def test_review_daily_cap_tenths():
    u = _user()
    a = apply_review_award(u, 100, 45)
    assert a["earned_tenths"] == 5
    assert a["pesos_display"] == 0.5


def test_review_cap_blocks_further():
    u = _user()
    a = apply_review_award(u, 10, REVIEW_DAILY_CAP_TENTHS)
    assert a["earned_tenths"] == 0


def test_tenths_carry_to_whole_peso():
    u = _user(tenths=8, pesos=10)
    a = apply_review_award(u, 5, 0)
    assert a["earned_tenths"] == 5
    assert u.peso_tenths == 3
    assert u.pesos == 11
