from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UserPublic, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.name is not None:
        current.name = payload.name
    if payload.avatar is not None:
        current.avatar = payload.avatar
    if payload.ui_language is not None and payload.ui_language in ("en", "ru"):
        current.ui_language = payload.ui_language
    db.commit()
    db.refresh(current)
    return current
