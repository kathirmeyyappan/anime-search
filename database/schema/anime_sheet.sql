-- Anime I've seen, by franchise (not by individual entry like anime_mal) —
-- granular personal ratings, watch details, and my own notes. Source: my
-- Google Sheet. Repopulated via TRUNCATE + INSERT on every sync, same as
-- anime_mal (see cron/anime_sheet_to_supabase.py).
--
-- mal_id is a soft reference to anime_mal.mal_id (extracted by regex from the
-- sheet's Anime URL column), not a real FK constraint — a hard FK would break
-- anime_mal's TRUNCATE-based sync, and not every sheet entry necessarily maps
-- to a current anime_mal row anyway.

-- CASCADE also drops anime_combined (it depends on this table) — re-run
-- anime_combined.sql after this.
DROP TABLE IF EXISTS anime_sheet CASCADE;

CREATE TABLE anime_sheet (
    -- sheet: Anime Name. Natural key — one row per franchise.
    anime_name          TEXT PRIMARY KEY,

    -- sheet: Rating. My personal score for the franchise.
    score               NUMERIC,

    -- sheet: Year First Watched
    first_watched_year  INTEGER,

    -- sheet: Year First Released
    release_year        INTEGER,

    -- sheet: Caught Up
    caught_up           BOOLEAN,

    -- sheet: Accessibility
    accessibility       SMALLINT,

    -- sheet: Notes. My own written review/thoughts.
    notes               TEXT,

    -- Extracted via regex from sheet: Anime URL (not stored itself). Soft
    -- reference to anime_mal.mal_id — see header note. Null if no URL/no match.
    mal_id              INTEGER,

    -- Not from the sheet. Bookkeeping timestamp for when this row was last
    -- (re)written by the sync job.
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE anime_sheet IS
    'Anime I''ve seen, by franchise. Personal ratings/notes from my Google Sheet. Repopulated via TRUNCATE + INSERT on every sync; mal_id is a soft (non-FK) reference to anime_mal.mal_id.';

COMMENT ON COLUMN anime_sheet.anime_name IS
    'sheet: Anime Name. Primary key — one row per franchise.';
COMMENT ON COLUMN anime_sheet.score IS
    'sheet: Rating — my personal score for the franchise.';
COMMENT ON COLUMN anime_sheet.first_watched_year IS
    'sheet: Year First Watched.';
COMMENT ON COLUMN anime_sheet.release_year IS
    'sheet: Year First Released.';
COMMENT ON COLUMN anime_sheet.caught_up IS
    'sheet: Caught Up.';
COMMENT ON COLUMN anime_sheet.accessibility IS
    'sheet: Accessibility.';
COMMENT ON COLUMN anime_sheet.notes IS
    'sheet: Notes — my own written review/thoughts.';
COMMENT ON COLUMN anime_sheet.mal_id IS
    'Extracted via regex from sheet: Anime URL. Soft reference to anime_mal.mal_id, not a DB-enforced FK.';
COMMENT ON COLUMN anime_sheet.synced_at IS
    'Not from the sheet. Bookkeeping timestamp for when this row was last (re)written by the sync job.';
