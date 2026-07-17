-- Idempotent (IF NOT EXISTS), safe to blindly re-run. See anime_mal_indexes.sql
-- for why these live separately from the destructive anime_sheet.sql.

-- Unique (not PK): gives the same join speed against anime_mal.mal_id as a
-- PK would, but tolerates null (a sheet row with no/unmatched Anime URL yet)
-- without breaking the sync — a hard PK can't be null, ever.
CREATE UNIQUE INDEX IF NOT EXISTS idx_anime_sheet_mal_id ON anime_sheet (mal_id);
