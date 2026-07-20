# search

Natural-language query agent, fully self-hosted on Modal — no external LLM API. One Modal App (`anime-search`, defined in `model.py`, extended by `agent.py`) so the whole thing deploys as one unit.

Files
- `model.py` — Qwen2.5-7B-Instruct served via vLLM on an A10G GPU, `@app.cls` kept warm across calls
- `sandbox_runner.py` — runs inside a Modal Sandbox only, executes one validated SQL query. No separate read-only DB role (Supabase's pooler doesn't play nice with custom roles — not worth the fight); defense in depth is just the read-only session + SELECT-only check, both enforced here.
- `agent.py` — orchestrator + HTTP endpoint. Bounded loop (up to `MAX_TOOL_CALLS`): model gets the query + tool contract, and on each turn either answers (optionally with a `data` subset alongside the summary) or calls `run_sql` (executed in a Sandbox); the result feeds back in and it can decide to query again based on what it learned, or answer

v1 is intentionally minimal: no retry-on-error self-correction, no TODO.txt context injection yet. Extend from here once the basic wiring is proven out.

Setup
Own dedicated secret (same DB credential as the sync pipeline's, deployed independently so this feature's containers don't also get MAL/Sheets creds they don't need):
```bash
set -a; source search/.env; set +a
modal secret create search-secrets SUPABASE_DB_URL="$SUPABASE_DB_URL" --force
```

Invoking
- `modal run search/agent.py --query "..."` — runs once now, prints the JSON result. For testing.
- `modal deploy search/agent.py` — deploys the App; `query_endpoint` becomes a stable HTTP URL you can POST `{"query": "..."}` to.
