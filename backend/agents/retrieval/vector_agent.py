import os

from qdrant_client import QdrantClient

from backend.ingestion.embedder import embed_texts
from backend.ingestion.indexer import COLLECTION


def _qdrant() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
    )


def retrieve(sub_questions: list[dict], top_k: int = 3) -> list[dict]:
    mine = [q for q in sub_questions if q["agent"] == "vector"]
    if not mine:
        return []

    client = _qdrant()
    results: list[dict] = []
    for q in mine:
        vector = embed_texts([q["question"]])[0]
        response = client.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        for r in response.points:
            results.append({
                "agent": "vector",
                "question": q["question"],
                "text": r.payload.get("text", ""),
                "source": r.payload.get("source", "unknown"),
                "score": r.score,
            })
    return results
