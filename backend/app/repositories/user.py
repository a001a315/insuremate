import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower(), User.deleted_at.is_(None)))

    def create(self, email: str, full_name: str, hashed_password: str, hospital_name: str = "", hospital_city: str | None = None) -> User:
        user = User(email=email.lower(), full_name=full_name.strip(), hashed_password=hashed_password,
                    hospital_name=hospital_name.strip(), hospital_city=hospital_city)
        self.db.add(user)
        self.db.commit()
        return user
