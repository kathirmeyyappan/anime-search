"""Modal app: daily cron that repopulates anime_mal in Supabase from MAL.

Test (runs once immediately, no schedule set up): modal run database/cron/modal_cron.py
Deploy (activates the daily schedule):            modal deploy database/cron/modal_cron.py
"""

import modal

app = modal.App("supabase-sync")

image = (
    modal.Image.debian_slim()
    .uv_pip_install("psycopg2-binary", "requests")
    .add_local_python_source("mal_client", "anime_mal_to_supabase")
)


@app.function(
    image=image,
    schedule=modal.Cron("0 6 * * *"),  # daily, 06:00 UTC
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
    print(f"Synced {written} anime rows to Supabase.")


@app.local_entrypoint()
def main():
    # `modal run database/cron/modal_cron.py` to do a one-off remote run
    sync_anime_mal.remote()
