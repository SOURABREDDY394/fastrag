from functools import lru_cache
import os

from fastapi import HTTPException

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "5"))


@lru_cache
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load embedding model: {exc}",
        ) from exc


def generate_embedding(text: str) -> list[float]:
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Cannot embed empty text.")

    try:
        model = get_embedding_model()
        embedding = model.encode(clean_text)
        return embedding.tolist()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding generation failed: {exc}",
        ) from exc


def generate_embeddings_for_chunks(
    chunks: list[dict],
    batch_size: int | None = None,
) -> list[dict]:
    try:
        valid_chunks = [
            {**chunk, "chunk_text": chunk.get("chunk_text", "").strip()}
            for chunk in chunks
            if chunk.get("chunk_text", "").strip()
        ]

        if not valid_chunks:
            return []

        model = get_embedding_model()
        embedded_chunks = []
        effective_batch_size = batch_size or EMBEDDING_BATCH_SIZE

        for start in range(0, len(valid_chunks), effective_batch_size):
            batch = valid_chunks[start : start + effective_batch_size]
            print("Embedding batch size", len(batch), flush=True)
            embeddings = model.encode([chunk["chunk_text"] for chunk in batch])
            embedded_chunks.extend(
                {
                    **chunk,
                    "embedding": embedding.tolist(),
                }
                for chunk, embedding in zip(batch, embeddings, strict=True)
            )

        return embedded_chunks

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings for chunks: {exc}",
        ) from exc
