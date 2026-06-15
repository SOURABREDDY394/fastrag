import logging
import time

from fastapi import HTTPException

from app.services.document_service import get_document
from app.services.embedding_service import generate_embedding
from app.services.groq_service import generate_answer_from_context
from app.services.search_service import (
    get_document_overview_chunks,
    get_document_unit_chunks,
    search_similar_chunks_by_embedding,
)

logger = logging.getLogger(__name__)

NO_CHUNKS_MESSAGE = (
    "No relevant document chunks found. Please upload a PDF first or ask a "
    "question related to the uploaded documents."
)
MAX_MATCH_COUNT = 7
FAST_MODE_MATCH_COUNT = 3
MAX_CONTEXT_CHARS = 11000
FAST_MODE_CONTEXT_CHARS = 4500
SUMMARY_CONTEXT_CHARS = 15000
SUMMARY_SAMPLE_COUNT = 22
UNIT_CONTEXT_CHARS = 18000
UNIT_SAMPLE_COUNT = 14


def elapsed_ms(start_time: float) -> int:
    return round((time.perf_counter() - start_time) * 1000)


def build_context_from_chunks(chunks: list[dict], max_chars: int) -> str:
    context_blocks = []
    used_chars = 0

    for chunk in chunks:
        page_number = chunk.get("page_number")
        chunk_text = (chunk.get("chunk_text") or "").strip()

        if not chunk_text:
            continue

        block = f"Page {page_number}:\n{chunk_text}"
        remaining_chars = max_chars - used_chars

        if remaining_chars <= 0:
            break

        if len(block) > remaining_chars:
            block = block[:remaining_chars].rstrip()

        context_blocks.append(block)
        used_chars += len(block)

    return "\n\n---\n\n".join(context_blocks)


def build_sources_from_chunks(chunks: list[dict]) -> list[dict]:
    return [
        {
            "document_id": chunk.get("document_id"),
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk.get("chunk_index"),
            "similarity": chunk.get("similarity"),
        }
        for chunk in chunks
    ]


def build_retrieved_chunks(chunks: list[dict]) -> list[dict]:
    return [
        {
            "id": chunk.get("id"),
            "document_id": chunk.get("document_id"),
            "chunk_text": chunk.get("chunk_text"),
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk.get("chunk_index"),
            "similarity": chunk.get("similarity"),
        }
        for chunk in chunks
    ]


def log_latency(latency: dict) -> None:
    logger.info("[FastRAG] Embedding: %sms", latency["embedding_ms"])
    logger.info("[FastRAG] Retrieval: %sms", latency["retrieval_ms"])
    logger.info("[FastRAG] Context: %sms", latency["context_ms"])
    logger.info("[FastRAG] Groq: %sms", latency["generation_ms"])
    logger.info("[FastRAG] Total: %sms", latency["total_ms"])


def resolve_answer_mode(question: str, requested_mode: str) -> str:
    return requested_mode


def ask_question(
    question: str,
    document_id: str | None = None,
    match_count: int = 5,
    fast_mode: bool = False,
    answer_mode: str = "exam",
    unit_number: int | None = None,
) -> dict:
    total_start_time = time.perf_counter()
    clean_question = question.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if document_id:
        document = get_document(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        if document.get("status") != "ready" and (document.get("total_chunks") or 0) <= 0:
            latency = {
                "embedding_ms": 0,
                "retrieval_ms": 0,
                "context_ms": 0,
                "generation_ms": 0,
                "total_ms": elapsed_ms(total_start_time),
            }
            return {
                "answer": "Document is still processing. Please wait until indexing is complete.",
                "sources": [],
                "retrieved_chunks": [],
                "latency": latency,
            }

        if document.get("status") == "ready" and (document.get("total_chunks") or 0) <= 0:
            context = (
                f"Uploaded document: {document.get('filename') or 'PDF'}.\n"
                "The fast preview completed, but no searchable text chunks were extracted. "
                "The document may be scanned or image-only. Answer the user's question as a helpful study assistant, "
                "and clearly mention when the answer is general knowledge rather than grounded in extracted document text."
            )
            generation_start_time = time.perf_counter()
            answer = generate_answer_from_context(
                question=clean_question,
                context=context,
                fast_mode=True,
            )
            generation_ms = elapsed_ms(generation_start_time)
            latency = {
                "embedding_ms": 0,
                "retrieval_ms": 0,
                "context_ms": 0,
                "generation_ms": generation_ms,
                "total_ms": elapsed_ms(total_start_time),
            }
            return {
                "answer": answer,
                "sources": [],
                "retrieved_chunks": [],
                "latency": latency,
            }

    effective_answer_mode = resolve_answer_mode(clean_question, answer_mode)
    if effective_answer_mode == "unit" and unit_number is None:
        raise HTTPException(
            status_code=400,
            detail="Choose a unit number before creating unit notes.",
        )
    effective_match_count = (
        FAST_MODE_MATCH_COUNT if fast_mode else min(match_count, MAX_MATCH_COUNT)
    )
    max_context_chars = (
        SUMMARY_CONTEXT_CHARS
        if effective_answer_mode == "summary"
        else (
            UNIT_CONTEXT_CHARS
            if effective_answer_mode == "unit"
            else (FAST_MODE_CONTEXT_CHARS if fast_mode else MAX_CONTEXT_CHARS)
        )
    )

    embedding_ms = 0
    retrieval_ms = 0
    unit_page_range = None
    if effective_answer_mode == "unit":
        retrieval_start_time = time.perf_counter()
        chunks, unit_page_range = get_document_unit_chunks(
            document_id=document_id,
            unit_number=unit_number,
            sample_count=UNIT_SAMPLE_COUNT,
        )
        retrieval_ms = elapsed_ms(retrieval_start_time)
    elif effective_answer_mode == "summary":
        retrieval_start_time = time.perf_counter()
        chunks = get_document_overview_chunks(
            document_id=document_id,
            sample_count=SUMMARY_SAMPLE_COUNT,
        )
        retrieval_ms = elapsed_ms(retrieval_start_time)
    else:
        embedding_start_time = time.perf_counter()
        question_embedding = generate_embedding(clean_question)
        embedding_ms = elapsed_ms(embedding_start_time)

        retrieval_start_time = time.perf_counter()
        chunks = search_similar_chunks_by_embedding(
            query_embedding=question_embedding,
            document_id=document_id,
            match_count=effective_match_count,
        )
        retrieval_ms = elapsed_ms(retrieval_start_time)

    context_start_time = time.perf_counter()
    context = build_context_from_chunks(chunks, max_chars=max_context_chars)
    sources = build_sources_from_chunks(chunks)
    retrieved_chunks = build_retrieved_chunks(chunks)
    context_ms = elapsed_ms(context_start_time)

    if not chunks or not context:
        latency = {
            "embedding_ms": embedding_ms,
            "retrieval_ms": retrieval_ms,
            "context_ms": context_ms,
            "generation_ms": 0,
            "total_ms": elapsed_ms(total_start_time),
        }
        log_latency(latency)
        return {
            "answer": NO_CHUNKS_MESSAGE,
            "sources": [],
            "retrieved_chunks": [],
            "latency": latency,
        }

    generation_start_time = time.perf_counter()
    answer = generate_answer_from_context(
        question=clean_question,
        context=context,
        fast_mode=fast_mode and effective_answer_mode == "exam",
        answer_mode=effective_answer_mode,
        unit_number=unit_number,
        unit_page_range=unit_page_range,
    )
    generation_ms = elapsed_ms(generation_start_time)

    latency = {
        "embedding_ms": embedding_ms,
        "retrieval_ms": retrieval_ms,
        "context_ms": context_ms,
        "generation_ms": generation_ms,
        "total_ms": elapsed_ms(total_start_time),
    }
    log_latency(latency)

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": retrieved_chunks,
        "latency": latency,
        "answer_mode": effective_answer_mode,
        "unit_number": unit_number if effective_answer_mode == "unit" else None,
        "unit_page_range": unit_page_range,
    }
