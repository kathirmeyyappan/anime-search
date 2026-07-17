"""Fetch the full anime spreadsheet and fully repopulate `anime_sheet` in Supabase.

`run_sync()` takes credentials as arguments (not env vars itself) so the Modal
cron job can call it directly from a modal.Secret, without needing a .env file.

Running this file directly (`python3 anime_sheet_to_supabase.py`) does a local
dry run using database/.env.
"""

import os
import re
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

from sheet_client import fetch_sheet_rows

# Column indices in the sheet (0-indexed, matches header row order).
COL_ANIME_NAME = 2
COL_SCORE = 3
COL_FIRST_WATCHED_YEAR = 4
COL_RELEASE_YEAR = 5
COL_MAL_RATING = 6
COL_CAUGHT_UP = 7
COL_ACCESSIBILITY = 9
COL_ANIME_URL = 12
COL_NOTES = 13

MAL_ID_RE = re.compile(r"/anime/(\d+)")

INSERT_COLUMNS = [
    "anime_name",
    "score",
    "first_watched_year",
    "release_year",
    "mal_rating",
    "caught_up",
    "accessibility",
    "notes",
    "mal_id",
]


def _cell(row: list[str], index: int) -> str | None:
    """Sheets API omits trailing empty cells, so a row may be shorter than expected."""
    return row[index] if index < len(row) and row[index] != "" else None


def _to_number(value: str | None) -> float | None:
    return float(value) if value is not None else None


def _to_int(value: str | None) -> int | None:
    return int(float(value)) if value is not None else None


def _extract_mal_id(anime_url: str | None) -> int | None:
    if not anime_url:
        return None
    match = MAL_ID_RE.search(anime_url)
    return int(match.group(1)) if match else None


def _transform_row(row: list[str]) -> dict[str, Any]:
    return {
        "anime_name": _cell(row, COL_ANIME_NAME),
        "score": _to_number(_cell(row, COL_SCORE)),
        "first_watched_year": _to_int(_cell(row, COL_FIRST_WATCHED_YEAR)),
        "release_year": _to_int(_cell(row, COL_RELEASE_YEAR)),
        "mal_rating": _to_number(_cell(row, COL_MAL_RATING)),
        "caught_up": (_cell(row, COL_CAUGHT_UP) or "").upper() == "TRUE",
        "accessibility": _to_int(_cell(row, COL_ACCESSIBILITY)),
        "notes": _cell(row, COL_NOTES),
        "mal_id": _extract_mal_id(_cell(row, COL_ANIME_URL)),
    }


def run_sync(google_api_key: str, sheet_key: str, sheet_tab_name: str, supabase_db_url: str) -> int:
    """Fetch the sheet and fully repopulate the Supabase `anime_sheet` table.

    TRUNCATE + bulk INSERT happen inside one transaction, so a crash mid-run
    rolls back and leaves the previous table contents intact.

    Returns the number of rows written.
    """
    raw_rows = fetch_sheet_rows(google_api_key, sheet_key, sheet_tab_name)
    raw_rows = [row for row in raw_rows if _cell(row, COL_ANIME_NAME)]
    rows = [_transform_row(row) for row in raw_rows]
    values = [tuple(row[col] for col in INSERT_COLUMNS) for row in rows]

    conn = psycopg2.connect(supabase_db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE anime_sheet")
                execute_values(
                    cur,
                    f"INSERT INTO anime_sheet ({', '.join(INSERT_COLUMNS)}) VALUES %s",
                    values,
                )
    finally:
        conn.close()

    return len(rows)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")

    written = run_sync(
        google_api_key=os.environ["GOOGLE_API_KEY"],
        sheet_key=os.environ["SHEET_KEY"],
        sheet_tab_name=os.environ["SHEET_TAB_NAME"],
        supabase_db_url=os.environ["SUPABASE_DB_URL"],
    )
    print(f"Synced {written} anime_sheet rows to Supabase.")
