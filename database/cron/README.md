# cron

Pattern: one Modal App (`supabase-sync`) in `modal_cron.py`. `daily_sync` is the only scheduled function — it fetches from every source first (no DB connection open yet), then does all writes + the `anime_combined` refresh in one shared transaction, so a mid-pipeline failure rolls back everything rather than leaving tables out of sync with each other. Each sync module exposes `fetch_rows()` (network, no DB) and `write_rows(cur, rows)` (write given an existing cursor, no commit of its own) for this; `run_sync()` glues both together with its own connection, kept around for standalone/local testing. `sync_anime_mal`/`sync_anime_sheet` stay as plain (unscheduled) Modal functions for ad hoc remote testing of one table at a time.

Adding a new synced table
1. Write a sync module exposing `fetch_rows(...)` and `write_rows(cur, rows)` (see `anime_mal_to_supabase.py`)
2. Bundle it into the image (own image if it needs different deps)
3. In `daily_sync`, call its `fetch_rows()` before the transaction opens, `write_rows()` inside it
4. New creds go on as more keys on the same secret
5. `modal deploy database/cron/modal_cron.py`

Invoking
- `modal run database/cron/modal_cron.py` — runs `daily_sync` once now. For testing.
- `modal deploy database/cron/modal_cron.py` — registers the App; `daily_sync`'s schedule is what makes it recur. No immediate execution.
