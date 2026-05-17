import logging
import shutil
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.services.document_service import create_uploaded_document, update_document
from app.services.pdf_processing_service import process_pdf_document

router = APIRouter(prefix="/upload", tags=["Upload"])
UPLOAD_DIR = Path("uploads")
logger = logging.getLogger(__name__)


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
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_path.stat().st_size == 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

        document_id = create_uploaded_document(filename=safe_filename)
        update_document(document_id, {"status": "processing"})

        background_tasks.add_task(
            process_pdf_document,
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
            "status": "processing",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {exc}") from exc
    finally:
        await file.close()
