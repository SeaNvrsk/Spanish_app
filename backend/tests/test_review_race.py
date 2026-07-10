"""Regression test: concurrent card creation for the same word must not crash
the request and roll back pesos/streak/progress (the Kristina bug).

Root cause: /review/grade and /lessons/{id}/complete (via seed_lesson_cards)
both call _get_or_create_card for the same word. Each does "SELECT ... first()"
then, if nothing is found, inserts a new Card. Under SQLite's write-lock
serialization, request A can insert+commit a card for a word between request
B's SELECT (which saw nothing) and B's INSERT attempt, so B's plain INSERT
raises IntegrityError on the (user_id, word_es) unique constraint — crashing
the whole request and rolling back everything already computed in it
(pesos, streak, lesson completion). The fix makes the INSERT an atomic
"ON CONFLICT DO NOTHING" upsert so a losing writer never crashes.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import SessionLocal, Base, engine
from app.models import User, Card
from app.msk_time import msk_today
from app.routers.review import GradeItem, _get_or_create_card


def test_losing_writer_upsert_does_not_raise_integrity_error():
    """Simulates the exact race: another request already committed the card
    between our SELECT and our INSERT attempt."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="race@test.com", name="Race", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Winning writer: another request already created + committed this card.
        winner = Card(
            user_id=user.id,
            word_es="presentar",
            word_en="to introduce",
            word_ru="представлять",
            ease=2.5,
            interval=1,
            reps=0,
            lapses=0,
            due=msk_today(),
        )
        db.add(winner)
        db.commit()

        # Losing writer: our SELECT (in a scenario where it ran before the
        # commit above) found nothing, so we attempt the same insert anyway.
        stmt = (
            sqlite_insert(Card)
            .values(
                user_id=user.id,
                word_es="presentar",
                word_en="to introduce",
                word_ru="представлять",
                ease=2.5,
                interval=0,
                reps=0,
                lapses=0,
                due=msk_today(),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "word_es"])
        )
        db.execute(stmt)  # must NOT raise IntegrityError
        db.commit()

        cards = db.query(Card).filter(Card.user_id == user.id, Card.word_es == "presentar").all()
        assert len(cards) == 1, "must not create a duplicate row"
        assert cards[0].id == winner.id, "the winning writer's row must survive untouched"
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "race@test.com").delete()
        db.commit()
        db.close()


def test_get_or_create_card_idempotent_for_existing_word():
    """Calling _get_or_create_card twice (fresh cache each time, as separate
    requests would) for a word that already exists must not error and must
    return the same underlying card."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="race2@test.com", name="Race2", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        item = GradeItem(word_es="chao", word_en="bye", word_ru="пока", correct=True)
        card1 = _get_or_create_card(db, user.id, item, {})
        db.commit()

        card2 = _get_or_create_card(db, user.id, item, {})
        db.commit()

        assert card1.id == card2.id
        count = db.query(Card).filter(Card.user_id == user.id, Card.word_es == "chao").count()
        assert count == 1
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "race2@test.com").delete()
        db.commit()
        db.close()


def test_lesson_complete_transaction_survives_card_seed_conflict(monkeypatch):
    """End-to-end guard: simulate the real request order from Lesson.jsx --
    a card for a lesson's word already exists (created by an earlier
    /review/grade call) when /lessons/{id}/complete calls seed_lesson_cards.
    The whole transaction (pesos, progress) must still commit successfully.
    """
    from app.routers.review import seed_lesson_cards

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="race3@test.com", name="Race3", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Pre-existing card for a word that also appears as a lesson flashcard,
        # mimicking a /review/grade call that already ran and committed.
        pre = Card(
            user_id=user.id,
            word_es="Hola",
            word_en="Hello",
            word_ru="Привет",
            ease=2.5,
            interval=1,
            reps=1,
            lapses=0,
            due=msk_today(),
        )
        db.add(pre)
        db.commit()

        lesson = {
            "exercises": [
                {"id": "x1", "type": "flashcard", "es": "Hola", "translations": {"en": "Hello", "ru": "Привет"}},
                {"id": "x2", "type": "flashcard", "es": "Adiós", "translations": {"en": "Bye", "ru": "Пока"}},
            ]
        }

        # Must not raise, and must not need a rollback for the caller's other
        # pending changes (simulated by mutating the user in the same txn).
        user.pesos = (user.pesos or 0) + 5
        seed_lesson_cards(db, user.id, lesson)
        db.commit()

        db.refresh(user)
        assert user.pesos == 5
        cards = {c.word_es for c in db.query(Card).filter(Card.user_id == user.id).all()}
        assert cards == {"Hola", "Adiós"}
    finally:
        db.query(Card).filter(Card.user_id == user.id).delete()
        db.query(User).filter(User.email == "race3@test.com").delete()
        db.commit()
        db.close()
