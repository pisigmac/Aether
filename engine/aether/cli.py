from __future__ import annotations

import argparse
import json
from pathlib import Path

from aether.config import settings
from aether.corpus import DEFAULT_MANIFEST, parse_local_overrides, seed_corpus
from aether.eval import evaluate_time_machine
from aether.export import export_evolution, load_evolution_jsonl
from aether.physics.predictor import HeuristicPredictor, mae, train_linear
from aether.storage.db import AetherDB


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aether", description="Aether engine CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    exp = sub.add_parser("export-evolution", help="Dump Evolution Records for training")
    exp.add_argument("--out", required=True)
    exp.add_argument("--db", default="")
    exp.add_argument("--format", choices=("jsonl", "parquet"), default="jsonl")

    train = sub.add_parser("train-time-machine", help="Fit the Phase 2 linear predictor")
    train.add_argument("--in", dest="source", required=True)
    train.add_argument("--out", required=True)

    seed = sub.add_parser("seed-corpus", help="Ingest the license-filtered seed corpus")
    seed.add_argument("--db", default="")
    seed.add_argument("--manifest", default="")
    seed.add_argument("--data-dir", default="")
    seed.add_argument("--max-samples", type=int, default=12)
    seed.add_argument("--lookback-months", type=int, default=36)
    seed.add_argument("--local", action="append", default=[], metavar="NAME=PATH")
    seed.add_argument("--fetch-swhids", action="store_true")

    ev = sub.add_parser("eval-time-machine", help="Frozen hold-out MAE vs heuristic")
    ev.add_argument("--in", dest="source", required=True)
    ev.add_argument("--out", default="")
    ev.add_argument("--test-fraction", type=float, default=0.3)

    args = parser.parse_args(argv)
    if args.cmd == "export-evolution":
        db_path = Path(args.db) if args.db else settings.data_dir / "aether.db"
        count = export_evolution(AetherDB(db_path), Path(args.out), args.format)
        print(f"wrote {count} evolution records to {args.out}")
        return 0
    if args.cmd == "train-time-machine":
        records = load_evolution_jsonl(Path(args.source))
        model = train_linear(records)
        model.save(Path(args.out))
        learned_mae = mae(records, model)
        heuristic_mae = mae(records, HeuristicPredictor())
        print(
            json.dumps(
                {
                    "model_id": model.model_id,
                    "training_records": model.training_records,
                    "learned_mae": round(learned_mae, 4),
                    "heuristic_mae": round(heuristic_mae, 4),
                    "beats_heuristic": learned_mae < heuristic_mae,
                    "pattern_head": bool(model.pattern_weights),
                    "path": args.out,
                }
            )
        )
        return 0
    if args.cmd == "seed-corpus":
        db_path = Path(args.db) if args.db else settings.data_dir / "aether.db"
        manifest = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST
        data_dir = Path(args.data_dir) if args.data_dir else None
        rows = seed_corpus(
            AetherDB(db_path),
            manifest,
            lookback_months=args.lookback_months,
            max_samples=args.max_samples,
            local_overrides=parse_local_overrides(args.local),
            data_dir=data_dir,
            fetch_swhids=args.fetch_swhids,
        )
        print(json.dumps({"db": str(db_path), "repos": rows}, indent=2))
        return 0 if all(row.get("ok") for row in rows) else 1
    if args.cmd == "eval-time-machine":
        records = load_evolution_jsonl(Path(args.source))
        report = evaluate_time_machine(records, args.test_fraction)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            report["path"] = args.out
        print(json.dumps(report))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
