import uuid

from mcp.server.fastmcp import FastMCP

from backend.ingestion.chunker import chunk_document
from backend.ingestion.embedder import embed_texts
from backend.ingestion.indexer import index_chunks, log_ingestion
from backend.graph.pipeline import pipeline
from backend.memory import redis_memory

mcp = FastMCP("ContextPilot")


@mcp.tool()
def ingest_document(content: str, filename: str = "document.txt") -> dict:
    """Ingest a text document into the ContextPilot knowledge base.

    Args:
        content: The full text content of the document to ingest.
        filename: A name for the document (used for source attribution).
    """
    if not content.strip():
        return {"error": "Document content is empty"}

    chunks = chunk_document(content)
    if not chunks:
        return {"error": "Document too short to chunk"}

    embeddings = embed_texts(chunks)
    chunk_count = index_chunks(chunks, embeddings, filename)
    log_ingestion(filename, chunk_count)
    return {"filename": filename, "chunk_count": chunk_count, "status": "indexed"}


@mcp.tool()
def run_query(question: str, session_id: str = "") -> dict:
    """Submit a research question to the multi-agent ContextPilot pipeline.

    Args:
        question: The research question to answer.
        session_id: Optional session ID for memory continuity across calls.
                    A new ID is generated if not provided.
    """
    if not question.strip():
        return {"error": "Question cannot be empty"}

    sid = session_id.strip() or str(uuid.uuid4())

    initial_state = {
        "query": question,
        "session_id": sid,
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
    result = pipeline.invoke(initial_state)
    return {
        "answer": result["answer"],
        "citations": result.get("citations", []),
        "sources": result.get("sources", []),
        "session_id": sid,
        "cache_hit": result.get("cache_hit", False),
        "critic_scores": result.get("critic_scores", {}),
        "iterations": result.get("iteration", 1),
    }


@mcp.tool()
def get_session_memory(session_id: str) -> dict:
    """Retrieve all cached query-answer pairs for a session.

    Args:
        session_id: The session ID whose memory to retrieve.
    """
    entries = redis_memory.get_session(session_id)
    return {"session_id": session_id, "count": len(entries), "entries": entries}


@mcp.tool()
def clear_session(session_id: str) -> dict:
    """Clear all cached memory for a session.

    Args:
        session_id: The session ID to clear.
    """
    cleared = redis_memory.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}


if __name__ == "__main__":
    mcp.run()
