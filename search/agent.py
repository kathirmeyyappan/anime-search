"""Orchestrator + HTTP endpoint for the anime search agent.

Bounded tool-use loop (up to MAX_TOOL_CALLS run_sql calls):
  1. Model sees the query + tool contract, responds with strict JSON: either
     a run_sql tool call or a final answer.
  2. Each tool call runs inside a Modal Sandbox (isolated, read-only DB role
     — see sandbox_runner.py); the result gets appended to the conversation
     and the model gets another turn — it can run another query based on
     what it just learned, or answer.
  3. If the cap is hit without an answer, one last turn forces a best-effort
     final answer from whatever's been learned so far.

Test: modal run search/agent.py --query "..."
Deploy: modal deploy search/agent.py
"""

import json
from pathlib import Path

import modal
from pydantic import BaseModel

from model import Model, app

SEARCH_DIR = Path(__file__).parent

agent_image = modal.Image.debian_slim().pip_install("fastapi[standard]")


class QueryRequest(BaseModel):
    query: str

sandbox_image = modal.Image.debian_slim().pip_install("psycopg2-binary").add_local_file(
    str(SEARCH_DIR / "sandbox_runner.py"), "/root/sandbox_runner.py"
)

SYSTEM_PROMPT = """You are a helpful assistant that answers natural language questions about \
Kathir's anime-watching history and MyAnimeList data by querying a Postgres database.

Available tables:
- anime_mal: full mirror of his current MyAnimeList list. Columns include mal_id, title, \
synopsis, mean (MAL's global score), media_type, airing_status, genres, num_episodes, \
my_status (watch status), score (personal 0-10 MAL score), my_start_date, my_finish_date, \
image_url.
- anime_sheet: his personal franchise-level ratings/notes, one row per franchise. Columns: \
anime_name, score (personal decimal rating), first_watched_year, release_year, caught_up, \
accessibility, notes (written thoughts), mal_id.
- anime_combined: FULL OUTER JOIN of the above two tables on mal_id — nothing dropped from \
either side, nulls where a side has no match. Has my_mal_score/my_sheet_score (the two \
tables' separately-scaled personal scores) plus every other column from both tables.

By default, exclude my_status = 'plan_to_watch' entries when answering general questions — \
that means he hasn't watched it, so it's not representative of taste or history. Only \
include plan_to_watch entries when specifically asked about them.

Respond with STRICT JSON only — no other text, no markdown code fences. Exactly one of:
1. To run a read-only query: {"tool": "run_sql", "args": {"query": "<a single SELECT statement>"}}
2. To give a final answer: {"answer": "<natural language answer>", "data": [<optional: specific \
rows/values from a query worth returning alongside the answer, omit or null if not relevant>]}

You can run more than one query in sequence — e.g. look something up first, then decide what \
to query next based on the result — there's no fixed number, just don't run a query you don't \
need. Only SELECT statements are allowed. Prefer anime_combined when a question needs both MAL \
and sheet data."""


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _run_sql_in_sandbox(query: str) -> dict:
    sb = modal.Sandbox.create(
        app=app,
        image=sandbox_image,
        secrets=[modal.Secret.from_name("search-secrets")],
        timeout=30,
    )
    try:
        proc = sb.exec("python", "/root/sandbox_runner.py", query, timeout=25)
        proc.wait()
        output = proc.stdout.read()
        return json.loads(output)
    finally:
        sb.terminate()


MAX_TOOL_CALLS = 5


@app.function(image=agent_image, timeout=180)
def answer_query(query: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    model = Model()
    sql_used = []

    for _ in range(MAX_TOOL_CALLS):
        response = model.generate.remote(messages)

        try:
            parsed = _parse_json_response(response)
        except json.JSONDecodeError:
            return {"answer": None, "error": f"Model did not return valid JSON: {response!r}", "sql_used": sql_used}

        if "answer" in parsed:
            return {"answer": parsed["answer"], "data": parsed.get("data"), "sql_used": sql_used}

        if parsed.get("tool") != "run_sql":
            return {"answer": None, "error": f"Unrecognized response shape: {parsed!r}", "sql_used": sql_used}

        sql_query = parsed["args"]["query"]
        sql_used.append(sql_query)
        tool_result = _run_sql_in_sandbox(sql_query)

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Query result: {json.dumps(tool_result)}"})

    # Hit the cap without an answer — force one last best-effort turn instead
    # of throwing away everything learned so far.
    messages.append({
        "role": "user",
        "content": (
            "You've reached the query limit. Give your best final answer now as "
            '{"answer": "...", "data": [...]} JSON only, based on what you\'ve learned so far.'
        ),
    })
    final_response = model.generate.remote(messages)
    try:
        parsed_final = _parse_json_response(final_response)
        return {"answer": parsed_final.get("answer"), "data": parsed_final.get("data"), "sql_used": sql_used}
    except json.JSONDecodeError:
        return {
            "answer": None,
            "error": f"Model did not return valid JSON on final turn: {final_response!r}",
            "sql_used": sql_used,
        }


@app.function(image=agent_image)
@modal.fastapi_endpoint(method="POST")
def query_endpoint(item: QueryRequest) -> dict:
    return answer_query.local(item.query)


@app.local_entrypoint()
def main(query: str = "What's the highest-rated anime I've completed?"):
    result = answer_query.remote(query)
    print(json.dumps(result, indent=2))


@app.local_entrypoint()
def test_sandbox(sql: str = "SELECT mal_id, title FROM anime_mal LIMIT 3"):
    """Tests just the Sandbox + read-only DB path — no GPU, no model, fast.
    Isolates DB/permission/secret issues from GPU cold-start issues.
    """
    print(json.dumps(_run_sql_in_sandbox(sql), indent=2))
