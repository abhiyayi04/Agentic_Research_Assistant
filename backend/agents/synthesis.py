import json
import os

from openai import OpenAI

_openai: OpenAI | None = None

_SYSTEM = """You are a research synthesis agent. Given a user question and retrieved context from multiple sources, generate a comprehensive, well-structured answer with inline citations.

Rules:
- Cite sources inline using [1], [2], etc. — every factual claim must be grounded in the provided context
- If multiple sources say the same thing, deduplicate the information and cite all of them
- Be concise but complete — use markdown formatting where helpful (bullet points, bold)
- If the context is insufficient to fully answer the question, say so clearly

Respond with valid JSON only:
{
  "answer": "Your answer with inline citations like [1] and [2]...",
  "citations": [
    {"id": 1, "source": "source name or URL", "quote": "brief supporting quote from that source"}
  ]
}"""


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


def synthesize(query: str, context: list[dict]) -> dict:
    if not context:
        return {
            "answer": "No relevant information found. Please ingest some documents first.",
            "citations": [],
        }

    # Sort by relevance score, cap at 10 chunks to stay within token limits
    ranked = sorted(context, key=lambda c: c.get("score", 0), reverse=True)[:10]

    context_blocks = [
        f"[{i}] Source: {c['source']} (retrieved by {c['agent']} agent)\n{c['text']}"
        for i, c in enumerate(ranked, 1)
    ]

    response = _get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": f"Question: {query}\n\nContext:\n\n" + "\n\n".join(context_blocks),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    data = json.loads(response.choices[0].message.content)
    return {
        "answer": data.get("answer", ""),
        "citations": data.get("citations", []),
    }
