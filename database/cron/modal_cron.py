"""Modal app: daily cron that repopulates anime_mal + anime_sheet in Supabase
and refreshes anime_combined, all in ONE transaction — if anything fails
partway (a bad row, a network hiccup, whatever), everything rolls back and
yesterday's data in both tables + the view stays fully intact. daily_sync is
the only scheduled function; sync_anime_mal/sync_anime_sheet stay
independently callable (their own connection/commit) for standalone testing.

Test (runs the full pipeline once, no schedule set up): modal run database/cron/modal_cron.py
Deploy (activates the daily schedule):                  modal deploy database/cron/modal_cron.py
"""

import modal

app = modal.App("supabase-sync")

image = (
    modal.Image.debian_slim()
    .uv_pip_install("psycopg2-binary", "requests")
    .add_local_python_source(
        "mal_client",
        "anime_mal_to_supabase",
        "sheet_client",
        "anime_sheet_to_supabase",
    )
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-sync-secrets")],
    timeout=600,
)
def sync_anime_mal() -> None:
    import os
    from anime_mal_to_supabase import run_sync

    written = run_sync(
        mal_client_id=os.environ["MAL_CLIENT_ID"],
        mal_username=os.environ["MAL_USERNAME"],
        supabase_db_url=os.environ["SUPABASE_DB_URL"],
    )
    print(f"Synced {written} anime_mal rows to Supabase.")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-sync-secrets")],
    timeout=600,
)
def sync_anime_sheet() -> None:
    import os
    from anime_sheet_to_supabase import run_sync

    written = run_sync(
        google_api_key=os.environ["GOOGLE_API_KEY"],
        sheet_key=os.environ["SHEET_KEY"],
        sheet_tab_name=os.environ["SHEET_TAB_NAME"],
        supabase_db_url=os.environ["SUPABASE_DB_URL"],
    )
    print(f"Synced {written} anime_sheet rows to Supabase.")


@app.function(
    image=image,
    schedule=modal.Cron("0 6 * * *"),  # daily, 06:00 UTC — the only scheduled function
    secrets=[modal.Secret.from_name("supabase-sync-secrets")],
    timeout=900,
)
def daily_sync() -> None:
    import os

    import psycopg2

    import anime_mal_to_supabase
    import anime_sheet_to_supabase

    # Fetch from MAL/Sheets before opening the DB transaction — no reason to
    # hold a connection open across slow external API calls, and if either
    # fetch fails (network, timeout, etc.) nothing below ever runs.
    mal_rows = anime_mal_to_supabase.fetch_rows(
        os.environ["MAL_CLIENT_ID"], os.environ["MAL_USERNAME"]
    )
    sheet_rows = anime_sheet_to_supabase.fetch_rows(
        os.environ["GOOGLE_API_KEY"], os.environ["SHEET_KEY"], os.environ["SHEET_TAB_NAME"]
    )

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    try:
        with conn:
            with conn.cursor() as cur:
                # all of our writes happen in one transaction
                anime_mal_to_supabase.write_rows(cur, mal_rows)
                anime_sheet_to_supabase.write_rows(cur, sheet_rows)
                cur.execute("REFRESH MATERIALIZED VIEW anime_combined")
    finally:
        conn.close()

    print(f"Synced {len(mal_rows)} anime_mal rows, {len(sheet_rows)} anime_sheet rows, refreshed anime_combined.")


@app.local_entrypoint()
def main():
    # `modal run database/cron/modal_cron.py` to run the full pipeline once
    daily_sync.remote()
