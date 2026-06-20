from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import ingest, query, sessions
from backend.ingestion.indexer import ensure_mysql_schema, ensure_qdrant_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_qdrant_collection()
    ensure_mysql_schema()
    yield


app = FastAPI(title="ContextPilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "contextpilot-backend"}
