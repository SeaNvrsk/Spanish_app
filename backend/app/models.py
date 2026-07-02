from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base
from .msk_time import msk_today, msk_now


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar = Column(String, default="🦊")  # emoji avatar, fun for family
    ui_language = Column(String, default="ru")  # ru | en

    # Legacy DB column name "xp" — stores pesos directly.
    pesos = Column("xp", Integer, default=0, nullable=False)
    # Fractional pesos from review (0.1 steps); 0–9 tenths carried on the user.
    peso_tenths = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_active_date = Column(Date, nullable=True)
    # Pesos carried over from a previous month (winner's optional roll-over).
    carryover_pesos = Column(Integer, default=0, nullable=False)
    # Admin observes all stats but is excluded from family rankings / peso prizes.
    is_admin = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    progress = relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    activity = relationship("DailyActivity", back_populates="user", cascade="all, delete-orphan")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(String, nullable=False, index=True)

    completed = Column(Boolean, default=False, nullable=False)
    best_score = Column(Integer, default=0, nullable=False)  # 0-100 (%)
    stars = Column(Integer, default=0, nullable=False)  # 0-3
    pesos_earned = Column("xp_earned", Integer, default=0, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    last_completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="progress")


class Card(Base):
    """A vocabulary card scheduled with a lightweight SM-2 spaced-repetition algorithm."""

    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("user_id", "word_es", name="uq_user_word"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    word_es = Column(String, nullable=False, index=True)
    word_en = Column(String, default="")
    word_ru = Column(String, default="")

    ease = Column(Float, default=2.5, nullable=False)       # difficulty factor
    interval = Column(Integer, default=0, nullable=False)   # days until next review
    reps = Column(Integer, default=0, nullable=False)       # successful reviews in a row
    lapses = Column(Integer, default=0, nullable=False)     # times forgotten
    due = Column(Date, default=msk_today, nullable=False, index=True)
    last_reviewed = Column(DateTime, nullable=True)

    user = relationship("User")


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_user_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day = Column(Date, default=msk_today, nullable=False)
    pesos = Column("xp", Integer, default=0, nullable=False)
    review_pesos = Column("review_xp", Integer, default=0, nullable=False)  # tenths earned today (cap 50)
    lessons_completed = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="activity")
