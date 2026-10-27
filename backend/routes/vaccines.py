from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_user
from models import User
from schemas import ExplainIn
from services import llm_service, vaccine_service

router = APIRouter(tags=["Vaccine information"])

NOTICE = ("Educational information only. It is not a diagnosis or a personal recommendation. "
          "Ask a healthcare provider what is right for you.")


@router.get("/vaccines")
def list_vaccines(q: str = Query("", max_length=100), category: str = Query("", max_length=60),
                  user: User = Depends(get_current_user)):
    return {
        "vaccines": vaccine_service.search(q, category),
        "categories": vaccine_service.categories(),
        "library_version": vaccine_service.library_version(),
        "notice": NOTICE,
    }


@router.get("/vaccines/{vaccine_name}")
def get_vaccine(vaccine_name: str, user: User = Depends(get_current_user)):
    v = vaccine_service.lookup(vaccine_name)
    if v is None:
        raise HTTPException(404, "That vaccine isn't in the library yet.")
    return v


@router.get("/assistant/status")
def assistant_status(user: User = Depends(get_current_user)):
    return llm_service.status()


@router.post("/assistant/explain")
def explain(body: ExplainIn, user: User = Depends(get_current_user)):
    """Simplify a vaccine's description, or text the user pasted in."""
    if body.vaccine_id:
        v = vaccine_service.lookup(body.vaccine_id)
        if v is None:
            raise HTTPException(404, "That vaccine isn't in the library yet.")
        source = v["technical_description"]
        result = llm_service.simplify(source)
        if result["method"] == "rules":  # the curated wording is better than rules when it exists
            result["text"], result["method"] = v["simple_explanation"], "curated"
        return {**result, "original": source, "source": v["sources"][0] if v["sources"] else None, "notice": result["notice"] or NOTICE}

    text = (body.text or "").strip()
    if len(text) < 10:
        raise HTTPException(422, "Paste at least a sentence of text to simplify.")
    result = llm_service.simplify(text)
    return {**result, "original": text, "source": None, "notice": result["notice"] or NOTICE}
