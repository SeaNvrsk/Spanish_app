from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=6, max_length=128)
    avatar: Optional[str] = "🦊"
    ui_language: Optional[str] = "ru"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- User ----------
class UserPublic(BaseModel):
    id: int
    email: EmailStr
    name: str
    avatar: str
    ui_language: str
    pesos: int
    current_streak: int
    longest_streak: int
    last_active_date: Optional[date]
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    avatar: Optional[str] = None
    ui_language: Optional[str] = None


# ---------- Progress ----------
class LessonResult(BaseModel):
    lesson_id: str
    score: int = Field(ge=0, le=100)  # percentage correct


class LessonProgressPublic(BaseModel):
    lesson_id: str
    completed: bool
    best_score: int
    stars: int
    pesos_earned: int
    attempts: int

    class Config:
        from_attributes = True


class CompleteResponse(BaseModel):
    pesos_earned: int
    total_pesos: int
    stars: int
    best_score: int
    current_streak: int
    leveled_up: bool
    new_completion: bool


# ---------- Leaderboard ----------
class LeaderboardEntry(BaseModel):
    rank: int
    id: int
    name: str
    avatar: str
    pesos: int
    current_streak: int
    is_me: bool = False


# ---------- Stats ----------
class DailyActivityPublic(BaseModel):
    day: date
    pesos: int
    lessons_completed: int

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_pesos: int
    lessons_completed: int
    current_streak: int
    longest_streak: int
    cefr_level: str
    level_progress_percent: int
    rank: int
    total_users: int
    is_admin: bool = False
    activity: List[DailyActivityPublic]


class FamilyMemberStats(BaseModel):
    id: int
    name: str
    avatar: str
    is_admin: bool
    pesos: int
    month_pesos: int
    current_streak: int
    longest_streak: int
    lessons_completed: int
    cefr_level: str
    level_progress_percent: int
    rank: Optional[int] = None  # None for admin (excluded from competition)


class FamilyOverviewResponse(BaseModel):
    competitors: int
    month: str
    members: List[FamilyMemberStats]


# ---------- Achievements ----------
class AchievementPublic(BaseModel):
    id: str
    icon: str
    category: str
    unlocked: bool


class AchievementsResponse(BaseModel):
    unlocked_count: int
    total_count: int
    achievements: List[AchievementPublic]


# ---------- Vocabulary ----------
class VocabularyEntry(BaseModel):
    word_es: str
    word_en: str
    word_ru: str
    reps: int
    lapses: int
    image_url: Optional[str] = None


class VocabularyResponse(BaseModel):
    count: int
    words: List[VocabularyEntry]
