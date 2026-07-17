"""Thin client for pulling a user's full MyAnimeList list via the official MAL API v2.

Auth: Client-ID-only (no OAuth). This only works for a *public* MAL list —
MAL requires a full OAuth2 user token to read a private list.
"""

import time
from typing import Any

import requests

MAL_API_BASE = "https://api.myanimelist.net/v2"

# Anime metadata fields we want on each list entry, plus the nested list_status
# object (your personal status/score/progress on that anime). This is the
# "everything useful" field set — a few very heavy/rarely-needed nested fields
# (pictures, related_anime, related_manga, recommendations, statistics) are
# left out on purpose; add them here if you decide you want them too.
ANIME_FIELDS = [
    "id",
    "title",
    "main_picture",
    "alternative_titles",
    "start_date",
    "end_date",
    "synopsis",
    "mean",
    "rank",
    "popularity",
    "num_list_users",
    "num_scoring_users",
    "nsfw",
    "created_at",
    "updated_at",
    "media_type",
    "status",
    "genres",
    "num_episodes",
    "start_season",
    "broadcast",
    "source",
    "average_episode_duration",
    "rating",
    "studios",
]

LIST_STATUS_FIELDS = [
    "status",
    "score",
    "num_episodes_watched",
    "is_rewatching",
    "updated_at",
    "priority",
    "num_times_rewatched",
    "rewatch_value",
    "tags",
    "comments",
    "start_date",
    "finish_date",
]

PAGE_LIMIT = 500
REQUEST_TIMEOUT_S = 30
RATE_LIMIT_SLEEP_S = 0.3
MAX_ATTEMPTS = 3
RETRY_BASE_SLEEP_S = 2


def _build_fields_param() -> str:
    node_fields = ",".join(ANIME_FIELDS)
    list_status_fields = ",".join(LIST_STATUS_FIELDS)
    return f"{node_fields},list_status{{{list_status_fields}}}"


def _get_with_retry(url: str, headers: dict, params: dict | None) -> requests.Response | None:
    """GET with bounded retries on timeout/connection errors (transient, not our bug)."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            return requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_S)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(RETRY_BASE_SLEEP_S * 2**attempt)


def fetch_full_animelist(client_id: str, username: str) -> list[dict[str, Any]]:
    """Fetch every entry of `username`'s MAL anime list, fully paginated.

    Returns a flat list of raw MAL API entries, each shaped like:
      { "node": {...anime metadata...}, "list_status": {...your status...} }
    """
    headers = {"X-MAL-CLIENT-ID": client_id}
    url = f"{MAL_API_BASE}/users/{username}/animelist"
    params = {
        "fields": _build_fields_param(),
        "nsfw": "true",
        "limit": PAGE_LIMIT,
        "sort": "list_updated_at",
    }

    entries: list[dict[str, Any]] = []
    next_url = url
    next_params = params

    while next_url:
        res = _get_with_retry(next_url, headers, next_params)
        if not res.ok:
            raise RuntimeError(f"MAL request failed ({res.status_code}): {res.text[:500]}")

        data = res.json()
        entries.extend(data.get("data", []))

        next_url = data.get("paging", {}).get("next")
        next_params = None  # `next` is already a fully-formed URL with query params baked in

        if next_url:
            time.sleep(RATE_LIMIT_SLEEP_S)

    return entries
