import os
import re
from datetime import datetime, timedelta, timezone

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.services.document_service import get_document, mark_document_failed, update_document
from app.services.indexing_jobs import find_saved_file_path, register_document_file, run_indexing_job

router = APIRouter(prefix="/documents", tags=["Documents"])
PROCESSING_STALE_MINUTES = int(os.getenv("PROCESSING_STALE_MINUTES", "20"))
STALE_PROCESSING_MESSAGE = (
    "Document processing took too long on the deployed server. "
    "Try again with a smaller PDF section or a compressed file."
)


def parse_uploaded_at(uploaded_at: str | None) -> datetime | None:
    if not uploaded_at:
        return None

    try:
        return datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
    except ValueError:
        return None


def mark_stale_processing_document(document: dict) -> dict:
    if document.get("status") not in {"processing", "extracting", "queued"}:
        return document

    total_pages = document.get("total_pages") or 0
    processed_pages = document.get("processed_pages") or 0
    if total_pages > 0 and processed_pages >= total_pages:
        update_document(
            document["id"],
            {
                "status": "ready",
                "error_message": None,
            },
        )
        return {
            **document,
            "status": "ready",
            "error_message": None,
        }

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


def get_current_status(document: dict) -> str:
    status = document.get("status")
    if status == "ready":
        return "completed"
    if status == "failed":
        return "failed"
    if status in {"processing", "extracting", "queued"}:
        if (document.get("total_chunks") or 0) > 0:
            return "indexing"
        if (document.get("processed_pages") or 0) > 0:
            return "extracting"
        return status
    return status or "uploaded"


def get_failed_pages(document: dict) -> list[int]:
    error_message = document.get("error_message") or ""
    return [int(match) for match in re.findall(r"\d+", error_message)[:20]]


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
        "current_status": get_current_status(document),
        "total_pages": document.get("total_pages") or 0,
        "processed_pages": document.get("processed_pages") or 0,
        "total_chunks": document.get("total_chunks") or 0,
        "failed_pages": get_failed_pages(document),
        "error_message": document.get("error_message"),
    }


@router.post("/{document_id}/start-indexing")
def start_indexing(document_id: str, background_tasks: BackgroundTasks):
    document = get_document(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    saved_file_path = find_saved_file_path(document_id)
    if not saved_file_path:
        raise HTTPException(
            status_code=404,
            detail="Saved PDF file was not found on this server.",
        )

    register_document_file(document_id, saved_file_path)
    update_document(document_id, {"status": "queued", "error_message": None})
    print("ADDING BACKGROUND INDEXING TASK", document_id, saved_file_path, flush=True)
    background_tasks.add_task(
        run_indexing_job,
        document_id,
        saved_file_path,
        document.get("filename") or Path(saved_file_path).name,
    )

    return {
        "message": "Indexing task queued.",
        "document_id": document_id,
        "saved_file_path": saved_file_path,
    }
