from functools import lru_cache

from fastapi import HTTPException

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


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


def generate_embeddings_for_chunks(chunks: list[dict]) -> list[dict]:
    try:
        valid_chunks = [
            {**chunk, "chunk_text": chunk.get("chunk_text", "").strip()}
            for chunk in chunks
            if chunk.get("chunk_text", "").strip()
        ]

        if not valid_chunks:
            return []

        model = get_embedding_model()
        embeddings = model.encode([chunk["chunk_text"] for chunk in valid_chunks])

        return [
            {
                **chunk,
                "embedding": embedding.tolist(),
            }
            for chunk, embedding in zip(valid_chunks, embeddings, strict=True)
        ]

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings for chunks: {exc}",
        ) from exc
