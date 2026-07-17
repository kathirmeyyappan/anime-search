"""One-off: print sheet headers + a few rows to design the anime_sheet schema.

Usage: python3 fetch_sheet_sample.py
Requires GOOGLE_API_KEY, SHEET_KEY, SHEET_TAB_NAME in database/.env.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from sheet_client import fetch_sheet_rows

load_dotenv(Path(__file__).parent.parent / ".env")


def main() -> None:
    api_key = os.environ["GOOGLE_API_KEY"]
    sheet_key = os.environ["SHEET_KEY"]
    tab_name = os.environ["SHEET_TAB_NAME"]

    headers = fetch_sheet_rows(api_key, sheet_key, tab_name, cell_range="A1:N1")
    rows = fetch_sheet_rows(api_key, sheet_key, tab_name, cell_range="A2:N")

    print(f"Headers: {headers[0] if headers else '(none)'}\n")
    print(f"Fetched {len(rows)} data rows. First 5:\n")
    for row in rows[:5]:
        print(row)


if __name__ == "__main__":
    main()
