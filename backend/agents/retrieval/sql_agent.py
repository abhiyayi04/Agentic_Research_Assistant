import json
import os

import pymysql
import pymysql.cursors
from openai import OpenAI

_openai: OpenAI | None = None

_SCHEMA = """
Tables in the contextpilot database:
- ingested_documents(id INT, filename VARCHAR(255), chunk_count INT, ingested_at TIMESTAMP)
"""

_SYSTEM = (
    f"Generate a safe, read-only MySQL SELECT query for this schema:\n{_SCHEMA}\n"
    'Return JSON only: {"sql": "SELECT ..."}'
)


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


def _mysql():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "contextpilot"),
        password=os.getenv("MYSQL_PASSWORD", "contextpilot"),
        database=os.getenv("MYSQL_DB", "contextpilot"),
        autocommit=True,
    )


def _generate_sql(question: str) -> str:
    response = _get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": question},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content).get("sql", "")


def retrieve(sub_questions: list[dict]) -> list[dict]:
    mine = [q for q in sub_questions if q["agent"] == "sql"]
    if not mine:
        return []

    results: list[dict] = []
    for q in mine:
        try:
            sql = _generate_sql(q["question"])
            if not sql.strip().upper().startswith("SELECT"):
                continue
            conn = _mysql()
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            conn.close()
            results.append({
                "agent": "sql",
                "question": q["question"],
                "text": json.dumps(rows, default=str),
                "source": "mysql",
                "score": 1.0,
            })
        except Exception as exc:
            results.append({
                "agent": "sql",
                "question": q["question"],
                "text": f"SQL error: {exc}",
                "source": "mysql",
                "score": 0.0,
            })
    return results
