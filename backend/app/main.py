import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ask import router as ask_router
from app.routes.documents import router as documents_router
from app.routes.search import router as search_router
from app.routes.upload import router as upload_router
from app.services.embedding_service import get_embedding_model

logging.basicConfig(level=logging.INFO)

LOCAL_FRONTEND_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


app = FastAPI(
    title="StudyRAG API",
    description="Phase 1 backend for uploading PDFs, retrieving relevant chunks, and answering questions with Groq.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def warm_embedding_model():
    get_embedding_model()


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


app.include_router(upload_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
