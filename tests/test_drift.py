import copy
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
import clean

ROOT = Path(__file__).resolve().parents[1]


class DriftReview(unittest.TestCase):
    def configuration(self):
        cfg = json.loads((ROOT / "pipeline_config.json").read_text())
        cfg["_review"] = []
        cfg["_encodings"] = {}
        return cfg

    def test_new_file_is_visible_not_ingested(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            shutil.copytree(ROOT / "raw", raw)
            (raw / "unrecognized.csv").write_text("unknown,value\nx,1\n")
            cfg = self.configuration()
            clean.inspect_inputs(raw, ROOT / "geography", cfg)
            flags = [r for r in cfg["_review"] if r["category"] == "unknown_file"]
            self.assertEqual([r["source"] for r in flags], ["unrecognized.csv"])
            self.assertFalse(any(r["blocking"] for r in cfg["_review"]))

    def test_renamed_missing_new_columns_block_publication(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            shutil.copytree(ROOT / "raw", raw)
            file = raw / "labor.zip"
            with zipfile.ZipFile(file) as archive:
                contents = {name: archive.read(name) for name in archive.namelist()}
            member = next(name for name in contents if name.endswith("-Data.csv"))
            self.assertIn(b'"GEO_ID"', contents[member])
            contents[member] = contents[member].replace(b'"GEO_ID"', b'"GEOID"', 1)
            with zipfile.ZipFile(file, "w") as archive:
                for name, content in contents.items():
                    archive.writestr(name, content)
            output = Path(td) / "output"
            output.mkdir()
            (output / "accepted.marker").write_text("unchanged")
            result = clean.run(ROOT / "pipeline_config.json", raw, output)
            self.assertEqual(result, 2)
            self.assertEqual((output / "accepted.marker").read_text(), "unchanged")
            report = json.loads((output / "review_report.json").read_text())
            changes = [r for r in report["items"] if r["category"] == "schema_changed"]
            self.assertTrue(report["blocking"])
            self.assertEqual(len(changes), 1)
            detail = json.loads(changes[0]["detail"])
            self.assertEqual(detail["missing"], ["GEO_ID"])
            self.assertEqual(detail["new"], ["GEOID"])
            self.assertTrue(detail["possible_renames"])


if __name__ == "__main__":
    unittest.main()
