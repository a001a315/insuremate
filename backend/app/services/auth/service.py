from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository

# Pre-computed so login takes similar time whether or not the email exists.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthError(Exception):
    pass


class EmailTaken(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AuthService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def register(self, email: str, full_name: str, password: str, hospital_name: str = "", hospital_city: str | None = None) -> tuple[User, str]:
        if self.users.get_by_email(email):
            raise EmailTaken("An account with this email already exists.")
        user = self.users.create(email, full_name, hash_password(password), hospital_name, hospital_city)
        return user, create_access_token(str(user.id))

    def login(self, email: str, password: str) -> tuple[User, str]:
        user = self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentials("Incorrect email or password.")
        if not verify_password(password, user.hashed_password) or not user.is_active:
            raise InvalidCredentials("Incorrect email or password.")
        return user, create_access_token(str(user.id))
