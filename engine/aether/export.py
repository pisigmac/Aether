from __future__ import annotations

import json
from pathlib import Path

from aether.ir.models import EvolutionRecord
from aether.storage.db import AetherDB


def export_evolution(db: AetherDB, out: Path, fmt: str = "jsonl") -> int:
    records = db.list_all_evolution()
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        return _write_parquet(records, out)
    with out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec.model_dump_json() + "\n")
    return len(records)


def load_evolution_jsonl(path: Path) -> list[EvolutionRecord]:
    rows: list[EvolutionRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(EvolutionRecord.model_validate_json(line))
    return rows


def _write_parquet(records: list[EvolutionRecord], out: Path) -> int:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("Parquet export needs pyarrow. pip install pyarrow or use --format jsonl.") from exc
    table = pa.Table.from_pylist([r.model_dump() for r in records])
    pq.write_table(table, out)
    return len(records)
