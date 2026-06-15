from fastapi import APIRouter

router = APIRouter()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    # Phase 3B: retrieve session history from Redis
    pass


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    # Phase 3B: clear session memory from Redis
    pass
