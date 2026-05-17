from fastapi import APIRouter, HTTPException

from app.models.schemas import AskRequest
from app.services.rag_service import ask_question

router = APIRouter(prefix="/ask", tags=["Ask"])


@router.post("")
def ask(request: AskRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = ask_question(
        question=question,
        document_id=request.document_id,
        match_count=request.match_count,
        fast_mode=request.fast_mode,
    )

    return {
        "question": question,
        **result,
    }
