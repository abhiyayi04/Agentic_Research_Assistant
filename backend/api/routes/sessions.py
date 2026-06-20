from fastapi import APIRouter

from backend.memory import redis_memory

router = APIRouter()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    entries = redis_memory.get_session(session_id)
    return {"session_id": session_id, "count": len(entries), "entries": entries}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    cleared = redis_memory.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}
