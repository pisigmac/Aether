# Phase 2 data adapters

These are **not** on the forecast path in Phase 1. They exist so bulk training can attach later without scraping.

## GH Archive

- Site: https://www.gharchive.org/
- Use: public GitHub *event* metadata (pushes, PRs), not file contents
- Access: hourly JSON dumps or BigQuery `githubarchive`

Example (also on `GhArchiveAdapter.EXAMPLE_QUERY`):

```sql
SELECT repo.name, COUNT(*) AS push_events
FROM `githubarchive.day.20260101`
WHERE type = 'PushEvent'
GROUP BY repo.name
ORDER BY push_events DESC
LIMIT 20
```

## Software Heritage Graph

- Docs: https://docs.softwareheritage.org/devel/swh-export/graph/
- Use: legal historical commit/directory graphs identified by SWHIDs
- Respect bulk-access terms; do not treat the archive as a mirror

Phase 1 ingest is local `git` + a license allowlist (`MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`).
