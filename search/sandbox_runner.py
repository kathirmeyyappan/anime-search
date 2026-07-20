"""Runs inside a Modal Sandbox only — never invoked directly. Executes one
validated, read-only SQL query and prints the result as JSON to stdout. This
is the actual isolation boundary between SQL an LLM decided to run and the
rest of the system: its own container, its own read-only DB role, nothing
else available to it.

Defense in depth, three separate layers: (1) search_readonly Postgres role
can only SELECT, nothing else, (2) the session itself is set read-only,
(3) this script rejects anything that isn't a plain SELECT before even
trying to run it.
"""

import json
import os
import sys

import psycopg2
import psycopg2.extras

MAX_ROWS = 200


def _is_select_only(sql: str) -> bool:
    """True only for a single SELECT statement — rejects stacked statements
    like "SELECT 1; DROP TABLE x;" outright, rather than just checking the
    start of the string.
    """
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    return len(statements) == 1 and statements[0].lower().startswith("select")


def main() -> None:
    sql = sys.argv[1]

    if not _is_select_only(sql):
        print(json.dumps({"error": "Only SELECT queries are allowed."}))
        return

    conn = None
    try:
        conn = psycopg2.connect(os.environ["READONLY_SUPABASE_DB_URL"])
        conn.set_session(readonly=True)
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        truncated = len(rows) > MAX_ROWS
        result = {"rows": rows[:MAX_ROWS], "truncated": truncated}
        print(json.dumps(result, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
