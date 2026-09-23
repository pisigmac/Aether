# Aether backlog

Living tracker from Phase 1 (shipped) to the original product: a predictive physics engine for software architecture.

Status: `done` · `now` · `next` · `later` · `blocked` · `wont`

Priority: `P0` must-ship for that phase · `P1` should · `P2` nicety

Rules carried forward from Phase 1:

- No unauthorized scrape. Legal APIs and license allowlists only.
- Parsers never leak into physics or UI. Forecasts travel as `ForecastBundle`.
- Do not claim a model trained on millions of repos until that job exists.
- Ghost Lab stays labeled honest until real agents ship.
- Do not replace Ledger, ContextWeave, or GuardLoop. Call them.

---

## Phase map

| Phase | Name | Outcome | Status |
| --- | --- | --- | --- |
| 1 | Vertical slice | Ingest → IR → heuristic forecast → weather UI | **done** |
| 2 | Learned Time Machine | Legal corpus + first trained model on Evolution Records | **now** |
| 3 | Agentic Ghost Lab | Real ghost developers behind `GhostRunner`, gated | later |
| 4 | Polyglot + scale | More languages on IR v1; graph kernel if needed | later |
| 5 | Product | SSO, orgs, hosted ingest — the original brief is complete | later |

Five phases to the brief. Nothing after Phase 1 is scheduled. Work Phase 2 before 3 unless a ticket says otherwise. Phase 4 language parsers can start in parallel with late Phase 2 if IR stays stable.

---

## Phase 1 — Vertical slice

Shipped 2026-09-22. Closed here so later phases can point at seams.

| ID | Item | Status | Seams |
| --- | --- | --- | --- |
| P1-01 | IR v1 (`Node`, `Edge`, `Contract`, `Snapshot`, `Universe`, `ChangeSet`) | done | [`engine/aether/ir/models.py`](engine/aether/ir/models.py) |
| P1-02 | Legal local git ingest + license allowlist + snapshot sampler | done | [`engine/aether/acquisition/`](engine/aether/acquisition/) |
| P1-03 | Tree-sitter Python + TypeScript parsers → IR only | done | [`engine/aether/parsers/`](engine/aether/parsers/) |
| P1-04 | Heuristic Time Machine, Butterfly, Ghost Lab, Cost Horizon | done | [`engine/aether/physics/`](engine/aether/physics/) |
| P1-05 | Weather dashboard (Radar, Butterfly, Ghosts, Cost, Ingest) | done | [`web/`](web/) |
| P1-06 | Evolution Record rows in SQLite (`evolution` table) | done | [`datasets/SCHEMA.md`](datasets/SCHEMA.md), [`engine/aether/storage/db.py`](engine/aether/storage/db.py) |
| P1-07 | GH Archive + Software Heritage **stubs** | done | [`engine/aether/acquisition/adapters.py`](engine/aether/acquisition/adapters.py) |
| P1-08 | `GhostRunner` protocol (heuristic planners) | done | [`engine/aether/physics/ghosts.py`](engine/aether/physics/ghosts.py) |
| P1-09 | `polyglot-debt` fixture + planted schema PR | done | [`fixtures/polyglot-debt/`](fixtures/polyglot-debt/) |
| P1-10 | Async ingest jobs + live percent / stage | done | `POST /v1/jobs`, `GET /v1/jobs/{id}`, [`web/app/ingest/page.tsx`](web/app/ingest/page.tsx) |

---

## Phase 2 — Learned Time Machine

**Goal.** Forecasts come from a trained model on license-filtered chronological histories, not only exponential smoothing. Same IR. Same dashboard.

**Exit.** A held-out set of Evolution Records beats the Phase 1 heuristic on next-horizon `metric_vector` (mass, coupling, churn, cycles, god-module count, contract leaks). UI still says what the source is (`heuristic` vs `learned`).

### Data

| ID | Pri | Status | Item | Acceptance | Notes |
| --- | --- | --- | --- | --- | --- |
| P2-01 | P0 | now | Implement `GhArchiveAdapter.fetch_velocity` | Returns commits/week (and actor count) from GH Archive hourly dumps or BigQuery `githubarchive`. No HTML scrape. | Query lives on the stub. Use for velocity prior when local git is thin. |
| P2-02 | P0 | now | Implement `SoftwareHeritageAdapter.fetch_history` | Returns revision/directory chain for an origin via SWH graph / SWHIDs. Bulk-access terms and Ethical Charter respected. Content fetched only for allowlisted licenses. | Not a mirror of the archive. |
| P2-03 | P0 | now | License-filtered seed corpus (2–3 small OSS repos, then tens) | Each clone MIT / Apache-2.0 / BSD. Evolution Records written for every sample. Corpus manifest checked in under `datasets/` (URLs + SPDX + SWHIDs). | `aether seed-corpus` reads `datasets/corpus/manifest.json` (`clsx`, `markupsafe`, `httpcore`). Optional `--local NAME=PATH` and `--fetch-swhids`. |
| P2-04 | P0 | now | Training export | `aether export-evolution --out parquet` (or JSONL) dumps `evolution` rows with `horizon_target` filled. Schema matches [`datasets/SCHEMA.md`](datasets/SCHEMA.md). | This is the supervised table. Do not invent a second schema. |
| P2-05 | P1 | now | Ingest cancel + size caps | Job can be cancelled. Reject / warn above configurable file count, snapshot count, and clone size. Progress bar shows cancel. | `POST /v1/jobs/{id}/cancel`. Caps: `AETHER_MAX_SOURCE_FILES`, `AETHER_MAX_CLONE_BYTES`, `AETHER_MAX_SNAPSHOTS`. |
| P2-06 | P1 | now | Clone progress from `git --progress` | Percent during clone/fetch, not a flat 8–12% hold. | Git percent maps onto ingest 8–16. |
| P2-07 | P2 | now | Optional OSS allowlist clones in UI | Ingest page offers 3 documented demo URLs. | clsx, markupsafe, httpcore. Fills the URL field. |

### Model

| ID | Pri | Status | Item | Acceptance | Notes |
| --- | --- | --- | --- | --- | --- |
| P2-10 | P0 | now | Baseline regressor on `metric_vector` | Predict `horizon_target` from current vector + `delta_from_prev` + velocity. Beat heuristic MAE on a frozen split. | Residual + standardized features. Old absolute model files still load. |
| P2-11 | P0 | now | `TimeMachine` swap seam | `build_timeline` uses a `Predictor` protocol: heuristic default, learned if a model file is present. `ForecastBundle.heuristic` is `false` when learned. | Do not fork a second forecast payload. |
| P2-12 | P1 | now | Pattern-label model (optional head) | Predict `pattern_labels` at +K samples. Used to drive Cost Horizon drivers, not Radar copy. | Trained only when consecutive records carry labels. Heuristic Cost Horizon still uses `detect_patterns`. |
| P2-13 | P1 | now | Calibration + confidence | Each timeline cell can carry `pressure_lo` / `pressure_hi`. Radar fog when interval is wide. | Band widens with slope and months. Month 0 on a flat series is a point. Fog at width ≥ 0.6. |
| P2-14 | P2 | now | Narrative templates from predicted labels | Keep structured `narrative_kind`. Do not free-generate architecture fiction. | Heuristic timeline keeps the pressure narrative. Templates apply only when the pattern head returns labels. |

### Product / UX

| ID | Pri | Status | Item | Acceptance |
| --- | --- | --- | --- | --- |
| P2-20 | P0 | now | Source badge on Radar | “Heuristic from this repo’s history” vs “Learned model vN · trained on M Evolution Records”. |
| P2-21 | P1 | now | Job list | Ingest page shows recent jobs (percent, stage, error) from `GET /v1/jobs`. | In-memory store, newest first. Existing `GET /v1/jobs/{id}` unchanged. |
| P2-22 | P1 | now | Compare heuristic vs learned | Toggle on one universe. Same `ChangeSet`. | `GET /v1/universes/{id}/forecast?mode=heuristic\|learned`. Compare does not overwrite the cached auto forecast. |

### Phase 2 non-goals

- Millions of repos in one jump
- Wiring ghosts to LLMs
- New languages
- Auth / SaaS

---

## Phase 3 — Agentic Ghost Lab

**Goal.** Extensibility scores come from agents that actually try to attach a feature to a checkout (or a shadow IR + patch), not only planners.

**Exit.** At least four catalog intents run as real agents on `polyglot-debt` and one OSS repo. Each run has a verdict, files touched, and a trace id. UI still says “agent run”, never “simulated developer swarm” unless N is large and disclosed.

| ID | Pri | Status | Item | Acceptance | Depends |
| --- | --- | --- | --- | --- | --- |
| P3-01 | P0 | now | `GhostRunner` agent implementation | Second runner satisfies the same protocol as the heuristic planner. Catalog intents unchanged. | `AgentGhostRunner` attaches a shadow IR node. `run_ghost_lab()` still defaults to `HeuristicGhostRunner`. |
| P3-02 | P0 | now | GuardLoop gate | Every ghost session has a budget, loop detect, and secret scrub. No keys in Aether env — KeyMint. | `POST /v1/universes/{id}/ghosts` opens one GuardLoop task per agent lab (`max_loops`, strict scrub, loop-check). Heuristic forecast is unchanged. Bearer key is a request header, not an Aether setting. KeyMint still supplies that key when it is the broker. |
| P3-03 | P0 | now | TraceLens (or OTLP) per ghost | Each `GhostResult` carries `trace_id`. Dashboard links out. | Agent ghost sessions post one TraceLens trace when `AETHER_TRACELENS_URL` is set. The JWT is the `X-TraceLens-Key` header. Heuristic forecast stays untraced. |
| P3-04 | P0 | later | Sandbox checkout | Ghosts write in a worktree / temp clone, never the user’s dirty tree. | |
| P3-05 | P1 | later | IR-first ghosts (cheap path) | Agent may propose IR mutations only; physics re-scores without applying a full patch. | P3-01 |
| P3-06 | P1 | later | Intent pack v2 | Keep the 8 Phase 1 intents. Add `add_openapi_client`, `extract_service`, `add_queue`. | |
| P3-07 | P2 | later | Parallel ghosts with a cap | Configurable N (default 4, hard max 16). Copy discloses N. Not “thousands” until cost and GuardLoop say so. | P3-02 |
| P3-08 | P1 | later | Ghost Lab UI: run / replay / fail reason | Table already exists. Add run button, duration, trace link, artifact path. | |

### Phase 3 non-goals

- Unbounded LLM rewrite of the future codebase
- Replacing GuardLoop’s governance

---

## Phase 4 — Polyglot and scale

**Goal.** IR stays v1 (or a documented v2). More languages emit it. Large graphs stay interactive.

**Exit.** A third language (Go or Java) produces modules, symbols, and at least one contract kind. Butterfly on a 50k-node graph returns in a published budget, or a Rust kernel is justified with numbers.

| ID | Pri | Status | Item | Acceptance | Notes |
| --- | --- | --- | --- | --- | --- |
| P4-01 | P0 | later | IR contract test harness | Golden fixtures: Python / TS / (new lang) emit comparable nodes for the same toy app. | Prevents parser drift. |
| P4-02 | P0 | later | Third language parser (Go *or* Java — pick one) | Tree-sitter (or official) → IR only. | Prefer the language Aether users ingest most. |
| P4-03 | P1 | later | Fourth language | Same harness. | |
| P4-04 | P0 | later | OpenAPI-first contract linker | If `openapi.json` exists, frontend fetch paths bind to it with high confidence. Name-matching is fallback. Unresolved stays `unresolved`. | [`engine/aether/parsers/contracts.py`](engine/aether/parsers/contracts.py) |
| P4-05 | P1 | later | SQL / Prisma / SQLAlchemy index detection | `missing_index` is evidence-based, not “schema exists ⇒ missing”. | |
| P4-06 | P1 | later | Graph performance budget | Publish p95 for diffusion on 10k / 50k nodes. Rust kernel only if Python + networkx misses the budget. | Phase 1 note already said this. |
| P4-07 | P2 | later | Snapshot sampling policies | Weekly / every-Nth / tag-only, configurable per universe. | |
| P4-08 | P2 | later | IR v2 (only if forced) | Additive fields first. Bump `ir_version`. Old bundles still load. | Avoid a rewrite. |

---

## Phase 5 — Product

**Goal.** A team can run Aether on their repos without sharing a laptop. The original brief is complete: Time Machine, Butterfly, Ghosts, Cost — predictive, not reactive.

**Exit.** One org, two users, SSO, two universes, audit of who ingested what. Forecasts persist across sessions.

| ID | Pri | Status | Item | Acceptance | Notes |
| --- | --- | --- | --- | --- | --- |
| P5-01 | P0 | later | OpenDesk (or suite) SSO | Login, org, JWT. Engine rejects unauthenticated mutating routes. | Call as service. Do not invent a password scheme. |
| P5-02 | P0 | later | Universe ownership | List / get / delete scoped to org. | |
| P5-03 | P0 | later | Hosted ingest workers | Clone and parse off the API process. Jobs survive process restart (Redis or DB, not in-memory only). | Replaces [`engine/aether/jobs.py`](engine/aether/jobs.py) process memory. |
| P5-04 | P1 | later | Postgres for universes / evolution / forecasts | SQLite remains an embedded/dev option. | |
| P5-05 | P1 | later | Audit log | Who ingested which URL/path, when, license decision. | |
| P5-06 | P2 | later | Billing hook | Meter universes and ghost-minutes. Do not build a ledger — use existing billing if the suite has one. | After SSO. |
| P5-07 | P1 | later | GitHub App / PR comment | Bot posts +8 month narrative + Radar link on a PR. | The original “feed Aether a PR” surface. |
| P5-08 | P2 | later | IDE / Cursor mention | Thin client: open Radar for current repo. Dashboard stays the system of record. | |

### Phase 5 non-goals

- Building a new identity stack
- Training-data marketplace
- 3D globe visualizations

---

## Cross-cutting

Always allowed, any phase, if they do not skip phase exits.

| ID | Pri | Status | Item |
| --- | --- | --- | --- |
| X-01 | P1 | now | Keep `ForecastBundle` the only UI contract. Additive fields only. |
| X-02 | P1 | now | Tests on every parser / physics / job change. Fixture `polyglot-debt` stays green. |
| X-03 | P1 | now | Copy stays honest (`heuristic` vs `learned` vs `agent`). |
| X-04 | P2 | later | CI: engine pytest + web lint/typecheck + compose smoke. |
| X-05 | P2 | later | Catalog Aether in workspace `PROJECTS_INDEX.md` / portfolio docs. |
| X-06 | P1 | later | Nested-git dogfood: optional `git log -- <subdir>` when ingest root ≠ toplevel (Aether lives inside WorkSpace git). |

---

## Explicitly out

| Item | Why |
| --- | --- |
| Scraping GitHub HTML / raw mass clones of arbitrary licenses | Legal + Phase 1 contract |
| Claiming “trained on millions” before P2-10 ships | Honesty |
| Replacing Ledger / ContextWeave / GuardLoop | Complementary products |
| Unbounded ghost swarms | Cost, safety, GuardLoop |
| Chem / bio / exploit tooling | Not this product |

---

## How to use this file

1. When starting work, set the ticket to `now` and date it under **Log**.
2. When shipping, set `done` and add the PR / commit in **Log**.
3. Do not invent a Phase 6 until Phase 5 exit is met.
4. If a ticket needs a new IR field, add it here first (`X-01`).

### Log

| Date | Change |
| --- | --- |
| 2026-09-23 | Backlog created. Phase 1 closed. Phase 2 is the next workstream. |
| 2026-09-23 | Phase 2 P0 in progress on `dev`: GH Archive + SWH adapters, corpus manifest, export/train CLI, linear predictor, Radar source badge. |
