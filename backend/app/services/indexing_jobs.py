import os
import traceback
from pathlib import Path

from app.services.document_service import get_document, mark_document_failed
from app.services.pdf_processing_service import process_pdf_document

UPLOAD_DIR = Path("uploads")
DOCUMENT_FILE_PATHS: dict[str, str] = {}


def register_document_file(document_id: str, saved_file_path: str) -> None:
    DOCUMENT_FILE_PATHS[document_id] = saved_file_path


def find_saved_file_path(document_id: str) -> str | None:
    saved_file_path = DOCUMENT_FILE_PATHS.get(document_id)
    if saved_file_path and os.path.exists(saved_file_path):
        return saved_file_path

    document = get_document(document_id)
    filename = (document or {}).get("filename")
    if not filename:
        return None

    matches = sorted(
        UPLOAD_DIR.glob(f"*_{Path(filename).name}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        return None

    return str(matches[0])


def run_indexing_job(document_id: str, saved_file_path: str, filename: str | None = None) -> None:
    print("BACKGROUND INDEXING STARTED", document_id, saved_file_path, flush=True)
    print("FILE EXISTS:", os.path.exists(saved_file_path), flush=True)

    try:
        if not os.path.exists(saved_file_path):
            raise FileNotFoundError(saved_file_path)

        process_pdf_document(
            document_id=document_id,
            file_path=saved_file_path,
            filename=filename or Path(saved_file_path).name,
        )
    except Exception as exc:
        traceback.print_exc()
        mark_document_failed(document_id, str(exc))
