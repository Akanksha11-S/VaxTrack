"""Plain-language explanations of vaccine information.

Order of preference
1. An optional LLM (Anthropic, or any OpenAI-compatible API) rewrites *supplied, trusted text* more simply.
2. If no LLM is configured, or the call fails, a rule-based simplifier is used.
3. For library vaccines, curated explanations written in data/vaccines.json are always available.

Only text typed into the vaccine information page is ever sent to an external service, and only when
LLM_PROVIDER and LLM_API_KEY are set. Uploaded documents and personal records are never sent.
"""
import logging
import re

import httpx

from config import settings

log = logging.getLogger("vaxtrack")

SYSTEM_PROMPT = (
    "You rewrite vaccine information in plain, friendly language for the general public (reading age about 12). "
    "Use only facts that appear in the text you are given. Do not add new medical facts, doses, schedules, "
    "recommendations, or advice. Do not diagnose or tell the reader what to do. Keep it under 80 words. "
    "Return only the rewritten text."
)

NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

GLOSSARY = [
    (r"\bprovides? protection against\b", "helps protect you against"),
    (r"\bconfers? immunity (?:to|against)\b", "helps your body defend itself against"),
    (r"\binvasive disease\b", "serious infection"),
    (r"\bgastroenteritis\b", "a stomach infection with diarrhoea and vomiting"),
    (r"\bmorbidity\b", "illness"),
    (r"\bprophylactic\b", "preventive"),
    (r"\bimmuni[sz]ation\b", "vaccination"),
    (r"\badministered\b", "given"),
    (r"\badministration\b", "giving the vaccine"),
    (r"\bintramuscular(?:ly)?\b", "into the muscle"),
    (r"\bsubcutaneous(?:ly)?\b", "under the skin"),
    (r"\bintradermal(?:ly)?\b", "into the skin"),
    (r"\bpathogens?\b", "germs"),
    (r"\befficacy\b", "how well it works"),
    (r"\badverse events?\b", "side effects"),
    (r"\bseroprotection\b", "protection shown in blood tests"),
    (r"\bimmunogenic(?:ity)?\b", "able to trigger protection"),
    (r"\bin infants and young children\b", "in babies and young children"),
]

PROTECT_PATTERN = re.compile(
    r"^(?:the\s+)?(?P<name>.+?)\s+vaccines?\s+(?:provides?|offers?|gives?)\s+(?:protection|immunity)\s+against\s+(?P<list>.+?)\.?$",
    re.I,
)


def status() -> dict:
    return {
        "llm_enabled": settings.llm_enabled,
        "provider": settings.LLM_PROVIDER if settings.llm_enabled else None,
        "model": (settings.LLM_MODEL or _default_model()) if settings.llm_enabled else None,
    }


def _default_model() -> str:
    return "claude-haiku-5-5" if settings.LLM_PROVIDER == "anthropic" else "gpt-4o-mini"


# ------------------------------------------------------------- rule-based fallback
def simplify_with_rules(text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    out = []
    for sentence in sentences:
        m = PROTECT_PATTERN.match(sentence)
        if m:
            items = [i.strip() for i in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group("list")) if i.strip()]
            name = m.group("name").strip()
            if 2 <= len(items) <= 6:
                joined = ", ".join(items[:-1]) + (", and " if len(items) > 2 else " and ") + items[-1]
                out.append(f"The {name} vaccine helps protect you against {NUMBER_WORDS[len(items)]} infections: {joined}.")
                continue
        for pattern, replacement in GLOSSARY:
            sentence = re.sub(pattern, replacement, sentence, flags=re.I)
        sentence = sentence[0].upper() + sentence[1:]
        if not sentence.endswith((".", "!", "?")):
            sentence += "."
        out.append(sentence)
    return " ".join(out)


# ------------------------------------------------------------- LLM
def _call_llm(text: str) -> str:
    timeout = httpx.Timeout(20.0)
    model = settings.LLM_MODEL or _default_model()
    if settings.LLM_PROVIDER == "anthropic":
        base = settings.LLM_BASE_URL or "https://api.anthropic.com"
        resp = httpx.post(
            f"{base.rstrip('/')}/v1/messages",
            headers={"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 300, "system": SYSTEM_PROMPT,
                  "messages": [{"role": "user", "content": f"Text to simplify:\n\n{text}"}]},
            timeout=timeout,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json()["content"] if b.get("type") == "text").strip()

    base = settings.LLM_BASE_URL or "https://api.openai.com/v1"
    resp = httpx.post(
        f"{base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        json={"model": model, "max_tokens": 300, "temperature": 0.2,
              "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                           {"role": "user", "content": f"Text to simplify:\n\n{text}"}]},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def simplify(text: str) -> dict:
    """Return {"text", "method", "notice"}. Never raises: falls back to rules if the LLM fails."""
    text = " ".join(text.split())
    notice = None
    if settings.llm_enabled:
        try:
            result = _call_llm(text)
            if result:
                return {"text": result, "method": "llm", "notice": None}
        except Exception as exc:  # network error, bad key, rate limit, malformed response...
            log.warning("LLM request failed (%s); using the rule-based simplifier.", type(exc).__name__)
            notice = "The AI service wasn't available, so a simpler rule-based explanation was used."
    return {"text": simplify_with_rules(text), "method": "rules", "notice": notice}
