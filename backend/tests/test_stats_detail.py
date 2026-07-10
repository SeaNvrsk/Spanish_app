"""Stats detail builder tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, Base, engine
from app.models import User, LessonProgress, DailyActivity
from app.stats_detail import build_user_stats_detail, _lesson_pesos_for_day
from app.main import _ensure_columns
from app.msk_time import msk_today


def test_build_user_stats_detail_splits_earnings():
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    db = SessionLocal()
    try:
        user = User(email="stats@test.com", name="Stats", hashed_password="x")
        db.add(user)
        db.flush()
        db.add(
            LessonProgress(
                user_id=user.id,
                lesson_id="w01-d1",
                completed=True,
                best_score=90,
                stars=3,
                pesos_earned=4,
                attempts=1,
            )
        )
        db.add(
            DailyActivity(
                user_id=user.id,
                day=msk_today(),
                pesos=4,
                review_pesos=3,
                lessons_completed=1,
            )
        )
        db.commit()
        detail = build_user_stats_detail(db, user)
        assert detail["earnings_totals"]["pesos_lessons"] == 4
        assert detail["earnings_totals"]["pesos_review"] == 0.3
        assert len(detail["lesson_history"]) == 1
        assert detail["lesson_history"][0]["lesson_id"] == "w01-d1"
        assert detail["daily_earnings"][-1]["pesos_review"] == 0.3
        assert detail["daily_earnings"][-1]["pesos_lessons"] == 4
    finally:
        db.query(DailyActivity).filter(DailyActivity.user_id == user.id).delete()
        db.query(LessonProgress).filter(LessonProgress.user_id == user.id).delete()
        db.query(User).filter(User.email == "stats@test.com").delete()
        db.commit()
        db.close()


def test_legacy_daily_split_kristina_carry_case():
    """Mixed day: 5 lesson + 3.9 review must not show 6 lesson pesos."""
    row = DailyActivity(
        user_id=1,
        day=msk_today(),
        pesos=9,
        review_pesos=39,
        lesson_pesos=0,
        lessons_completed=1,
    )
    assert _lesson_pesos_for_day(row) == 5
