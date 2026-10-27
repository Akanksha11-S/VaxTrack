"""Vaccine library: loads data/vaccines.json and resolves free-text names to library entries."""
import json
import re
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "vaccines.json"


# Words that appear on every card; they must never be fuzzy-matched to a vaccine.
GENERIC_WORDS = {"vaccine", "vaccines", "vaccination", "vaccinations", "immunization", "immunisation", "dose", "doses",
                 "date", "given", "booster", "name", "record", "card", "batch", "age", "birth", "child", "details"}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


@lru_cache(maxsize=4)
def _load(mtime: float) -> dict:
    with open(DATA_FILE, encoding="utf-8") as fh:
        payload = json.load(fh)
    vaccines = payload["vaccines"]
    by_id = {v["id"]: v for v in vaccines}
    index: dict[str, str] = {}
    for v in vaccines:
        for alias in [v["name"], v["id"], *v.get("aliases", [])]:
            index.setdefault(norm(alias), v["id"])
    return {"version": payload.get("version"), "vaccines": vaccines, "by_id": by_id, "index": index}


def _data() -> dict:
    # Keyed on the file's modified time so edits to vaccines.json apply without a restart.
    return _load(DATA_FILE.stat().st_mtime)


def library_version() -> str | None:
    return _data()["version"]


def all_vaccines() -> list[dict]:
    return _data()["vaccines"]


def get_by_id(vaccine_id: str) -> dict | None:
    return _data()["by_id"].get(vaccine_id)


def alias_index() -> dict[str, str]:
    return _data()["index"]


def display_name(vaccine_id: str) -> str:
    v = get_by_id(vaccine_id)
    return v["name"] if v else vaccine_id


def categories() -> list[str]:
    seen: list[str] = []
    for v in all_vaccines():
        if v["category"] not in seen:
            seen.append(v["category"])
    return seen


def lookup(name_or_id: str) -> dict | None:
    """Find a vaccine by id or by any alias (exact, after normalisation)."""
    v = get_by_id(name_or_id)
    if v:
        return v
    vid = alias_index().get(norm(name_or_id))
    return get_by_id(vid) if vid else None


def search(query: str = "", category: str = "") -> list[dict]:
    q = norm(query)
    out = []
    for v in all_vaccines():
        if category and v["category"] != category:
            continue
        if q:
            haystack = norm(" ".join([v["name"], *v["aliases"], *v["diseases"], v["purpose"]]))
            if q not in haystack:
                continue
        out.append(v)
    return out


def canonicalize(text: str) -> tuple[dict | None, float]:
    """Match free text to a library vaccine. Returns (vaccine, score) or (None, 0.0).

    Order of attempts: exact alias -> alias contained as whole words -> fuzzy match.
    Very short aliases (<= 3 characters) only ever match exactly, to avoid false hits.
    """
    n = norm(text)
    if not n:
        return None, 0.0
    index = alias_index()
    if n in index:
        return get_by_id(index[n]), 1.0

    padded = f" {n} "
    best_alias = ""
    for alias in index:
        if len(alias) >= 3 and f" {alias} " in padded and len(alias) > len(best_alias):
            best_alias = alias
    if best_alias:
        return get_by_id(index[best_alias]), 0.95

    if len(n) >= 5 and n not in GENERIC_WORDS:
        candidates = [a for a in index if len(a) >= 5 and not (set(a.split()) & GENERIC_WORDS)]
        close = get_close_matches(n, candidates, n=1, cutoff=0.82)
        if close:
            from difflib import SequenceMatcher
            return get_by_id(index[close[0]]), round(SequenceMatcher(None, n, close[0]).ratio(), 2)
    return None, 0.0


def satisfied_by(rule_vaccine_id: str) -> set[str]:
    """Vaccine ids whose records can count towards a schedule rule for rule_vaccine_id."""
    ids = {rule_vaccine_id}
    for v in all_vaccines():
        if rule_vaccine_id in v.get("satisfies", []):
            ids.add(v["id"])
    return ids
