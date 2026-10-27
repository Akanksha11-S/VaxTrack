"""VaxTrack API entry point.  Run with:  uvicorn main:app --reload"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import models  # noqa: F401  (registers tables)
from config import settings
from database import Base, SessionLocal, engine
from routes import auth, documents, profile, reminders, reports, schedule, vaccinations, vaccines
from services import file_service, schedule_service, email_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("vaxtrack")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Additive SQLite migration for installations created before card-specific due dates.
    if settings.DATABASE_URL.startswith("sqlite:"):
        from sqlalchemy import inspect, text
        with engine.begin() as conn:
            tables = set(inspect(engine).get_table_names())
            if "vaccination_records" in tables:
                cols = {c["name"] for c in inspect(engine).get_columns("vaccination_records")}
                if "next_due_date" not in cols:
                    conn.execute(text("ALTER TABLE vaccination_records ADD COLUMN next_due_date DATE"))
                if "next_due_date_estimated" not in cols:
                    conn.execute(text("ALTER TABLE vaccination_records ADD COLUMN next_due_date_estimated BOOLEAN NOT NULL DEFAULT 0"))
            if "reminders" in tables:
                cols = {c["name"] for c in inspect(engine).get_columns("reminders")}
                if "date_source" not in cols:
                    conn.execute(text("ALTER TABLE reminders ADD COLUMN date_source VARCHAR(16) NOT NULL DEFAULT 'schedule'"))
                if "email_sent_for" not in cols:
                    conn.execute(text("ALTER TABLE reminders ADD COLUMN email_sent_for DATE"))
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        schedule_service.seed_schedules(db)
        removed = file_service.purge_expired(db)
        if removed:
            log.info("Retention policy removed %d expired uploads.", removed)
    async def reminder_email_loop():
        while True:
            try:
                result = await asyncio.to_thread(email_service.send_due_reminders)
                if result.get("sent"):
                    log.info("Sent %d scheduled reminder emails.", result["sent"])
            except Exception as exc:
                log.warning("Reminder email check failed (%s).", type(exc).__name__)
            await asyncio.sleep(max(300, settings.REMINDER_CHECK_INTERVAL_SECONDS))

    email_task = asyncio.create_task(reminder_email_loop())
    try:
        yield
    finally:
        email_task.cancel()
        try:
            await email_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="VaxTrack API",
    version="1.0.0",
    description="Vaccination record tracker: OCR import, schedule matching, reminders and PDF reports. "
                "Educational use only - not medical advice.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"],
)


def _friendly(err: dict) -> str:
    """Replace pydantic's technical wording with plain language."""
    kind, ctx = err.get("type", ""), err.get("ctx", {})
    if kind == "missing":
        return "This field is required."
    if kind == "string_too_short":
        return "This field is required." if ctx.get("min_length") == 1 else f"Use at least {ctx.get('min_length')} characters."
    if kind == "string_too_long":
        return f"Use at most {ctx.get('max_length')} characters."
    if kind.startswith("date") or kind == "date_parsing":
        return "Enter a valid date."
    if kind in ("int_parsing", "int_type"):
        return "Enter a whole number."
    if kind in ("greater_than_equal", "less_than_equal"):
        return "That number is out of range."
    if kind == "literal_error":
        return "That isn't one of the allowed choices."
    return err["msg"].removeprefix("Value error, ")


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        message = _friendly(err)
        errors.append({"field": field, "message": message})
    return JSONResponse(status_code=422, content={"detail": "Some details need fixing.", "errors": errors})


@app.exception_handler(SQLAlchemyError)
async def database_handler(_request: Request, exc: SQLAlchemyError):
    log.error("Database error: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The database couldn't complete that request. Please try again."})


@app.exception_handler(Exception)
async def unexpected_handler(_request: Request, exc: Exception):
    log.error("Unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for module in (auth, profile, documents, vaccinations, schedule, vaccines, reminders, reports):
    app.include_router(module.router)


@app.get("/health", tags=["System"])
def health():
    from services import ocr_service
    return {"status": "ok", "ocr_available": ocr_service.is_available()}
