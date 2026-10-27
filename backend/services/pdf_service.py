"""Vaccination report as a PDF (ReportLab / Platypus)."""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

INK = colors.HexColor("#14312F")
MUTED = colors.HexColor("#566E6B")
TEAL = colors.HexColor("#0E7C73")
LINE = colors.HexColor("#D5E0DD")
TINT = colors.HexColor("#EEF5F3")

DISCLAIMER = (
    "This report is for personal record keeping and education. It is not medical advice and it is not an official "
    "vaccination certificate. Records marked 'Not confirmed' were read from a document or entered without confirmation. "
    "Estimated dates are based on the selected reference schedule, which is simplified, and are not appointments. "
    "Actual schedules depend on country, age, medical circumstances and official recommendations - please check with a "
    "healthcare provider or your national immunization programme."
)


def safe(text) -> str:
    """The built-in PDF fonts only cover Latin-1/Windows-1252, so replace anything else rather than print boxes."""
    if text is None:
        return ""
    return escape(str(text).encode("cp1252", "replace").decode("cp1252"))


def fmt_date(value) -> str:
    if not value:
        return "Date not recorded"
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return value.strftime("%d %b %Y").lstrip("0")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, textColor=INK, alignment=TA_LEFT, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=10, textColor=MUTED, leading=14),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=INK, spaceBefore=16, spaceAfter=6),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=9, leading=12, textColor=INK),
        "head": ParagraphStyle("hd", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8, leading=11, textColor=MUTED),
        "empty": ParagraphStyle("e", parent=base["Normal"], fontSize=9.5, textColor=MUTED, leading=13),
    }


def _table(header, rows, widths, st):
    data = [[Paragraph(safe(h), st["head"]) for h in header]]
    data += [[Paragraph(safe(c), st["cell"]) for c in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def build_report(user_name: str, date_of_birth: date, schedule: dict, records: list[dict], upcoming: list[dict],
                 generated_on: date | None = None) -> bytes:
    """records: serialised records with flags. upcoming: schedule items (upcoming / potentially due)."""
    generated_on = generated_on or date.today()
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title="VaxTrack vaccination report", author="VaxTrack",
    )
    width = A4[0] - 36 * mm
    story = [Paragraph("VaxTrack", ParagraphStyle("brand", parent=st["sub"], textColor=TEAL, fontName="Helvetica-Bold", fontSize=11)),
             Paragraph("Vaccination report", st["title"]), Spacer(1, 4)]

    info = [
        ["Name", user_name], ["Date of birth", fmt_date(date_of_birth)], ["Report generated", fmt_date(generated_on)],
        ["Reference schedule", f"{schedule['name']} (version {schedule['version']})"],
        ["Schedule source", schedule["source"]],
    ]
    info_table = Table([[Paragraph(f"<b>{safe(k)}</b>", st["cell"]), Paragraph(safe(v), st["cell"])] for k, v in info],
                       colWidths=[38 * mm, width - 38 * mm])
    info_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(info_table)

    # --- recorded vaccinations
    story.append(Paragraph("Recorded vaccinations", st["h2"]))
    if records:
        ordered = sorted(records, key=lambda r: (r["vaccination_date"] is None, r["vaccination_date"] or "", r["vaccine_name"]))
        rows = [[r["vaccine_name"], "-" if r["dose_number"] is None else str(r["dose_number"]),
                 fmt_date(r["vaccination_date"]),
                 "Confirmed" if r["verification_status"] == "confirmed" else "Not confirmed",
                 r["source_document"] or ("Entered manually" if r["source_type"] == "manual" else "Uploaded card")]
                for r in ordered]
        story.append(_table(["Vaccine", "Dose", "Date", "Status", "Source"], rows,
                            [width * 0.34, width * 0.08, width * 0.19, width * 0.16, width * 0.23], st))
    else:
        story.append(Paragraph("No vaccination records have been added yet.", st["empty"]))

    # --- upcoming
    story.append(Paragraph("Upcoming doses (estimated)", st["h2"]))
    story.append(Paragraph("Estimated from your date of birth and the selected schedule. These are not appointments.", st["small"]))
    story.append(Spacer(1, 4))
    if upcoming:
        rows = [[u["vaccine_name"], u["dose_label"], fmt_date(u["estimated_date"]), u["status_label"]] for u in upcoming]
        story.append(_table(["Vaccine", "Dose", "Estimated date", "Status"], rows,
                            [width * 0.34, width * 0.28, width * 0.20, width * 0.18], st))
    else:
        story.append(Paragraph("No upcoming doses are estimated for the selected schedule.", st["empty"]))

    # --- review
    story.append(Paragraph("Records that need review", st["h2"]))
    flagged = [r for r in records if r["flags"]]
    if flagged:
        rows = [[r["vaccine_name"] + (f" (dose {r['dose_number']})" if r["dose_number"] is not None else ""),
                 fmt_date(r["vaccination_date"]), "; ".join(f["message"] for f in r["flags"])] for r in flagged]
        story.append(_table(["Record", "Date", "Reason"], rows, [width * 0.30, width * 0.18, width * 0.52], st))
    else:
        story.append(Paragraph("Every saved record is confirmed and no inconsistencies were found.", st["empty"]))

    story.append(Spacer(1, 14))
    story.append(KeepTogether([Paragraph("Important", st["h2"]), Paragraph(safe(DISCLAIMER), st["small"])]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 11 * mm, "VaxTrack - personal vaccination record (educational use)")
        canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
