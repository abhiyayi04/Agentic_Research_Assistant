import io

import pypdf
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.ingestion.chunker import chunk_document
from backend.ingestion.embedder import embed_texts
from backend.ingestion.indexer import index_chunks, log_ingestion

router = APIRouter()


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename.endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif file.filename.endswith(".txt"):
        text = content.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    chunks = chunk_document(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document too short to chunk")

    embeddings = embed_texts(chunks)
    chunk_count = index_chunks(chunks, embeddings, file.filename)
    log_ingestion(file.filename, chunk_count)

    return {"filename": file.filename, "chunk_count": chunk_count, "status": "indexed"}
