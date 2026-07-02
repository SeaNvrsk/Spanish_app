from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..achievements import compute_achievements
from ..database import get_db
from ..deps import get_current_user
from ..models import User, Card
from ..schemas import AchievementsResponse, VocabularyResponse, VocabularyEntry

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/achievements", response_model=AchievementsResponse)
def achievements(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return compute_achievements(db, current)


@router.get("/vocabulary", response_model=VocabularyResponse)
def vocabulary(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cards = (
        db.query(Card)
        .filter(Card.user_id == current.id)
        .order_by(Card.word_es.asc())
        .all()
    )
    words = [
        VocabularyEntry(
            word_es=c.word_es,
            word_en=c.word_en or "",
            word_ru=c.word_ru or "",
            reps=c.reps or 0,
            lapses=c.lapses or 0,
        )
        for c in cards
    ]
    return VocabularyResponse(count=len(words), words=words)
