import logging
import os
import time

import fitz

from app.services.chunking_service import chunk_page_text
from app.services.document_service import (
    batch_insert_chunks,
    build_chunk_rows,
    mark_document_failed,
    update_document,
    utc_now,
)
from app.services.embedding_service import generate_embeddings_for_chunks
from app.services.pdf_service import OCR_REQUIRED_MESSAGE, extract_text_from_page

logger = logging.getLogger(__name__)
MAX_INDEX_PAGES = int(os.getenv("MAX_INDEX_PAGES", "80"))
MAX_LARGE_FILE_INDEX_PAGES = int(os.getenv("MAX_LARGE_FILE_INDEX_PAGES", "2"))
LARGE_FILE_BYTES = int(os.getenv("LARGE_FILE_MB", "100")) * 1024 * 1024
MAX_INDEX_CHUNKS = int(os.getenv("MAX_INDEX_CHUNKS", "250"))
MAX_INDEX_SECONDS = int(os.getenv("MAX_INDEX_SECONDS", "60"))


def process_pdf_document(document_id: str, file_path: str, filename: str) -> None:
    started_at = time.perf_counter()
    chunks_created = 0
    chunks_inserted = 0
    text_pages_count = 0
    ocr_pages_count = 0
    next_chunk_index = 0
    pages_to_index = 0

    try:
        logger.info("[FastRAG] Background indexing started: %s", filename)
        update_document(
            document_id,
            {
                "status": "processing",
                "error_message": None,
                "processed_pages": 0,
                "total_chunks": 0,
            },
        )

        with fitz.open(file_path) as document:
            source_total_pages = document.page_count
            max_pages_for_file = (
                MAX_LARGE_FILE_INDEX_PAGES
                if os.path.getsize(file_path) > LARGE_FILE_BYTES
                else MAX_INDEX_PAGES
            )
            pages_to_index = min(source_total_pages, max(max_pages_for_file, 1))
            update_document(document_id, {"total_pages": pages_to_index})
            logger.info(
                "[FastRAG] total_pages=%s pages_to_index=%s filename=%s",
                source_total_pages,
                pages_to_index,
                filename,
            )

            for page_index in range(pages_to_index):
                if time.perf_counter() - started_at > MAX_INDEX_SECONDS:
                    logger.warning(
                        "[FastRAG] indexing time limit reached after %s pages: %s",
                        page_index,
                        filename,
                    )
                    break

                if chunks_inserted >= MAX_INDEX_CHUNKS:
                    logger.info(
                        "[FastRAG] indexing chunk limit reached at %s chunks: %s",
                        chunks_inserted,
                        filename,
                    )
                    break

                page_number = page_index + 1
                page = document.load_page(page_index)
                extracted_page = extract_text_from_page(page, page_number)
                page_text = extracted_page["text"]
                extraction_method = extracted_page["method"]

                if extraction_method == "ocr":
                    ocr_pages_count += 1
                else:
                    text_pages_count += 1

                logger.info(
                    "[FastRAG] Page %s extracted using %s",
                    page_number,
                    extraction_method.upper() if extraction_method == "ocr" else "text",
                )

                page_chunks = chunk_page_text(
                    page_number=page_number,
                    text=page_text,
                    start_chunk_index=next_chunk_index,
                )
                next_chunk_index += len(page_chunks)
                chunks_created += len(page_chunks)

                if page_chunks:
                    remaining_chunks = MAX_INDEX_CHUNKS - chunks_inserted
                    page_chunks = page_chunks[:remaining_chunks]
                    embedded_chunks = generate_embeddings_for_chunks(page_chunks)
                    chunk_rows = build_chunk_rows(document_id, embedded_chunks)
                    chunks_inserted += batch_insert_chunks(chunk_rows)
                    logger.info("[FastRAG] Chunks inserted: %s", chunks_inserted)

                update_document(
                    document_id,
                    {
                        "processed_pages": page_number,
                        "total_chunks": chunks_inserted,
                    },
                )
                logger.info(
                    "[FastRAG] processed_pages=%s chunks_created=%s chunks_inserted=%s filename=%s",
                    page_number,
                    chunks_created,
                    chunks_inserted,
                    filename,
                )

        if chunks_inserted <= 0:
            error_message = "No readable text was found in this PDF."
            mark_document_failed(document_id, error_message)
            logger.error(
                "[FastRAG] indexing failed: %s filename=%s total_pages=%s text_pages=%s ocr_pages=%s chunks_created=%s chunks_inserted=%s",
                error_message,
                filename,
                pages_to_index,
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
                "error_message": None,
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
        logger.exception("[FastRAG] Background indexing failed: %s error=%s", filename, exc)
        error_message = str(exc)
        if OCR_REQUIRED_MESSAGE in error_message:
            mark_document_failed(document_id, OCR_REQUIRED_MESSAGE)
        else:
            mark_document_failed(document_id, error_message)
