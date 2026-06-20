import hashlib
import json
import os

import redis as redis_lib

_client: redis_lib.Redis | None = None
SESSION_TTL = int(os.getenv("SESSION_TTL", 3600))


def _get_client() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
    return _client


def _key(session_id: str, query: str) -> str:
    q_hash = hashlib.md5(query.strip().lower().encode()).hexdigest()[:12]
    return f"cp:session:{session_id}:{q_hash}"


def get(session_id: str, query: str) -> dict | None:
    try:
        val = _get_client().get(_key(session_id, query))
        return json.loads(val) if val else None
    except Exception:
        return None


def save(session_id: str, query: str, result: dict) -> None:
    try:
        _get_client().setex(_key(session_id, query), SESSION_TTL, json.dumps(result))
    except Exception:
        pass


def get_session(session_id: str) -> list[dict]:
    try:
        client = _get_client()
        keys = client.keys(f"cp:session:{session_id}:*")
        entries = []
        for key in keys:
            val = client.get(key)
            if val:
                entries.append({
                    "key": key,
                    "ttl_seconds": client.ttl(key),
                    "data": json.loads(val),
                })
        return entries
    except Exception:
        return []


def clear_session(session_id: str) -> int:
    try:
        client = _get_client()
        keys = client.keys(f"cp:session:{session_id}:*")
        return client.delete(*keys) if keys else 0
    except Exception:
        return 0
