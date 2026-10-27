"""SMTP email delivery for due-soon vaccination reminders.

Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM in .env.
Delivery is idempotent per reminder date; changing the due date permits a fresh email.
"""
import logging
import smtplib
from email.message import EmailMessage
from datetime import date

from config import settings
from database import SessionLocal
from models import Reminder, User

log = logging.getLogger("vaxtrack.email")


def configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def send_due_reminders(today: date | None = None) -> dict:
    today = today or date.today()
    if not configured():
        return {"sent": 0, "skipped": True, "reason": "SMTP is not configured."}
    sent = 0
    with SessionLocal() as db:
        rows = (db.query(Reminder).join(User).filter(
            User.reminders_enabled.is_(True), Reminder.status == "pending",
            Reminder.remind_from <= today,
        ).all())
        for reminder in rows:
            if reminder.email_sent_for == reminder.estimated_date:
                continue
            user = reminder.user
            msg = EmailMessage()
            msg["Subject"] = f"VaxTrack vaccine reminder: {reminder.vaccine_name}"
            msg["From"] = settings.SMTP_FROM
            msg["To"] = user.email
            msg.set_content(
                f"Hello {user.name},\n\n"
                f"This is a VaxTrack reminder for {reminder.vaccine_name}, dose {reminder.dose_number}.\n"
                f"Due date: {reminder.estimated_date.strftime('%d %b %Y')}\n\n"
                f"{reminder.reason}\n\n"
                "Please confirm the date with your vaccination card or healthcare provider. "
                "This reminder is not a medical appointment or medical advice.\n\n"
                "VaxTrack"
            )
            try:
                if settings.SMTP_USERNAME:
                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                        smtp.starttls()
                        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                        smtp.send_message(msg)
                else:
                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                        smtp.send_message(msg)
                reminder.email_sent_for = reminder.estimated_date
                db.commit()
                sent += 1
            except Exception as exc:
                db.rollback()
                log.warning("Reminder email delivery failed for reminder %s (%s).", reminder.id, type(exc).__name__)
    return {"sent": sent, "skipped": False}
