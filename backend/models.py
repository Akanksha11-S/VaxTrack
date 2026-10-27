from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VaccinationSchedule(Base):
    """A reference schedule. Seeded from data/schedules.json at start-up."""
    __tablename__ = "vaccination_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(500))
    date_order: Mapped[str] = mapped_column(String(3), default="DMY")
    description: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    date_of_birth: Mapped[date] = mapped_column(Date)
    schedule_key: Mapped[str] = mapped_column(ForeignKey("vaccination_schedules.key"))
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_lead_days: Mapped[int] = mapped_column(Integer, default=14)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    schedule: Mapped[VaccinationSchedule] = relationship()
    records: Mapped[list["VaccinationRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(160))
    stored_filename: Mapped[str] = mapped_column(String(80))
    file_type: Mapped[str] = mapped_column(String(10))  # jpg | png | pdf
    size_bytes: Mapped[int] = mapped_column(Integer)
    processing_status: Mapped[str] = mapped_column(String(20), default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="documents")

    __table_args__ = (
        CheckConstraint("processing_status IN ('uploaded','processing','processed','no_text','failed','expired')",
                        name="ck_document_status"),
    )


class VaccinationRecord(Base):
    __tablename__ = "vaccination_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vaccine_name: Mapped[str] = mapped_column(String(100))
    dose_number: Mapped[int | None] = mapped_column(Integer)
    vaccination_date: Mapped[date | None] = mapped_column(Date)
    next_due_date: Mapped[date | None] = mapped_column(Date)
    next_due_date_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    source_document: Mapped[str | None] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(10), default="manual")  # manual | ocr
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(String(12), default="confirmed")  # confirmed | unverified
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="records")

    __table_args__ = (
        CheckConstraint("dose_number IS NULL OR (dose_number >= 0 AND dose_number <= 20)", name="ck_record_dose"),
        CheckConstraint("verification_status IN ('confirmed','unverified')", name="ck_record_verification"),
        CheckConstraint("source_type IN ('manual','ocr')", name="ck_record_source"),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vaccine_id: Mapped[str] = mapped_column(String(40))
    vaccine_name: Mapped[str] = mapped_column(String(100))
    dose_number: Mapped[int] = mapped_column(Integer)
    estimated_date: Mapped[date] = mapped_column(Date)
    remind_from: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(400))
    date_source: Mapped[str] = mapped_column(String(16), default="schedule")  # card | estimate | schedule
    email_sent_for: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(14), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="reminders")

    __table_args__ = (
        UniqueConstraint("user_id", "vaccine_id", "dose_number", name="uq_reminder_dose"),
        CheckConstraint("status IN ('pending','acknowledged','completed','dismissed')", name="ck_reminder_status"),
    )
