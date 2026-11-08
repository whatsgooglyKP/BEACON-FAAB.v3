import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class Integration(unittest.TestCase):
    def test_golden_batch_and_idempotence(self):
        self.assertTrue((ROOT / "clean.py").exists(), "Reusable cleaner is absent")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fresh"
            cmd = [
                str(ROOT / ".venv/bin/python"),
                str(ROOT / "clean.py"),
                "--config",
                str(ROOT / "pipeline_config.json"),
                "--output",
                str(out),
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            baseline = ROOT / "audited_baseline"
            for filename in ["tract_clean.parquet", "tract_all_sources.parquet"]:
                old = pd.read_parquet(baseline / filename)
                new = pd.read_parquet(out / filename)
                pd.testing.assert_frame_equal(
                    new[old.columns],
                    old,
                    check_dtype=False,
                    check_exact=False,
                    rtol=1e-12,
                    atol=1e-12,
                )
            self.assertEqual(
                set(f.name for f in baseline.iterdir())
                - set(f.name for f in out.iterdir()),
                set(),
            )
            first = {
                f.name: f.read_bytes()
                for f in out.iterdir()
                if f.suffix in [".csv", ".geojson"]
                and f.name not in ["review_report.csv"]
            }
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.assertEqual(first, {name: (out / name).read_bytes() for name in first})
            report = json.loads((out / "review_report.json").read_text())
            self.assertFalse(report["blocking"])


if __name__ == "__main__":
    unittest.main()
