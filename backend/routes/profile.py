from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User
from schemas import ProfileUpdate, UserOut
from services import reminder_service, schedule_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.put("", response_model=UserOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != user.email:
        if db.query(User).filter(User.email == data["email"], User.id != user.id).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Another account already uses this email.")
    if "schedule_key" in data and schedule_service.get_schedule(db, data["schedule_key"]) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That vaccination schedule isn't supported.")
    for field in ("name", "email", "date_of_birth", "schedule_key"):
        if data.get(field) is not None:
            setattr(user, field, data[field])
    for field in ("reminders_enabled", "reminder_lead_days"):
        if data.get(field) is not None:
            setattr(user, field, data[field])
    db.commit()
    # Date of birth, schedule and reminder lead time all change estimated dates.
    reminder_service.sync_reminders(db, user)
    return user
