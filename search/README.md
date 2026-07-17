# search

Natural-language query agent, fully self-hosted on Modal — no external LLM API. One Modal App (`anime-search`, defined in `model.py`, extended by `agent.py`) so the whole thing deploys as one unit.

Files
- `model.py` — Qwen2.5-7B-Instruct served via vLLM on an A10G GPU, `@app.cls` kept warm across calls
- `sandbox_runner.py` — runs inside a Modal Sandbox only, executes one validated read-only SQL query
- `agent.py` — orchestrator + HTTP endpoint. Fixed two-step flow: model gets the query + tool contract → either answers directly or calls `run_sql` (executed in a Sandbox, isolated, read-only DB role) → gets one more turn with the result to answer

v1 is intentionally minimal: no retry/self-correction loop, no TODO.txt context injection, single tool call max. Extend from here once the basic wiring is proven out.

Setup
1. `psql "$SUPABASE_DB_URL" -f database/schema/readonly_role.sql` (creates `search_readonly`, placeholder password)
2. `psql "$SUPABASE_DB_URL" -c "ALTER ROLE search_readonly WITH PASSWORD '...';"` — set the real password directly, never in a file
3. Build `READONLY_SUPABASE_DB_URL` (same host/port/dbname as `SUPABASE_DB_URL`, user `search_readonly`, percent-encode any special characters in the password)
4. `modal secret create search-secrets READONLY_SUPABASE_DB_URL="$READONLY_SUPABASE_DB_URL"`

Invoking
- `modal run search/agent.py --query "..."` — runs once now, prints the JSON result. For testing.
- `modal deploy search/agent.py` — deploys the App; `query_endpoint` becomes a stable HTTP URL you can POST `{"query": "..."}` to.
