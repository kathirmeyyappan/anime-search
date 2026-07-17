"""Thin client for reading the anime Google Sheet via Sheets API v4.
Auth is a plain API key (read-only, sheet must be shared/public).
"""

import requests

SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
REQUEST_TIMEOUT_S = 30


def fetch_sheet_rows(api_key: str, sheet_key: str, tab_name: str, cell_range: str = "A2:N") -> list[list[str]]:
    """Raw row values for one tab, starting after the header row (row 1).
    Returns a list of rows, each a list of cell strings — no field names attached.
    """
    url = f"{SHEETS_API_BASE}/{sheet_key}/values/{tab_name}!{cell_range}"
    res = requests.get(url, params={"key": api_key}, timeout=REQUEST_TIMEOUT_S)
    if not res.ok:
        raise RuntimeError(f"Sheets request failed ({res.status_code}): {res.text[:500]}")
    return res.json().get("values", [])
