from fastapi import HTTPException

from app.db.supabase_client import get_supabase_client
from app.services.embedding_service import generate_embedding


def embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def search_similar_chunks(
    question: str,
    document_id: str | None = None,
    match_count: int = 5,
) -> list[dict]:
    clean_question = question.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if match_count < 1 or match_count > 10:
        raise HTTPException(
            status_code=400,
            detail="match_count must be between 1 and 10.",
        )

    question_embedding = generate_embedding(clean_question)

    return search_similar_chunks_by_embedding(
        query_embedding=question_embedding,
        document_id=document_id,
        match_count=match_count,
    )


def search_similar_chunks_by_embedding(
    query_embedding: list[float],
    document_id: str | None = None,
    match_count: int = 5,
) -> list[dict]:
    if match_count < 1 or match_count > 10:
        raise HTTPException(
            status_code=400,
            detail="match_count must be between 1 and 10.",
        )

    supabase = get_supabase_client()

    rpc_params = {
        "query_embedding": embedding_to_pgvector(query_embedding),
        "match_count": match_count,
        "filter_document_id": document_id,
    }

    try:
        response = supabase.rpc("match_document_chunks", rpc_params).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase vector search failed: {exc}",
        ) from exc

    return response.data or []
