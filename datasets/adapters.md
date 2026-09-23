# Phase 2 data adapters

These attach legal public archives. They are not GitHub HTML scrapers and they do not mirror Software Heritage.

## GH Archive

- Site: https://www.gharchive.org/
- Use: public GitHub *event* metadata (pushes, PRs), not file contents
- Access: hourly JSON dumps (`https://data.gharchive.org/YYYY-MM-DD-H.json.gz`) or BigQuery `githubarchive`

`GhArchiveAdapter.fetch_velocity(repo)` reads local dumps from `AETHER_GHARCHIVE_DIR` (or an explicit `dumps=` list) and returns `commits_per_week` plus actor count.

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
- Web API: `https://archive.softwareheritage.org/api/1/`
- Use: legal historical commit/directory graphs identified by SWHIDs
- Respect bulk-access terms; do not treat the archive as a mirror
- Content blobs are **not** fetched here. License-allowlisted clones still go through local git ingest.

`SoftwareHeritageAdapter.fetch_history(origin_url)` walks origin → visits → snapshot → revision → directory.

## Seed corpus

Checked-in manifest: [`datasets/corpus/manifest.json`](corpus/manifest.json)

| Repo | SPDX |
| --- | --- |
| https://github.com/lukeed/clsx | MIT |
| https://github.com/pallets/markupsafe | BSD-3-Clause |
| https://github.com/encode/httpcore | BSD-3-Clause |

## Training export

```bash
aether export-evolution --out datasets/evolution.jsonl
aether train-time-machine --in datasets/evolution.jsonl --out data/time_machine.json
```

Set `AETHER_MODEL_PATH` to the trained file so `ForecastBundle.heuristic` is `false`.
