from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.rag import run as run_rag

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None  # reserved for Phase 3B memory


@router.post("/query")
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return run_rag(req.question)
