import unittest
from pathlib import Path


class CleanerContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert Path("clean.py").exists(), "Reusable clean.py has not been implemented"
        import clean

        cls.clean = clean

    def test_geoid_normalization(self):
        f = self.clean.normalize_geoid
        self.assertEqual(f("1400000US12095016700"), "12095016700")
        self.assertEqual(f("12095016700"), "12095016700")
        self.assertEqual(f("1001020100"), "01001020100")
        self.assertEqual(f("167.00", state="12", county="095"), "12095016700")
        self.assertEqual(f("12095016700.0"), "12095016700")
        for bad in ["167.00", "32801", "12095", "1.2095e10", "120950167001"]:
            with self.assertRaises(ValueError):
                f(bad)

    def test_sentinels_and_censoring(self):
        f = self.clean.normalize_value
        self.assertEqual(f("0")[0], 0)
        self.assertEqual(f("-23")[0], -23)
        for raw in ["(X)", "N", "-", "**", "***", "-666666666", "N/A", "*"]:
            value, reason, lower = f(raw)
            self.assertIsNone(value)
            self.assertTrue(reason)
        self.assertEqual(f("250,000+"), (None, "topcoded_lower_bound", 250000.0))
        self.assertEqual(f("12%", unit="percent")[0], 12)
        self.assertEqual(f("nonsense")[1], "unparsed_value")

    def test_explicit_units(self):
        f = self.clean.normalize_unit
        self.assertEqual(f(0.42, "fraction"), 42)
        self.assertEqual(f(0.42, "percent"), 0.42)
        self.assertEqual(f(5, "percentage_points"), 5)
        self.assertEqual(f(12, "count"), 12)
        with self.assertRaises(ValueError):
            f(0.5, "unknown_rate")

    def test_duplicate_conflicts(self):
        import pandas as pd

        frame = pd.DataFrame({"geoid": ["12095016700"] * 2, "value": [3, 3]})
        result, removed = self.clean.deduplicate(frame)
        self.assertEqual((len(result), removed), (1, 1))
        frame.loc[1, "value"] = 4
        with self.assertRaises(ValueError):
            self.clean.deduplicate(frame)

    def test_checked_reader_quarantines_new_fields(self):
        import tempfile
        import pandas as pd

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.csv"
            path.write_text("GEOID,value,new_field\n12095016700,3,not-approved\n")
            config = {
                "accepted_schemas": {"sample.csv": ["GEOID", "value"]},
                "geoid": {"full_id_aliases": ["GEOID"]},
                "_review": [],
                "_encodings": {},
            }
            result = self.clean.read_checked(path, config)
            self.assertEqual(list(result.columns), ["GEOID", "value"])
            # Preflight is responsible for the visible schema review entry.
            self.assertEqual(
                self.clean.schema_diff(
                    config["accepted_schemas"]["sample.csv"],
                    ["GEOID", "value", "new_field"],
                )["new"],
                ["new_field"],
            )

    def test_checked_reader_rejects_invalid_geography_and_conflicts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.csv"
            config = {
                "accepted_schemas": {"sample.csv": ["GEOID", "value"]},
                "geoid": {"full_id_aliases": ["GEOID"]},
                "_review": [],
                "_encodings": {},
            }
            for content in [
                "GEOID,value\n32801,3\n",
                "GEOID,value\n12095016700,3\n12095016700,4\n",
            ]:
                path.write_text(content)
                with self.assertRaises(ValueError):
                    self.clean.read_checked(path, config)

    def test_encoding_is_detected_for_the_full_file_with_header_only_scan(self):
        content = "GEOID,value,name\n12095016700,1,Peña\n".encode("cp1252")
        data, encoding = self.clean.read_csv_bytes(content, headers_only=True)
        self.assertEqual(encoding, "cp1252")
        self.assertEqual(list(data.columns), ["GEOID", "value", "name"])
        self.assertEqual(len(data), 0)

    def test_percent_symbol_cannot_relabel_a_count(self):
        with self.assertRaises(ValueError):
            self.clean.normalize_value("12%", unit="count")

    def test_schema_diff(self):
        diff = self.clean.schema_diff(
            ["GEO_ID", "NAME", "value"], ["GEOID", "NAME", "new_value"]
        )
        self.assertEqual(diff["missing"], ["GEO_ID", "value"])
        self.assertEqual(diff["new"], ["GEOID", "new_value"])
        self.assertTrue(diff["possible_renames"])


if __name__ == "__main__":
    unittest.main()
