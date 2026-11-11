"""Load experiment configs, enforce the one-factor-at-a-time rule, and hash them."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

CONFIGS = Path(__file__).parent / "configs"
PROMPTS = Path(__file__).parent / "prompts"
# Keys that are bookkeeping, not experimental factors.
NOT_FACTORS = {"name", "base", "factor", "override", "writeup.enabled"}


def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and k in out and isinstance(out[k], dict) and k != "weights":
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _flat(d, prefix=""):
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and k != "weights":
            yield from _flat(v, key + ".")
        else:
            yield key, v


def _group(key: str) -> str:
    """Which factor a changed key belongs to (ranking weights belong to 'ranking')."""
    if key.startswith("ranking."):
        return "ranking"
    if key.startswith("confidence."):
        return "confidence"
    return key


def load(name: str) -> dict:
    raw = yaml.safe_load((CONFIGS / f"{name}.yaml").read_text())
    if "base" not in raw:
        raw["factor"] = None
        return raw
    base = load(raw["base"])
    cfg = _merge(base, raw.get("override", {}))
    cfg.update(name=raw["name"], base=raw["base"], factor=raw["factor"])
    changed = {_group(k) for k, v in _flat(cfg) if k not in NOT_FACTORS and dict(_flat(base)).get(k) != v}
    if changed != {raw["factor"]}:
        raise ValueError(f"{name}: must change exactly one factor ({raw['factor']}); changed {sorted(changed)}")
    return cfg


def all_names() -> list[str]:
    names = sorted(p.stem for p in CONFIGS.glob("*.yaml") if p.stem != "pricing")
    return ["baseline"] + [n for n in names if n != "baseline"]


def config_hash(cfg: dict) -> str:
    """Stable hash of everything that affects results, including the prompt text."""
    payload = {k: v for k, v in cfg.items() if k not in ("name", "base", "factor")}
    if cfg.get("writeup", {}).get("enabled"):
        payload["_prompt_sha"] = hashlib.sha256((PROMPTS / f"{cfg['writeup']['prompt_version']}.txt").read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


def pricing() -> dict:
    return yaml.safe_load((CONFIGS / "pricing.yaml").read_text())
