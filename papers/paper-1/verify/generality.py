#!/usr/bin/env python3.13
"""Section 3.3 checks for Paper 1 v0.4: what does and does not carry over from the
three-record family. Exact rational arithmetic, closed form of Proposition 2 with the
coordinate box, re-implemented here.

  (a) Padding: appending records with A_i = B_i = y_i leaves every radius unchanged.
      True by construction (such records add nothing to the loss difference); checked.
  (b) Scale: multiplying forecasts, reference values and the box by lambda multiplies
      every radius by lambda. At q = 1/2: 3/2, 3, 15 for lambda = 1, 2, 10.
  (c) MSE: under squared error the same family has a q-dependent score gap 4(1+q)/3,
      strict reversal infimum 1+q for q < 1 inside the box and none at q = 1, so the
      reversal cost is exactly a quarter of the total MSE gap. The constant-score
      phenomenon does not survive the change of loss.

Prints JSON. Exit 0 if every check holds.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction as F


def radii(A, B, y, lo, hi):
    N = sum(abs(b - t) - abs(a - t) for a, b, t in zip(A, B, y))
    terms = []
    for i, (a, b, t) in enumerate(zip(A, B, y)):
        if a == b:
            continue
        reach = hi[i] if b > t else min(-lo[i], t)
        if min(a, b) <= t <= max(a, b):
            dz = F(0)
        elif abs(t - b) > abs(t - a):
            dz = abs(t - a)
        else:
            continue
        if reach <= dz:
            continue
        cap = min(abs(b - t) - abs(a - t) + abs(a - b), 2 * (reach - dz))
        if cap > 0:
            terms.append((dz, cap))
    tie = strict = None
    for k in range(1, len(terms) + 1):
        for S in itertools.combinations(terms, k):
            cp, dz = sum(s[1] for s in S), sum(s[0] for s in S)
            if cp >= N and (tie is None or dz < tie):
                tie = dz
            if cp > N and (strict is None or dz < strict):
                strict = dz
    return (None if tie is None else N / 2 + tie), (None if strict is None else N / 2 + strict)


def family(q, lam=F(1), pad=()):
    A = [2 * lam, F(0), F(0)] + list(pad)
    B = [F(0), 2 * lam, F(0)] + list(pad)
    y = [(2 + q) * lam, lam, (3 - q) * lam] + list(pad)
    n = len(y)
    return A, B, y, [-lam] * n, [lam] * n


def main() -> int:
    out, ok = {}, True

    rows = []
    for pad in ((), (F(0),), (F(0), F(5))):
        for q in (F(0), F(1, 2), F(3, 4), F(1)):
            A, B, y, lo, hi = family(q, pad=pad)
            rows.append([len(y), str(q), *map(str, radii(A, B, y, lo, hi))])
    base = {r[1]: r[2:] for r in rows if r[0] == 3}
    pad_ok = all(r[2:] == base[r[1]] for r in rows)
    out["a_padding"] = {"holds": pad_ok, "rows": rows,
                        "note": "trivial: padded records have A_i = B_i and contribute nothing"}
    ok &= pad_ok

    sc = []
    for lam in (F(1), F(2), F(10)):
        A, B, y, lo, hi = family(F(1, 2), lam)
        sc.append([str(lam), *map(str, radii(A, B, y, lo, hi))])
    scale_ok = [r[2] for r in sc] == ["3/2", "3", "15"] and all(r[1] == str(F(r[0])) for r in sc)
    out["b_scale"] = {"holds": scale_ok, "rows": sc, "expected_strict": ["3/2", "3", "15"],
                      "note": "positive homogeneity of L1 cost and of MAE"}
    ok &= scale_ok

    ms = []
    mse_ok = True
    for q in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1)):
        A, B, y = [F(2), F(0), F(0)], [F(0), F(2), F(0)], [2 + q, F(1), 3 - q]
        gap = sum((b - t) ** 2 - (a - t) ** 2 for a, b, t in zip(A, B, y))
        # D_MSE(y') = 4 (y1' - y2'); the box gives y1' >= 1 + q and y2' <= 2.
        feasible = 1 + q < 2
        inf_ = (y[0] - y[1]) if feasible else None
        # witness check: just past the infimum B wins, at the infimum it is a tie
        if feasible:
            eps = F(1, 1000)
            d1, d2 = -(q + eps), F(1)              # cost 1 + q + eps, inside the box
            yy = [y[0] + d1, y[1] + d2, y[2]]
            win = sum((b - t) ** 2 for b, t in zip(B, yy)) < sum((a - t) ** 2 for a, t in zip(A, yy))
            mse_ok &= win and inf_ == 1 + q and inf_ / gap == F(1, 4)
        else:
            mse_ok &= q == 1
        ms.append({"q": str(q), "mse_mean_gap": str(gap / 3), "strict_infimum": str(inf_),
                   "infimum_over_total_gap": None if inf_ is None else str(inf_ / gap)})
    out["c_mse"] = {"holds": mse_ok, "rows": ms,
                    "note": "under MSE the reversal cost is a fixed quarter of the total gap, so here the score gap determines it"}
    ok &= mse_ok

    out["OVERALL"] = {"all_claims_verified": ok}
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
