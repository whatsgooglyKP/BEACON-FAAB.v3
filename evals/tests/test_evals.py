"""Fast checks that the lab measures what it claims to measure.

Run:  python -m unittest discover -s evals/tests -t . -v
"""
import json
import shutil
import subprocess
import unittest

from evals import config as C
from evals.beacon_rules import candidates, recompute_flags
from evals.data import REPO, load_tracts
from evals.gold import _perturbation_cases, _reference_lists
from evals.grader import grade, seeded_errors
from evals.metrics import cohen_kappa, overlap_at_k, rbo
from evals.perturb import run_cases
from evals.writeup import facts_for, mock_writeup

T = load_tracts()
PLACES = {p for t in T for p in (t.get("place_name"), t.get("official_neighborhood")) if p}


class Parity(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_python_ranking_matches_app_js(self):
        js = json.loads(subprocess.run(["node", str(REPO / "evals/js_reference.mjs")], capture_output=True, text=True, check=True).stdout)
        for key, ids in js.items():
            d, c = key.split("_")
            self.assertEqual([t["geoid"] for t in candidates(T, d, c == "true")], ids, key)

    def test_confidence_rule_matches_pipeline_labels(self):
        for t in T:
            self.assertEqual(recompute_flags(t)["evidence_confidence"], t["evidence_confidence"], t["geoid"])


class Configs(unittest.TestCase):
    def test_every_experiment_changes_one_factor(self):
        for n in C.all_names():
            C.load(n)  # raises if more than one factor differs

    def test_hash_changes_with_factor(self):
        self.assertNotEqual(C.config_hash(C.load("baseline")), C.config_hash(C.load("exp_prompt_v2")))


class Perturbations(unittest.TestCase):
    def test_reference_rule_passes_all_rule_derived_cases(self):
        ref, _ = _reference_lists(T)
        res = run_cases(T, _perturbation_cases(T, ref), {"variant": "screening_v1"})
        self.assertTrue(all(r["passed"] for r in res), res)


class Grader(unittest.TestCase):
    def setUp(self):
        self.f = facts_for(candidates(T)[0], 1)
        self.good = mock_writeup(self.f, "v2")

    def test_correct_text_passes(self):
        self.assertTrue(grade(self.good, self.f, PLACES)["faithful"])

    def test_every_seeded_error_is_caught(self):
        for kind, bad in seeded_errors(self.good, self.f, "Kissimmee").items():
            self.assertFalse(grade(bad, self.f, PLACES)["faithful"], kind)

    def test_shaky_questions_detected(self):
        g = grade(self.good, self.f, PLACES)
        self.assertEqual(g["shaky_asked"], self.f["shaky_numbers"])


class ConfidencePhrasings(unittest.TestCase):
    """Real Gemini phrasings the first grader version missed (found in error analysis)."""
    def test_quoted_and_trailing_labels(self):
        from evals.grader import stated_confidence as sc
        self.assertEqual(sc('carries a "Medium" evidence confidence label'), "Medium")
        self.assertEqual(sc('the evidence confidence label for this location is "Medium."'), "Medium")
        self.assertEqual(sc('leading to a "Medium" confidence label'), "Medium")
        self.assertEqual(sc("It has High evidence confidence."), "High")


class Metrics(unittest.TestCase):
    def test_basic(self):
        a = list("abcdefghij")
        self.assertEqual(overlap_at_k(a, a), 1.0)
        self.assertAlmostEqual(rbo(a, a), 1.0)
        self.assertEqual(cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)


if __name__ == "__main__":
    unittest.main()
