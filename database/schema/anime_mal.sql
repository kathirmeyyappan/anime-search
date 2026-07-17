-- Anime list table: a full mirror of Uji_Gintoki_Bowl's MyAnimeList list.
--
-- This table is fully repopulated on every sync run (TRUNCATE + re-INSERT in
-- a single transaction, so a mid-run crash rolls back and leaves the previous
-- data intact instead of leaving the table half-empty). There is no upsert /
-- diffing logic — MAL is the source of truth, this table just mirrors it.
--
-- Source: GET https://api.myanimelist.net/v2/users/{username}/animelist
-- Each raw MAL API entry looks like:
--   {
--     "node": { ...anime metadata... },
--     "list_status": { ...my personal status on that anime... }
--   }
-- The comment above each column below says which of those two objects (and
-- which key within it) the column is sourced from.

DROP TABLE IF EXISTS anime_mal;

CREATE TABLE anime_mal (
    -- node.id
    -- MAL's own anime ID. Renamed from "id" to "mal_id" to make clear this is
    -- MyAnimeList's identifier, not a locally-generated one, and to sidestep
    -- ambiguity with the bare word "id". This is my primary key since it's
    -- stable and unique per anime.
    mal_id                  INTEGER PRIMARY KEY,

    -- node.title
    -- The "canonical" MAL title (usually the Japanese romaji title).
    title                   TEXT NOT NULL,

    -- node.alternative_titles
    -- Kept as-is (raw JSON): { "synonyms": [...], "en": "...", "ja": "..." }
    alternative_titles      JSONB,

    -- node.start_date
    -- MAL dates are sometimes partial (e.g. just "2025" or "2025-12" for
    -- anime whose exact air date isn't pinned down yet). To keep this a real
    -- DATE (so range queries still work), the sync script normalizes partial
    -- dates to the first day of the known period: year-only -> Jan 1,
    -- year-month -> the 1st of that month. This means a handful of rows lose
    -- exact-day precision, but every row stays queryable as a DATE.
    start_date              DATE,

    -- node.end_date (same partial-date normalization as start_date)
    end_date                DATE,

    -- node.synopsis
    synopsis                TEXT,

    -- node.mean
    -- MAL's global average score for the anime (not my personal score).
    -- NULL when the anime doesn't have enough ratings yet.
    mean                    NUMERIC,

    -- node.num_list_users
    -- How many MAL users have this anime on their list at all.
    num_list_users          INTEGER,

    -- node.media_type
    -- e.g. "tv", "movie", "ova", "ona", "special".
    media_type              TEXT,

    -- node.status
    -- Renamed to "airing_status" to disambiguate from my personal watch
    -- status (see my_status below). e.g. "finished_airing", "currently_airing".
    airing_status           TEXT,

    -- node.genres
    -- Raw MAL shape is [{ "id": 2, "name": "Adventure" }, ...]; flattened here
    -- to just the genre name strings, e.g. {"Adventure","Comedy"}.
    genres                  TEXT[],

    -- node.num_episodes
    -- Total episode count for the series (0 if not yet known, e.g. ongoing).
    num_episodes            INTEGER,

    -- node.start_season
    -- Kept as-is (raw JSON): { "year": 2025, "season": "fall" }
    start_season            JSONB,

    -- node.source
    -- What the anime is adapted from, e.g. "original", "manga", "light_novel".
    source                  TEXT,

    -- node.studios
    -- Raw MAL shape is [{ "id": 4, "name": "Toei Animation" }, ...], kept
    -- as-is (raw JSON) since there's a mix of one or more studios per anime.
    studios                 JSONB,

    -- list_status.status
    -- Renamed to "my_status" to disambiguate from the anime's airing_status.
    -- One of: "watching", "completed", "on_hold", "dropped", "plan_to_watch".
    my_status               TEXT,

    -- list_status.score
    -- My personal 0-10 score for the anime. 0 means unscored.
    score                   SMALLINT,

    -- list_status.is_rewatching
    is_rewatching           BOOLEAN,

    -- list_status.updated_at
    -- Renamed to "my_updated_at": when I last touched this list entry
    -- (as opposed to node.updated_at, which isn't stored here, tracking when
    -- MAL's metadata for the anime itself last changed).
    my_updated_at           TIMESTAMPTZ,

    -- list_status.start_date
    -- Renamed to "my_start_date": when I personally started watching.
    -- Native DATE is fine here (unlike node dates above) since MAL always
    -- gives these as full dates or leaves them empty/null.
    my_start_date           DATE,

    -- list_status.finish_date -> "my_finish_date"
    my_finish_date          DATE,

    -- list_status.num_times_rewatched
    num_times_rewatched     INTEGER,

    -- Not from MAL. Bookkeeping column so I can see, from the data itself,
    -- when this row was last (re)written by the sync job.
    synced_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The -- comments above only live in this file — Postgres discards them once
-- this script runs. COMMENT ON persists the same documentation into the
-- database's own catalog (pg_description), so it's still there later via
-- `\d+ anime_mal` in psql, `col_description(...)` in a query, or Supabase
-- Studio's table editor — including for an agent introspecting the schema
-- with no access to this repo.
COMMENT ON TABLE anime_mal IS
    'Full mirror of my MyAnimeList list. Repopulated via TRUNCATE + INSERT in one transaction on every sync run (see database/sync_to_supabase.py); MAL is the source of truth, no upsert/diff logic.';

COMMENT ON COLUMN anime_mal.mal_id IS
    'node.id — MAL''s own anime ID. Primary key.';
COMMENT ON COLUMN anime_mal.title IS
    'node.title — canonical MAL title (usually the Japanese romaji title).';
COMMENT ON COLUMN anime_mal.alternative_titles IS
    'node.alternative_titles — raw JSON {synonyms, en, ja}.';
COMMENT ON COLUMN anime_mal.start_date IS
    'node.start_date — normalized to a full DATE; MAL''s partial dates (year-only or year-month) are rounded down to the 1st of the known period.';
COMMENT ON COLUMN anime_mal.end_date IS
    'node.end_date — same partial-date normalization as start_date.';
COMMENT ON COLUMN anime_mal.synopsis IS
    'node.synopsis.';
COMMENT ON COLUMN anime_mal.mean IS
    'node.mean — MAL''s global average score for the anime (not my personal score). Null if not enough ratings yet.';
COMMENT ON COLUMN anime_mal.num_list_users IS
    'node.num_list_users — how many MAL users have this anime on their list at all.';
COMMENT ON COLUMN anime_mal.media_type IS
    'node.media_type — e.g. tv, movie, ova, ona, special.';
COMMENT ON COLUMN anime_mal.airing_status IS
    'node.status, renamed to disambiguate from my_status — e.g. finished_airing, currently_airing.';
COMMENT ON COLUMN anime_mal.genres IS
    'node.genres, flattened from [{id, name}, ...] to just the name strings.';
COMMENT ON COLUMN anime_mal.num_episodes IS
    'node.num_episodes — total episode count for the series (0 if not yet known, e.g. ongoing).';
COMMENT ON COLUMN anime_mal.start_season IS
    'node.start_season — raw JSON {year, season}.';
COMMENT ON COLUMN anime_mal.source IS
    'node.source — what the anime is adapted from, e.g. original, manga, light_novel.';
COMMENT ON COLUMN anime_mal.studios IS
    'node.studios — raw JSON [{id, name}, ...], one or more studios per anime.';
COMMENT ON COLUMN anime_mal.my_status IS
    'list_status.status, renamed to disambiguate from airing_status — one of watching, completed, on_hold, dropped, plan_to_watch.';
COMMENT ON COLUMN anime_mal.score IS
    'list_status.score — my personal 0-10 score for the anime. 0 means unscored.';
COMMENT ON COLUMN anime_mal.is_rewatching IS
    'list_status.is_rewatching.';
COMMENT ON COLUMN anime_mal.my_updated_at IS
    'list_status.updated_at, renamed — when I last touched this list entry (not when MAL''s own metadata for the anime changed).';
COMMENT ON COLUMN anime_mal.my_start_date IS
    'list_status.start_date, renamed — when I personally started watching.';
COMMENT ON COLUMN anime_mal.my_finish_date IS
    'list_status.finish_date, renamed — when I personally finished watching.';
COMMENT ON COLUMN anime_mal.num_times_rewatched IS
    'list_status.num_times_rewatched.';
COMMENT ON COLUMN anime_mal.synced_at IS
    'Not from MAL. Bookkeeping timestamp for when this row was last (re)written by the sync job.';
