import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.graph.pipeline import pipeline

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


@router.post("/query")
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    session_id = req.session_id or str(uuid.uuid4())

    initial_state = {
        "query": req.question,
        "session_id": session_id,
        "sub_questions": [],
        "retrieved_context": [],
        "answer": "",
        "citations": [],
        "sources": [],
        "critique": "",
        "iteration": 0,
        "critic_scores": {},
        "cache_hit": False,
    }
    result = await asyncio.to_thread(pipeline.invoke, initial_state)
    return {
        "answer": result["answer"],
        "citations": result.get("citations", []),
        "sources": result["sources"],
        "sub_questions": result.get("sub_questions", []),
        "critic_scores": result.get("critic_scores", {}),
        "iterations": result.get("iteration", 1),
        "session_id": session_id,
        "cache_hit": result.get("cache_hit", False),
    }
