# StudyRAG / FastRAG Backend

StudyRAG is a Phase 1 FastAPI backend for uploading PDFs, extracting page text, chunking content, creating local embeddings, storing vectors in Supabase PostgreSQL with pgvector, retrieving relevant chunks, and generating answers with Groq.

## Features

- `GET /` health check
- `POST /upload/pdf` PDF upload, extraction, chunking, embedding, and storage
- `POST /ask` question answering with optional `document_id` filtering
- Page-aware sources in answers
- Local embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- Supabase pgvector retrieval through an RPC function

## Project Structure

```text
app/main.py
app/routes/upload.py
app/routes/ask.py
app/services/pdf_service.py
app/services/chunking_service.py
app/services/embedding_service.py
app/services/groq_service.py
app/services/rag_service.py
app/db/supabase_client.py
app/models/schemas.py
requirements.txt
.env.example
README.md
```

## Supabase SQL

Run this in the Supabase SQL Editor before starting the API.

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  total_pages int,
  uploaded_at timestamp with time zone default now()
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  chunk_text text not null,
  page_number int not null,
  chunk_index int not null,
  embedding vector(384),
  created_at timestamp with time zone default now()
);

create index if not exists document_chunks_embedding_idx
on document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function match_document_chunks(
  query_embedding vector(384),
  match_count int default 5,
  filter_document_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  chunk_text text,
  page_number int,
  chunk_index int,
  similarity float
)
language sql
stable
as $$
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.chunk_text,
    document_chunks.page_number,
    document_chunks.chunk_index,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where filter_document_id is null
     or document_chunks.document_id = filter_document_id
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;
```

## Environment Setup

Create a `.env` file:

```bash
cp .env.example .env
```

Fill in:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_KEY=your-supabase-publishable-or-anon-key
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
```

Use the Supabase service role key for backend-only development when possible. If you use `SUPABASE_KEY` instead, make sure your Supabase row level security policies allow the required `documents`, `document_chunks`, and RPC operations during development.

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Test with Swagger

1. Start the API with `uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/docs`.
3. Run `GET /` and confirm:

```json
{
  "message": "StudyRAG backend is running"
}
```

4. Run `POST /upload/pdf`.
5. Choose a PDF file and execute.
6. Copy the returned `document_id`.
7. Run `POST /ask` with:

```json
{
  "question": "Explain deadlock prevention",
  "document_id": "paste-document-id-here"
}
```

You can omit `document_id` to search across all uploaded PDFs.

## Test with Postman

### Health Check

- Method: `GET`
- URL: `http://127.0.0.1:8000/`

### Upload PDF

- Method: `POST`
- URL: `http://127.0.0.1:8000/upload/pdf`
- Body: `form-data`
- Key: `file`
- Type: `File`
- Value: select a PDF

Expected response:

```json
{
  "document_id": "uuid",
  "filename": "notes.pdf",
  "total_pages": 12,
  "total_chunks": 45
}
```

### Ask Question

- Method: `POST`
- URL: `http://127.0.0.1:8000/ask`
- Body: `raw` JSON

```json
{
  "question": "Explain deadlock prevention",
  "document_id": "optional-document-uuid"
}
```

Expected response:

```json
{
  "answer": "...",
  "sources": [
    {
      "document_id": "...",
      "page_number": 1,
      "chunk_index": 0,
      "similarity": 0.82
    }
  ],
  "retrieved_chunks": [
    {
      "document_id": "...",
      "page_number": 1,
      "chunk_index": 0,
      "similarity": 0.82,
      "chunk_text": "..."
    }
  ]
}
```

## Notes

- First embedding call downloads the `all-MiniLM-L6-v2` model, so it can take a little longer.
- Empty PDF pages are skipped safely.
- Chunks are about 900 characters with 180 characters of overlap.
- The backend loads secrets from `.env`; API keys are never hardcoded.
