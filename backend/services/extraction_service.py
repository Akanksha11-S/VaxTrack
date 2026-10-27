"""Turn OCR text lines into candidate vaccination records.

Principles
- Never invent a value. A field that cannot be read is left empty and listed in `issues`.
- Ambiguous situations (several dates on a line, day/month order unclear) are flagged for the user.
- Everything returned is a *suggestion*: verification_status is always "unverified".
"""
import re
from dataclasses import dataclass
from datetime import date

from services import vaccine_service
from services.ocr_service import OCRLine

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
NOISE = str.maketrans("OoIl|", "00111")  # characters OCR commonly confuses with digits

NUMERIC_DATE = re.compile(r"(?<![\w/])([0-9OoIl|]{1,4})\s?([/\-.])\s?([0-9OoIl|]{1,2})\s?\2\s?([0-9OoIl|]{2,4})(?![\w/])")
TEXT_DATE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s\-/.,]*({MONTH_RE})[\s\-/.,]*(\d{{2,4}})\b", re.I)
TEXT_DATE_MDY = re.compile(rf"\b({MONTH_RE})[\s\-/.,]*(\d{{1,2}})(?:st|nd|rd|th)?[\s,\-/.]+(\d{{4}})\b", re.I)
MONTH_YEAR = re.compile(rf"\b({MONTH_RE})[\s\-/.,]+(\d{{4}})\b", re.I)

DOSE_BEFORE_DATE = re.compile(r"(?:dose\W{0,2}|#)?\b(\d{1,2})\b\W*$", re.I)
DOSE_AFTER_ALIAS = re.compile(
    r"^\W{0,3}(?:dose\W{0,2})?#?\s*(\d{1,2})\b(?![/\-.]\d)(?!\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|days?)\b)", re.I
)
ROMAN_AFTER_ALIAS = re.compile(r"^\W{0,3}(III|II|I)\b")
ORDINAL_DOSE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s*dose\b", re.I)
DOSE_WORD = re.compile(r"\bdose\s*[:#\-]?\s*(\d{1,2})\b", re.I)
BOOSTER = re.compile(r"\bboost(?:er)?\b", re.I)
STOP_WORDS = re.compile(r"\b(dob|d\.o\.b|birth|born|age|issued?|expir\w*|exp|valid|print\w*|mfg|manufactur\w*|signature|registration)\b", re.I)
ROMAN = {"I": 1, "II": 2, "III": 3}

LOW_CONFIDENCE = 60.0


@dataclass
class DateHit:
    start: int
    end: int
    raw: str
    iso: str | None = None
    partial: bool = False
    ambiguous: bool = False
    invalid: bool = False
    inferred: bool = False


@dataclass
class VaccineHit:
    start: int
    end: int
    raw: str
    vaccine: dict
    score: float


# ----------------------------------------------------------------------- dates
def _expand_year(y: int, today: date) -> int:
    if y >= 100:
        return y
    return 2000 + y if y <= today.year % 100 else 1900 + y


def _make_date(y: int, m: int, d: int, today: date) -> date | None:
    try:
        value = date(y, m, d)
    except ValueError:
        return None
    return value if 1900 <= value.year <= today.year + 1 else None


def find_dates(text: str, date_order: str = "DMY", today: date | None = None) -> list[DateHit]:
    """Find every date in a piece of text, in reading order. Unreadable dates come back with iso=None."""
    today = today or date.today()
    hits: list[DateHit] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < h.end and e > h.start for h in hits)

    for m in TEXT_DATE_DMY.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        d, mon, y = int(m.group(1)), MONTHS[m.group(2)[:3].lower()], _expand_year(int(m.group(3)), today)
        value = _make_date(y, mon, d, today)
        hits.append(DateHit(m.start(), m.end(), m.group(0), value.isoformat() if value else None, invalid=value is None))
    for m in TEXT_DATE_MDY.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        mon, d, y = MONTHS[m.group(1)[:3].lower()], int(m.group(2)), int(m.group(3))
        value = _make_date(y, mon, d, today)
        hits.append(DateHit(m.start(), m.end(), m.group(0), value.isoformat() if value else None, invalid=value is None))
    for m in NUMERIC_DATE.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        a, _sep, b, c = (g.translate(NOISE) for g in m.groups())
        if not (a.isdigit() and b.isdigit() and c.isdigit()):
            continue
        hit = DateHit(m.start(), m.end(), m.group(0))
        iso_style = len(a) == 4 and len(c) <= 2
        if iso_style:
            value = _make_date(int(a), int(b), int(c), today)
        elif len(a) <= 2 and len(c) in (2, 4):
            first, second, year = int(a), int(b), _expand_year(int(c), today)
            month, day = (first, second) if date_order == "MDY" else (second, first)
            value = _make_date(year, month, day, today)
            if value is None:  # maybe the other order is the only valid reading
                value = _make_date(year, day, month, today)
            elif first <= 12 and second <= 12 and first != second:
                hit.ambiguous = True
        else:
            value = None
        hit.iso, hit.invalid = (value.isoformat() if value else None), value is None
        hits.append(hit)
    for m in MONTH_YEAR.finditer(text):
        if not overlaps(m.start(), m.end()):
            hits.append(DateHit(m.start(), m.end(), m.group(0), None, partial=True))
    return sorted(hits, key=lambda h: h.start)


DUE_LABEL = re.compile(r"\b(?:next\s+(?:due\s+)?date|next\s+dose\s+date|due\s+date|next\s+due|due\s+on|next\s+vaccination)\s*[:：\-]?", re.I)


def find_due_date(text: str, date_order: str = "DMY", today: date | None = None) -> DateHit | None:
    """Find a date explicitly labelled as a future/next due date, independent of card layout."""
    labels = list(DUE_LABEL.finditer(text))
    if not labels:
        return None
    today = today or date.today()
    # Use the first labelled date, bounded before another field label when possible.
    for label in labels:
        tail = text[label.end():]
        boundary = re.search(r"\b(?:remarks?|status|given|administered|vaccine|dose)\s*[:：]", tail, re.I)
        if boundary:
            tail = tail[:boundary.start()]
        hits = [h for h in find_dates(tail, date_order, today) if h.iso]
        if hits:
            h = hits[0]
            return DateHit(label.end() + h.start, label.end() + h.end, h.raw, h.iso, h.partial, h.ambiguous, h.invalid)
    return None


def normalize_date(text: str, date_order: str = "DMY", today: date | None = None) -> str | None:
    """Return an ISO date for the first complete date found in text, else None."""
    for hit in find_dates(text, date_order, today):
        if hit.iso:
            return hit.iso
    return None


# -------------------------------------------------------------------- vaccines
_PATTERN_CACHE: dict[int, list[tuple[re.Pattern, str, bool]]] = {}


def _alias_patterns() -> list[tuple[re.Pattern, str, bool]]:
    index = vaccine_service.alias_index()
    key = id(index)
    if key not in _PATTERN_CACHE:
        _PATTERN_CACHE.clear()
        patterns = []
        for alias, vid in index.items():
            body = r"[\s\-]*".join(re.escape(part) for part in alias.split())
            short = len(alias.replace(" ", "")) <= 2
            regex = re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z])", re.I)
            patterns.append((regex, vid, short))
        _PATTERN_CACHE[key] = patterns
    return _PATTERN_CACHE[key]


def _plausible_short_alias(word: str) -> bool:
    """Two-letter names (MR, JE, Td, TT) only count when capitalised, which avoids matching 'mr' or 'je' in ordinary words.
    'Mr' is excluded outright because it is almost always a title."""
    if word == "Mr":
        return False
    return word.isupper() or word[0].isupper()


def find_vaccines(text: str) -> list[VaccineHit]:
    found: list[VaccineHit] = []
    for regex, vid, short in _alias_patterns():
        for m in regex.finditer(text):
            if short and not _plausible_short_alias(m.group(0)):
                continue
            found.append(VaccineHit(m.start(), m.end(), m.group(0), vaccine_service.get_by_id(vid), 1.0))
    found.sort(key=lambda h: -(h.end - h.start))
    chosen: list[VaccineHit] = []
    for h in found:
        if not any(h.start < c.end and h.end > c.start for c in chosen):
            chosen.append(h)
    if chosen:
        return sorted(chosen, key=lambda h: h.start)

    # Fuzzy fallback for misread names such as "Pentavalnt" or "Hepatitls B".
    words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[A-Za-z]{4,}", text)
             if m.group(0).lower() not in vaccine_service.GENERIC_WORDS]
    for i, (s, e, w) in enumerate(words):
        for span_end, phrase in ((e, w), (words[i + 1][1], text[s:words[i + 1][1]]) if i + 1 < len(words) else (None, None)):
            if span_end is None:
                continue
            vaccine, score = vaccine_service.canonicalize(phrase)
            if vaccine and score >= 0.82:
                return [VaccineHit(s, span_end, phrase, vaccine, score)]
    return []


def _dose_from_text(rest: str) -> int | None:
    m = DOSE_AFTER_ALIAS.match(rest)
    if m:
        return _valid_dose(int(m.group(1)))
    m = ROMAN_AFTER_ALIAS.match(rest)
    return ROMAN[m.group(1)] if m else None


def _valid_dose(n: int) -> int | None:
    return n if 0 <= n <= 12 else None


def _explicit_dose(line: str) -> int | None:
    m = ORDINAL_DOSE.search(line) or DOSE_WORD.search(line)
    return _valid_dose(int(m.group(1))) if m else None


# ------------------------------------------------------------------ main logic
def extract_candidates(lines: list[OCRLine], date_order: str = "DMY", source_document: str | None = None,
                       today: date | None = None) -> list[dict]:
    today = today or date.today()
    results: list[dict] = []
    seen: set[tuple] = set()
    consumed: set[int] = set()

    def add(line: OCRLine, vaccine_hit: VaccineHit | None, hit_date: DateHit | None, dose: int | None,
            extra_issues: list[str], due_hit: DateHit | None = None) -> None:
        issues = list(extra_issues)
        vaccine = vaccine_hit.vaccine if vaccine_hit else None
        iso = hit_date.iso if hit_date else None
        if due_hit and due_hit.inferred:
            issues.append("Possible next due date inferred from a later date in this row - verify it against the card.")
        if vaccine is None:
            issues.append("Vaccine name not recognised - choose or type it.")
        elif vaccine_hit.score < 1.0:
            issues.append("Vaccine name was matched approximately - check it.")
        if hit_date is None:
            issues.append("Date not found.")
        elif hit_date.partial:
            issues.append("Only a month and year were found, so the date is blank.")
        elif hit_date.invalid:
            issues.append("A date was found but couldn't be read reliably.")
        elif hit_date.ambiguous:
            issues.append(f"Read with the {'month' if date_order == 'MDY' else 'day'} first - check the day and month.")
        if iso and date.fromisoformat(iso) > today:
            issues.append("This date is in the future.")
        if dose is None and vaccine is not None and not vaccine.get("single_dose"):
            issues.append("Dose number not found.")
        conf = line.confidence
        if conf is not None and conf < LOW_CONFIDENCE:
            issues.append("The text was hard to read - check every field.")

        key = (vaccine["id"] if vaccine else vaccine_hit and vaccine_hit.raw, iso, dose)
        if vaccine is not None and key in seen:
            return
        seen.add(key)
        notes = "Booster" if BOOSTER.search(line.text) else None
        results.append({
            "temp_id": f"r{len(results) + 1}",
            "vaccine_name": vaccine["name"] if vaccine else "",
            "vaccine_matched": vaccine is not None,
            "match_score": round(vaccine_hit.score, 2) if vaccine_hit else None,
            "raw_vaccine_text": vaccine_hit.raw if vaccine_hit else None,
            "vaccination_date": iso,
            "next_due_date": due_hit.iso if due_hit else None,
            "next_due_date_raw": due_hit.raw if due_hit else None,
            "next_due_date_estimated": bool(due_hit and due_hit.inferred),
            "date_raw": hit_date.raw if hit_date else None,
            "dose_number": dose,
            "notes": notes,
            "source_document": source_document,
            "ocr_confidence": conf,
            "verification_status": "unverified",
            "source_type": "ocr",
            "issues": issues,
            "raw_line": line.text,
        })

    for idx, line in enumerate(lines):
        if idx in consumed:
            continue
        text = line.text
        vhits = find_vaccines(text)
        due_hit = find_due_date(text, date_order, today)
        all_dates = find_dates(text, date_order, today)
        # Some table cards show the due-date column only in the header. If a vaccine row
        # has an administered date followed by a future date, treat the latter as a candidate.
        if due_hit is None and find_vaccines(text) and len(all_dates) >= 2:
            earlier = [d for d in all_dates[:-1] if d.iso and date.fromisoformat(d.iso) <= today]
            last = all_dates[-1]
            if earlier and last.iso and date.fromisoformat(last.iso) > today:
                last.inferred = True
                due_hit = last
        dates = [d for d in all_dates if not (due_hit and d.start < due_hit.end and d.end > due_hit.start)]

        if not vhits:
            letters = re.sub(r"\d|[^A-Za-z ]", " ", text)
            has_words = re.search(r"[A-Za-z]{3,}", letters) and not STOP_WORDS.search(text)
            if dates and has_words:
                add(line, None, dates[0], _explicit_dose(text), [], due_hit)
            continue

        extra: list[str] = []
        if not dates and idx + 1 < len(lines):  # the date may have wrapped onto the next line
            nxt = lines[idx + 1]
            nd = find_dates(nxt.text, date_order, today)
            if nd and not find_vaccines(nxt.text):
                dates, consumed = nd, consumed | {idx + 1}
                extra.append("The date was read from the line below.")

        if len(vhits) == 1:
            vh = vhits[0]
            if not dates:
                add(line, vh, None, _dose_from_text(text[vh.end:]) or _explicit_dose(text), extra, due_hit)
            else:
                prev_end = vh.end
                for dh in dates:
                    region = text[prev_end:dh.start] if dh.start >= prev_end else ""
                    m = DOSE_BEFORE_DATE.search(region)
                    dose = _valid_dose(int(m.group(1))) if m else None
                    if dose is None and len(dates) == 1:
                        dose = _dose_from_text(text[vh.end:]) or _explicit_dose(text)
                    add(line, vh, dh, dose, extra, due_hit)
                    prev_end = dh.end
        elif dates and len(dates) == len(vhits):
            for vh, dh in zip(vhits, dates):
                add(line, vh, dh, _dose_from_text(text[vh.end:dh.start]), extra, due_hit)
        elif len(dates) == 1:
            for vh in vhits:
                add(line, vh, dates[0], _dose_from_text(text[vh.end:]), extra + ["One date is shared by several vaccines on this line - check it."], due_hit)
        else:
            for vh in vhits:
                add(line, vh, None, _dose_from_text(text[vh.end:]), extra + ["Several dates on this line - choose the correct one."], due_hit)
    return results
