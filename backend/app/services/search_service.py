import re

from fastapi import HTTPException

from app.db.supabase_client import get_supabase_client
from app.services.embedding_service import generate_embedding


def embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def search_similar_chunks(
    question: str,
    document_id: str | None = None,
    match_count: int = 5,
) -> list[dict]:
    clean_question = question.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if match_count < 1 or match_count > 10:
        raise HTTPException(
            status_code=400,
            detail="match_count must be between 1 and 10.",
        )

    question_embedding = generate_embedding(clean_question)

    return search_similar_chunks_by_embedding(
        query_embedding=question_embedding,
        document_id=document_id,
        match_count=match_count,
    )


def search_similar_chunks_by_embedding(
    query_embedding: list[float],
    document_id: str | None = None,
    match_count: int = 5,
) -> list[dict]:
    if match_count < 1 or match_count > 10:
        raise HTTPException(
            status_code=400,
            detail="match_count must be between 1 and 10.",
        )

    supabase = get_supabase_client()

    rpc_params = {
        "query_embedding": embedding_to_pgvector(query_embedding),
        "match_count": match_count,
        "filter_document_id": document_id,
    }

    try:
        response = supabase.rpc("match_document_chunks", rpc_params).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase vector search failed: {exc}",
        ) from exc

    return response.data or []


def get_document_overview_chunks(
    document_id: str,
    sample_count: int = 15,
) -> list[dict]:
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("document_chunks")
            .select("id, document_id, chunk_text, page_number, chunk_index")
            .eq("document_id", document_id)
            .order("page_number")
            .order("chunk_index")
            .limit(1000)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase document overview retrieval failed: {exc}",
        ) from exc

    chunks = response.data or []
    if len(chunks) <= sample_count:
        return [{**chunk, "similarity": None} for chunk in chunks]

    structural_terms = ("syllabus", "contents", "unit -", "unit i", "chapter")
    structural_chunks = [
        chunk
        for chunk in chunks
        if any(
            term in (chunk.get("chunk_text") or "").lower()
            for term in structural_terms
        )
    ][:5]

    remaining_count = max(sample_count - len(structural_chunks), 1)
    evenly_spaced_chunks = []
    for index in range(remaining_count):
        position = round(index * (len(chunks) - 1) / max(remaining_count - 1, 1))
        evenly_spaced_chunks.append(chunks[position])

    selected_by_id = {
        chunk["id"]: {**chunk, "similarity": None}
        for chunk in [*structural_chunks, *evenly_spaced_chunks]
    }

    return sorted(
        selected_by_id.values(),
        key=lambda chunk: (
            chunk.get("page_number") or 0,
            chunk.get("chunk_index") or 0,
        ),
    )


def get_document_unit_chunks(
    document_id: str,
    unit_number: int,
    unit_count: int = 5,
    sample_count: int = 14,
) -> tuple[list[dict], tuple[int, int]]:
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("document_chunks")
            .select("id, document_id, chunk_text, page_number, chunk_index")
            .eq("document_id", document_id)
            .order("page_number")
            .order("chunk_index")
            .limit(1000)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase unit retrieval failed: {exc}",
        ) from exc

    chunks = response.data or []
    if not chunks:
        return [], (0, 0)

    maximum_page = max(chunk.get("page_number") or 0 for chunk in chunks)
    range_pattern = re.compile(r"(\d{1,4})\s*[-\u2013\u2014]\s*(\d{1,4})")
    detected_ranges: list[tuple[int, int]] = []
    for chunk in chunks[:20]:
        for start_text, end_text in range_pattern.findall(
            chunk.get("chunk_text") or ""
        ):
            start_page = int(start_text)
            end_page = int(end_text)
            if (
                1 <= start_page <= end_page <= maximum_page + 5
                and end_page - start_page >= 5
            ):
                detected_ranges.append((start_page, end_page))

    unique_ranges = []
    for page_range in detected_ranges:
        if page_range not in unique_ranges:
            unique_ranges.append(page_range)

    if len(unique_ranges) >= unit_count:
        unit_ranges = unique_ranges[:unit_count]
    else:
        pages_per_unit = max(maximum_page // unit_count, 1)
        unit_ranges = []
        for index in range(unit_count):
            start_page = index * pages_per_unit + 1
            end_page = (
                maximum_page
                if index == unit_count - 1
                else (index + 1) * pages_per_unit
            )
            unit_ranges.append((start_page, end_page))

    if unit_number > len(unit_ranges):
        raise HTTPException(
            status_code=400,
            detail=f"Unit {unit_number} was not found in this document.",
        )

    start_page, end_page = unit_ranges[unit_number - 1]
    unit_chunks = [
        chunk
        for chunk in chunks
        if start_page <= (chunk.get("page_number") or 0) <= end_page
    ]
    if len(unit_chunks) <= sample_count:
        sampled_chunks = unit_chunks
    else:
        sampled_chunks = []
        for index in range(sample_count):
            position = round(
                index * (len(unit_chunks) - 1) / max(sample_count - 1, 1)
            )
            sampled_chunks.append(unit_chunks[position])

    selected_by_id = {
        chunk["id"]: {**chunk, "similarity": None}
        for chunk in sampled_chunks
    }
    selected_chunks = sorted(
        selected_by_id.values(),
        key=lambda chunk: (
            chunk.get("page_number") or 0,
            chunk.get("chunk_index") or 0,
        ),
    )

    return selected_chunks, (start_page, end_page)
