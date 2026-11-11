"""Telemetry: one row per experiment run and one row per model call.

Written twice, on purpose: an append-only JSONL file (easy to diff / grep)
and a SQLite database (easy to query). Neither ever contains credentials —
rows are built from an explicit allow-list of fields.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

RUNS = Path(__file__).parent / "runs"
CALL_FIELDS = ["run_id", "config_name", "config_hash", "data_fingerprint", "mode", "model", "prompt_version",
               "temperature", "seed", "repeat", "geoid", "rank", "latency_s", "prompt_tokens", "output_tokens",
               "thought_tokens", "cost_usd", "retries", "error", "data_quality_flags", "shaky_numbers",
               "shaky_asked", "faithful", "unsupported_numbers", "wrong_places", "confidence_correct", "ts"]
RUN_FIELDS = ["run_id", "config_name", "config_hash", "data_fingerprint", "mode", "factor", "started", "finished",
              "n_calls", "n_errors", "total_retries", "summary"]


class Telemetry:
    def __init__(self, root: Path = RUNS):
        root.mkdir(exist_ok=True)
        self.jsonl = root / "telemetry.jsonl"
        self.db = sqlite3.connect(root / "telemetry.sqlite")
        self.db.execute(f"CREATE TABLE IF NOT EXISTS calls ({', '.join(CALL_FIELDS)})")
        self.db.execute(f"CREATE TABLE IF NOT EXISTS runs ({', '.join(RUN_FIELDS)})")

    def _write(self, table, fields, row):
        clean = {k: row.get(k) for k in fields}
        clean.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        with self.jsonl.open("a") as fh:
            fh.write(json.dumps({"table": table, **clean}) + "\n")
        vals = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in (clean.get(k) for k in fields)]
        self.db.execute(f"INSERT INTO {table} VALUES ({', '.join('?' * len(fields))})", vals)
        self.db.commit()

    def call(self, row):
        row.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        self._write("calls", CALL_FIELDS, row)

    def run(self, row):
        self._write("runs", RUN_FIELDS, row)

    def reset(self):
        self.db.execute("DELETE FROM calls"); self.db.execute("DELETE FROM runs"); self.db.commit()
        self.jsonl.write_text("")
