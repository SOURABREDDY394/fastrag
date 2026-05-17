import re

from fastapi import HTTPException


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_page_text(
    page_number: int,
    text: str,
    start_chunk_index: int = 0,
    chunk_size: int = 1500,
    overlap: int = 150,
) -> list[dict]:
    if chunk_size <= 0:
        raise HTTPException(status_code=400, detail="chunk_size must be greater than 0.")

    if overlap < 0:
        raise HTTPException(status_code=400, detail="overlap cannot be negative.")

    if overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="overlap must be smaller than chunk_size.",
        )

    page_text = clean_text(text)

    if not page_text:
        return []

    chunks = []
    chunk_index = start_chunk_index
    start = 0

    while start < len(page_text):
        end = min(start + chunk_size, len(page_text))
        chunk_text = page_text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                }
            )
            chunk_index += 1

        if end == len(page_text):
            break

        start = end - overlap

    return chunks


def chunk_pdf_pages(
    extracted_pages: list[dict],
    chunk_size: int = 1500,
    overlap: int = 150,
) -> list[dict]:
    if chunk_size <= 0:
        raise HTTPException(status_code=400, detail="chunk_size must be greater than 0.")

    if overlap < 0:
        raise HTTPException(status_code=400, detail="overlap cannot be negative.")

    if overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="overlap must be smaller than chunk_size.",
        )

    chunks = []
    chunk_index = 0

    for page in extracted_pages:
        page_number = page.get("page_number")
        page_chunks = chunk_page_text(
            page_number=page_number,
            text=page.get("text", ""),
            start_chunk_index=chunk_index,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        chunks.extend(page_chunks)
        chunk_index += len(page_chunks)

    return chunks
