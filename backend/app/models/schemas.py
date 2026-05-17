from typing import Optional

from pydantic import BaseModel, Field


class UploadStoredResponse(BaseModel):
    message: str
    document_id: str
    filename: str
    total_pages: int
    extracted_pages_count: int
    total_chunks: int
    stored_chunks: int


class SearchRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    match_count: int = Field(default=5, ge=1, le=10)


class AskRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    match_count: int = Field(default=5, ge=1, le=10)
    fast_mode: bool = False
