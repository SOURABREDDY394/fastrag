from fastapi import APIRouter, HTTPException

from app.models.schemas import SearchRequest
from app.services.search_service import search_similar_chunks

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("")
def search_chunks(request: SearchRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    matches = search_similar_chunks(
        question=question,
        document_id=request.document_id,
        match_count=request.match_count,
    )

    if not matches:
        return {
            "question": question,
            "matches_count": 0,
            "message": "No matching chunks found.",
            "matches": [],
        }

    return {
        "question": question,
        "matches_count": len(matches),
        "matches": matches,
    }
