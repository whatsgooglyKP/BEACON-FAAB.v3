# Beacon evaluation & telemetry lab (`evals/`)

This folder adds an **experiment harness** beside the Beacon Neighborhood Action Desk. It does not change the app (`app/`) or the data pipeline; it reads the same cleaned, public tract data the app ships with (`app/public/data/tracts.json`, `snap_gap.json`) and measures how Beacon's decisions behave.

It answers three questions:

1. **Ranking** — If we change how the top 10 tracts are chosen, how much does the shortlist move, and how stable is it when the Census estimates wobble inside their margins of error?
2. **Confidence labels** — Do Beacon's High / Medium / Low evidence-confidence labels actually predict which picks are stable?
3. **Write-ups** — If Gemini wrote the plain-English note for each shortlisted tract, would it stay faithful to Beacon's numbers and place names, state the right confidence label, and ask organizers to verify the shaky numbers? (The shipped app has **no** generative AI. This is an evaluation-only candidate feature, so it can be measured before anything ships.)

## Run it

```bash
pip install -r evals/requirements.txt         # PyYAML + requests
python -m evals.run --all                     # everything, offline; write-ups use a MOCK writer
python -m evals.run --all --live              # write-ups from Gemini (needs GEMINI_API_KEY in env)
python -m unittest discover -s evals/tests -t . -v   # self-tests (or: make evals-test)
```

`make evals` and `make evals-live` do the same. Output: `evals/reports/REPORT.md` (tables + SVG charts), `metrics.json`, and `writeups.jsonl`. Per-call telemetry goes to `evals/runs/telemetry.jsonl` and `evals/runs/telemetry.sqlite`, which are git-ignored and regenerated on each run.

**Gemini safety:** the key is read from `GEMINI_API_KEY`, sent only in a request header, and never printed, logged, or written. `--max-live-calls` (default 100) caps spending, and `--pause` spaces calls out for rate limits. Mock results are always labelled MOCK in the report.

## How it works

| Piece | File | What it does |
|---|---|---|
| Rule ports | `beacon_rules.py` | Python copies of the app's shortlist rule (`domain.js candidates`) and the pipeline's confidence rule. A test runs the **real JS** with Node and confirms identical output for all four lens settings, and the confidence rule re-derives all 490 stored labels exactly. |
| Gold set | `gold.py` → `gold/gold_set.json` | Labeled test set. **Rule-derived only, with no human or expert labels.** Contents: the reference top 10 (the shipped app's output), a "robust core" (tracts that still qualify at their 90% lower poverty bound), re-derived confidence labels, and 8 perturbation cases. Each case edits one number and states the outcome the written rule requires, e.g. "widen poverty MOE to 12 points → label must drop to Medium" or "set households to 150 → Low and excluded." |
| Experiments | `configs/*.yaml` | `baseline.yaml` plus one file per experiment. The loader **refuses** any experiment that changes more than one factor. Factors: ranking variant, confidence rule, prompt version, Gemini model, temperature. Fixed seed; every run stores a config hash, which covers the prompt text, and a data fingerprint. |
| Stability | `perturb.py` | Monte Carlo: redraws every poverty and SNAP estimate inside its published 90% MOE (500 draws, fixed seed), re-ranks, and measures top-10 Jaccard overlap and per-tract shortlist flip rates. |
| Calibration | `perturb.py` | Mean flip rate by confidence label. A useful label should give *High* the lowest flip rate. |
| Write-ups | `writeup.py`, `prompts/v1.txt`, `prompts/v2.txt` | Builds the facts JSON for each tract, calls Gemini (or the mock), and handles retries and backoff. v2 adds explicit rules: MOE, exact label, no new numbers, one verification question per shaky number. |
| Grader | `grader.py` | Faithful = every number traces to the facts, the tract's own place is named and no other place is, and the confidence label is correct. It also records which shaky numbers got a verification question. It is self-checked by **seeded errors**: we deliberately corrupt passing write-ups (wrong number, wrong place, wrong label, invented statistic) and count how many it catches. |
| Telemetry | `telemetry.py` | One row per call and per run: latency, prompt, output and thinking tokens, estimated cost, model, config hash, data-quality flags, shaky numbers present vs. asked about, errors, retries. Built from an allow-list of fields, so credentials cannot leak into it. |
| Hand grading | `hand_grading/to_grade.csv`, `agreement.py` | 30 write-ups for a human to grade. Once filled in, the next run reports grader-vs-human raw agreement and Cohen's kappa. The sheet is never overwritten after grading starts. |
| Report | `report.py`, `charts.py` | `REPORT.md` with comparison tables and dependency-free SVG charts. |

## Known limits (read before quoting numbers)

* Gold labels come from rules, not experts. "Agreement with reference" means "same as the shipped app," not "correct."
* Monte Carlo noise assumes independent normal errors (sd = MOE/1.645) and keeps the 17.0% cutoff fixed, as the app does.
* The grader is simple pattern matching. It can wrongly flag a correct mention of a neighboring city, or miss a paraphrased error. The hand-grade agreement check exists to measure this.
* Costs are estimates from list prices in `configs/pricing.yaml`. Live runs are small (10 tracts × 2 repeats per config).

## For Kevin: what's left for you

1. Open `evals/hand_grading/to_grade.csv` and fill `human_faithful` (yes/no) for the 30 rows, using the rule in the file. Then rerun `python -m evals.run --all --live`, or just `python -m evals.hand_grading.agreement`.
2. Optional: ask a food-bank organizer to rank 10–20 tracts. That would be the first *real* expert gold label; add it as a new list in `gold/` and compare against it.

## Suggested resume bullet

See the "Results" section below, which is filled from the measured run.

## Results (measured 11/11/2026; see `reports/REPORT.md`)

Deterministic parts (exact and reproducible with the fixed seed):

* **Rule parity:** the Python ports match the shipped JS shortlist for all 4 lens settings, and re-derive all 490 confidence labels exactly. All rule-derived perturbation cases pass for the reference rule (8/8).
* **The top 10 is fragile.** When estimates are redrawn inside their margins of error (500 draws), the reference top 10 keeps a mean Jaccard overlap of only **0.33** with itself (p05 0.18). Only **6 of 10** picks still clear the cutoff at their 90% lower bound.
* **Ranking variants:** composite weighting keeps 8/10 of the reference picks. Conservative lower-bound mode shrinks the shortlist to 7 tracts, all of them robust. The driving-distance lens keeps 5/10.
* **Shipped confidence labels don't predict stability.** "High" tracts flip in or out of the shortlist in 17.4% of draws versus 17.9% for "Medium" (+0.5 pts). The experimental **margin-aware** rule (High only if the cutoff lies outside the 90% interval) separates them: 1.7% vs 18.4% (+16.7 pts).

Live Gemini write-ups (4 configs × top 10 tracts × 2 repeats = 80 calls, all real):

* Every config scored 100% on the automated faithfulness checks: no unsupported numbers, no wrong places, correct confidence label.
* **Prompt v2 is the one that matters.** It raised verification questions for flagged shaky numbers from **0% to 100%**, for 45% more input tokens (330 → 478) and about $0.0041 → $0.0049 per 20-write-up run (estimated, list price).
* Latency p50/p95: baseline gemini-3.1-flash-lite 2.39 / 24.42 s (one slow outlier); 3.5-flash-lite 1.20 / 7.21 s; temperature 0.2 run 0.97 / 2.14 s. Same-seed repeats gave the same verdict 100% of the time.
* **Error analysis caught a grader bug.** The first grader marked 4 baseline write-ups unfaithful. Manual inspection showed all 4 were correct, with the label written in quotes (`a "Medium" evidence confidence label`). The regex was fixed, regression tests were added from those real phrasings, and the saved outputs were re-graded with `--replay` (no new calls). The seeded-error self-check now catches 263/263 injected errors.
* Operational telemetry: `gemini-3-flash-preview` (the original baseline model) hit its free-tier daily quota (HTTP 429), and 5 of 80 calls on the first pass returned transient HTTP 403. Both were logged, and the failed calls were recovered by resuming from the cache. The baseline was switched to `gemini-3.1-flash-lite`, with `gemini-3.5-flash-lite` as the model variant.
* Limits: the faithfulness grader checks numbers, places and labels, not claims made in words. One live note said SNAP was "well above regional thresholds", which no fact supports. That kind of error is what the 30-item hand-grade check is for.

### Suggested resume bullet (honest; based on the numbers above)

> Built a config-driven experiment and telemetry harness for Beacon, a food-access screening tool covering 490 Central Florida census tracts, and for a candidate Gemini write-up feature. It runs one-factor A/B tests of ranking logic, confidence rules, prompts, models and temperature, logs latency, tokens, cost and errors to JSONL and SQLite, and reproduces every metric with one command. Monte Carlo testing inside Census error margins showed the top-10 shortlist was unstable (Jaccard 0.33) and the shipped confidence labels didn't predict stability. A margin-aware rule I designed separated them by 16.7 points. A revised prompt raised flagging of uncertain numbers from 0% to 100% across 80 live Gemini calls.
