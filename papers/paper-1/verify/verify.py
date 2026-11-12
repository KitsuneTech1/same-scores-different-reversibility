#!/usr/bin/env python3.13
"""Paper 1 v0.4 verifier. Exact rational arithmetic, standard library only.

It checks the manuscript three ways and never imports the analysis code:

  A. An exact polyhedral oracle (cell decomposition plus vertex enumeration, n <= 3)
     recomputes Proposition 1 (Table 1) from the definitions, including attainment.
  B. An independent implementation of the closed form in Proposition 2 is compared
     with the oracle on random instances with random coordinate boxes, and the
     nonattainment corollary is checked on every instance.
  C. Every number the manuscript states about the archive (claims.json) is recomputed
     from the raw cohort medians and truth vectors in data/.

Run from anywhere. Prints a JSON summary. Exit 0 only if every check passes.
"""
from __future__ import annotations

import itertools
import json
import random
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent


# ------------------------------------------------------------------ A. exact oracle
def _solve(rows, rhs):
    """Gaussian elimination over Fractions. Returns the solution or None if singular."""
    n = len(rows)
    M = [list(r) + [b] for r, b in zip(rows, rhs)]
    for c in range(n):
        piv = next((r for r in range(c, n) if M[r][c] != 0), None)
        if piv is None:
            return None
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def _sgn(x):
    return (x > 0) - (x < 0)


def oracle(A, B, y, lo, hi):
    """Exact tie radius and strict infimum over {d : lo <= d <= hi, y + d >= 0}, cost ||d||_1.

    The box is split at every breakpoint of |A_i - y_i - d_i|, |B_i - y_i - d_i| and |d_i|.
    On each closed cell the loss difference D and the cost are affine, so the minimum over
    {D = 0} or over the closure of {D < 0} is attained at a vertex, enumerated exactly.
    Returns dict(tie, strict, strict_attained). None means the event is infeasible.
    """
    n = len(y)
    lo = [max(l, -t) for l, t in zip(lo, y)]
    cuts = []
    for i in range(n):
        pts = {lo[i], hi[i]}
        for p in (F(0), A[i] - y[i], B[i] - y[i]):
            if lo[i] < p < hi[i]:
                pts.add(p)
        s = sorted(pts)
        cuts.append([(s[k], s[k + 1]) for k in range(len(s) - 1)] or [(s[0], s[0])])
    best_tie = best_strict = None
    strict_attained = False
    for cell in itertools.product(*cuts):
        mid = [(a + b) / 2 for a, b in cell]
        sA = [_sgn(y[i] + mid[i] - A[i]) for i in range(n)]
        sB = [_sgn(y[i] + mid[i] - B[i]) for i in range(n)]
        s0 = [_sgn(mid[i]) for i in range(n)]
        c = [sB[i] - sA[i] for i in range(n)]
        c0 = sum(sB[i] * (y[i] - B[i]) - sA[i] * (y[i] - A[i]) for i in range(n))

        def D(d):
            return c0 + sum(ci * di for ci, di in zip(c, d))

        def cost(d):
            return sum(si * di for si, di in zip(s0, d))

        def inside(d):
            return all(cell[i][0] <= d[i] <= cell[i][1] for i in range(n))

        corners = [list(v) for v in itertools.product(*cell)]
        cands = list(corners)
        if any(ci != 0 for ci in c):
            for act in itertools.combinations(range(n), n - 1):
                for side in itertools.product((0, 1), repeat=n - 1):
                    rows, rhs = [list(map(F, c))], [-c0]
                    for k, i in enumerate(act):
                        e = [F(0)] * n
                        e[i] = F(1)
                        rows.append(e)
                        rhs.append(cell[i][side[k]])
                    sol = _solve(rows, rhs)
                    if sol is not None and inside(sol):
                        cands.append(sol)
        for d in cands:
            if D(d) == 0:
                k = cost(d)
                if best_tie is None or k < best_tie:
                    best_tie = k
        if min(D(v) for v in corners) < 0:                       # the cell meets {D < 0}
            for d in cands:
                if D(d) <= 0:
                    k = cost(d)
                    if best_strict is None or k < best_strict:
                        best_strict, strict_attained = k, D(d) < 0
                    elif k == best_strict and D(d) < 0:
                        strict_attained = True
    return {"tie": best_tie, "strict": best_strict, "strict_attained": strict_attained}


# ------------------------------------------------------------------ B. closed form
def closed_form(A, B, y, lo=None, hi=None):
    """Proposition 2, written independently of bin/paper1-analysis.py."""
    n = len(y)
    N = sum(abs(b - t) - abs(a - t) for a, b, t in zip(A, B, y))
    terms = []
    for i in range(n):
        a, b, t = A[i], B[i], y[i]
        if a == b:
            continue
        if b > t:
            reach = None if hi is None else hi[i]
        else:
            reach = t if lo is None else min(-lo[i], t)
        if min(a, b) <= t <= max(a, b):
            dz = F(0)
        elif abs(t - b) > abs(t - a):          # a lies between t and b
            dz = abs(t - a)
        else:                                  # b lies between a and t
            continue
        cap = (abs(b - t) - abs(a - t)) + abs(a - b)
        if reach is not None:
            if reach <= dz:
                continue
            cap = min(cap, 2 * (reach - dz))
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
    return {"N": N, "bound": N / 2,
            "tie": None if tie is None else N / 2 + tie,
            "strict": None if strict is None else N / 2 + strict}


# ------------------------------------------------------------------ checks
def check_family():
    rows, ok = [], True
    want = {F(0): F(1), F(1, 4): F(5, 4), F(1, 2): F(3, 2), F(3, 4): F(7, 4), F(1): None}
    for q, s_want in want.items():
        A, B, y = [F(2), F(0), F(0)], [F(0), F(2), F(0)], [2 + q, F(1), 3 - q]
        LA = sum(abs(a - t) for a, t in zip(A, y)) / 3
        LB = sum(abs(b - t) for b, t in zip(B, y)) / 3
        o = oracle(A, B, y, [F(-1)] * 3, [F(1)] * 3)
        u = oracle(A, B, y, [F(-10)] * 3, [F(10)] * 3)
        good = (LA == F(4, 3) and LB == 2 and o["tie"] == 1 and o["strict"] == s_want
                and not o["strict_attained"] and u["strict"] == 1 + q)
        ok &= good
        rows.append({"q": str(q), "LA": str(LA), "LB": str(LB), "tie": str(o["tie"]),
                     "strict_box": str(o["strict"]), "strict_attained": o["strict_attained"],
                     "strict_wide_box": str(u["strict"]), "pass": good})
    o1 = oracle([F(5)], [F(23)], [F(5)], [F(-100)], [F(100)])
    n1 = o1["tie"] == 9 and o1["strict"] == 9 and not o1["strict_attained"]
    return ok and n1, {"rows": rows, "n1_example": {k: str(v) for k, v in o1.items()}, "n1_pass": n1}


def check_closed_form(trials=400, seed=11):
    rng = random.Random(seed)
    done = mism = attained = below = 0
    for _ in range(trials):
        n = rng.choice([1, 2, 2, 3, 3])
        A = [F(rng.randint(0, 12)) for _ in range(n)]
        B = [F(rng.randint(0, 12)) for _ in range(n)]
        y = [F(rng.randint(0, 12)) for _ in range(n)]
        NA = sum(abs(a - t) for a, t in zip(A, y))
        NB = sum(abs(b - t) for b, t in zip(B, y))
        if NA == NB:
            continue
        if NA > NB:
            A, B = B, A
        lo = [F(-rng.randint(0, 9), rng.choice([1, 2])) for _ in range(n)]
        hi = [F(rng.randint(0, 9), rng.choice([1, 2])) for _ in range(n)]
        o = oracle(A, B, y, lo, hi)
        c = closed_form(A, B, y, lo, hi)
        done += 1
        if o["tie"] != c["tie"] or o["strict"] != c["strict"]:
            mism += 1
        if o["strict_attained"]:
            attained += 1
        if c["tie"] is not None and c["tie"] < c["bound"]:
            below += 1
    return mism == 0 and attained == 0 and below == 0, {
        "instances": done, "oracle_vs_closed_form_mismatches": mism,
        "strict_infimum_attained": attained, "radius_below_bound": below}


def check_claims():
    cohort = json.loads((PAPER / "data" / "cohort-v04.json").read_text(encoding="utf-8"))
    truth = json.loads((PAPER / "data" / "truth.json").read_text(encoding="utf-8"))
    claims = json.loads((HERE / "claims.json").read_text(encoding="utf-8"))
    W = cohort["weeks"]
    y = [F(v) for v in truth["decision"]["values"]]
    yl = [F(v) for v in truth["later"]["values"]]
    fc = {m: [F(r[w]["median"]) for w in W] for m, r in cohort["models"].items()
          if all(r.get(w, {}).get("median") is not None for w in W)}

    def tot(f, t):
        return sum(abs(a - b) for a, b in zip(f, t))

    mae = {m: tot(f, y) / 8 for m, f in fc.items()}
    order = sorted(fc, key=lambda m: (mae[m], m))
    L = tot(y, yl)
    got = {"n_models": len(fc), "n_pairs": len(fc) * (len(fc) - 1) // 2, "later_l1": int(L),
           "model_dirs_with_window_files": len(cohort["models"]),
           "models_any_median": sum(1 for r in cohort["models"].values()
                                    if any(v.get("median") for v in r.values()))}
    pairs = []
    for a, b in itertools.combinations(order, 2):
        pairs.append((a, b, closed_form(fc[a], fc[b], y), tot(fc[b], yl) < tot(fc[a], yl)))
    got["bound_ge_L"] = sum(1 for p in pairs if p[2]["bound"] >= L)
    got["exact_gt_L"] = sum(1 for p in pairs if p[2]["strict"] is None or p[2]["strict"] > L)
    got["bound_lt_L"] = sum(1 for p in pairs if p[2]["bound"] < L)
    got["exact_lt_L"] = sum(1 for p in pairs if p[2]["strict"] is not None and p[2]["strict"] < L)
    got["later_reversals"] = sum(1 for p in pairs if p[3])
    got["reversed_pairs"] = [f"{a}|{b}" for a, b, _, fl in pairs if fl]
    got["tie_equals_strict"] = sum(1 for p in pairs if p[2]["tie"] == p[2]["strict"])
    for k in ("1.01", "1.25", "2", "10"):
        got[f"ratio_gt_{k}"] = sum(1 for p in pairs if p[2]["strict"] is not None
                                   and p[2]["strict"] / p[2]["bound"] > F(k))
    got["ratio_max"] = str(max(p[2]["strict"] / p[2]["bound"] for p in pairs if p[2]["strict"]))
    for t in (50, 100, 150, 300, 500, 1000):
        got[f"bound_ge_{t}"] = sum(1 for p in pairs if p[2]["bound"] >= t)
        got[f"exact_gt_{t}"] = sum(1 for p in pairs if p[2]["strict"] is None or p[2]["strict"] > t)
    got["ranks"] = {m: order.index(m) + 1 for m in claims.get("ranks", {})}
    got["mae_1dp"] = {m: f"{float(mae[m]):.1f}" for m in claims.get("mae_1dp", {})}
    got["pair_radii_2dp"] = {f"{a}|{b}": [f"{float(r['bound']):.2f}", f"{float(r['strict']):.2f}"]
                             for a, b, r, _ in pairs if f"{a}|{b}" in claims.get("pair_radii_2dp", {})}
    tw = truth["three_week"]
    y3 = [F(v) for v in tw["decision"]]
    bp, cu = fc["BPagano-RtDriven"][:3], fc["CU-select"][:3]
    r3 = closed_form(bp, cu, y3)
    got["v02_three_week_2dp"] = [f"{float(r3['bound']):.2f}", f"{float(r3['strict']):.2f}"]
    gaps = set()
    for dl in tw["adjacent_revisions"] + [[str(b - a) for a, b in zip(y3, [F(v) for v in tw["later"]])]]:
        yy = [a + F(d) for a, d in zip(y3, dl)]
        gaps.add(tot(cu, yy) - tot(bp, yy))
    got["v02_three_week_gap_invariant"] = len(gaps) == 1
    r8 = closed_form(fc["BPagano-RtDriven"], fc["CU-select"], y)
    got["v02_eight_week_2dp"] = [f"{float(r8['bound']):.2f}", f"{float(r8['strict']):.2f}"]
    outside = [sum(1 for i in range(8) if y[i] > max(fc[a][i], fc[b][i]) or y[i] < min(fc[a][i], fc[b][i]))
               for a, b, _, _ in pairs]
    got["pairs_outside_all_8"] = sum(1 for o in outside if o == 8)
    got["mean_weeks_outside_2dp"] = f"{sum(outside) / len(outside):.2f}"

    got["ratio_eq_1"] = sum(1 for p in pairs if p[2]["strict"] is not None and p[2]["strict"] == p[2]["bound"])
    mn = min((p for p in pairs if p[2]["strict"] is not None), key=lambda p: p[2]["strict"])
    got["min_exact_pair"] = f"{mn[0]}|{mn[1]}"

    # ---- every row of the manuscript's data tables, parsed from paper.md
    md = (PAPER / "paper.md").read_text(encoding="utf-8")
    tbl_bad = check_tables(md, fc, mae, tot(fc["CU-select"], yl) / 8, order, y, yl, pairs, L, truth)
    got["tables_ok"] = not tbl_bad
    if tbl_bad:
        got["tables_ok"] = tbl_bad[:20]

    got.update(check_history(md, fc, y, W, pairs))

    keys = [k for k in claims if not k.startswith("_")]
    bad = {k: {"claimed": claims[k], "recomputed": got[k]} for k in keys if k in got and claims[k] != got[k]}
    missing = [k for k in keys if k not in got]
    return not bad and not missing, {"checked": len(keys), "mismatches": bad, "unchecked": missing}


def _fmt(x, nd, comma=False):
    from decimal import Decimal, ROUND_HALF_UP, getcontext
    getcontext().prec = 60
    x = F(x)
    d = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    return f"{d:,}" if comma else f"{d}"


def _table_after(md, marker):
    """Rows (lists of cells) of the first Markdown table after the line containing marker."""
    lines = md.splitlines()
    k = next(i for i, ln in enumerate(lines) if marker in ln)
    while not lines[k].startswith("|"):
        k += 1
    rows = []
    k += 2                                            # skip header and alignment rows
    while k < len(lines) and lines[k].startswith("|"):
        rows.append([c.strip() for c in lines[k].strip().strip("|").split("|")])
        k += 1
    return rows


def check_tables(md, fc, mae, _unused, order, y, yl, pairs, L, truth):
    bad = []

    def tot(f, t):
        return sum(abs(a - b) for a, b in zip(f, t))

    rank_later = sorted(fc, key=lambda m: (tot(fc[m], yl), m))
    # Table B.1: full ranking
    rows = _table_after(md, "**Table B.1.**")
    if len(rows) != len(order):
        bad.append(f"B.1 has {len(rows)} rows, cohort has {len(order)}")
    for r, m in zip(rows, order):
        want = [str(order.index(m) + 1), m, _fmt(mae[m], 1, True), _fmt(tot(fc[m], yl) / 8, 1, True),
                str(rank_later.index(m) + 1)]
        if r != want:
            bad.append(f"B.1 row {r} != {want}")
    pr = {(a, b): (r, fl) for a, b, r, fl in pairs}

    def pair_row(a, b, star=False):
        r, fl = pr[(a, b)]
        return [a + (" *" if star else ""), b, _fmt(mae[b] - mae[a], 2), _fmt(r["bound"], 2), _fmt(r["strict"], 2)]

    # Table 3: pairs the bound cannot certify against L but the exact radius can
    rescued = [(a, b) for a, b, r, _ in pairs if r["bound"] < L <= r["strict"]]
    rows = _table_after(md, "**Table 3.**")
    if sorted((r[0], r[1]) for r in rows) != sorted(rescued):
        bad.append("Table 3 pair set differs from recomputation")
    for r in rows:
        if (r[0], r[1]) in pr and r != pair_row(r[0], r[1]):
            bad.append(f"Table 3 row {r} != {pair_row(r[0], r[1])}")
    # Table B.2: exact radius below L, starred pair reversed
    below = [(a, b) for a, b, r, _ in pairs if r["strict"] is not None and r["strict"] < L]
    rows = _table_after(md, "**Table B.2.**")
    names = [(r[0].rstrip(" *"), r[1]) for r in rows]
    if sorted(names) != sorted(below):
        bad.append("Table B.2 pair set differs from recomputation")
    for r, (a, b) in zip(rows, names):
        if (a, b) in pr and r != pair_row(a, b, star=pr[(a, b)][1]):
            bad.append(f"Table B.2 row {r} != {pair_row(a, b, star=pr[(a, b)][1])}")
    # Table 2: threshold sensitivity
    rows = _table_after(md, "**Table 2.**")
    hdr = [ln for ln in md.splitlines() if ln.startswith("| Threshold |")][0]
    ths = [int(c.strip()) for c in hdr.strip().strip("|").split("|")[1:]]
    wb = [str(sum(1 for p in pairs if p[2]["bound"] >= t)) for t in ths]
    we = [str(sum(1 for p in pairs if p[2]["strict"] is None or p[2]["strict"] > t)) for t in ths]
    if rows[0][1:] != wb or rows[1][1:] != we:
        bad.append(f"Table 2 {rows} != {wb} / {we}")
    # Table 4: the original pair
    rows = _table_after(md, "**Table 4.**")
    W3 = truth["three_week"]
    y3, yl3 = [F(v) for v in W3["decision"]], [F(v) for v in W3["later"]]
    cu, bp = fc["CU-select"], fc["BPagano-RtDriven"]
    for (lab, a, b, t, n) in (("Eight weeks, decision", cu, bp, y, 8), ("Eight weeks, later", cu, bp, yl, 8),
                              ("Three weeks, decision", cu[:3], bp[:3], y3, 3), ("Three weeks, later", cu[:3], bp[:3], yl3, 3)):
        r = next(r for r in rows if r[0] == lab)
        ma, mb = tot(a, t) / n, tot(b, t) / n
        want = [_fmt(ma, 3), _fmt(mb, 3), _fmt(ma - mb, 3)]
        if r[1:4] != want:
            bad.append(f"Table 4 {lab}: {r[1:4]} != {want}")
    return bad


def check_history(md, fc, y, W, pairs):
    """Section 6.5 and Table 5, recomputed from the US rows of every truth-file version."""
    import datetime as dt
    raw = json.loads((PAPER / "data" / "truth-vintages.json").read_text(encoding="utf-8"))
    vers = raw["versions"]

    def weekly(rows):
        out = []
        for w in W:
            sat = dt.date.fromisoformat(w)
            days = [str(sat - dt.timedelta(days=k)) for k in range(7)]
            if any(d not in rows for d in days):
                return None
            out.append(sum(F(rows[d]) for d in days))
        return out

    def tot(f, t):
        return sum(abs(a - b) for a, b in zip(f, t))

    comp = [(v["time"], v["commit"], weekly(v["us_rows"])) for v in vers]
    comp = [c for c in comp if c[2] is not None]
    dec_i = next(i for i, c in enumerate(comp) if c[1].startswith("80bf182e77a1"))
    post = comp[dec_i + 1:]
    up = {(a, b): closed_form(fc[a], fc[b], y, lo=[F(0)] * 8, hi=None)["strict"] for a, b, _, _ in pairs}
    ex = {(a, b): r["strict"] for a, b, r, _ in pairs}
    bd = {(a, b): r["bound"] for a, b, r, _ in pairs}
    ever, viol, stats, leaders = set(), 0, {}, []
    for t, c, wv in post:
        cost = tot(wv, y)
        rev = [(a, b) for a, b, _, _ in pairs if tot(fc[b], wv) < tot(fc[a], wv)]
        ever |= set(rev)
        viol += sum(1 for k in rev if not cost > ex[k])
        lead = min(fc, key=lambda m: (tot(fc[m], wv), m))
        if not leaders or leaders[-1][1] != lead:
            leaders.append((t[:10], lead))
        stats[c[:7]] = [t[:10], c[:7], f"{int(cost):,}",
                        str(sum(1 for k in bd if bd[k] < cost)), str(sum(1 for k in ex if ex[k] < cost)),
                        str(sum(1 for k in up if up[k] is not None and up[k] < cost)), str(len(rev)), lead]
    fin = post[-1][2]
    fin_order = sorted(fc, key=lambda m: (tot(fc[m], fin), m))
    costs = [tot(c[2], y) for c in post]
    imax = max(range(len(post)), key=lambda i: costs[i])
    got = {
        "hist_versions": len(vers), "hist_complete": len(comp), "hist_post": len(post),
        "hist_full_stream": sum(1 for v in vers if v.get("git_blob_sha1")),
        "hist_lfs_tail": sum(1 for v in vers if v.get("lfs_oid")),
        "hist_all_upward": sum(1 for c in post if all(a >= b for a, b in zip(c[2], y))),
        "hist_max": [post[imax][0][:10], int(costs[imax])],
        "hist_final": [post[-1][0][:10], int(costs[-1])],
        "hist_final_revision": [int(a - b) for a, b in zip(fin, y)],
        "hist_ever_reversed": len(ever),
        "hist_final_reversed": sum(1 for a, b, _, _ in pairs if tot(fc[b], fin) < tot(fc[a], fin)),
        "hist_radius_violations": viol,
        "hist_upward_immune": sum(1 for v in up.values() if v is None),
        "hist_leaders": [list(x) for x in leaders],
        "hist_final_ranks": {m: fin_order.index(m) + 1 for m in ("UMass-MechBayes", "Columbia_UNC-SurvCon",
                                                                  "COVIDhub-ensemble", "COVIDhub-baseline")},
        "hist_decision_reproduced": comp[dec_i][2] == y,
    }
    adj = []
    for (_, _, w0), (_, _, w1) in zip(comp, comp[1:]):
        d = [b - a for a, b in zip(w0, w1)]
        if any(d) and d not in adj:
            adj.append(d)
    got["hist_adjacent_nonzero"] = len(adj)
    rows = _table_after(md, "**Table 5.**")
    bad = [r for r in rows if stats.get(r[1]) != r]
    got["table5_ok"] = not bad or [f"{r} != {stats.get(r[1])}" for r in bad]
    return got


def main() -> int:
    out = {}
    ok_a, out["A_proposition1_oracle"] = check_family()
    ok_b, out["B_closed_form_vs_oracle"] = check_closed_form()
    ok_c, out["C_archive_claims"] = check_claims()
    out["OVERALL"] = {"all_claims_verified": ok_a and ok_b and ok_c, "A": ok_a, "B": ok_b, "C": ok_c}
    print(json.dumps(out, indent=2))
    return 0 if out["OVERALL"]["all_claims_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
