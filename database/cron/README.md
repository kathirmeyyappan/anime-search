# cron

Pattern: one Modal App (`supabase-sync`) in `modal_cron.py`, one `@app.function` per synced table, each calling a sync function that does the actual TRUNCATE+INSERT.

Adding a new synced table
1. Write a sync module (creds as args, does TRUNCATE+INSERT)
2. Add a new `@app.function(schedule=modal.Cron(...), secrets=[modal.Secret.from_name("supabase-sync-secrets")])` in `modal_cron.py` calling it
3. Bundle the new module into the image (own image if it needs different deps)
4. New creds go on as more keys on the same secret
5. `modal deploy database/cron/modal_cron.py` — additive, doesn't touch existing scheduled functions

Invoking
- `modal run database/cron/modal_cron.py` — runs locally, triggers one real remote call now. For testing.
- `modal deploy database/cron/modal_cron.py` — registers the App; each function's schedule is what makes it recur. No immediate execution.
