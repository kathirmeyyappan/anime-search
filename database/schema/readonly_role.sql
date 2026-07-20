-- Read-only Postgres role for the search agent's Modal Sandbox. SELECT-only
-- on the search-relevant tables/views — separate from the sync pipeline's
-- full-access role, so the agent (or SQL an LLM decides to run) can never
-- write/truncate/drop even if application-level validation fails.
--
-- CHANGE_ME_PASSWORD below is a placeholder — replace it before running, and
-- never commit the real password (this file is safe to commit as-is since
-- it's a placeholder, but don't edit-then-commit with a real one in place).
--
-- Idempotent-safe to re-run (won't error if the role already exists), but
-- re-running does NOT change an existing role's password — use ALTER ROLE
-- for that.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'search_readonly') THEN
        CREATE ROLE search_readonly WITH LOGIN PASSWORD 'agent-only-reads';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO search_readonly;
GRANT USAGE ON SCHEMA public TO search_readonly;

-- Add new tables/views here as they're added to the schema.
GRANT SELECT ON anime_mal, anime_sheet, anime_combined TO search_readonly;
