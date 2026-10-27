from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Reminder, User
from schemas import ReminderUpdate
from services import reminder_service, email_service

router = APIRouter(prefix="/reminders", tags=["Reminders"])

NOTICE = ("These dates are estimates based on your date of birth and the selected schedule. "
          "They are not confirmed appointments.")


def _payload(db: Session, user: User) -> dict:
    return {
        "enabled": user.reminders_enabled,
        "lead_days": user.reminder_lead_days,
        "email_enabled": email_service.configured(),
        "notice": NOTICE,
        "reminders": [reminder_service.serialize(r) for r in reminder_service.list_reminders(db, user)],
    }


@router.get("")
def get_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder_service.sync_reminders(db, user)
    return _payload(db, user)


@router.put("/{reminder_id}")
def update_reminder(reminder_id: int, body: ReminderUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter_by(id=reminder_id, user_id=user.id).first()
    if reminder is None:
        raise HTTPException(404, "Reminder not found.")
    reminder.status = body.status
    db.commit()
    return reminder_service.serialize(reminder)


@router.post("/recalculate")
def recalculate(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder_service.sync_reminders(db, user)
    return _payload(db, user)
