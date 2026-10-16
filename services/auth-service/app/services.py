"""Auth business logic: registration, authentication, token resolution."""
from sqlalchemy.orm import Session

from .exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    UserNotFound,
)
from .models import User
from .repositories import UserRepository
from .security import create_access_token, decode_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)

    def register(self, email: str, password: str, full_name: str = "") -> User:
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        user = self._users.add(
            User(email=email, full_name=full_name, hashed_password=hash_password(password))
        )
        self._db.commit()
        self._db.refresh(user)
        return user

    def login(self, email: str, password: str) -> str:
        """Return a signed JWT, or raise InvalidCredentials."""
        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentials()
        return create_access_token(subject=str(user.id), extra={"email": user.email})

    def get_public_user(self, user_id: int) -> User:
        """Public profile lookup (host of a booking page)."""
        user = self._users.get(user_id)
        if user is None:
            raise UserNotFound()
        return user

    def user_from_token(self, token: str) -> User:
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            raise InvalidToken()
        user = self._users.get(int(payload["sub"]))
        if user is None:
            raise InvalidToken("User not found")
        return user
