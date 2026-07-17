-- Indexes for anime_mal. Separate from anime_mal.sql (destructive) since
-- this file is idempotent (IF NOT EXISTS) and safe to blindly re-run.
-- Run anime_mal.sql first on fresh setup, then this. Survives TRUNCATE +
-- re-INSERT with no rebuild needed.

-- my_status is filtered on constantly (e.g. excluding plan_to_watch entries
-- from most queries — see TODO.txt at repo root for the agent-facing note).
CREATE INDEX IF NOT EXISTS idx_anime_mal_my_status ON anime_mal (my_status);

-- Supports chronological browsing/range queries over the anime's air date.
CREATE INDEX IF NOT EXISTS idx_anime_mal_start_date ON anime_mal (start_date);

-- Supports ranking/filtering by MAL's global score (good vs bad anime).
-- Note: this is node.mean, not my personal score.
CREATE INDEX IF NOT EXISTS idx_anime_mal_mean ON anime_mal (mean);

-- Supports chronological queries over when I personally watched things
-- (distinct from start_date above, which is the anime's air date).
CREATE INDEX IF NOT EXISTS idx_anime_mal_my_start_date ON anime_mal (my_start_date);
