"""Fetch the full MAL list and fully repopulate the `anime_mal` table in Supabase.

fetch_rows() (network, no DB) and write_rows() (DB write given an existing
cursor, no connection/commit of its own) are split apart so the Modal cron
pipeline can share one transaction across anime_mal + anime_sheet + the
anime_combined refresh (see cron/modal_cron.py). run_sync() glues both
together with its own connection, for standalone/local use.

Running this file directly (`python3 anime_mal_to_supabase.py`) does a local
dry run using database/.env.
"""

import os
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

from mal_client import fetch_full_animelist

# Single source of truth for both the SQL column list and the VALUES tuple
# order in run_sync() below (both are built by iterating this same list, so
# they can't drift relative to each other). Every name here must have a
# matching key in the dict _transform_entry() returns, or run_sync() raises
# KeyError instead of silently inserting misaligned data.
INSERT_COLUMNS = [
    "mal_id",
    "title",
    "alternative_titles",
    "image_url",
    "start_date",
    "end_date",
    "synopsis",
    "mean",
    "num_list_users",
    "media_type",
    "airing_status",
    "genres",
    "num_episodes",
    "start_season",
    "source",
    "studios",
    "my_status",
    "score",
    "is_rewatching",
    "my_updated_at",
    "my_start_date",
    "my_finish_date",
    "num_times_rewatched",
]


def _none_if_empty(value: Any) -> Any:
    return value if value not in (None, "") else None


def _normalize_partial_date(value: Any) -> Any:
    """Normalize a MAL node date ("YYYY", "YYYY-MM", or "YYYY-MM-DD") to a full
    date string so it can be stored as a real SQL DATE. Partial dates are
    filled in to the first day of the known period (year-only -> Jan 1,
    year-month -> the 1st of that month), trading exact-day precision on
    those specific rows for every row staying queryable as a DATE.
    """
    value = _none_if_empty(value)
    if value is None:
        return None
    parts = value.split("-")
    if len(parts) == 1:
        return f"{parts[0]}-01-01"
    if len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-01"
    return value


def _transform_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Map one raw MAL API entry ({node, list_status}) to an `anime_mal` table row."""
    node = entry.get("node", {})
    list_status = entry.get("list_status", {})

    genres = [g["name"] for g in node.get("genres", []) if "name" in g]
    main_picture = node.get("main_picture") or {}
    image_url = main_picture.get("large") or main_picture.get("medium")

    return {
        "mal_id": node["id"],
        "title": node.get("title"),
        "alternative_titles": Json(node["alternative_titles"]) if node.get("alternative_titles") is not None else None,
        "image_url": image_url,
        "start_date": _normalize_partial_date(node.get("start_date")),
        "end_date": _normalize_partial_date(node.get("end_date")),
        "synopsis": node.get("synopsis"),
        "mean": node.get("mean"),
        "num_list_users": node.get("num_list_users"),
        "media_type": node.get("media_type"),
        "airing_status": node.get("status"),
        "genres": genres,
        "num_episodes": node.get("num_episodes"),
        "start_season": Json(node["start_season"]) if node.get("start_season") is not None else None,
        "source": node.get("source"),
        "studios": Json(node["studios"]) if node.get("studios") is not None else None,
        "my_status": list_status.get("status"),
        "score": list_status.get("score"),
        "is_rewatching": list_status.get("is_rewatching"),
        "my_updated_at": _none_if_empty(list_status.get("updated_at")),
        "my_start_date": _normalize_partial_date(list_status.get("start_date")),
        "my_finish_date": _normalize_partial_date(list_status.get("finish_date")),
        "num_times_rewatched": list_status.get("num_times_rewatched"),
    }


def fetch_rows(mal_client_id: str, mal_username: str) -> list[dict[str, Any]]:
    """Fetch + transform only — no DB connection touched."""
    entries = fetch_full_animelist(mal_client_id, mal_username)
    return [_transform_entry(e) for e in entries]


def write_rows(cur, rows: list[dict[str, Any]]) -> None:
    """TRUNCATE + bulk INSERT using the given cursor. Caller owns the
    connection/transaction/commit — this never commits on its own, so it can
    be composed into a larger shared transaction.
    """
    values = [tuple(row[col] for col in INSERT_COLUMNS) for row in rows]
    cur.execute("TRUNCATE anime_mal")
    execute_values(
        cur,
        f"INSERT INTO anime_mal ({', '.join(INSERT_COLUMNS)}) VALUES %s",
        values,
    )


def run_sync(mal_client_id: str, mal_username: str, supabase_db_url: str) -> int:
    """Standalone convenience wrapper: fetch + write + commit with its own
    connection. TRUNCATE + INSERT happen inside one transaction (`with conn:`),
    so a crash mid-run rolls back rather than leaving the table half-populated.

    Returns the number of rows written.
    """
    rows = fetch_rows(mal_client_id, mal_username)

    conn = psycopg2.connect(supabase_db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                write_rows(cur, rows)
    finally:
        conn.close()

    return len(rows)


# for running local sync to datsbase
if __name__ == "__main__":    
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")

    written = run_sync(
        mal_client_id=os.environ["MAL_CLIENT_ID"],
        mal_username=os.environ["MAL_USERNAME"],
        supabase_db_url=os.environ["SUPABASE_DB_URL"],
    )
    print(f"Synced {written} anime rows to Supabase.")
