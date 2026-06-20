import os

try:
    from tavily import TavilyClient
    _HAS_TAVILY = True
except ImportError:
    _HAS_TAVILY = False

_client = None


def _get_client():
    global _client
    if _client is None and _HAS_TAVILY:
        key = os.getenv("TAVILY_API_KEY", "")
        if key:
            _client = TavilyClient(api_key=key)
    return _client


def retrieve(sub_questions: list[dict]) -> list[dict]:
    mine = [q for q in sub_questions if q["agent"] == "web"]
    if not mine:
        return []

    client = _get_client()
    if not client:
        return [
            {
                "agent": "web",
                "question": q["question"],
                "text": "Web search unavailable (TAVILY_API_KEY not configured).",
                "source": "web",
                "score": 0.0,
            }
            for q in mine
        ]

    results: list[dict] = []
    for q in mine:
        try:
            resp = client.search(query=q["question"], max_results=3)
            for r in resp.get("results", []):
                results.append({
                    "agent": "web",
                    "question": q["question"],
                    "text": r.get("content", ""),
                    "source": r.get("url", "web"),
                    "score": r.get("score", 0.5),
                })
        except Exception as exc:
            results.append({
                "agent": "web",
                "question": q["question"],
                "text": f"Web search error: {exc}",
                "source": "web",
                "score": 0.0,
            })
    return results
