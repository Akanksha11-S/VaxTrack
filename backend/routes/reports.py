import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, VaccinationRecord
from routes.schedule import schedule_out
from services import pdf_service, record_service, schedule_service

log = logging.getLogger("vaxtrack")
router = APIRouter(prefix="/reports", tags=["PDF report"])


@router.get("/vaccination-pdf")
def vaccination_pdf(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = schedule_service.get_schedule(db, user.schedule_key)
    if schedule is None:
        raise HTTPException(404, "The selected schedule is no longer available. Choose another in your profile.")
    records = record_service.annotate(db, user, db.query(VaccinationRecord).filter_by(user_id=user.id).all())
    items = schedule_service.evaluate_for_user(db, user)
    upcoming = sorted((i for i in items if i["status"] in ("upcoming", "potentially_due") and i["estimated_date"]),
                      key=lambda i: i["estimated_date"])
    try:
        pdf = pdf_service.build_report(user.name, user.date_of_birth, schedule_out(schedule), records,
                                       [schedule_service.serialize_item(i) for i in upcoming])
    except Exception as exc:
        log.error("PDF generation failed: %s", type(exc).__name__)
        raise HTTPException(500, "We couldn't create the PDF report. Try again in a moment.")
    filename = f"vaxtrack-report-{date.today().isoformat()}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})
