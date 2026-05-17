import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ask import router as ask_router
from app.routes.documents import router as documents_router
from app.routes.search import router as search_router
from app.routes.upload import router as upload_router

logging.basicConfig(level=logging.INFO)

DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://frontend-beta-nine-exumkm1408.vercel.app",
    "https://frontend-76ihbafug-sourabreddy394s-projects.vercel.app",
]


def get_allowed_origins() -> list[str]:
    configured_origins = os.getenv("FRONTEND_ORIGINS", "")
    origins = [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    return origins or DEFAULT_ALLOWED_ORIGINS


app = FastAPI(
    title="StudyRAG API",
    description="Phase 1 backend for uploading PDFs, retrieving relevant chunks, and answering questions with Groq.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "StudyRAG backend is running"}


app.include_router(upload_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
