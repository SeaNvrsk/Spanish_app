"""Regression test: get_daily must not crash when a concurrent request has
already created today's DailyActivity row (same bug class as the Card race
in test_review_race.py — unique constraint on (user_id, day))."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import SessionLocal, Base, engine
from app.models import User, DailyActivity
from app.msk_time import msk_today
from app.gamification import get_daily, bump_daily


def test_losing_writer_daily_activity_upsert_does_not_raise():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="daily-race@test.com", name="DailyRace", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        today = msk_today()

        winner = DailyActivity(user_id=user.id, day=today, pesos=5, review_pesos=0, lessons_completed=1)
        db.add(winner)
        db.commit()

        stmt = (
            sqlite_insert(DailyActivity)
            .values(user_id=user.id, day=today, pesos=0, review_pesos=0, lessons_completed=0)
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
        )
        db.execute(stmt)  # must NOT raise
        db.commit()

        rows = db.query(DailyActivity).filter(DailyActivity.user_id == user.id, DailyActivity.day == today).all()
        assert len(rows) == 1
        assert rows[0].pesos == 5, "winning writer's row must survive untouched"
    finally:
        db.query(DailyActivity).filter(DailyActivity.user_id == user.id).delete()
        db.query(User).filter(User.email == "daily-race@test.com").delete()
        db.commit()
        db.close()


def test_get_daily_idempotent_across_calls():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="daily-race2@test.com", name="DailyRace2", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        today = msk_today()

        row1 = get_daily(db, user, today)
        db.commit()
        row2 = get_daily(db, user, today)
        db.commit()

        assert row1.id == row2.id
        count = db.query(DailyActivity).filter(DailyActivity.user_id == user.id, DailyActivity.day == today).count()
        assert count == 1
    finally:
        db.query(DailyActivity).filter(DailyActivity.user_id == user.id).delete()
        db.query(User).filter(User.email == "daily-race2@test.com").delete()
        db.commit()
        db.close()


def test_bump_daily_after_conflict_updates_correct_row():
    """seed_lesson_cards-style scenario: bump_daily must update the surviving
    row's totals correctly even if our own insert attempt lost the race."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(email="daily-race3@test.com", name="DailyRace3", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        today = msk_today()

        winner = DailyActivity(user_id=user.id, day=today, pesos=5, review_pesos=10, lessons_completed=1)
        db.add(winner)
        db.commit()

        bump_daily(db, user, today, pesos=3, completed=True, review_pesos=2)
        db.commit()

        row = db.query(DailyActivity).filter(DailyActivity.user_id == user.id, DailyActivity.day == today).first()
        assert row.pesos == 8
        assert row.review_pesos == 12
        assert row.lessons_completed == 2
    finally:
        db.query(DailyActivity).filter(DailyActivity.user_id == user.id).delete()
        db.query(User).filter(User.email == "daily-race3@test.com").delete()
        db.commit()
        db.close()
