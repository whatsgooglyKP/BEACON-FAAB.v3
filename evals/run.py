"""One command to reproduce every Beacon experiment.

    python -m evals.run --all            # deterministic parts + MOCK write-ups (free, offline)
    python -m evals.run --all --live     # same, but write-ups come from Gemini (needs GEMINI_API_KEY)

Steps: build the rule-derived gold set -> for each config: ranking agreement,
perturbation tests, Monte Carlo stability, confidence calibration, write-ups +
faithfulness grading with telemetry -> grader self-checks -> REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

from . import config as C
from .beacon_rules import confidence_label
from .data import display_name, data_fingerprint, load_tracts
from .gold import build_gold
from .grader import grade, seeded_errors
from .metrics import mean, overlap_at_k, percentile, rbo
from .perturb import calibration, monte_carlo, run_cases
from .ranking import rank
from .telemetry import Telemetry
from .writeup import GeminiError, facts_for, gemini_writeup, mock_writeup, render_prompt

HERE = Path(__file__).parent
REPORTS = HERE / "reports"
CACHE = HERE / "runs" / "live_cache.jsonl"  # git-ignored; successful live outputs, for resuming


def _cost(model, usage, prices):
    p = prices.get(model, {"input": 0, "output": 0})
    out_tokens = (usage.get("candidatesTokenCount") or 0) + (usage.get("thoughtsTokenCount") or 0)
    return ((usage.get("promptTokenCount") or 0) * p["input"] + out_tokens * p["output"]) / 1e6


def run_config(cfg, tracts, gold, tel, live, prices, all_places, budget, replay=None):
    """Run one config end to end and return its summary dict."""
    run_id, chash, fp = uuid.uuid4().hex[:10], C.config_hash(cfg), data_fingerprint()
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    order = rank(tracts, cfg["ranking"])
    ids = [t["geoid"] for t in order]
    ref = gold["reference_top10"]
    robust = set(gold["robust_core"])
    by = {t["geoid"]: t for t in tracts}
    s = {"config": cfg["name"], "factor": cfg.get("factor"), "config_hash": chash, "top10": ids[:10],
         "top10_names": [display_name(by[g]) for g in ids[:10]], "shortlist_size": len(ids),
         "overlap_at_10": overlap_at_k(ids, ref), "rbo_at_10": rbo(ids, ref),
         "robust_share_top10": sum(g in robust for g in ids[:10]) / max(1, min(10, len(ids)))}
    cases = run_cases(tracts, gold["perturbation_cases"], cfg["ranking"])
    s["perturbation"] = {"passed": sum(c["passed"] for c in cases), "total": len(cases),
                         "failed": [c["id"] for c in cases if not c["passed"]]}
    mc = monte_carlo(tracts, cfg["ranking"], cfg["stability"]["draws"], cfg["seed"])
    s["stability_top10_jaccard_mean"] = mean(mc["top10_jaccard"])
    s["stability_top10_jaccard_p05"] = percentile(mc["top10_jaccard"], 0.05)
    relabelled = [{**t, "evidence_confidence": confidence_label(t, cfg["confidence"]["variant"])} for t in tracts]
    lens = "dd" if cfg["ranking"]["variant"] == "screening_driving" else "sd"
    s["calibration"] = calibration(relabelled, mc["flip_rate"], lens)
    s["confidence_label_counts"] = {k: sum(t["evidence_confidence"] == k for t in relabelled) for k in ("High", "Medium", "Low")}
    s["confidence_rule_agreement"] = mean([float(gold["confidence_labels"][t["geoid"]] == t["evidence_confidence"]) for t in tracts]) if cfg["confidence"]["variant"] == "pipeline_v1" else None

    w = cfg["writeup"]
    s["writeups"] = []
    n_err = n_retry = 0
    if w.get("enabled"):
        mode = "gemini" if live else "mock"
        for rep in range(w["repeats"]):
            for i, g in enumerate(ids[: w["top_k"]], 1):
                t = by[g]
                f = facts_for(t, i)
                text, usage, retries, err = "", {}, 0, None
                t0 = time.perf_counter()
                cached = (replay or {}).get((cfg["name"], chash, g, rep))
                if cached:
                    # Replay a saved live output: same text and telemetry, no new API call.
                    text, err, retries, latency = cached["text"], cached["error"], cached["retries"], cached["latency_s"]
                    usage = {"promptTokenCount": cached["prompt_tokens"], "candidatesTokenCount": cached["output_tokens"], "thoughtsTokenCount": cached["thought_tokens"]}
                elif mode == "mock":
                    text = mock_writeup(f, w["prompt_version"])
                    latency = time.perf_counter() - t0
                elif budget["left"] <= 0:
                    err, latency = "skipped: live call budget exhausted", 0.0
                else:
                    key = f"{chash}|{g}|{rep}"
                    hit = budget["cache"].get(key)
                    if hit:
                        # Resume support: a successful live call from an interrupted run is reused, not re-bought.
                        text, usage, retries, latency = hit["text"], hit["usage"], hit["retries"], hit["latency_s"]
                    else:
                        budget["left"] -= 1
                        try:
                            text, usage, retries, latency = gemini_writeup(render_prompt(f, w["prompt_version"]), w["model"], w["temperature"], cfg["seed"] + i)
                            with CACHE.open("a") as fh:
                                fh.write(json.dumps({"key": key, "text": text, "usage": usage, "retries": retries, "latency_s": latency}) + "\n")
                        except GeminiError as exc:
                            err, retries, latency = str(exc), exc.retries, time.perf_counter() - t0
                        time.sleep(budget.get("pause", 0))
                gr = grade(text, f, all_places) if text else None
                n_err += err is not None; n_retry += retries
                row = {"run_id": run_id, "config_name": cfg["name"], "config_hash": chash, "data_fingerprint": fp,
                       "mode": mode, "model": w["model"] if mode == "gemini" else "mock", "prompt_version": w["prompt_version"],
                       "temperature": w["temperature"], "seed": cfg["seed"] + i, "repeat": rep, "geoid": g, "rank": i,
                       "latency_s": round(latency, 4), "prompt_tokens": usage.get("promptTokenCount"),
                       "output_tokens": usage.get("candidatesTokenCount"), "thought_tokens": usage.get("thoughtsTokenCount"),
                       "cost_usd": _cost(w["model"], usage, prices) if mode == "gemini" else 0.0, "retries": retries, "error": err,
                       "data_quality_flags": [k for k in ("high_poverty_moe", "high_snap_moe", "distance_definition_sensitive", "small_denominator_proxy", "mixed_vintage_flag") if t.get(k)],
                       "shaky_numbers": f["shaky_numbers"], "shaky_asked": gr["shaky_asked"] if gr else None,
                       "faithful": gr["faithful"] if gr else None, "unsupported_numbers": gr["unsupported_numbers"] if gr else None,
                       "wrong_places": gr["wrong_places"] if gr else None, "confidence_correct": gr["confidence_correct"] if gr else None}
                tel.call(row)
                s["writeups"].append({**row, "text": text, "facts": f, "grade": gr})
    s["n_errors"], s["total_retries"] = n_err, n_retry
    tel.run({"run_id": run_id, "config_name": cfg["name"], "config_hash": chash, "data_fingerprint": fp,
             "mode": ("gemini" if live else "mock") if w.get("enabled") else "deterministic", "factor": cfg.get("factor"),
             "started": started, "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n_calls": len(s["writeups"]),
             "n_errors": n_err, "total_retries": n_retry,
             "summary": {k: s[k] for k in ("overlap_at_10", "rbo_at_10", "stability_top10_jaccard_mean")}})
    return s


def grader_selfcheck(results, all_places):
    """Seeded-error test: corrupt write-ups the grader passed; count how many it catches."""
    caught, total, by_kind = 0, 0, {}
    pool = [w for r in results for w in r["writeups"] if w["grade"] and w["grade"]["faithful"]]
    others = sorted(all_places)
    for w in pool:
        f = w["facts"]
        other = next(p for p in others if p.lower() not in f["place_name"].lower() and f["place_name"].lower() not in p.lower())
        for kind, bad in seeded_errors(w["text"], f, other).items():
            if bad == w["text"]:
                continue  # mutation not applicable to this text
            total += 1
            hit = not grade(bad, f, all_places)["faithful"]
            caught += hit
            k = by_kind.setdefault(kind, [0, 0]); k[0] += hit; k[1] += 1
    return {"faithful_pool": len(pool), "mutations": total, "caught": caught,
            "by_kind": {k: {"caught": a, "total": b} for k, (a, b) in by_kind.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="run every config in evals/configs")
    ap.add_argument("--config", action="append", help="run only these config names")
    ap.add_argument("--live", action="store_true", help="use Gemini for write-ups (needs GEMINI_API_KEY)")
    ap.add_argument("--max-live-calls", type=int, default=100, help="hard cap on Gemini calls for cost safety")
    ap.add_argument("--replay", action="store_true", help="re-grade saved live write-ups from reports/writeups.jsonl (no API calls)")
    ap.add_argument("--fresh", action="store_true", help="ignore cached live outputs and call Gemini again")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between live calls (rate limits)")
    a = ap.parse_args(argv)
    replay = None
    if a.replay:
        rows = [json.loads(l) for l in (REPORTS / "writeups.jsonl").read_text().splitlines() if l.strip()]
        replay = {(r["config_name"], r["config_hash"], r["geoid"], r["repeat"]): r for r in rows if r["mode"] == "gemini"}
        a.live = True
    if a.live and not a.replay and not os.environ.get("GEMINI_API_KEY"):
        ap.error("--live needs GEMINI_API_KEY in the environment (it is never printed or stored)")
    names = C.all_names() if a.all or not a.config else a.config
    tracts = load_tracts()
    gold = build_gold()
    all_places = {p for t in tracts for p in (t.get("place_name"), t.get("official_neighborhood")) if p}
    tel = Telemetry()
    tel.reset()
    budget = {"left": 0 if a.replay else a.max_live_calls, "pause": 0 if a.replay else a.pause, "cache": {}}
    if a.live and not a.replay and not a.fresh and CACHE.exists():
        budget["cache"] = {r["key"]: r for r in map(json.loads, CACHE.read_text().splitlines())}
    elif a.fresh and CACHE.exists():
        CACHE.unlink()
    results = []
    for n in names:
        cfg = C.load(n)
        print(f"[evals] {n} ({cfg.get('factor') or 'reference'}) ...", flush=True)
        results.append(run_config(cfg, tracts, gold, tel, a.live, C.pricing(), all_places, budget, replay))
    check = grader_selfcheck(results, all_places)
    from .hand_grading.agreement import refresh_template, agreement
    refresh_template(results)
    from .report import write_report
    write_report(results, gold, check, agreement(), live=a.live, replayed=a.replay)
    print(f"[evals] wrote {REPORTS / 'REPORT.md'}")


if __name__ == "__main__":
    main()
