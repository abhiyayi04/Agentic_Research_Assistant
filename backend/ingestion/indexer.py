import os
import time
import uuid

import pymysql
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION = "documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


def _qdrant() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
    )


def _mysql():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "contextpilot"),
        password=os.getenv("MYSQL_PASSWORD", "contextpilot"),
        database=os.getenv("MYSQL_DB", "contextpilot"),
        autocommit=True,
    )


def ensure_qdrant_collection():
    client = _qdrant()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION in existing:
        info = client.get_collection(COLLECTION)
        if info.config.params.vectors.size != VECTOR_SIZE:
            client.delete_collection(COLLECTION)
        else:
            return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def ensure_mysql_schema(retries: int = 6, delay: float = 5.0):
    for attempt in range(retries):
        try:
            conn = _mysql()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ingested_documents (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        chunk_count INT NOT NULL,
                        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.close()
            return
        except Exception as exc:
            if attempt == retries - 1:
                print(f"Warning: MySQL schema init failed after {retries} attempts: {exc}")
            else:
                time.sleep(delay)


def index_chunks(
    chunks: list[str], embeddings: list[list[float]], doc_name: str
) -> int:
    client = _qdrant()
    ensure_qdrant_collection()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload={"text": chunk, "source": doc_name, "chunk_index": i},
        )
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def log_ingestion(filename: str, chunk_count: int):
    try:
        conn = _mysql()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ingested_documents (filename, chunk_count) VALUES (%s, %s)",
                (filename, chunk_count),
            )
        conn.close()
    except Exception as exc:
        print(f"Warning: could not log ingestion to MySQL: {exc}")
