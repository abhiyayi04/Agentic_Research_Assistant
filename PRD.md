# Product Requirements Document (PRD)
## ContextPilot — Multi-Agent Research Assistant

---

## 1. Problem Statement

### 1.1 The Problem
Knowledge workers and researchers spend a significant portion of their time manually searching through documents, databases, and the web to answer complex analytical questions. Traditional search tools are keyword-based and return raw results — they do not synthesize, reason, or validate answers. Basic RAG (Retrieval-Augmented Generation) systems improve on this but are fundamentally limited: they retrieve once, answer once, and have no mechanism to catch poor quality or incomplete answers.

The core gaps in existing solutions:
- Single-pass retrieval misses nuanced, multi-faceted questions that require decomposition
- No self-correction — if the first retrieval is poor, the answer is poor
- No memory — every session starts from zero, repeating the same retrievals
- No cross-source reasoning — answers are siloed to one data source at a time
- No observability — there is no way to measure whether the system is actually working well

### 1.2 The Solution
ContextPilot is a multi-agent research assistant built for researchers, analysts, and business users who work with large document collections and need synthesized answers across structured and unstructured data. Instead of a single retrieval-answer loop, ContextPilot uses a coordinated system of specialized AI agents that decompose complex questions, retrieve from multiple sources in parallel, synthesize and validate answers, and self-correct when quality is insufficient — all while maintaining session memory and full observability.

---

## 2. Goals

- Build a production-quality agentic RAG system that demonstrates multi-agent orchestration
- Achieve measurable retrieval quality and answer faithfulness via LangSmith evaluation
- Demonstrate stateful, memory-aware agent behavior across multi-turn sessions
- Showcase full observability across all agent nodes and retrieval pipelines

---

## 3. Functional Requirements

### 3.1 Document Ingestion
- Accept PDF and plain text file uploads via the React frontend
- Chunk documents using semantic chunking strategy (not fixed-size)
- Generate embeddings and store in Qdrant vector database
- Extract structured tabular data into MySQL for SQL agent access
- Return ingestion confirmation with chunk count and indexing status

### 3.2 Planner Agent
- Accept raw user query as input
- Decompose query into 2–4 focused sub-questions
- Determine which retrieval tools are required for each sub-question
- Check Redis session memory before planning — reuse prior retrieved context if available
- Output a structured execution plan for the retrieval agents

### 3.3 Retrieval Agents (Parallel Execution)
- **Vector Agent:** Perform semantic search over Qdrant, return top-k chunks with source metadata
- **SQL Agent:** Generate and execute SQL queries against MySQL, return structured results
- **Web Agent:** Query Tavily API for real-time web results, return summarized findings
- All three agents run in parallel via LangGraph's parallel node execution
- Each agent returns results with source attribution for citation generation

### 3.4 Synthesis Agent
- Receive all retrieved context from parallel retrieval agents
- Merge and deduplicate overlapping information
- Generate a coherent, well-structured answer
- Attach inline citations mapping each claim to its source document/URL/table
- Output structured response: answer text + citations list + confidence signal

### 3.5 Critic Agent
- Evaluate the synthesized answer on three dimensions:
  - **Faithfulness:** Is every claim grounded in retrieved sources?
  - **Completeness:** Were all sub-questions from the planner addressed?
  - **Confidence:** How certain is the system in its answer?
- If any dimension falls below threshold, return a critique and trigger re-planning
- If all dimensions pass, approve the answer for delivery
- Log all evaluation scores to LangSmith

### 3.6 Memory Layer
- Store query-answer pairs in Redis with session-scoped keys
- TTL of 1 hour per session (configurable)
- Planner agent reads memory before dispatching retrieval
- On cache hit, skip retrieval and synthesize from memory
- Log memory hit/miss rates for observability

### 3.7 MCP Integration
- Expose ContextPilot tools via Model Context Protocol server
- Allow external MCP-compatible clients to invoke the agent pipeline
- Tools exposed: ingest_document, run_query, get_session_memory, clear_session

### 3.8 Observability
- Instrument all agent nodes with LangSmith tracing
- Track per-node: latency, token usage, retrieval scores, faithfulness, citation accuracy
- Expose metrics endpoint for Prometheus scraping
- Frontend dashboard showing: query history, agent traces, evaluation scores, memory hit rate

### 3.9 API Layer
- RESTful API via FastAPI
- Endpoints:
  - `POST /ingest` — upload and index a document
  - `POST /query` — submit a research question
  - `GET /sessions/{session_id}` — retrieve session history
  - `DELETE /sessions/{session_id}` — clear session memory
  - `GET /health` — service health check
  - `GET /metrics` — Prometheus metrics

### 3.10 CI/CD
- GitHub Actions pipeline triggered on every PR and merge to main
- PR checks: unit tests, linting, Docker build validation
- On merge: full test suite, Docker image build and push, deployment

---

## 4. Non-Functional Requirements

- Query response time (p95) — < 15 seconds end-to-end
- API availability — 99% uptime in local/dev environment
- Concurrent sessions supported — ≥ 10 simultaneous users
- Memory footprint — < 4GB RAM in Docker Compose setup
- Document ingestion time — < 30 seconds per 50-page PDF

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│         (Upload UI | Chat UI | Dashboard)            │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────┐
│                  FastAPI Backend                      │
│              (REST API + MCP Server)                 │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│            LangGraph Agent Orchestrator              │
│                                                      │
│  ┌─────────────┐         ┌──────────────────────┐   │
│  │   Planner   │────────▶│   Retrieval Layer    │   │
│  │    Agent    │         │  ┌────────────────┐  │   │
│  └─────────────┘         │  │  Vector Agent  │  │   │
│         ▲                │  ├────────────────┤  │   │
│         │ re-plan        │  │   SQL Agent    │  │   │
│  ┌──────┴──────┐         │  ├────────────────┤  │   │
│  │   Critic    │         │  │   Web Agent    │  │   │
│  │    Agent    │         │  └────────────────┘  │   │
│  └──────┬──────┘         └──────────┬───────────┘   │
│         │ evaluate                  │ context        │
│  ┌──────▼──────┐◀──────────────────┘               │
│  │  Synthesis  │                                     │
│  │    Agent    │                                     │
│  └─────────────┘                                     │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│    Qdrant    │ │    MySQL    │ │   Redis    │
│ Vector Store │ │ Struct Data │ │  Memory   │
└──────────────┘ └─────────────┘ └────────────┘
                        │
                ┌───────▼──────┐
                │  LangSmith   │
                │ Observability│
                └──────────────┘
```

### 5.2 Agent Flow

```
User Query
     │
     ▼
Planner Agent ──── checks Redis memory ────▶ Cache Hit? ──Yes──▶ Skip to Synthesis
     │ No
     ▼
Decompose into sub-questions
     │
     ▼
┌────────────────────────────────┐
│     Parallel Retrieval         │
│  Vector │ SQL │ Web (Tavily)   │
└────────────────┬───────────────┘
                 │ all results
                 ▼
          Synthesis Agent
          (merge + cite)
                 │
                 ▼
           Critic Agent
     ┌─────────────────────┐
     │ Faithfulness score  │
     │ Completeness score  │
     │ Confidence score    │
     └──────────┬──────────┘
                │
         Pass threshold?
        /              \
      Yes               No
       │                 │
       ▼                 ▼
  Deliver Answer    Re-plan with
  with Citations    Critique Feedback
```

### 5.3 Data Flow

**Ingestion Flow:**
```
File Upload ──▶ FastAPI /ingest ──▶ Chunk & Embed ──▶ Qdrant (vectors)
                                 └──▶ Extract Tables ──▶ MySQL (structured)
```

**Query Flow:**
```
POST /query ──▶ FastAPI ──▶ LangGraph Orchestrator ──▶ Agent Pipeline
                                                           │
                                              LangSmith Trace ◀──── all nodes
                                                           │
                                              FastAPI response ──▶ React UI
```

---

## 6. Tech Stack

- **Frontend** — React (Chat UI, file upload, observability dashboard)
- **Backend** — FastAPI / Python (REST API, MCP server, request routing)
- **Agent Orchestration** — LangGraph (multi-agent workflow definition and execution)
- **LLM Framework** — LangChain (tool definitions, prompt templates, chain utilities)
- **LLM Provider** — OpenAI GPT-4o (planner, synthesis, critic, and SQL agent reasoning)
- **Vector Database** — Qdrant (semantic document storage and retrieval)
- **Structured Database** — MySQL (tabular data storage for SQL agent)
- **Memory Layer** — Redis (session-scoped episodic memory with TTL)
- **Web Search** — Tavily API (real-time web retrieval for web agent)
- **Observability** — LangSmith (agent tracing, evaluation scoring, latency tracking)
- **Metrics** — Prometheus + Grafana (infrastructure and API metrics dashboard)
- **Containerization** — Docker + Docker Compose (local development and deployment)
- **CI/CD** — GitHub Actions (automated testing, build, and deployment pipeline)
- **Protocol** — MCP / Model Context Protocol (external agent interoperability)

---

## 7. Project Structure

```
contextpilot/
├── backend/
│   ├── agents/
│   │   ├── planner.py          # Planner agent
│   │   ├── retrieval/
│   │   │   ├── vector_agent.py # Qdrant semantic search
│   │   │   ├── sql_agent.py    # MySQL structured queries
│   │   │   └── web_agent.py    # Tavily web search
│   │   ├── synthesis.py        # Synthesis agent
│   │   └── critic.py           # Critic agent
│   ├── graph/
│   │   └── pipeline.py         # LangGraph workflow definition
│   ├── memory/
│   │   └── redis_memory.py     # Redis session memory layer
│   ├── ingestion/
│   │   ├── chunker.py          # Semantic document chunking
│   │   ├── embedder.py         # Embedding generation
│   │   └── indexer.py          # Qdrant + MySQL indexing
│   ├── api/
│   │   ├── routes/
│   │   │   ├── ingest.py       # /ingest endpoint
│   │   │   ├── query.py        # /query endpoint
│   │   │   └── sessions.py     # /sessions endpoints
│   │   └── main.py             # FastAPI app entry point
│   ├── mcp/
│   │   └── server.py           # MCP server definition
│   └── observability/
│       └── langsmith.py        # LangSmith instrumentation
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface/  # Query input + answer display
│   │   │   ├── FileUpload/     # Document upload component
│   │   │   └── Dashboard/      # Observability dashboard
│   │   └── App.jsx
│   └── package.json
├── docker/
│   ├── docker-compose.yml      # All services: backend, qdrant, mysql, redis
│   └── Dockerfile              # Backend container
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions pipeline
├── tests/
│   ├── unit/                   # Unit tests per agent
│   └── integration/            # End-to-end pipeline tests
├── PRD.md                      # This document
└── README.md
```

---

## 8. Build Phases

### Phase 1 — Foundation
- Set up Docker Compose with FastAPI, Qdrant, MySQL, Redis
- Build document ingestion pipeline (chunking, embedding, indexing)
- Build basic single-agent RAG (no orchestration yet)
- Verify end-to-end: upload PDF → ask question → get answer

### Phase 2 — Multi-Agent System
- Build Planner agent with query decomposition
- Build all three Retrieval agents (vector, SQL, web)
- Wire parallel retrieval in LangGraph
- Build Synthesis agent with citation attachment

### Phase 3 — Critic Loop + Memory
- Build Critic agent with faithfulness/completeness/confidence scoring
- Implement re-planning feedback loop
- Add Redis memory layer to Planner
- Test multi-turn conversations and memory hit rate

### Phase 4 — Observability, MCP & Polish
- Connect LangSmith tracing across all agent nodes
- Build React frontend (chat UI + file upload + dashboard)
- Add MCP server exposing agent tools
- Set up GitHub Actions CI/CD pipeline
- Run benchmarks and capture real metrics for resume bullets
