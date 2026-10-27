import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _check_dob(value: date) -> date:
    if value > date.today():
        raise ValueError("Date of birth can't be in the future.")
    if value.year < 1900:
        raise ValueError("Enter a valid date of birth.")
    return value


def _check_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address.")
    return value


# --------------------------------------------------------------------- auth / profile
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=72)
    date_of_birth: date
    schedule_key: str | None = None

    _email = field_validator("email")(_check_email)
    _dob = field_validator("date_of_birth")(_check_dob)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Enter your name.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Use at least one letter and one number.")
        return v


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    date_of_birth: date
    schedule_key: str
    reminders_enabled: bool
    reminder_lead_days: int


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = None
    date_of_birth: date | None = None
    schedule_key: str | None = None
    reminders_enabled: bool | None = None
    reminder_lead_days: Literal[3, 7, 14, 30] | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return _check_email(v) if v is not None else v

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v):
        return _check_dob(v) if v is not None else v

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("Enter your name.")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --------------------------------------------------------------------- vaccination records
def _check_vaccination_date(value: date | None) -> date | None:
    if value is None:
        return value
    if value > date.today():
        raise ValueError("A vaccination date can't be in the future.")
    if value.year < 1900:
        raise ValueError("Enter a valid vaccination date.")
    return value


class RecordIn(BaseModel):
    vaccine_name: str = Field(min_length=1, max_length=100)
    dose_number: int | None = Field(default=None, ge=0, le=20)
    vaccination_date: date | None = None
    next_due_date: date | None = None
    next_due_date_estimated: bool = False
    notes: str | None = Field(default=None, max_length=500)
    verification_status: Literal["confirmed", "unverified"] = "confirmed"
    source_type: Literal["manual", "ocr"] = "manual"
    ocr_confidence: float | None = Field(default=None, ge=0, le=100)
    allow_duplicate: bool = False

    _date = field_validator("vaccination_date")(_check_vaccination_date)

    @field_validator("vaccine_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Enter a vaccine name.")
        return v

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        v = (v or "").strip()
        return v or None


class RecordUpdate(BaseModel):
    """Partial update. Fields left out are unchanged; sending null clears an optional field."""
    vaccine_name: str | None = Field(default=None, min_length=1, max_length=100)
    dose_number: int | None = Field(default=None, ge=0, le=20)
    vaccination_date: date | None = None
    next_due_date: date | None = None
    next_due_date_estimated: bool | None = None
    notes: str | None = Field(default=None, max_length=500)
    verification_status: Literal["confirmed", "unverified"] | None = None
    allow_duplicate: bool = False

    _date = field_validator("vaccination_date")(_check_vaccination_date)

    @field_validator("vaccine_name")
    @classmethod
    def _name(cls, v):
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("Enter a vaccine name.")
        return v


class BulkRecordsIn(BaseModel):
    document_id: int | None = None
    records: list[RecordIn] = Field(min_length=1, max_length=100)
    allow_duplicates: bool = False


class ReminderUpdate(BaseModel):
    status: Literal["pending", "acknowledged", "completed", "dismissed"]


class ExplainIn(BaseModel):
    text: str | None = Field(default=None, max_length=1500)
    vaccine_id: str | None = Field(default=None, max_length=40)
