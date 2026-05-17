import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
BATCH_SIZE = 100


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def create_uploaded_document(filename: str) -> str:
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("documents")
            .insert(
                {
                    "filename": filename,
                    "status": "uploaded",
                    "processed_pages": 0,
                    "total_pages": 0,
                    "total_chunks": 0,
                    "uploaded_at": utc_now(),
                }
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create document row in Supabase: {exc}",
        ) from exc

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Supabase did not return an inserted document row.",
        )

    return response.data[0]["id"]


def get_document(document_id: str) -> dict | None:
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("documents")
            .select(
                "id, filename, status, total_pages, processed_pages, total_chunks, error_message, uploaded_at, processed_at"
            )
            .eq("id", document_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch document status from Supabase: {exc}",
        ) from exc

    if not response.data:
        return None

    return response.data[0]


def update_document(document_id: str, values: dict) -> None:
    supabase = get_supabase_client()

    try:
        supabase.table("documents").update(values).eq("id", document_id).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update document in Supabase: {exc}",
        ) from exc


def mark_document_failed(document_id: str, error_message: str) -> None:
    try:
        update_document(
            document_id,
            {
                "status": "failed",
                "error_message": error_message[:1000],
            },
        )
    except Exception as exc:
        logger.error("Failed to mark document as failed: %s", exc)


def build_chunk_rows(document_id: str, embedded_chunks: list[dict]) -> list[dict]:
    return [
        {
            "document_id": document_id,
            "chunk_text": chunk["chunk_text"],
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
            "embedding": embedding_to_pgvector(chunk["embedding"]),
        }
        for chunk in embedded_chunks
    ]


def batch_insert_chunks(chunk_rows: list[dict], batch_size: int = BATCH_SIZE) -> int:
    if not chunk_rows:
        return 0

    supabase = get_supabase_client()
    stored_chunks = 0

    for start in range(0, len(chunk_rows), batch_size):
        batch = chunk_rows[start : start + batch_size]

        try:
            response = supabase.table("document_chunks").insert(batch).execute()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to insert document chunks into Supabase "
                    f"for batch starting at index {start}: {exc}"
                ),
            ) from exc

        if not response.data or len(response.data) != len(batch):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Supabase chunk insert returned an unexpected result "
                    f"for batch starting at index {start}."
                ),
            )

        stored_chunks += len(response.data)

    return stored_chunks
