import json
import os

from openai import OpenAI

_openai: OpenAI | None = None

_SYSTEM = """You are a research query planner. Decompose the user's question into 2-4 focused sub-questions and assign each to the best retrieval agent:
- "vector": questions about document content, concepts, definitions, explanations
- "sql": questions about counts, statistics, metadata, or structured/tabular data
- "web": questions requiring current or real-time information

Return valid JSON only:
{"sub_questions": [{"question": "...", "agent": "vector|sql|web"}]}"""


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


def plan(query: str, critique: str = "") -> list[dict]:
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": query},
    ]

    if critique:
        messages.append({
            "role": "user",
            "content": (
                f"The previous answer was insufficient. Critic feedback:\n{critique}\n\n"
                "Generate NEW, more targeted sub-questions to fill the gaps identified above. "
                "Focus on what was missing or incomplete."
            ),
        })

    response = _get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("sub_questions", [{"question": query, "agent": "vector"}])
