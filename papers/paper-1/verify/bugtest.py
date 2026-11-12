#!/usr/bin/env python3.13
"""Adversarial bug test for Paper 1 v0.4.

Written to try to BREAK the manuscript's claims by brute force, without the exact
oracle in verify.py and without the analysis code. Every search is an exhaustive scan of
an integer lattice (all values scaled to integers, so arithmetic is exact and fast).
A lattice scan can refute a claim but cannot prove one; verify.py supplies the proofs
by exact vertex enumeration. Exit 0 if no claim is refuted.

  C1  MAE is (1/n)-Lipschitz in the reference vector under L1.
  C2  Every strict reversal costs more than ng/2 and every tie costs at least ng/2.
  C3  The constant 1/2 is tight (n = 1, A = y, B = y + c).
  C4  Proposition 1 (Table 1): lattice minimum of a strict reversal sits within one
      lattice step above 1 + q, and no lattice point reverses strictly at q = 1.
  C5  Nonattainment: no lattice point with cost <= r_strict reverses strictly.
  C6  Proposition 2 closed form against exhaustive lattice search, random instances.
  C7  MSE remark: in the box, strict reversal is infeasible at q = 1, and for q < 1
      the strict infimum is 1 + q, a fixed quarter of the total MSE gap.
"""
from __future__ import annotations

import itertools
import random
import sys
from fractions import Fraction as F


def tot(f, y):
    return sum(abs(a - b) for a, b in zip(f, y))


# ---------------------------------------------------------------- C1
def c1(trials=600, rng=random.Random(1)):
    worst = F(0)
    for _ in range(trials):
        n = rng.randint(1, 6)
        f = [rng.randint(-50, 50) for _ in range(n)]
        y = [rng.randint(-50, 50) for _ in range(n)]
        d = [rng.randint(-9, 9) for _ in range(n)]
        if not any(d):
            continue
        ch = abs(F(tot(f, [a + b for a, b in zip(y, d)]) - tot(f, y), n))
        lim = F(sum(abs(x) for x in d), n)
        if ch > lim:
            return False, f"violated: change {ch} > {lim}"
        worst = max(worst, ch / lim)
    return True, f"{trials} trials, tightest ratio {float(worst):.3f}"


# ---------------------------------------------------------------- C2
def c2(trials=250, rng=random.Random(2)):
    checked = pts = 0
    closest = None
    for _ in range(trials):
        n = rng.randint(1, 3)
        A = [rng.randint(0, 16) for _ in range(n)]
        B = [rng.randint(0, 16) for _ in range(n)]
        y = [rng.randint(0, 16) for _ in range(n)]
        if tot(A, y) == tot(B, y):
            continue
        if tot(A, y) > tot(B, y):
            A, B = B, A
        N = tot(B, y) - tot(A, y)                      # = n * g, integer
        checked += 1
        rngs = [range(-t, 21) for t in y]
        for d in itertools.product(*rngs):
            yy = [a + b for a, b in zip(y, d)]
            D = tot(B, yy) - tot(A, yy)
            if D > 0:
                continue
            c = sum(abs(x) for x in d)
            pts += 1
            if D < 0 and not 2 * c > N:
                return False, f"strict reversal at cost {c} <= ng/2 = {N}/2: A={A} B={B} y={y} d={d}"
            if D == 0 and 2 * c < N:
                return False, f"tie at cost {c} < ng/2: A={A} B={B} y={y} d={d}"
            r = F(2 * c, N)
            closest = r if closest is None else min(closest, r)
    return True, f"{checked} instances, {pts} reversal or tie lattice points, closest cost/(ng/2) = {float(closest):.4f}"


# ---------------------------------------------------------------- C3
def c3():
    out = []
    for c in (2, 4, 10, 100):
        eps = F(1, 10 ** 6)
        z = F(c, 2) + eps                     # A = y = 0, B = c
        ok = abs(c - z) < abs(0 - z) and z - F(c, 2) == eps
        out.append(ok)
    return all(out), "reversal at ng/2 + 1e-6 for c = 2, 4, 10, 100"


# ---------------------------------------------------------------- C4, C5
def family_scan(q, step=16):
    """Scale by step so the lattice d in (1/step)Z is integer. Box |d| <= 1."""
    s = step
    A, B = [2 * s, 0, 0], [0, 2 * s, 0]
    y = [int((2 + q) * s), s, int((3 - q) * s)]
    best = None
    viol = 0
    target = (1 + q) * s
    for d in itertools.product(range(-s, s + 1), repeat=3):
        yy = [a + b for a, b in zip(y, d)]
        if min(yy) < 0:
            continue
        if tot(B, yy) < tot(A, yy):
            c = sum(abs(x) for x in d)
            best = c if best is None else min(best, c)
            if q < 1 and c <= target:
                viol += 1
    return best, viol


def c4_c5():
    rows, ok4, ok5 = [], True, True
    s = 16
    for q in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1)):
        best, viol = family_scan(q, s)
        if q < 1:
            got = None if best is None else F(best, s)
            good = got is not None and 1 + q < got <= 1 + q + F(3, s)
            ok4 &= good
            ok5 &= viol == 0
            rows.append(f"q={q}: lattice min {got} (claim 1+q={1 + q}, unattained)")
        else:
            ok4 &= best is None
            rows.append(f"q=1: lattice reversals {'none' if best is None else best}")
    return ok4, ok5, "; ".join(rows)


# ---------------------------------------------------------------- C6
def closed_form(A, B, y):
    N = tot(B, y) - tot(A, y)
    terms = []
    for a, b, t in zip(A, B, y):
        if a == b:
            continue
        if min(a, b) <= t <= max(a, b):
            dz = 0
        elif abs(t - b) > abs(t - a):
            dz = abs(t - a)
        else:
            continue
        terms.append((dz, abs(b - t) - abs(a - t) + abs(a - b)))
    best = None
    for k in range(1, len(terms) + 1):
        for S in itertools.combinations(terms, k):
            if sum(x[1] for x in S) > N:
                v = sum(x[0] for x in S)
                best = v if best is None else min(best, v)
    return None if best is None else F(N, 2) + best


def c6(trials=200, rng=random.Random(6)):
    s = 4                                     # lattice step 1/4
    done = 0
    for _ in range(trials):
        n = rng.randint(1, 2)
        A = [rng.randint(0, 10) for _ in range(n)]
        B = [rng.randint(0, 10) for _ in range(n)]
        y = [rng.randint(0, 10) for _ in range(n)]
        if tot(A, y) == tot(B, y):
            continue
        if tot(A, y) > tot(B, y):
            A, B = B, A
        r = closed_form(A, B, y)
        As, Bs, ys = [a * s for a in A], [b * s for b in B], [t * s for t in y]
        best = None
        for d in itertools.product(*[range(-t, 15 * s) for t in ys]):
            yy = [a + b for a, b in zip(ys, d)]
            if tot(Bs, yy) < tot(As, yy):
                c = sum(abs(x) for x in d)
                best = c if best is None else min(best, c)
        done += 1
        g = None if best is None else F(best, s)
        if r is None:
            if best is not None:
                return False, f"closed form says infeasible, lattice reverses at {g}: A={A} B={B} y={y}"
            continue
        if g is None or not (r < g <= r + F(n, s)):
            return False, f"closed form {r} vs lattice {g}: A={A} B={B} y={y}"
    return True, f"{done} random instances, closed form within one lattice step below every lattice minimum"


# ---------------------------------------------------------------- C7
def c7(step=16):
    s = step
    rows, ok = [], True
    for q in (F(0), F(1, 2), F(3, 4), F(1)):
        A, B = [2 * s, 0, 0], [0, 2 * s, 0]
        y = [int((2 + q) * s), s, int((3 - q) * s)]
        sq = lambda f, t: sum((a - b) ** 2 for a, b in zip(f, t))
        gap = sq(B, y) - sq(A, y)                  # total MSE gap, scaled by s^2
        best = None
        for d in itertools.product(range(-s, s + 1), range(-s, s + 1), (0,)):
            yy = [a + b for a, b in zip(y, d)]
            if sq(B, yy) < sq(A, yy):
                c = sum(abs(x) for x in d)
                best = c if best is None else min(best, c)
        if q < 1:
            got = F(best, s)
            good = 1 + q < got <= 1 + q + F(2, s) and F(gap, s * s) == 4 * (1 + q)
            ok &= good
            rows.append(f"q={q}: lattice min {got}, total MSE gap {F(gap, s * s)}, ratio (1+q)/gap = 1/4")
        else:
            ok &= best is None
            rows.append("q=1: no strict reversal in the box")
    return ok, "; ".join(rows)


def main():
    res = []
    for name, fn in (("C1 MAE is (1/n)-Lipschitz", c1), ("C2 gap bound", c2), ("C3 constant 1/2 tight", c3)):
        ok, msg = fn()
        res.append((name, ok, msg))
    ok4, ok5, msg = c4_c5()
    res.append(("C4 Proposition 1 by lattice", ok4, msg))
    res.append(("C5 strict infimum never attained", ok5, "no lattice point at cost <= 1+q reverses strictly"))
    for name, fn in (("C6 Proposition 2 vs lattice", c6), ("C7 MSE remark", c7)):
        ok, msg = fn()
        res.append((name, ok, msg))
    fails = 0
    for name, ok, msg in res:
        print(("PASS " if ok else "FAIL ") + name)
        print("      " + msg)
        fails += not ok
    print(f"\nOVERALL: {'PASS' if not fails else 'FAIL'} ({fails} failing)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
