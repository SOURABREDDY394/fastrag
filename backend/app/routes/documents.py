import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.services.document_service import get_document, mark_document_failed

router = APIRouter(prefix="/documents", tags=["Documents"])
PROCESSING_STALE_MINUTES = int(os.getenv("PROCESSING_STALE_MINUTES", "20"))
STALE_PROCESSING_MESSAGE = (
    "Document processing took too long on the deployed server. "
    "Try uploading a smaller PDF or split this file into smaller parts."
)


def parse_uploaded_at(uploaded_at: str | None) -> datetime | None:
    if not uploaded_at:
        return None

    try:
        return datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
    except ValueError:
        return None


def mark_stale_processing_document(document: dict) -> dict:
    if document.get("status") != "processing":
        return document

    uploaded_at = parse_uploaded_at(document.get("uploaded_at"))
    if not uploaded_at:
        return document

    if uploaded_at.tzinfo is None:
        uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)

    stale_after = timedelta(minutes=max(PROCESSING_STALE_MINUTES, 1))
    if datetime.now(timezone.utc) - uploaded_at < stale_after:
        return document

    mark_document_failed(document["id"], STALE_PROCESSING_MESSAGE)
    return {
        **document,
        "status": "failed",
        "error_message": STALE_PROCESSING_MESSAGE,
    }


@router.get("/{document_id}/status")
def get_document_status(document_id: str):
    document = get_document(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    document = mark_stale_processing_document(document)

    return {
        "document_id": document["id"],
        "filename": document.get("filename"),
        "status": document.get("status"),
        "total_pages": document.get("total_pages") or 0,
        "processed_pages": document.get("processed_pages") or 0,
        "total_chunks": document.get("total_chunks") or 0,
        "error_message": document.get("error_message"),
    }
