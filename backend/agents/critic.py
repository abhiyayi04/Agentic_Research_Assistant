import json
import os

from openai import OpenAI

FAITHFULNESS_THRESHOLD = 0.7
COMPLETENESS_THRESHOLD = 0.7
CONFIDENCE_THRESHOLD = 0.6

_openai: OpenAI | None = None

_SYSTEM = """You are a critic agent evaluating an AI research assistant's answer.

Score the answer on three dimensions:
1. faithfulness (0.0–1.0): Are ALL claims grounded in the retrieved context? 1.0 = fully grounded, 0.0 = hallucinated.
2. completeness (0.0–1.0): Did the answer address EVERY sub-question the planner identified? 1.0 = all addressed, 0.0 = none addressed.
3. confidence (0.0–1.0): How confident should the system be given the available context? 1.0 = context is rich and unambiguous, 0.0 = context is sparse or contradictory.

Return JSON only:
{
  "faithfulness": 0.0,
  "completeness": 0.0,
  "confidence": 0.0,
  "critique": "Specific description of what is missing, wrong, or needs improvement.",
  "passed": true
}

Set "passed" to true only if faithfulness >= 0.7 AND completeness >= 0.7 AND confidence >= 0.6."""


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


def evaluate(
    query: str,
    sub_questions: list[dict],
    context: list[dict],
    answer: str,
) -> dict:
    sub_q_text = "\n".join(f"- [{q['agent']}] {q['question']}" for q in sub_questions)
    context_text = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context[:8]
    )

    response = _get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Original question: {query}\n\n"
                    f"Sub-questions identified by planner:\n{sub_q_text}\n\n"
                    f"Retrieved context:\n{context_text}\n\n"
                    f"Generated answer:\n{answer}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    # Enforce thresholds ourselves — don't fully trust the LLM's passed flag
    f = max(0.0, min(1.0, float(data.get("faithfulness", 1.0))))
    c = max(0.0, min(1.0, float(data.get("completeness", 1.0))))
    conf = max(0.0, min(1.0, float(data.get("confidence", 1.0))))
    passed = (
        f >= FAITHFULNESS_THRESHOLD
        and c >= COMPLETENESS_THRESHOLD
        and conf >= CONFIDENCE_THRESHOLD
    )

    return {
        "faithfulness": f,
        "completeness": c,
        "confidence": conf,
        "critique": data.get("critique", ""),
        "passed": passed,
    }
