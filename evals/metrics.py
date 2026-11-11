"""Plain metric functions used by the report (no external dependencies)."""
from __future__ import annotations

import math


def overlap_at_k(a, b, k=10):
    return len(set(a[:k]) & set(b[:k])) / k


def rbo(a, b, p=0.9, k=10):
    """Rank-biased overlap (truncated at depth k, normalised to 1 for identical lists)."""
    s, norm = 0.0, 0.0
    for d in range(1, k + 1):
        w = p ** (d - 1)
        s += w * len(set(a[:d]) & set(b[:d])) / d
        norm += w
    return s / norm


def percentile(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def cohen_kappa(a, b):
    """Agreement between two raters beyond chance (used for grader vs. human)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    labels = {x for p in pairs for x in p}
    pe = sum((sum(x == l for x, _ in pairs) / n) * (sum(y == l for _, y in pairs) / n) for l in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)
