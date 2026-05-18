import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.services.document_service import create_uploaded_document, update_document
from app.services.indexing_jobs import register_document_file, run_indexing_job

router = APIRouter(prefix="/upload", tags=["Upload"])
UPLOAD_DIR = Path("uploads")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024
logger = logging.getLogger(__name__)


@router.post("")
@router.post("/pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    is_pdf_content = file.content_type == "application/pdf"
    is_pdf_name = (file.filename or "").lower().endswith(".pdf")

    if not is_pdf_content and not is_pdf_name:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "uploaded.pdf").name
    file_path = UPLOAD_DIR / f"{uuid4()}_{safe_filename}"
    upload_start_time = time.perf_counter()

    try:
        print("Upload received", safe_filename, flush=True)
        bytes_written = 0
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "PDF is too large for this deployment. "
                            f"Upload a file up to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB "
                            "or split the PDF into smaller parts."
                        ),
                    )
                buffer.write(chunk)
        print("PDF saved", str(file_path), flush=True)
        print("FILE EXISTS:", os.path.exists(str(file_path)), flush=True)

        if file_path.stat().st_size == 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

        document_id = create_uploaded_document(filename=safe_filename)
        print("Document row created", document_id, flush=True)
        update_document(document_id, {"status": "queued"})
        register_document_file(document_id, str(file_path))
        print("ADDING BACKGROUND INDEXING TASK", document_id, str(file_path), flush=True)

        background_tasks.add_task(
            run_indexing_job,
            document_id,
            str(file_path),
            safe_filename,
        )

        logger.info(
            "[FastRAG] Upload accepted in %.2f seconds: %s",
            time.perf_counter() - upload_start_time,
            safe_filename,
        )

        return {
            "message": "PDF uploaded. Processing started.",
            "document_id": document_id,
            "filename": safe_filename,
            "status": "queued",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {exc}") from exc
    finally:
        await file.close()
