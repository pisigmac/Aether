# Commands

Append-only log of commands actually run while building Aether. Paths are relative to the repo root. Run engine tests from `engine/`. A pytest invocation from the repo root collects clones under `engine/data` and is the wrong command.

## 2026-09-25 — P4-02 Go parser

Install the Go grammar into the engine virtualenv:

```bash
cd engine && .venv/bin/python -m pip install 'tree-sitter-go>=0.23.0'
```

The first run failed. The retry that wrote into the virtualenv succeeded. See `docs/errors.md`.

Probe the grammar on a small `net/http` sample (package clause, function declaration, `http.HandleFunc("/orders", ...)`). This was a one-off interpreter session, not a checked-in script.

Parser, contract harness, and scan tests:

```bash
cd engine && .venv/bin/python -m pytest tests/test_ir_contract.py tests/test_parsers.py tests/test_scan.py -q --tb=short
```

Full engine suite after the parser was wired into the scan:

```bash
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

Result: 56 passed. Two existing warnings from FastAPI's Starlette test client. No product failure.

## 2026-09-25 — P4-04 OpenAPI linker

Linker tests, then the scan and IR contract tests, then the full engine suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_contracts.py tests/test_scan.py tests/test_ir_contract.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

The first focused run failed one new test. See `docs/errors.md`. After that fix, the full suite passed: 63 tests, same two Starlette warnings. No page changed, so the dashboard was not opened.

## 2026-09-25 — P4-03 Java parser

Install the Java grammar into the engine virtualenv:

```bash
cd engine && .venv/bin/python -m pip install 'tree-sitter-java>=0.23.0'
```

That install wrote into the virtualenv on the first try. A one-off interpreter session then printed the grammar nodes for a Spring controller (`class_declaration`, `method_declaration`, `annotation`, `string_literal`). `has_error` was false.

Parser, harness, and scan tests, then the full suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_ir_contract.py tests/test_parsers.py tests/test_scan.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

Result: 7 passed, then 64 passed. Same two Starlette warnings. The bulletin was opened at `http://127.0.0.1:13100/` because the hero line now names Java.

## 2026-09-25 — P4-05 missing index evidence

Index tests, physics, and parsers, then the full engine suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_indexes.py tests/test_physics.py tests/test_parsers.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

Both runs passed on the first try: 15, then 72. Same two Starlette warnings. No page changed, so the dashboard was not opened.

## 2026-09-25 — P4-06 diffusion budget

Time NetworkX graph build and `propagate` on sparse 10k and 50k graphs (one-off interpreter session, 7 calls). Then the budget test and the full suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_diffusion_budget.py tests/test_physics.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

The first budget assert failed. See `docs/errors.md`. After the adjacency-list walk, a 21-call measurement reported p95 79.9 ms at 10,000 nodes and 398.1 ms at 50,000. The full suite then passed: 74 tests, same two Starlette warnings. No page changed, so the dashboard was not opened.

## 2026-09-25 — P4-07 snapshot sampling

```bash
cd engine && .venv/bin/python -m pytest tests/test_acquisition.py tests/test_scan.py tests/test_api.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

Both passed on the first try: 14, then 80. Same two Starlette warnings. The ingest page at `http://127.0.0.1:13100/ingest` shows the sampling select. Choosing Every Nth commit reveals N (default 10). Choosing Tags only hides it. The jobs list on that page said "Failed to fetch", so a live ingest was not submitted.

## 2026-09-25 — P5-01 OpenDesk sign-in

Install the JWT library into the engine virtualenv, then auth tests and the full suite:

```bash
cd engine && .venv/bin/python -m pip install 'PyJWT[crypto]>=2.9.0'
cd engine && .venv/bin/python -m pytest tests/test_auth.py tests/test_api.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

7 passed, then 84 passed. Same two Starlette warnings. The sign-in page at `http://127.0.0.1:13100/login` posted toward OpenDesk on port 8090. OpenDesk was not running, so the page stayed on `/login` and showed "Failed to fetch".

## 2026-09-25 — P5-02 universe ownership

Ownership tests, then the full suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_ownership.py tests/test_api.py tests/test_auth.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

12 passed, then 89 passed. Same two Starlette warnings.

The engine was started on port 18100 so the dashboard could reach it. The ingest page at `http://127.0.0.1:13100/ingest` listed the local universes. Deleting the throwaway row `/tmp/p502-delete-me` removed it. The pandas universe and the Radar forecast for polyglot-debt stayed.

## 2026-09-25 — P5-03 ingest worker

Job tests, then the full suite:

```bash
cd engine && .venv/bin/python -m pytest tests/test_jobs.py tests/test_api.py tests/test_closeout.py tests/test_ownership.py tests/test_auth.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

26 passed, then 94 passed. Same two Starlette warnings.

The engine on port 18100 was restarted so it would spawn the worker. `POST /v1/jobs` with path `/tmp/aether-p503-missing` returned queued, then the worker marked it error. After another restart, `GET /v1/jobs/29522a8eead4` was still that error. The ingest page showed the row. The throwaway row was deleted afterward.

## 2026-09-25 — P5-04 Postgres storage

Install the driver, then the SQLite suite and the Postgres round trip:

```bash
cd engine && .venv/bin/python -m pip install 'psycopg[binary]>=3.2.0'
cd engine && .venv/bin/python -m pytest tests -q --tb=line -k 'not test_postgres_stores'
docker run -d --name aether-p504-pg -e POSTGRES_PASSWORD=aether -e POSTGRES_DB=aether -p 127.0.0.1:55432:5432 postgres:16
cd engine && AETHER_TEST_DATABASE_URL='postgresql://postgres:aether@127.0.0.1:55432/aether' .venv/bin/python -m pytest tests/test_postgres.py -q --tb=short
docker rm -f aether-p504-pg
```

94 passed with the Postgres test deselected. That test then passed against Postgres 16. The container was removed afterward.

## 2026-09-25 — P5-05 ingest audit

```bash
cd engine && .venv/bin/python -m pytest tests/test_audit.py tests/test_jobs.py tests/test_ownership.py tests/test_pipeline.py tests/test_api.py -q --tb=short
cd engine && .venv/bin/python -m pytest tests -q --tb=line
```

19 passed, then 97 passed and 1 skipped (Postgres, no URL set). Same two Starlette warnings.

The engine on port 18100 was restarted. `POST /v1/universes` with `/tmp/aether-p505-gpl` returned 403. `GET /v1/audit` recorded actor `local`, license `GPL-3.0`, decision `rejected`. The ingest page showed that row. The throwaway row and directory were removed afterward.

## 2026-09-25 — Live bar

No engine change. The dashboard on port 13100 was already running.

Checked in the browser at `http://127.0.0.1:13100/radar` and `/butterfly`. With universe `502c3373221f4039`, the bar read `backend/models.py · storm · P 1.08` and linked to `/radar`.

```bash
curl -s -X POST http://127.0.0.1:18100/v1/jobs -H 'Content-Type: application/json' -d '{"path":".../engine/data/clones/8c58669e945b"}'
```

While that job ran, the bar switched through `18% · Sampling git history`, `40% · Parsing snapshot 6/15`, and `84% · Recording evolution 11/15`, then back to a forecast cell. The selected universe was set back to `502c3373221f4039` afterward. Both jobs updated universes that were already in the store.

## 2026-09-25 — Live bar outside the page

No engine change. Dashboard already on port 13100.

Opened `http://127.0.0.1:13100/radar` and `/butterfly`. The bar is `position: fixed` at the bottom. It read the Aether checkout, not the universe Radar had open: `engine/aether/parsers/typescript_parser.py · high-pressure · P 1.80`, with `python_parser.py`, `api.py`, and `metrics.py` under it. The last page content cleared the bar by about 34px. Clicking the bar opened `/radar`.

## 2026-09-25 — Desktop live bar

```bash
cd engine && .venv/bin/python -m pytest tests/test_live.py -q --tb=line
```

5 passed. Same two Starlette warnings.

The engine on port 18100 was restarted so `GET /v1/live` is served. `aether livebar` was started on this Wayland session. With `~/.aether/live-repo` set to this checkout it printed `Aether  engine/aether/parsers/typescript_parser.py  high-pressure  P 1.80  +8mo`. Writing `/tmp/pandas` switched the line to `pandas  pandas/_config/config.py  high-pressure  P 2.21  +8mo`. The file was set back to this checkout afterward.
