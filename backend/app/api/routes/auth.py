from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.services.auth.service import AuthService, EmailTaken, InvalidCredentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user, token = AuthService(db).register(body.email, body.full_name, body.password, body.hospital_name, body.hospital_city)
    except EmailTaken as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user, token = AuthService(db).login(body.email, body.password)
    except InvalidCredentials as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
