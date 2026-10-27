from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from config import settings
from database import get_db
from models import User
from schemas import LoginIn, RegisterIn, TokenOut, UserOut
from services import reminder_service, schedule_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Try signing in instead.")
    key = body.schedule_key or settings.DEFAULT_SCHEDULE_KEY
    if schedule_service.get_schedule(db, key) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That vaccination schedule isn't supported.")
    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password),
                date_of_birth=body.date_of_birth, schedule_key=key)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Try signing in instead.")
    reminder_service.sync_reminders(db, user)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "The email or password is incorrect.")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
