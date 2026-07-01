"""Family competition helpers: who counts toward rankings and monthly pesos."""

from sqlalchemy.orm import Session

from .models import User

# Active learners competing for monthly Mercado Libre rewards.
FAMILY_COMPETITORS = 3


def is_competitor(user: User) -> bool:
    return not bool(getattr(user, "is_admin", False))


def competitors(db: Session) -> list[User]:
    return db.query(User).filter(User.is_admin == False).order_by(User.id.asc()).all()  # noqa: E712
