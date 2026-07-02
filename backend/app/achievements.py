"""Achievement definitions and unlock checks."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from .curriculum import get_curriculum, get_all_lessons
from .models import User, LessonProgress, Card
from .schemas import AchievementPublic, AchievementsResponse


@dataclass(frozen=True)
class AchievementDef:
    id: str
    icon: str
    category: str


ACHIEVEMENT_DEFS: list[AchievementDef] = [
    AchievementDef("welcome", "👋", "special"),
    AchievementDef("first_lesson", "🎯", "learning"),
    AchievementDef("lessons_5", "📖", "learning"),
    AchievementDef("lessons_25", "📚", "learning"),
    AchievementDef("perfect_score", "💯", "learning"),
    AchievementDef("three_stars", "⭐", "learning"),
    AchievementDef("streak_3", "🔥", "streak"),
    AchievementDef("streak_7", "🔥", "streak"),
    AchievementDef("streak_30", "🏆", "streak"),
    AchievementDef("first_exam", "📝", "exam"),
    AchievementDef("capstone", "🎓", "exam"),
    AchievementDef("a1_complete", "🇲🇽", "learning"),
    AchievementDef("review_master", "🧠", "vocab"),
    AchievementDef("vocab_25", "📇", "vocab"),
    AchievementDef("vocab_100", "🗂️", "vocab"),
    AchievementDef("pesos_50", "💵", "special"),
    AchievementDef("pesos_200", "💰", "special"),
]


def _completed_ids(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(LessonProgress.lesson_id)
        .filter(LessonProgress.user_id == user_id, LessonProgress.completed == True)  # noqa: E712
        .all()
    )
    return {r[0] for r in rows}


def _level_complete(level: dict, completed_ids: set[str]) -> bool:
    lesson_ids = [d["id"] for wk in level["weeks"] for d in wk["days"]]
    return bool(lesson_ids) and all(lid in completed_ids for lid in lesson_ids)


def _unlock_map(db: Session, user: User) -> dict[str, bool]:
    completed = _completed_ids(db, user.id)
    progress_rows = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user.id)
        .all()
    )
    lessons_done = len(completed)
    has_perfect = any(p.best_score >= 100 for p in progress_rows)
    has_three_stars = any(p.stars >= 3 for p in progress_rows)

    all_lessons = get_all_lessons()
    exam_ids = {lid for lid, meta in all_lessons.items() if meta.get("kind") == "exam"}
    capstone_ids = {lid for lid, meta in all_lessons.items() if meta.get("kind") == "capstone"}

    card_count = db.query(Card).filter(Card.user_id == user.id).count()
    review_master = (
        db.query(Card)
        .filter(Card.user_id == user.id, Card.reps >= 5)
        .first()
        is not None
    )

    a1_done = False
    tree = get_curriculum()
    if tree:
        a1_done = _level_complete(tree[0], completed)

    return {
        "welcome": True,
        "first_lesson": lessons_done >= 1,
        "lessons_5": lessons_done >= 5,
        "lessons_25": lessons_done >= 25,
        "perfect_score": has_perfect,
        "three_stars": has_three_stars,
        "streak_3": user.longest_streak >= 3,
        "streak_7": user.longest_streak >= 7,
        "streak_30": user.longest_streak >= 30,
        "first_exam": bool(completed & exam_ids),
        "capstone": bool(completed & capstone_ids),
        "a1_complete": a1_done,
        "review_master": review_master,
        "vocab_25": card_count >= 25,
        "vocab_100": card_count >= 100,
        "pesos_50": user.pesos >= 50,
        "pesos_200": user.pesos >= 200,
    }


def compute_achievements(db: Session, user: User) -> AchievementsResponse:
    unlocked_map = _unlock_map(db, user)
    achievements = [
        AchievementPublic(
            id=defn.id,
            icon=defn.icon,
            category=defn.category,
            unlocked=unlocked_map.get(defn.id, False),
        )
        for defn in ACHIEVEMENT_DEFS
    ]
    unlocked_count = sum(1 for a in achievements if a.unlocked)
    return AchievementsResponse(
        unlocked_count=unlocked_count,
        total_count=len(achievements),
        achievements=achievements,
    )
