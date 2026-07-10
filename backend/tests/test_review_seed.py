"""Lesson vocab seeding and review queue sizing."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, Base, engine
from app.models import User, Card
from app.curriculum.builder import get_all_lessons
from app.msk_time import msk_today
from app.routers.review import (
    lesson_flashcard_vocab,
    seed_lesson_cards,
    rebalance_learner_cards,
    _dedupe_grade_items,
    _reviewable_count,
    _review_queue_cards,
    grade,
    GradeItem,
    GradePayload,
)
from datetime import timedelta


def test_lesson_flashcard_vocab_count():
    lesson = get_all_lessons()["w01-d1"]
    vocab = lesson_flashcard_vocab(lesson)
    assert len(vocab) == 13


def test_dedupe_grade_items_marks_wrong():
    items = [
        GradeItem(word_es="Hola", correct=True),
        GradeItem(word_es="Hola", correct=False),
    ]
    out = _dedupe_grade_items(items)
    assert len(out) == 1
    assert out[0].correct is False


def test_seed_lesson_cards_adds_missing_words():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="seed@test.com", name="Seed", hashed_password="x")
        db.add(user)
        db.flush()
        lesson = get_all_lessons()["w01-d1"]
        added = seed_lesson_cards(db, user.id, lesson)
        db.commit()
        assert added == 13
        count = db.query(Card).filter(Card.user_id == user.id).count()
        assert count == 13
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "seed@test.com").delete()
        db.commit()
        db.close()


def test_lesson_grade_does_not_advance_reps():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="lesson@test.com", name="Lesson", hashed_password="x")
        db.add(user)
        db.flush()
        card = Card(
            user_id=user.id,
            word_es="Hola",
            ease=2.5,
            interval=1,
            reps=0,
            lapses=0,
            due=msk_today(),
        )
        db.add(card)
        db.commit()

        from app.routers.review import grade as grade_fn, _get_or_create_card
        from app.routers.review import _apply_lesson_touch, _dedupe_grade_items

        items = _dedupe_grade_items([GradeItem(word_es="Hola", correct=True)] * 3)
        cache = {}
        for item in items:
            c = _get_or_create_card(db, user.id, item, cache)
            _apply_lesson_touch(c)
        db.commit()
        db.refresh(card)
        assert card.reps == 0
        assert card.due == msk_today()
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "lesson@test.com").delete()
        db.commit()
        db.close()


def test_reviewable_count_includes_learner_words():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="queue@test.com", name="Queue", hashed_password="x")
        db.add(user)
        db.flush()
        for i in range(25):
            db.add(
                Card(
                    user_id=user.id,
                    word_es=f"word{i}",
                    reps=1,
                    interval=3,
                    ease=2.5,
                    due=msk_today() + timedelta(days=5),
                )
            )
        db.commit()
        assert _reviewable_count(db, user.id) == 20
        queue = _review_queue_cards(db, user.id)
        assert len(queue) == 20
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "queue@test.com").delete()
        db.commit()
        db.close()
