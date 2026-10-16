"""Data-access layer for users. Only place that touches SQLAlchemy."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._db.scalar(select(User).where(User.email == email))

    def add(self, user: User) -> User:
        self._db.add(user)
        self._db.flush()
        return user
