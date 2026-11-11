"""Write evals/reports/REPORT.md (+ SVG charts, metrics.json, writeups.jsonl)."""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from .charts import bars
from .metrics import mean, percentile

REPORTS = Path(__file__).parent / "reports"


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _num(x, d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def writeup_stats(r):
    ws = [w for w in r["writeups"]]
    ok = [w for w in ws if w["grade"]]
    if not ws:
        return None
    lat = [w["latency_s"] for w in ok]
    by_tract = defaultdict(list)
    for w in ok:
        by_tract[w["geoid"]].append(w)
    multi = [v for v in by_tract.values() if len(v) > 1]
    shaky = [w["grade"]["shaky_coverage"] for w in ok if w["grade"]["shaky_coverage"] is not None]
    cost = sum(w["cost_usd"] or 0 for w in ws)
    faithful = sum(w["grade"]["faithful"] for w in ok)
    return {
        "mode": ws[0]["mode"], "model": ws[0]["model"], "n": len(ws), "graded": len(ok),
        "errors": sum(1 for w in ws if w["error"]), "retries": sum(w["retries"] for w in ws),
        "faithful_rate": faithful / len(ok) if ok else None,
        "unsupported_number_rate": mean([float(bool(w["grade"]["unsupported_numbers"])) for w in ok]),
        "wrong_place_rate": mean([float(bool(w["grade"]["wrong_places"])) for w in ok]),
        "confidence_correct_rate": mean([float(w["grade"]["confidence_correct"]) for w in ok]),
        "shaky_question_coverage": mean(shaky),
        "repeat_identical_text": mean([float(len({w["text"] for w in v}) == 1) for v in multi]) if multi else None,
        "repeat_same_verdict": mean([float(len({w["grade"]["faithful"] for w in v}) == 1) for v in multi]) if multi else None,
        "latency_p50_s": percentile(lat, 0.5), "latency_p95_s": percentile(lat, 0.95),
        "prompt_tokens_mean": mean([w["prompt_tokens"] for w in ok]),
        "output_tokens_mean": mean([w["output_tokens"] for w in ok]),
        "thought_tokens_mean": mean([w["thought_tokens"] for w in ok]),
        "cost_total_usd": cost, "cost_per_writeup_usd": cost / len(ok) if ok else None,
        "cost_per_faithful_usd": cost / faithful if faithful else None,
    }


def write_report(results, gold, check, agree, live, replayed=False):
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "charts").mkdir(exist_ok=True)
    mode = "LIVE Gemini" if live else "MOCK (deterministic templates — not model results)"
    L = [f"# Beacon evaluation & telemetry report", "",
         f"Generated {time.strftime('%m/%d/%Y %I:%M %p %Z')} by `python -m evals.run --all{' --replay' if replayed else (' --live' if live else '')}`."
         + (" Write-ups were replayed from saved live Gemini outputs (no new API calls)." if replayed else ""),
         f"Data fingerprint `{gold['data_fingerprint']}` · reference ranking from {gold['reference_source']} · write-up mode: **{mode}**.", "",
         "> Labels are rule-derived (see `evals/gold.py`); no human or expert labels exist yet. The shipped Beacon app has no",
         "> generative AI — the Gemini write-up is an evaluation-only candidate feature.", ""]

    L += ["## 1. Ranking experiments (vs. shipped reference top 10)", "",
          "| Config | Factor | Shortlist | Overlap@10 | RBO@10 | Robust share of top 10 | Perturbation tests | Stability (mean top-10 Jaccard) | Stability p05 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if r["factor"] in (None, "ranking"):
            p = r["perturbation"]
            L.append(f"| {r['config']} | {r['factor'] or 'reference'} | {r['shortlist_size']} | {_pct(r['overlap_at_10'])} | {_num(r['rbo_at_10'])} | "
                     f"{_pct(r['robust_share_top10'])} | {p['passed']}/{p['total']}{' (failed: ' + ', '.join(p['failed']) + ')' if p['failed'] else ''} | "
                     f"{_num(r['stability_top10_jaccard_mean'])} | {_num(r['stability_top10_jaccard_p05'])} |")
    base = results[0]
    L += ["", f"Reference top 10: {', '.join(f'{n} ({g})' for n, g in zip(base['top10_names'], base['top10']))}.", "",
          "*Robust share* = fraction of the top 10 whose poverty 90% lower bound still clears the cutoff. *Stability* = Jaccard overlap of the top 10 "
          f"before/after redrawing every poverty and SNAP estimate inside its margin of error ({base['config']}: fixed seed, see config).", ""]

    L += ["## 2. Confidence-label calibration", "",
          "Shortlist flip rate = share of Monte Carlo redraws in which a tract's shortlist membership changes. A useful label should give *High* the lowest flip rate.", "",
          "| Config | Label counts (H/M/L) | High: n, flip rate | Medium: n, flip rate | Separation (Medium − High) | Rule re-derivation agreement |", "|---|---|---|---|---|---|"]
    for r in results:
        if r["factor"] in (None, "confidence"):
            c, k = r["calibration"], r["confidence_label_counts"]
            hi, me = c.get("High", {}), c.get("Medium", {})
            sep = (me.get("mean_flip_rate") - hi.get("mean_flip_rate")) if hi and me else None
            L.append(f"| {r['config']} | {k['High']}/{k['Medium']}/{k['Low']} | {hi.get('n', 0)}, {_pct(hi.get('mean_flip_rate'))} | "
                     f"{me.get('n', 0)}, {_pct(me.get('mean_flip_rate'))} | {'n/a' if sep is None else f'{100*sep:+.1f} pts'} | {_pct(r['confidence_rule_agreement'])} |")
    L.append("")

    stats = {r["config"]: writeup_stats(r) for r in results if r["writeups"]}
    L += [f"## 3. Write-up experiments — {mode}", "",
          "| Config | Factor | Model | n (errors) | Faithful | Unsupported numbers | Wrong place | Confidence correct | Shaky-number questions | Same verdict on repeat | p50 / p95 latency (s) | Tokens in / out / thinking | Est. cost per run | Est. cost per faithful |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        s = stats.get(r["config"])
        if not s:
            continue
        L.append(f"| {r['config']} | {r['factor'] or 'reference'} | {s['model']} | {s['graded']} ({s['errors']}) | {_pct(s['faithful_rate'])} | {_pct(s['unsupported_number_rate'])} | "
                 f"{_pct(s['wrong_place_rate'])} | {_pct(s['confidence_correct_rate'])} | {_pct(s['shaky_question_coverage'])} | {_pct(s['repeat_same_verdict'])} | "
                 f"{_num(s['latency_p50_s'])} / {_num(s['latency_p95_s'])} | {_num(s['prompt_tokens_mean'], 0)} / {_num(s['output_tokens_mean'], 0)} / {_num(s['thought_tokens_mean'], 0)} | "
                 f"${s['cost_total_usd']:.4f} | {'n/a' if s['cost_per_faithful_usd'] is None else f'${s[chr(99)+"ost_per_faithful_usd"]:.5f}'} |")
    L += ["", "Costs are estimates from list prices in `evals/configs/pricing.yaml`. Retries: " +
          ", ".join(f"{k} {v['retries']}" for k, v in stats.items()) + ".", ""]

    L += ["## 4. Grader checks", "",
          f"* Seeded-error test: corrupted {check['mutations']} copies of {check['faithful_pool']} write-ups the grader had passed; it caught **{check['caught']}/{check['mutations']}**."
          + "".join(f" {k}: {v['caught']}/{v['total']}." for k, v in check["by_kind"].items()),
          ("* Grader vs. hand grades: **pending** — fill `evals/hand_grading/to_grade.csv` (30 items). " + agree["instructions"]) if agree["status"] == "pending"
          else f"* Grader vs. hand grades (n={agree['n']}): raw agreement {_pct(agree['raw_agreement'])}, Cohen's kappa {_num(agree['cohen_kappa'])}.", ""]

    # Charts
    rk = [r for r in results if r["factor"] in (None, "ranking")]
    bars(REPORTS / "charts/ranking_overlap.svg", "Top-10 overlap with shipped ranking", [(r["config"], r["overlap_at_10"]) for r in rk], "{:.0%}", 1)
    bars(REPORTS / "charts/ranking_stability.svg", "Top-10 stability under margin-of-error noise", [(r["config"], r["stability_top10_jaccard_mean"]) for r in rk], "{:.2f}", 1)
    if stats:
        bars(REPORTS / "charts/writeup_faithful.svg", f"Faithful write-ups ({'live' if live else 'MOCK'})", [(k, v["faithful_rate"]) for k, v in stats.items()], "{:.0%}", 1)
        bars(REPORTS / "charts/writeup_latency_p95.svg", f"p95 latency, seconds ({'live' if live else 'MOCK'})", [(k, v["latency_p95_s"]) for k, v in stats.items()], "{:.2f}")
    L += ["## 5. Charts", "", "![overlap](charts/ranking_overlap.svg)", "![stability](charts/ranking_stability.svg)"]
    if stats:
        L += ["![faithful](charts/writeup_faithful.svg)", "![latency](charts/writeup_latency_p95.svg)"]
    L += ["", "## 6. Reproduce", "", "```bash", "pip install -r evals/requirements.txt", "python -m evals.run --all          # offline, mock write-ups",
          "python -m evals.run --all --live   # Gemini write-ups (GEMINI_API_KEY in env)", "```",
          "Per-call telemetry: `evals/runs/telemetry.jsonl` and `evals/runs/telemetry.sqlite` (git-ignored, regenerated each run).", ""]
    (REPORTS / "REPORT.md").write_text("\n".join(L))
    slim = [{k: v for k, v in r.items() if k != "writeups"} | {"writeup_stats": stats.get(r["config"])} for r in results]
    (REPORTS / "metrics.json").write_text(json.dumps({"live": live, "results": slim, "grader_selfcheck": check, "hand_grade_agreement": agree}, indent=1, default=str))
    with (REPORTS / "writeups.jsonl").open("w") as fh:
        for r in results:
            for w in r["writeups"]:
                fh.write(json.dumps({k: w[k] for k in ("config_name", "config_hash", "mode", "model", "prompt_version", "temperature", "seed", "repeat", "geoid", "rank", "text", "grade", "error", "latency_s", "prompt_tokens", "output_tokens", "thought_tokens", "cost_usd", "retries", "facts")}) + "\n")
