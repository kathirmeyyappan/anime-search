-- FULL OUTER JOIN of anime_mal and anime_sheet on mal_id — nothing dropped
-- from either side (MAL entries with no sheet rating, and sheet entries not
-- currently on the MAL list, both still show up, with nulls on the missing
-- side). Gives an agent one correct pre-joined surface instead of
-- re-deriving the join (soft-reference mal_id, franchise-vs-entry mismatch)
-- every query. MATERIALIZED, not a plain view, for real read performance —
-- refreshed by the cron pipeline right after both source tables resync
-- (see cron/modal_cron.py), not automatically.
--
-- mal_id, score, synced_at exist on both source tables with different
-- meanings — aliased below (mal_score/sheet_score, mal_synced_at/sheet_synced_at)
-- to avoid collision.

DROP MATERIALIZED VIEW IF EXISTS anime_combined;

CREATE MATERIALIZED VIEW anime_combined AS
SELECT
    COALESCE(anime_mal.mal_id, anime_sheet.mal_id) AS mal_id,

    -- anime_mal columns
    anime_mal.title,
    anime_mal.alternative_titles,
    anime_mal.image_url,
    anime_mal.start_date,
    anime_mal.end_date,
    anime_mal.synopsis,
    anime_mal.mean,
    anime_mal.num_list_users,
    anime_mal.media_type,
    anime_mal.airing_status,
    anime_mal.genres,
    anime_mal.num_episodes,
    anime_mal.start_season,
    anime_mal.source,
    anime_mal.studios,
    anime_mal.my_status,
    anime_mal.score              AS my_mal_score,
    anime_mal.is_rewatching,
    anime_mal.my_updated_at,
    anime_mal.my_start_date,
    anime_mal.my_finish_date,
    anime_mal.num_times_rewatched,
    anime_mal.synced_at          AS mal_synced_at,

    -- anime_sheet columns
    anime_sheet.anime_name,
    anime_sheet.score            AS my_sheet_score,
    anime_sheet.first_watched_year,
    anime_sheet.release_year,
    anime_sheet.caught_up,
    anime_sheet.accessibility,
    anime_sheet.notes,
    anime_sheet.synced_at        AS sheet_synced_at
FROM anime_mal
FULL OUTER JOIN anime_sheet ON anime_mal.mal_id = anime_sheet.mal_id;

COMMENT ON MATERIALIZED VIEW anime_combined IS
    'FULL OUTER JOIN of anime_mal + anime_sheet on mal_id. Refreshed by the cron pipeline after both resync, not automatically — can be stale between runs.';

-- Plain pass-through columns (title, synopsis, mean, anime_name, notes, etc.)
-- keep their anime_mal/anime_sheet name and meaning — see that table's own
-- COMMENT ON COLUMN. Only the renamed/derived ones are re-documented here.
COMMENT ON COLUMN anime_combined.mal_id IS
    'COALESCE(anime_mal.mal_id, anime_sheet.mal_id). Null only if an unmatched sheet row itself has no resolvable mal_id.';
COMMENT ON COLUMN anime_combined.my_mal_score IS
    'anime_mal.score — my personal 0-10 MAL app score. See my_sheet_score for the separate, more granular sheet rating.';
COMMENT ON COLUMN anime_combined.my_sheet_score IS
    'anime_sheet.score — my personal sheet rating (decimal, more granular). See my_mal_score for the separate MAL app score.';
COMMENT ON COLUMN anime_combined.mal_synced_at IS
    'anime_mal.synced_at. Null if this row came only from anime_sheet (no anime_mal match).';
COMMENT ON COLUMN anime_combined.sheet_synced_at IS
    'anime_sheet.synced_at. Null if this row came only from anime_mal (no anime_sheet match).';
