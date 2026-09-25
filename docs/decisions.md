# Decisions

Append-only log of choices made while implementing backlog items. The backlog itself stays the ticket list. This file records why a choice was made.

## 2026-09-25 — P4-02 is Go, not Java

P4-01 was already done. The next unimplemented ticket was P4-02: a third language parser, Go or Java.

Go was picked.

- The ticket lists Go first.
- Repos ingested so far do not distinguish the two. None of them are Go or Java, so "the language users ingest most" does not pick a winner.
- `net/http` `HandleFunc`, plus Gin and chi verbs (`GET`, `Get`, and the other common verbs), map onto the HTTP contract the Python and TypeScript parsers already emit.
- Java stays the candidate if a fourth language is added later.

The parser writes the existing IR. The version is unchanged. An HTTP route uses `contract_id("http", path)`, so `fixtures/ir-contract/go/app.go` shares the `/orders` contract id with the Python and TypeScript toys.

Tree-sitter is the parser that runs when `tree-sitter-go` is installed. If that import or parse fails, a regex fallback still emits functions and `HandleFunc`-style routes. The unit test asserts the module was produced by tree-sitter, so a silent fallback does not pass as the grammar path.

`*_test.go` files are skipped, the same way `test_*.py` and `*.test.ts` already are.

Go imports that are not relative stay unresolved. That is the existing rule for non-Python specs. `net/http` is not turned into a resolved module.

`tree-sitter-go>=0.23.0` was added next to the existing Python and TypeScript grammars in `engine/pyproject.toml`.

Landing, ingest metadata, and the README language line now say Python, TypeScript, and Go. Those sentences were already claiming the parsed languages, so leaving Go off would have made the product page wrong.

Nothing was committed.

## 2026-09-25 — P4-04 OpenAPI binds before name matching

P4-02 was done. The next P0 was P4-04. P4-03 is a fourth language and is P1, so it stayed later.

`link_contracts` already read `openapi.json` and created contract nodes, then still joined TypeScript fetches to Python routes by normalized path. The spec was not used for the join.

The new order:

- A frontend fetch that matches an OpenAPI path binds to that contract at weight 3.0. Butterfly already caps edge weight at 3.0, so this is the highest confidence the graph can express. The frontend service edge for that hit is 1.5.
- A concrete fetch such as `/orders/9` matches a template such as `/orders/{id}`. Exact spec paths win over templates. If several templates match, the one with fewer parameters wins.
- If the spec has no path for that fetch, the old Python name match stays at weight 2.5, and the frontend service edge stays at 1.0.
- If neither matches, the edge stays `unresolved` at 0.4.
- Repos with no `openapi.json` keep the previous edges. `fixtures/polyglot-debt` has no spec, so its snapshot hashes do not move.
- Go stays a backend parser. It is not treated as a frontend fetch client.
- Spec files stay the three JSON paths already loaded (`openapi.json`, `backend/openapi.json`, `docs/openapi.json`). YAML was not added.

The IR version is unchanged. Nothing was committed.

## 2026-09-25 — P4-03 is Java

P4-04 was done. The next row was P4-03, a fourth language on the same IR harness. Java was already the candidate left when Go was chosen for P4-02.

The parser emits a module, a method symbol, and an HTTP contract. Mapping annotations are Spring `@GetMapping`, `@PostMapping`, `@PutMapping`, `@PatchMapping`, `@DeleteMapping`, `@RequestMapping`, and JAX-RS `@Path`. A class-level `@RequestMapping` prefixes the method path, so `@RequestMapping("/api")` plus `@GetMapping("/orders")` is `/api/orders`. The orders fixture has no class prefix, so its contract id matches Python, TypeScript, and Go.

Annotations are read only from that declaration's `modifiers` node. Reading the whole class would treat the method mapping as the class prefix and double the path.

`*Test.java` and `*Tests.java` are skipped, the same way `*_test.go` is skipped. Java imports are not relative, so they stay unresolved. Tree-sitter is the path the unit test asserts. A regex fallback covers methods and mapping annotations if the grammar package is missing.

The IR version is unchanged. The landing sentence, ingest description, and README language line now include Java. Nothing was committed.

## 2026-09-25 — P4-05 missing index needs a lookup

P4-03 was done. The next row was P4-05. `detect_patterns` added `missing_index` whenever any schema node existed. That is the behavior the ticket rejects.

The flag is now set on the schema node, and the pattern label is copied from that flag.

A column is a lookup when SQLAlchemy marks it `ForeignKey` or a query filters, orders, or joins on it; when a Prisma `@relation` lists it in `fields`; or when SQL declares a foreign key, a `WHERE`, or a `JOIN` on it. It is indexed when SQLAlchemy sets `primary_key`, `index`, or `unique`, when `__table_args__` or `Table` carries an `Index`, when Prisma uses `@id`, `@unique`, `@@index`, `@@unique`, or `@@id`, or when SQL declares a primary key, a unique constraint, or `CREATE INDEX`. `missing_index` is true only when a lookup is outside that set.

A table with columns and no lookup stays clear. The planted polyglot changeset can still set the flag by hand. `.prisma` and `.sql` files are read for this evidence only. They do not become language modules, so a long schema file is not a god module.

Snapshot hashes ignore node extras, so this does not change hashes by itself. Cost and the forecast narrative can drop `missing_index` on repos whose only evidence was "a table exists." The IR version is unchanged. Nothing was committed.

## 2026-09-25 — P4-06 no Rust kernel

P4-05 was done. The next row was P4-06. Phase 1 did not record a millisecond number. The phase goal is that large graphs stay interactive, so the bar is one Butterfly horizon: 250 ms p95 at 10,000 nodes and 800 ms p95 at 50,000. Those bars sit under the NetworkX timings and above run-to-run noise.

NetworkX `snapshot_graph` was the cost, not the decay walk. A horizon only travels a few hops before intensity drops below 0.08. Replacing that build inside `propagate` with a Python adjacency list meets the bar (79.9 ms and 398.1 ms). Metrics and cycle detection still use NetworkX.

A Rust kernel was not added. The decay numbers on a weight-1 chain are unchanged. Nothing was committed.

## 2026-09-25 — P4-07 sampling stays even unless asked

P4-06 was done. The next row was P4-07. History was already an even sample under the snapshot cap. That path stays the default so existing ingests do not change.

Three other policies are chosen per ingest and stored on the universe as `sample_policy` and `sample_every`. Old universe payloads still load: both fields have defaults, and `ir_version` stays 1.

- Weekly keeps the newest commit in each ISO week.
- Every Nth walks newest-first and keeps index 0, N, 2N, so the tip is always in the set. N is at least 1.
- Tags use the tagged commit, including annotated tags. If the lookback window has no tags, the sample is HEAD and the ingest warning says so.

The cap still applies after the policy. The ingest form sends the choice. Nothing was committed.

## 2026-09-25 — P5-01 calls OpenDesk and does not store passwords

P4-07 was done. P5-01 is suite SSO. OpenDesk Auth on port 8090 already issues RS256 tokens and publishes JWKS. Membrane is the existing consumer. Aether follows that contract instead of a local user table.

Auth code is its own package and pages:

- `engine/aether/auth/` verifies the bearer token and exposes `GET /v1/session`
- `web/lib/auth.ts` posts email and password to OpenDesk `/v1/auth/login` and keeps only the access token
- `web/app/(console)/login/` is the sign-in page and the OAuth callback

The engine checks `iss`, `aud` (`aether`), and `exp` with the JWKS key. `org_id` comes from the token, or from `X-Org-ID` when the caller sends it. Mutating routes (create universe, start or cancel a job, changeset, ghost run) return 401 when `AETHER_AUTH_JWKS_URL` is set and the bearer token is missing or invalid. Reads stay open. When that URL is empty, local ingest stays open so a laptop without OpenDesk still works. Nothing was committed.

## 2026-09-25 — P5-02 scopes a universe to its org

P5-01 was done. P5-02 is who can see a universe.

`org_id` is stored on the universe. It defaults to empty, so older database rows and older payloads still load. `ir_version` stays 1. Opening an existing SQLite file adds the column.

A create or a job copies the org from the signed-in principal. With OpenDesk off, that value stays empty and list, get, and delete stay open, matching the local-ingest rule from P5-01.

With OpenDesk on, list returns only that org. Get and delete of another org's id return 404, the same as a missing id. Forecast, graph, changeset, and ghost runs use that same check, so knowing an id is not enough to read or change another org's universe. The ingest page lists the universes the caller can see and can delete one after a confirm. Nothing was committed.

## 2026-09-25 — P5-03 keeps the queue in SQLite and runs it in another process

P5-02 was done. P5-03 is hosted ingest. The queue was a dict in the API process, so a restart forgot every job and the clone ran on an API thread.

The queue is a `jobs` table in the same SQLite file as the universes. Redis was not added. A laptop already has this database, and Postgres is a later ticket.

`POST /v1/jobs` only inserts a queued row. The API process starts `python -m aether.worker`, which claims a row and runs clone and parse. Set `AETHER_INGEST_WORKER=0` and run `aether worker` when the worker should be a separate service. Two workers can claim safely: the update matches `status = queued`.

A job left `running` by a dead process is queued again on worker start, unless that process is still alive. Cancel still wins over a later progress write. With OpenDesk on, list, get, and cancel follow the job's org. Nothing was committed.

## 2026-09-25 — P5-04 uses Postgres for the universe store and leaves jobs in SQLite

P5-03 was done. P5-04 is where universes, evolution, and forecasts live once more than one machine is writing them.

`AETHER_DATABASE_URL` empty means the existing SQLite file. That stays the laptop default, including `docker compose`. A `postgresql://` URL stores universes, snapshots, evolution, changesets, and forecasts in Postgres. Snapshots and changesets move with the universe because delete and forecast read them from the same database.

Ingest jobs stay in SQLite. The queue is a single-host worker claim, and P5-03 already made that durable without a second server. The API and the worker both call `open_database`, so they follow the same URL. Nothing was committed.

## 2026-09-25 — P5-05 records the license decision on the same database as the universe

P5-04 was done. P5-05 is who ingested what.

The row is written in `build_universe`, so a direct create and a worker job both record it. The actor is the OpenDesk email when someone is signed in, and `local` when OpenDesk is off. The target is the path or URL that was requested, not the clone directory. The license decision is `allowed`, `unknown` (no recognized license, ingest continued), or `rejected` (outside the allowlist, ingest stopped).

The table lives with universes, so it follows SQLite or Postgres. `GET /v1/audit` returns that org's rows when OpenDesk is on. The ingest page lists them. Nothing was committed.

## 2026-09-25 — Live bar uses the job and the +8 month cell

The bar sits in the dashboard shell so it stays visible on Radar, Butterfly, Ghost Lab, Cost Horizon, and Ingest.

While a job is queued or running, the bar shows that job's percent and stage. It does not show a pressure number until a forecast exists. When the job this session was watching finishes, the bar follows that universe.

After that, the bar shows the hottest cell on the frame nearest +8 months: path, calm / watch / high-pressure (or storm when that cell is in a collision), and pressure. The link opens Radar. A failed ingest with no forecast opens Ingest and shows the error. An older finished job does not replace the universe already on screen.

This is the dashboard bar. It is not an editor client, and P5-08 stays later. Nothing was committed.

## 2026-09-25 — Live bar sits outside the page and reads the Aether checkout

The first bar lived inside the header and showed one truncated line for whatever universe Radar had open.

The bar is now fixed to the bottom, outside the header and outside the page body. When a universe was ingested from a checkout named `Aether`, that universe is the reading, because that is the repo open in this workspace. The line is still the hottest cell nearest +8 months, and the narrative plus the next three modules are on the bar. A running ingest still replaces that reading with percent and stage. `docs/live-bar.md` is the feature note. Nothing was committed.

## 2026-09-25 — Live bar is a desktop strip plus an IDE plugin

The dashboard strip cannot see a repo change in the editor. The installable bar is a separate always-on-top window, `aether livebar`, and `ide/aether-livebar` writes the focused workspace to `~/.aether/live-repo`.

`GET /v1/live?repo=` is the reading both sides share. An exact checkout path matches a universe. A directory name matches only when it is unique. A queued or running job for that repo returns percent and stage with pressure left empty. The dashboard strip stays where it is. Nothing was committed.

## 2026-09-26 — CI publishes kaether and builds the VSIX

`.github/workflows/release.yml` tests the SDK and packages `ide/aether-livebar` on pushes to `dev` and `main`, and on pull requests. The VSIX is an Actions artifact. A published GitHub Release also attaches that VSIX to the release and publishes the `sdk` package, `kaether`, to PyPI.

PyPI auth is a trusted publisher for workflow `release.yml`, with no environment name and no token in the repo. The engine package is not published. A release fails if that version of kaether is already on PyPI. Nothing was committed.
