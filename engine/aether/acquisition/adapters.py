"""Legal Phase-2 adapters: GH Archive dumps and Software Heritage Web API. No HTML scrape."""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from aether.config import settings


Json = dict[str, Any]
HttpGet = Callable[[str], Any]


class GhArchiveAdapter:
    """Velocity from GH Archive hourly JSON dumps (https://www.gharchive.org/)."""

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

    DUMP_URL = "https://data.gharchive.org/{stamp}.json.gz"

    def __init__(self, dump_dir: Path | None = None) -> None:
        self.dump_dir = Path(dump_dir) if dump_dir else settings.gharchive_dir

    def fetch_velocity(self, repo: str, dumps: Sequence[Path] | None = None) -> dict[str, float]:
        """Return commits/week and actor count from local (or passed) GH Archive dumps."""
        paths = list(dumps) if dumps is not None else self._discover_dumps()
        if not paths:
            raise FileNotFoundError(
                "No GH Archive dumps. Set AETHER_GHARCHIVE_DIR or pass dumps= to fetch_velocity."
            )
        repo_key = repo.strip().lower().removeprefix("https://github.com/").removesuffix(".git")
        pushes = 0
        commits = 0
        actors: set[str] = set()
        stamps: list[datetime] = []
        for path in paths:
            for event in iter_gharchive_events(path):
                if event.get("type") != "PushEvent":
                    continue
                name = str((event.get("repo") or {}).get("name") or "").lower()
                if name != repo_key:
                    continue
                pushes += 1
                payload = event.get("payload") or {}
                commits += len(payload.get("commits") or [])
                actor = (event.get("actor") or {}).get("login")
                if actor:
                    actors.add(str(actor))
                created = event.get("created_at")
                if created:
                    stamps.append(_parse_iso(str(created)))
        weeks = _span_weeks(stamps)
        commit_count = commits or pushes
        return {
            "commits_per_week": round(commit_count / weeks, 4),
            "actors": float(len(actors)),
            "push_events": float(pushes),
            "weeks": weeks,
        }

    def _discover_dumps(self) -> list[Path]:
        if not self.dump_dir or not self.dump_dir.is_dir():
            return []
        out: list[Path] = []
        for pattern in ("*.json.gz", "*.jsonl", "*.json"):
            out.extend(sorted(self.dump_dir.glob(pattern)))
        return out


class SoftwareHeritageAdapter:
    """Revision/directory chain via the Software Heritage Web API. Not a mirror."""

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

    def __init__(self, api_base: str | None = None, http_get: HttpGet | None = None) -> None:
        self.api_base = (api_base or settings.swh_api_base).rstrip("/")
        self.http_get = http_get or _http_get_json

    def fetch_history(self, origin_url: str, *, max_visits: int = 5) -> list[dict[str, Any]]:
        """Return revision/directory rows for an origin. Metadata only — no blob fetch."""
        encoded = quote(origin_url, safe="")
        origin = self.http_get(f"{self.api_base}/origin/{encoded}/get/")
        if not isinstance(origin, dict) or origin.get("exception") == "NotFoundExc":
            raise FileNotFoundError(f"SWH origin not found: {origin_url}")
        visits = self.http_get(f"{self.api_base}/origin/{encoded}/visits/?per_page={max_visits}")
        if not isinstance(visits, list):
            visits = []
        rows: list[dict[str, Any]] = []
        for visit in visits[:max_visits]:
            snapshot_id = visit.get("snapshot")
            if not snapshot_id:
                continue
            snap = self.http_get(f"{self.api_base}/snapshot/{snapshot_id}/")
            branches = (snap or {}).get("branches") or {}
            target = _preferred_revision(branches)
            if not target:
                continue
            rev = self.http_get(f"{self.api_base}/revision/{target}/")
            if not isinstance(rev, dict):
                continue
            directory = rev.get("directory") or ""
            rows.append(
                {
                    "origin": origin_url,
                    "visit_date": visit.get("date") or "",
                    "snapshot": f"swh:1:snp:{snapshot_id}",
                    "revision": f"swh:1:rev:{target}",
                    "directory": f"swh:1:dir:{directory}" if directory else "",
                    "date": rev.get("date") or visit.get("date") or "",
                    "message": (rev.get("message") or "")[:240],
                }
            )
        return rows


def iter_gharchive_events(path: Path) -> Iterable[Json]:
    raw = path.read_bytes()
    if path.name.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        return
    if text.startswith("["):
        payload = json.loads(text)
        for event in payload:
            if isinstance(event, dict):
                yield event
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        if isinstance(event, dict):
            yield event


def _preferred_revision(branches: dict[str, Any]) -> str:
    for name in ("refs/heads/main", "refs/heads/master", "HEAD"):
        node = branches.get(name) or {}
        if node.get("target_type") == "revision" and node.get("target"):
            return str(node["target"])
    for node in branches.values():
        if isinstance(node, dict) and node.get("target_type") == "revision" and node.get("target"):
            return str(node["target"])
    return ""


def _http_get_json(url: str) -> Any:
    req = Request(url, headers={"User-Agent": "Aether/0.1 (+https://github.com/pisigmac/Aether)", "Accept": "application/json"})
    with urlopen(req, timeout=30) as res:  # noqa: S310 — SWH API only, caller supplies URL
        return json.loads(res.read().decode("utf-8"))


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _span_weeks(stamps: list[datetime]) -> float:
    if len(stamps) < 2:
        return 1.0
    stamps = sorted(stamps)
    days = max((stamps[-1] - stamps[0]).total_seconds() / 86400.0, 1.0)
    return max(days / 7.0, 1.0 / 7.0)
