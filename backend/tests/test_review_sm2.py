"""SRS interval caps and card merge safety."""

import sys
import os
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, Base, engine
from app.models import User, Card
from app.msk_time import msk_today
from app.routers.review import (
    _apply_sm2,
    _sanitize_card,
    _repair_cards,
    _cap_interval,
    MAX_REVIEW_INTERVAL_DAYS,
)


def _card(**kw):
    defaults = dict(
        user_id=1,
        word_es="test",
        ease=2.5,
        interval=0,
        reps=0,
        lapses=0,
        due=msk_today(),
    )
    defaults.update(kw)
    return Card(**defaults)


def test_cap_interval():
    assert _cap_interval(1259712) == MAX_REVIEW_INTERVAL_DAYS
    assert _cap_interval(0) == 1


def test_sanitize_card_fixes_huge_interval():
    c = _card(interval=1259712, due=msk_today() + timedelta(days=999999))
    assert _sanitize_card(c)
    assert c.interval == MAX_REVIEW_INTERVAL_DAYS
    assert c.due <= msk_today() + timedelta(days=MAX_REVIEW_INTERVAL_DAYS)


def test_apply_sm2_never_overflows():
    c = _card(interval=MAX_REVIEW_INTERVAL_DAYS, reps=10, ease=3.0)
    _apply_sm2(c, True)
    assert c.interval <= MAX_REVIEW_INTERVAL_DAYS
    assert c.due <= msk_today() + timedelta(days=MAX_REVIEW_INTERVAL_DAYS)


def test_repair_merge_keeps_sooner_due_date():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="merge@test.com", name="Merge", hashed_password="x")
        db.add(user)
        db.flush()

        fragment = Card(
            user_id=user.id,
            word_es="bien",
            word_ru="Я в порядке, спасибо.",
            interval=1,
            reps=0,
            ease=2.5,
            due=msk_today(),
        )
        full = Card(
            user_id=user.id,
            word_es="Estoy bien, gracias.",
            word_ru="Я в порядке, спасибо.",
            interval=1259712,
            reps=14,
            ease=3.0,
            due=msk_today() + timedelta(days=999999),
        )
        db.add_all([fragment, full])
        db.commit()

        out = _repair_cards(db, user.id, [fragment])
        db.commit()

        assert len(out) == 1
        survivor = out[0]
        assert survivor.word_es == "Estoy bien, gracias."
        assert survivor.interval <= MAX_REVIEW_INTERVAL_DAYS
        assert survivor.due <= msk_today() + timedelta(days=7)
        gone = db.query(Card).filter(Card.user_id == user.id, Card.word_es == "bien").first()
        assert gone is None
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "merge@test.com").delete()
        db.commit()
        db.close()
