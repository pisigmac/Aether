# polyglot-debt

Tiny FastAPI + TypeScript fixture used to demo Aether.

A planted “harmless” schema change (`orders.status` + `orders.metadata`) plus an unbounded `GET /orders` list is the 8-month frontend bottleneck story.

Run `python seed_git.py` once to create the chronological git history Aether samples.
