import gc
import logging
import os
import time
import traceback

import fitz

from app.services.chunking_service import chunk_page_text
from app.services.document_service import (
    batch_insert_chunks,
    build_chunk_rows,
    get_document,
    mark_document_failed,
    update_document,
    utc_now,
)
from app.services.embedding_service import generate_embeddings_for_chunks
from app.services.pdf_service import OCR_REQUIRED_MESSAGE, extract_text_from_page

logger = logging.getLogger(__name__)
PDF_BATCH_SIZE = int(os.getenv("PDF_BATCH_SIZE", "5"))
MAX_INDEX_CHUNKS = int(os.getenv("MAX_INDEX_CHUNKS", "0"))


def get_failed_pages_message(failed_pages: list[int]) -> str | None:
    if not failed_pages:
        return None
    return f"Some pages failed: {failed_pages[:20]}"


def process_pdf_document(document_id: str, file_path: str, filename: str) -> None:
    print("BACKGROUND INDEXING STARTED", document_id, file_path, flush=True)
    print("FILE EXISTS:", os.path.exists(file_path), flush=True)
    started_at = time.perf_counter()
    chunks_created = 0
    chunks_inserted = 0
    text_pages_count = 0
    ocr_pages_count = 0
    next_chunk_index = 0
    failed_pages = []

    try:
        existing_document = get_document(document_id) or {}
        chunks_inserted = existing_document.get("total_chunks") or 0
        next_chunk_index = chunks_inserted
        print("Starting indexing", {"document_id": document_id, "filename": filename}, flush=True)
        logger.info("[FastRAG] Background indexing started: %s", filename)
        update_document(
            document_id,
            {
                "status": "processing",
                "error_message": None,
                "total_chunks": chunks_inserted,
            },
        )

        with fitz.open(file_path) as document:
            total_pages = document.page_count
            start_page_index = min(
                max(existing_document.get("processed_pages") or 0, 0),
                total_pages,
            )
            update_document(document_id, {"total_pages": total_pages})
            logger.info(
                "[FastRAG] total_pages=%s batch_size=%s start_page=%s filename=%s",
                total_pages,
                PDF_BATCH_SIZE,
                start_page_index + 1,
                filename,
            )

            for batch_start in range(start_page_index, total_pages, PDF_BATCH_SIZE):
                if MAX_INDEX_CHUNKS > 0 and chunks_inserted >= MAX_INDEX_CHUNKS:
                    logger.info(
                        "[FastRAG] indexing chunk limit reached at %s chunks: %s",
                        chunks_inserted,
                        filename,
                    )
                    break

                batch_end = min(batch_start + PDF_BATCH_SIZE, total_pages)
                print(
                    f"Processing pages {batch_start + 1}-{batch_end}",
                    flush=True,
                )
                batch_chunks = []
                processed_page_count = batch_start

                for page_index in range(batch_start, batch_end):
                    page_number = page_index + 1
                    processed_page_count = page_number
                    try:
                        page = document.load_page(page_index)
                        extracted_page = extract_text_from_page(page, page_number)
                        page_text = extracted_page["text"]
                        extraction_method = extracted_page["method"]
                        print(
                            "Extracted text length",
                            {
                                "page_number": page_number,
                                "method": extraction_method,
                                "text_length": len(page_text),
                            },
                            flush=True,
                        )
                        del page
                    except Exception as exc:
                        failed_pages.append(page_number)
                        logger.exception(
                            "[FastRAG] Page %s failed; continuing: %s",
                            page_number,
                            exc,
                        )
                        continue

                    if extraction_method == "ocr":
                        ocr_pages_count += 1
                    else:
                        text_pages_count += 1

                    page_chunks = chunk_page_text(
                        page_number=page_number,
                        text=page_text,
                        start_chunk_index=next_chunk_index,
                    )
                    next_chunk_index += len(page_chunks)
                    chunks_created += len(page_chunks)
                    batch_chunks.extend(page_chunks)
                    del page_text, page_chunks

                print("Chunks created for this batch", len(batch_chunks), flush=True)

                if batch_chunks:
                    if MAX_INDEX_CHUNKS > 0:
                        remaining_chunks = MAX_INDEX_CHUNKS - chunks_inserted
                        batch_chunks = batch_chunks[:remaining_chunks]
                    embedded_chunks = generate_embeddings_for_chunks(batch_chunks)
                    chunk_rows = build_chunk_rows(document_id, embedded_chunks)
                    inserted_count = batch_insert_chunks(chunk_rows)
                    chunks_inserted += inserted_count
                    print("Inserted chunks count", inserted_count, flush=True)
                    logger.info("[FastRAG] Chunks inserted: %s", chunks_inserted)

                update_document(
                    document_id,
                    {
                        "processed_pages": processed_page_count,
                        "total_chunks": chunks_inserted,
                        "error_message": get_failed_pages_message(failed_pages),
                    },
                )
                print("Progress updated", processed_page_count, chunks_inserted, flush=True)
                logger.info(
                    "[FastRAG] processed_pages=%s chunks_created=%s chunks_inserted=%s filename=%s",
                    processed_page_count,
                    chunks_created,
                    chunks_inserted,
                    filename,
                )
                del batch_chunks
                if "embedded_chunks" in locals():
                    del embedded_chunks
                if "chunk_rows" in locals():
                    del chunk_rows
                gc.collect()
                print("Memory cleanup done", flush=True)

        if chunks_inserted <= 0:
            error_message = "No readable text was found in this PDF."
            mark_document_failed(document_id, error_message)
            logger.error(
                "[FastRAG] indexing failed: %s filename=%s total_pages=%s text_pages=%s ocr_pages=%s chunks_created=%s chunks_inserted=%s",
                error_message,
                filename,
                total_pages,
                text_pages_count,
                ocr_pages_count,
                chunks_created,
                chunks_inserted,
            )
            return

        update_document(
            document_id,
            {
                "status": "ready",
                "total_chunks": chunks_inserted,
                "processed_at": utc_now(),
                "error_message": get_failed_pages_message(failed_pages),
            },
        )
        logger.info(
            "[FastRAG] Background indexing ready: %s text_pages=%s ocr_pages=%s chunks_created=%s chunks_inserted=%s",
            filename,
            text_pages_count,
            ocr_pages_count,
            chunks_created,
            chunks_inserted,
        )
    except Exception as exc:
        traceback.print_exc()
        logger.exception("[FastRAG] Background indexing failed: %s error=%s", filename, exc)
        error_message = str(exc)
        if OCR_REQUIRED_MESSAGE in error_message:
            mark_document_failed(document_id, OCR_REQUIRED_MESSAGE)
        else:
            mark_document_failed(document_id, error_message)
