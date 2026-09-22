"""Phase-2 adapters. Interfaces + documented queries only — not on the forecast path."""

from __future__ import annotations


class GhArchiveAdapter:
    """Legal event/velocity metadata from GH Archive (https://www.gharchive.org/)."""

    EXAMPLE_QUERY = """
    -- BigQuery public dataset githubarchive.day
    SELECT
      repo.name,
      COUNT(*) AS push_events,
      COUNT(DISTINCT actor.login) AS actors
    FROM `githubarchive.day.20260101`
    WHERE type = 'PushEvent'
    GROUP BY repo.name
    ORDER BY push_events DESC
    LIMIT 20
    """

    def fetch_velocity(self, repo: str) -> float:
        raise NotImplementedError(
            "GH Archive is a Phase 2 source. Use local git velocity in Phase 1."
        )


class SoftwareHeritageAdapter:
    """Legal historical graphs via Software Heritage (no scrape, no bulk mirror)."""

    EXAMPLE_QUERY = """
    -- Software Heritage Graph (Athena / swh-graph)
    -- Resolve an origin, then walk revisions:
    --   origin -> snapshot -> revision -> directory
    -- Identify inputs with SWHIDs and respect bulk-access terms.
    SELECT id, date, directory
    FROM revision
    WHERE id = crc64('swh:1:rev:<sha1>')
    LIMIT 1
    """

    def fetch_history(self, origin_url: str) -> list[dict]:
        raise NotImplementedError(
            "Software Heritage is a Phase 2 source. Use local git samples in Phase 1."
        )
