import os

from openai import OpenAI
from qdrant_client import QdrantClient

from backend.ingestion.embedder import embed_texts
from backend.ingestion.indexer import COLLECTION

_openai: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


def _qdrant() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
    )


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    vector = embed_texts([query])[0]
    response = _qdrant().query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {"text": r.payload["text"], "source": r.payload["source"], "score": r.score}
        for r in response.points
    ]


def generate(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant documents found. Please ingest some documents first."

    context = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )
    response = _get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Answer the user's question using only "
                    "the provided context. Be concise and precise. If the context does not "
                    "contain enough information to answer, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def run(query: str, top_k: int = 5) -> dict:
    chunks = retrieve(query, top_k)
    answer = generate(query, chunks)
    sources = sorted({c["source"] for c in chunks})
    return {"answer": answer, "sources": sources}
