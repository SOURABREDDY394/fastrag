import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
BATCH_SIZE = 100


def format_supabase_error(action: str, exc: Exception) -> str:
    error_text = str(exc)
    normalized_error = error_text.lower()
    connection_markers = (
        "getaddrinfo failed",
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
    )

    if any(marker in normalized_error for marker in connection_markers):
        return (
            f"Supabase is unreachable while trying to {action}. "
            "Check that SUPABASE_URL points to an active Supabase project "
            "and that the computer is online."
        )

    if "row-level security" in normalized_error or "'42501'" in normalized_error:
        return (
            f"Supabase blocked permission to {action}. The configured publishable "
            "key is restricted by Row Level Security. Set "
            "SUPABASE_SERVICE_ROLE_KEY in the backend .env file."
        )

    return f"Supabase failed while trying to {action}: {error_text}"


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
            detail=format_supabase_error("create the document record", exc),
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
            detail=format_supabase_error("fetch the document status", exc),
        ) from exc

    if not response.data:
        return None

    return response.data[0]


def list_documents(limit: int = 50) -> list[dict]:
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("documents")
            .select(
                "id, filename, status, total_pages, processed_pages, total_chunks, error_message, uploaded_at, processed_at"
            )
            .order("uploaded_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=format_supabase_error("list saved documents", exc),
        ) from exc

    return response.data or []


def update_document(document_id: str, values: dict) -> None:
    supabase = get_supabase_client()

    try:
        supabase.table("documents").update(values).eq("id", document_id).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=format_supabase_error("update the document", exc),
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
                detail=format_supabase_error(
                    f"insert document chunks for batch starting at index {start}",
                    exc,
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
