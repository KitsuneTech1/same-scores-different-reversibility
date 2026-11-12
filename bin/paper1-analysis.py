#!/usr/bin/env python3.13
"""Paper 1 v0.4 analysis: exact reversal radii for every model pair in the widened cohort.

Reads   papers/paper-1/data/cohort-v04.json and papers/paper-1/data/truth.json
Writes  papers/paper-1/data/results-v04.json

Everything is exact rational arithmetic. The radius computation is the closed form of
Proposition 2 in the manuscript:

    r_tie    = N/2 + min { sum_S dz_i : sum_S cap_i >= N }
    r_strict = N/2 + min { sum_S dz_i : sum_S cap_i >  N }

where N is the total-absolute-error gap, dz_i is the dead zone of record i (how far the
reference value must move before it enters the interval between the two forecasts) and
cap_i is how much record i can lower the total-error difference. Optional coordinate
bounds truncate cap_i. Stdlib only.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "papers" / "paper-1" / "data"


# ------------------------------------------------------------------ exact core
def total_abs(f, y):
    return sum(abs(a - b) for a, b in zip(f, y))


def record_terms(a, b, t, lo=None, hi=None):
    """(dz, cap) for one record, or None if the record cannot lower D = |b-t| - |a-t|.

    lo/hi bound the revision d (t+d must also stay >= 0). Moving t toward b is the
    only direction that lowers D.
    """
    if a == b:
        return None
    toward_up = b > t
    reach = (hi if hi is not None else None) if toward_up else (-lo if lo is not None else None)
    if not toward_up:
        reach = t if reach is None else min(reach, t)          # t + d >= 0
    lo_ab, hi_ab = min(a, b), max(a, b)
    d_i = abs(b - t) - abs(a - t)
    if lo_ab <= t <= hi_ab:
        dz = F(0)
    elif (t - b) * (a - b) > 0:        # a lies between t and b
        dz = abs(t - a)
    else:                              # b lies between a and t: D already minimal
        return None
    cap = d_i + abs(a - b)
    if reach is not None:
        if reach <= dz:
            return None
        cap = min(cap, 2 * (reach - dz))
    if cap <= 0:
        return None
    return dz, cap


def radii(A, B, y, lo=None, hi=None):
    """A strictly better than B under total absolute error. Returns dict of exact values.

    lo/hi: optional per-record revision bounds (lists). None means unbounded except y+d >= 0.
    """
    N = total_abs(B, y) - total_abs(A, y)
    if N <= 0:
        raise ValueError("A must be strictly better")
    terms = []
    for i, (a, b, t) in enumerate(zip(A, B, y)):
        r = record_terms(a, b, t, None if lo is None else lo[i], None if hi is None else hi[i])
        if r is not None:
            terms.append(r)
    best_tie = best_strict = None
    for k in range(1, len(terms) + 1):
        for S in itertools.combinations(terms, k):
            cap = sum(s[1] for s in S)
            dz = sum(s[0] for s in S)
            if cap >= N and (best_tie is None or dz < best_tie):
                best_tie = dz
            if cap > N and (best_strict is None or dz < best_strict):
                best_strict = dz
    bound = N / 2
    return {
        "N": N,
        "bound": bound,
        "tie": None if best_tie is None else bound + best_tie,
        "strict": None if best_strict is None else bound + best_strict,
    }


def fstr(x):
    return None if x is None else str(x)


def ffloat(x, nd=4):
    return None if x is None else round(float(x), nd)


# ------------------------------------------------------------------ revision history
DECISION_TIME = "2021-01-03T16:40:12Z"      # commit 80bf182e77a1, the decision vintage


def weekly_from_daily(rows, weeks):
    """Sum exactly seven daily rows, Sunday to Saturday. None if any day is missing."""
    import datetime as dt
    out = []
    for w in weeks:
        sat = dt.date.fromisoformat(w)
        days = [(sat - dt.timedelta(days=6 - k)).isoformat() for k in range(7)]
        if not all(d in rows for d in days):
            return None
        out.append(sum(F(rows[d]) for d in days))
    return out


def vintage_history(fc, order, y, weeks, pairs):
    raw = json.loads((DATA / "truth-vintages.json").read_text(encoding="utf-8"))
    vers = raw["versions"]
    complete = []
    for v in vers:
        wv = weekly_from_daily(v["us_rows"], weeks)
        if wv is not None:
            complete.append((v["time"], v["commit"], wv))
    dec = [c for c in complete if c[1].startswith("80bf182e77a1")]
    assert dec and dec[0][2] == y, "decision vintage does not reproduce truth.json"
    post = [c for c in complete if c[0] > DECISION_TIME]
    real = [p for p in pairs if not p.get("tie_initially")]
    up = {}
    for p in real:
        a, b = p["better"], p["worse"]
        up[(a, b)] = radii(fc[a], fc[b], y, lo=[F(0)] * len(y), hi=None)["strict"]
    rows, first, viol = [], {}, 0
    for t, c, wv in post:
        cost = total_abs(wv, y)
        rev = []
        for p in real:
            a, b = p["better"], p["worse"]
            if total_abs(fc[b], wv) < total_abs(fc[a], wv):
                rev.append((a, b))
                first.setdefault((a, b), (t, cost))
                if not cost > F(p["strict_radius"]):
                    viol += 1
        lead = min(fc, key=lambda m: (total_abs(fc[m], wv), m))
        rows.append({
            "time": t, "commit": c, "cost": str(cost),
            "all_upward": all(x >= z for x, z in zip(wv, y)),
            "permitted_bound": sum(1 for p in real if F(p["bound"]) < cost),
            "permitted_exact": sum(1 for p in real if F(p["strict_radius"]) < cost),
            "permitted_upward": sum(1 for p in real if up[(p["better"], p["worse"])] is not None
                                    and up[(p["better"], p["worse"])] < cost),
            "reversed": len(rev), "leader": lead,
            "revision": [str(x - z) for x, z in zip(wv, y)],
        })
    final = rows[-1]
    fin_wv = post[-1][2]
    fin_order = sorted(fc, key=lambda m: (total_abs(fc[m], fin_wv), m))
    costs = [F(r["cost"]) for r in rows]
    imax = max(range(len(rows)), key=lambda i: costs[i])
    leaders = []
    for r in rows:
        if not leaders or leaders[-1][1] != r["leader"]:
            leaders.append([r["time"], r["leader"]])
    adj = []
    for (t0, c0, w0), (t1, c1, w1) in zip(complete, complete[1:]):
        d = [b - a for a, b in zip(w0, w1)]
        if any(d) and d not in adj:
            adj.append(d)
    return {
        "versions_total": len(vers),
        "versions_full_stream": sum(1 for v in vers if v.get("git_blob_sha1")),
        "versions_lfs_tail": sum(1 for v in vers if v.get("lfs_oid")),
        "complete": len(complete),
        "post_decision": len(post),
        "post_distinct_vectors": len({tuple(c[2]) for c in post}),
        "post_all_upward": sum(1 for r in rows if r["all_upward"]),
        "first_post": rows[0]["time"], "final_time": final["time"], "final_cost": final["cost"],
        "final_revision": final["revision"],
        "max_time": rows[imax]["time"], "max_cost": rows[imax]["cost"], "max_reversed": rows[imax]["reversed"],
        "ever_reversed": len(first), "final_reversed": final["reversed"],
        "radius_violations": viol,
        "upward_infeasible": sum(1 for v in up.values() if v is None),
        "adjacent_nonzero": len(adj),
        "leaders": leaders,
        "final_ranking": fin_order,
        "first_reversal": {f"{a}|{b}": [t, str(c)] for (a, b), (t, c) in first.items()},
        "upward_radius": {f"{a}|{b}": (None if v is None else str(v)) for (a, b), v in up.items()},
        "rows": rows,
    }


# ------------------------------------------------------------------ analysis
def main() -> int:
    cohort = json.loads((DATA / "cohort-v04.json").read_text(encoding="utf-8"))
    truth = json.loads((DATA / "truth.json").read_text(encoding="utf-8"))
    weeks = cohort["weeks"]
    n = len(weeks)
    y = [F(v) for v in truth["decision"]["values"]]
    y_later = [F(v) for v in truth["later"]["values"]]
    later_delta = [b - a for a, b in zip(y, y_later)]
    later_l1 = sum(abs(d) for d in later_delta)

    fc = {}
    for m, rec in cohort["models"].items():
        if all(rec.get(w, {}).get("median") is not None for w in weeks):
            fc[m] = [F(rec[w]["median"]) for w in weeks]
    mae = {m: total_abs(f, y) / n for m, f in fc.items()}
    mae_later = {m: total_abs(f, y_later) / n for m, f in fc.items()}
    order = sorted(fc, key=lambda m: (mae[m], m))

    # identical forecast vectors and the CU scenario family
    groups = {}
    for m in fc:
        groups.setdefault(tuple(fc[m]), []).append(m)
    identical = [sorted(g) for g in groups.values() if len(g) > 1]
    cu = [m for m in fc if m.startswith("CU-")]
    cu_select_sources = []
    if "CU-select" in fc:
        for i, w in enumerate(weeks):
            cu_select_sources.append([w, sorted(m for m in cu if m != "CU-select" and fc[m][i] == fc["CU-select"][i])])

    pairs = []
    for a, b in itertools.combinations(order, 2):
        if mae[a] == mae[b]:
            pairs.append({"better": a, "worse": b, "tie_initially": True})
            continue
        r = radii(fc[a], fc[b], y)
        outside = sum(1 for i in range(n) if y[i] > max(fc[a][i], fc[b][i]) or y[i] < min(fc[a][i], fc[b][i]))
        later_flip = mae_later[b] < mae_later[a]
        later_tie = mae_later[b] == mae_later[a]
        pairs.append({
            "better": a, "worse": b, "gap": fstr(mae[b] - mae[a]),
            "bound": fstr(r["bound"]), "tie_radius": fstr(r["tie"]), "strict_radius": fstr(r["strict"]),
            "ratio": None if r["strict"] is None else fstr(r["strict"] / r["bound"]),
            "same_family": a in cu and b in cu,
            "weeks_truth_outside_both": outside,
            "later_reversed": later_flip, "later_tied": later_tie,
            "rank_better": order.index(a) + 1, "rank_worse": order.index(b) + 1,
        })
    real = [p for p in pairs if not p.get("tie_initially")]

    def cnt(pred):
        return sum(1 for p in real if pred(p))

    thresholds = [50, 100, 141, 150, 300, 500, 1000]
    sens = []
    for t in thresholds:
        T = F(t)
        sens.append({
            "threshold": t,
            "bound_exceeds": cnt(lambda p: F(p["bound"]) >= T),
            "exact_exceeds": cnt(lambda p: p["strict_radius"] is None or F(p["strict_radius"]) > T),
        })
    L = later_l1
    within_bound = [p for p in real if F(p["bound"]) < L]
    within_exact = [p for p in real if p["strict_radius"] is not None and F(p["strict_radius"]) < L]
    flips = [p for p in real if p["later_reversed"]]
    # theorem check: an actual reversal at cost L requires r_strict < L
    flips_ok = all(p["strict_radius"] is not None and F(p["strict_radius"]) < L for p in flips)
    tie_eq_strict = cnt(lambda p: p["tie_radius"] == p["strict_radius"])
    ratio_gt = {str(k): cnt(lambda p, k=k: p["ratio"] is not None and F(p["ratio"]) > F(k)) for k in ("1.01", "1.25", "2", "10")}

    # v0.2 pair, three-week window (catalog and box analysis)
    tw = truth["three_week"]
    y3 = [F(v) for v in tw["decision"]]
    bp3, cu3 = fc["BPagano-RtDriven"][:3], fc["CU-select"][:3]
    r3 = radii(bp3, cu3, y3)
    gap3 = {"decision": fstr((total_abs(cu3, y3) - total_abs(bp3, y3)) / 3)}
    scen = []
    for dlt in tw["adjacent_revisions"] + [[str(b - a) for a, b in zip(y3, [F(v) for v in tw["later"]])]]:
        yy = [a + F(d) for a, d in zip(y3, dlt)]
        scen.append({"delta": dlt, "gap": fstr((total_abs(cu3, yy) - total_abs(bp3, yy)) / 3)})
    r8 = radii(fc["BPagano-RtDriven"], fc["CU-select"], y)

    # Proposition 1 family through the same closed form (box |d|<=1 and without box)
    fam = []
    for q in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1)):
        A, B, yq = [F(2), F(0), F(0)], [F(0), F(2), F(0)], [2 + q, F(1), 3 - q]
        rb = radii(A, B, yq, lo=[F(-1)] * 3, hi=[F(1)] * 3)
        ru = radii(A, B, yq)
        fam.append({"q": str(q), "LA": str(total_abs(A, yq) / 3), "LB": str(total_abs(B, yq) / 3),
                    "bound": fstr(rb["bound"]), "tie_box": fstr(rb["tie"]), "strict_box": fstr(rb["strict"]),
                    "tie_nobox": fstr(ru["tie"]), "strict_nobox": fstr(ru["strict"])})

    # ---------------------------------------------------------- full revision history
    vint = vintage_history(fc, order, y, weeks, pairs)

    top = order[:3]
    res = {
        "vintages": vint,
        "schema": "fulcrum.paper1.results.v04",
        "n_weeks": n,
        "models_any_data": sum(1 for rec in cohort["models"].values() if any(v.get("median") for v in rec.values())),
        "models_directories_with_window_files": len(cohort["models"]),
        "n_models": len(fc),
        "n_pairs": len(pairs),
        "initial_ties": [p for p in pairs if p.get("tie_initially")],
        "ranking": [{"rank": k + 1, "model": m, "mae": str(mae[m]), "mae_float": ffloat(mae[m], 3),
                     "mae_later": str(mae_later[m]), "rank_later": sorted(fc, key=lambda x: (mae_later[x], x)).index(m) + 1}
                    for k, m in enumerate(order)],
        "pairs": pairs,
        "later_delta": [str(d) for d in later_delta],
        "later_l1": str(later_l1),
        "sensitivity": sens,
        "reversible_within_later_l1": {
            "by_bound": len(within_bound), "by_exact": len(within_exact),
            "exact_list": [[p["better"], p["worse"], ffloat(F(p["gap"]), 4), ffloat(F(p["bound"]), 2), ffloat(F(p["strict_radius"]), 2)] for p in within_exact],
            "bound_only_list": [[p["better"], p["worse"], ffloat(F(p["gap"]), 4), ffloat(F(p["bound"]), 2), ffloat(F(p["strict_radius"]), 2) if p["strict_radius"] else None]
                                for p in within_bound if p not in within_exact],
        },
        "later_reversals": [[p["better"], p["worse"], p["rank_better"], p["rank_worse"], ffloat(F(p["strict_radius"]), 2)] for p in flips],
        "later_reversals_consistent_with_radius": flips_ok,
        "tie_equals_strict_pairs": tie_eq_strict,
        "ratio_counts": ratio_gt,
        "ratio_max": max((F(p["ratio"]) for p in real if p["ratio"]), default=None) and fstr(max(F(p["ratio"]) for p in real if p["ratio"])),
        "identical_forecast_groups": identical,
        "cu_family": sorted(cu),
        "cu_select_sources": cu_select_sources,
        "top3": top,
        "top_pairs": [p for p in real if p["better"] in top and p["worse"] in top],
        "v02_pair": {
            "eight_week": {"bound": fstr(r8["bound"]), "strict": fstr(r8["strict"]), "tie": fstr(r8["tie"])},
            "three_week": {"bound": fstr(r3["bound"]), "strict": fstr(r3["strict"]), "tie": fstr(r3["tie"]),
                           "gap_decision": gap3["decision"], "scenario_gaps": scen,
                           "truth_outside_both_all_weeks": all(y3[i] > max(bp3[i], cu3[i]) or y3[i] < min(bp3[i], cu3[i]) for i in range(3))},
        },
        "family": fam,
    }
    out = DATA / "results-v04.json"
    out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n_models", "n_pairs", "sensitivity", "reversible_within_later_l1",
                                          "later_reversals", "later_reversals_consistent_with_radius",
                                          "tie_equals_strict_pairs", "ratio_counts", "ratio_max",
                                          "identical_forecast_groups", "top3", "family")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
