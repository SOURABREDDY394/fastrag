from fastapi import APIRouter, HTTPException

from app.services.document_service import get_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{document_id}/status")
def get_document_status(document_id: str):
    document = get_document(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "document_id": document["id"],
        "filename": document.get("filename"),
        "status": document.get("status"),
        "total_pages": document.get("total_pages") or 0,
        "processed_pages": document.get("processed_pages") or 0,
        "total_chunks": document.get("total_chunks") or 0,
        "error_message": document.get("error_message"),
    }
