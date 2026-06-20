import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents import critic, planner, synthesis
from backend.agents.retrieval import sql_agent, vector_agent, web_agent
from backend.memory import redis_memory

MAX_ITERATIONS = 2


class AgentState(TypedDict):
    query: str
    session_id: str
    sub_questions: list[dict]
    retrieved_context: Annotated[list[dict], operator.add]
    answer: str
    citations: list[dict]
    sources: list[str]
    critique: str
    iteration: int
    critic_scores: dict
    cache_hit: bool


# ── nodes ──────────────────────────────────────────────────────────────────────

def memory_check_node(state: AgentState) -> dict:
    cached = redis_memory.get(state["session_id"], state["query"])
    if cached:
        return {**cached, "cache_hit": True}
    return {"cache_hit": False}


def planner_node(state: AgentState) -> dict:
    critique = state.get("critique", "")
    iteration = state.get("iteration", 0)
    sub_questions = planner.plan(state["query"], critique)
    return {
        "sub_questions": sub_questions,
        "retrieved_context": [],   # operator.add makes this a no-op on re-plan
        "iteration": iteration + 1,
    }


def vector_node(state: AgentState) -> dict:
    return {"retrieved_context": vector_agent.retrieve(state["sub_questions"])}


def sql_node(state: AgentState) -> dict:
    return {"retrieved_context": sql_agent.retrieve(state["sub_questions"])}


def web_node(state: AgentState) -> dict:
    return {"retrieved_context": web_agent.retrieve(state["sub_questions"])}


def synthesize_node(state: AgentState) -> dict:
    context = [c for c in state["retrieved_context"] if c.get("text")]
    result = synthesis.synthesize(state["query"], context)
    sources = sorted({c["source"] for c in context})
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "sources": sources,
    }


def critic_node(state: AgentState) -> dict:
    context = [c for c in state["retrieved_context"] if c.get("text")]
    scores = critic.evaluate(
        query=state["query"],
        sub_questions=state["sub_questions"],
        context=context,
        answer=state["answer"],
    )
    return {
        "critic_scores": scores,
        "critique": scores["critique"],
    }


def finalize_node(state: AgentState) -> dict:
    redis_memory.save(
        state["session_id"],
        state["query"],
        {
            "answer": state["answer"],
            "citations": state.get("citations", []),
            "sources": state["sources"],
            "sub_questions": state["sub_questions"],
            "critic_scores": state.get("critic_scores", {}),
        },
    )
    return {}


# ── routing ────────────────────────────────────────────────────────────────────

def _route_after_memory(state: AgentState) -> str:
    return "hit" if state.get("cache_hit") else "miss"


def _route_after_critic(state: AgentState) -> str:
    scores = state.get("critic_scores", {})
    iteration = state.get("iteration", 0)
    if scores.get("passed", True) or iteration >= MAX_ITERATIONS:
        return "finalize"
    return "replan"


# ── graph ──────────────────────────────────────────────────────────────────────

def _build():
    g = StateGraph(AgentState)

    g.add_node("memory_check", memory_check_node)
    g.add_node("planner", planner_node)
    g.add_node("vector_retrieval", vector_node)
    g.add_node("sql_retrieval", sql_node)
    g.add_node("web_retrieval", web_node)
    g.add_node("synthesize", synthesize_node)
    g.add_node("critic", critic_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "memory_check")
    g.add_conditional_edges("memory_check", _route_after_memory, {"hit": END, "miss": "planner"})

    g.add_edge("planner", "vector_retrieval")
    g.add_edge("planner", "sql_retrieval")
    g.add_edge("planner", "web_retrieval")
    g.add_edge("vector_retrieval", "synthesize")
    g.add_edge("sql_retrieval", "synthesize")
    g.add_edge("web_retrieval", "synthesize")
    g.add_edge("synthesize", "critic")
    g.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"replan": "planner", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)

    return g.compile()


pipeline = _build()
