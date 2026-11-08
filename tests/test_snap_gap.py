import unittest
from pathlib import Path
import pandas as pd
import numpy as np


class SnapGapContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.frame = pd.read_csv(cls.root / "output/tract_clean.csv", dtype={"geoid": str})

    def model(self):
        self.assertTrue((self.root / "snap_gap_model.py").exists(), "SNAP-gap model is not implemented")
        import snap_gap_model
        return snap_gap_model

    def test_deterministic_schema_and_baseline(self):
        m = self.model()
        a, meta = m.build_predictions(self.frame)
        b, meta2 = m.build_predictions(self.frame.sample(frac=1, random_state=7))
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(meta, meta2)
        self.assertEqual(len(a), 490)
        self.assertEqual(a.geoid.nunique(), 490)
        self.assertTrue(a.geoid.str.fullmatch(r"\d{11}").all())
        self.assertEqual(a.expected_pct.notna().sum(), 488)
        self.assertEqual(set(a.fold.dropna()), set(range(5)))
        self.assertTrue(a.expected_pct.dropna().between(0, 100).all())
        np.testing.assert_allclose(a.gap_pp, a.actual_pct-a.expected_pct, equal_nan=True)
        self.assertIn("baseline_mae_pp", meta)
        self.assertIn("cv_r2", meta)
        self.assertTrue(all(x in a for x in ["label", "reason", "drivers_json", "snap_moe_pp"]))

    def test_strict_non_snap_feature_allowlist_and_held_out_target(self):
        m = self.model()
        self.assertFalse(any("snap" in x.lower() for x in m.FEATURES))
        a, _ = m.build_predictions(self.frame)
        target = a[a.expected_pct.notna()].iloc[0]
        altered = self.frame.copy()
        altered.loc[altered.geoid == target.geoid, "snap_pct"] += 15
        altered["snap_households"] = 999999
        altered["high_snap_moe"] = False
        altered["snap_cv"] = 0
        altered["snap_leak"] = altered.snap_pct
        b, _ = m.build_predictions(altered)
        row = b[b.geoid == target.geoid].iloc[0]
        for key in ["expected_pct", "model_tolerance_pp", "drivers_json", "baseline_pct"]:
            self.assertEqual(target[key], row[key], key)
        np.testing.assert_allclose(m.feature_frame(self.frame), m.feature_frame(altered), equal_nan=True)

    def test_uncertainty_gate_and_missingness(self):
        m = self.model()
        self.assertEqual(m.classify_gap(5, 20, 1, 5)[0], "likely under-enrolled")
        self.assertEqual(m.classify_gap(5, 20, 10, 5)[0], "uncertain")
        self.assertEqual(m.classify_gap(1, 20, 2, 5)[0], "uncertain")
        self.assertEqual(m.classify_gap(10, 12, 1, 5)[0], "uncertain")
        self.assertEqual(m.classify_gap(5, 20, None, 5)[0], "uncertain")
        self.assertEqual(m.classify_gap(5, 20, 1, 5, enabled=False)[0], "uncertain")
        self.assertEqual(m.classify_gap(None, None, None, None)[0], "unavailable")
        # Imputed predictors do not get strong labels; zero-household tracts are excluded.
        f = self.frame.copy()
        f.loc[0, "poverty_pct"] = np.nan
        out, _ = m.build_predictions(f)
        self.assertEqual(out.set_index("geoid").loc[f.loc[0,"geoid"], "label"], "uncertain")

    def test_snapshot_refuses_stale_model_and_duplicate_keys(self):
        import importlib.util
        import json
        import tempfile
        spec = importlib.util.spec_from_file_location("prepare_data", self.root / "app/prepare_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "load_snap_gap"), "Freshness guard is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "tract_clean.csv").write_text("geoid\n12095017703\n")
            (path / "snap_gap.csv").write_text("geoid,drivers_json\n12095017703,[]\n")
            (path / "snap_gap_metadata.json").write_text(json.dumps({"input_sha256": "stale"}))
            with self.assertRaisesRegex(ValueError, "stale"):
                module.load_snap_gap(path, {"12095017703"})
            import hashlib
            (path / "snap_gap_metadata.json").write_text(json.dumps({"input_sha256": hashlib.sha256((path / "tract_clean.csv").read_bytes()).hexdigest()}))
            data = module.load_snap_gap(path, {"12095017703"})
            self.assertEqual(data["rows"][0]["geoid"], "12095017703")
            (path / "snap_gap.csv").write_text("geoid,drivers_json\n12095017703,[]\n12095017703,[]\n")
            with self.assertRaisesRegex(ValueError, "keys"):
                module.load_snap_gap(path, {"12095017703"})

    def test_driver_contributions_reconstruct_fold_prediction(self):
        import json
        m = self.model()
        out, _ = m.build_predictions(self.frame)
        for _, row in out[out.expected_pct.notna()].iterrows():
            drivers = json.loads(row.drivers_json)
            self.assertEqual(len(drivers), len(m.FEATURES))
            self.assertAlmostEqual(np.clip(row.intercept_pct + sum(d["contribution_pp"] for d in drivers), 0, 100), row.expected_pct, places=7)
            self.assertTrue(all(d["feature"] in m.FEATURES and d["description"] for d in drivers))

if __name__ == "__main__": unittest.main()
