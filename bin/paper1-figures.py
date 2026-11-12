#!/usr/bin/env python3.13
"""Paper 1 v0.4 figures, journal style.

Reads   papers/paper-1/data/results-v04.json, papers/paper-1/data/truth.json
Writes  papers/paper-1/figures/fig1..fig6 (PNG, 300 dpi)

Serif type matched to the manuscript (Palatino Linotype, STIX fallback), no in-figure
titles (captions carry the message), panel letters, restrained palette.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "papers" / "paper-1"
OUT = P1 / "figures"

INK = "#111111"
MUTED = "#6b6b6b"
LIGHT = "#d9d9d9"
NAVY = "#1d3557"
CRIMSON = "#9b2226"
OCHRE = "#b5832f"
TEAL = "#2a6f6a"
DPI = 300
W = 6.3          # text width in inches


def journal_theme():
    names = {f.name for f in font_manager.fontManager.ttflist}
    serif = "Palatino Linotype" if "Palatino Linotype" in names else "STIXGeneral"
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [serif, "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "custom",
        "mathtext.rm": serif,
        "mathtext.it": f"{serif}:italic",
        "mathtext.bf": f"{serif}:bold",
        "font.size": 8.6,
        "axes.labelsize": 8.6,
        "axes.titlesize": 8.6,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "legend.fontsize": 7.6,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.6,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "xtick.major.size": 3.2,
        "ytick.major.size": 3.2,
        "axes.grid": False,
        "legend.frameon": False,
        "lines.linewidth": 1.25,
        "lines.markersize": 4.2,
        "savefig.dpi": DPI,
        "figure.dpi": 110,
        "pdf.fonttype": 42,
    })
    return serif


def despine(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def panel(ax, letter):
    ax.text(-0.13, 1.04, f"({letter})", transform=ax.transAxes, fontsize=9.2,
            fontweight="bold", va="bottom", ha="left", color=INK)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, bbox_inches="tight", pad_inches=0.04, facecolor="white",
                metadata={"Software": None})
    plt.close(fig)
    print(f"  wrote {p.name} ({p.stat().st_size} bytes)")
    return p


# ------------------------------------------------------------------ figure 1
def fig_protocol():
    fig, ax = plt.subplots(figsize=(W, 1.55))
    ax.axis("off")
    stages = ["Evidence\nbundle", "Frozen\nadmissibility policy", "Deterministic\nranking core",
              "Reversal radii\nand audit record"]
    w, h, gap, x0, y0 = 0.205, 0.50, 0.058, 0.012, 0.25
    for i, lab in enumerate(stages):
        x = x0 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.0,rounding_size=0.018",
                                    facecolor="white" if i != 2 else "#f2f2f2",
                                    edgecolor=INK, lw=0.7))
        ax.text(x + w / 2, y0 + h / 2, lab, ha="center", va="center", fontsize=8.2,
                color=INK, linespacing=1.3)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + w + gap - 0.006, y0 + h / 2), xytext=(x + w + 0.006, y0 + h / 2),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7, mutation_scale=8))
    ax.text(0.5, 0.06, "Replay recomputes the ranking and the radii from the frozen bundle, "
                       "with no live request and no new model call.",
            ha="center", va="center", fontsize=7.6, color=MUTED, style="italic")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return save(fig, "fig2-protocol.png")


# ------------------------------------------------------------------ figure 2
def fig_family(res):
    fam = res["family"]
    q = [float(F(r["q"])) for r in fam]
    strict_box = [float(F(r["strict_box"])) if r["strict_box"] else None for r in fam]
    strict_nobox = [float(F(r["strict_nobox"])) for r in fam]
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.45), gridspec_kw={"wspace": 0.32})

    xs = [x for x, s in zip(q, strict_box) if s is not None]
    ys = [s for s in strict_box if s is not None]
    a.plot([0, 1], [1, 1], color=MUTED, lw=0.9, ls=(0, (4, 2)), zorder=2)
    a.plot([0, 1], [1, 2], color=MUTED, lw=0.8, ls=(0, (1, 1.6)), zorder=2)
    a.plot(xs, ys, "-o", color=NAVY, ms=4.0, mfc="white", mew=1.0, zorder=4)
    a.plot([1], [1], "s", color=TEAL, ms=4.2, zorder=4)
    a.plot([0, 0.25, 0.5, 0.75, 1], [1] * 5, "s", color=TEAL, ms=3.6, zorder=3)
    a.annotate("strict reversal infeasible\nin the box at $q=1$", xy=(0.975, 2.0), xytext=(0.02, 2.17),
               fontsize=7.4, ha="left", va="center", color=CRIMSON,
               arrowprops=dict(arrowstyle="-|>", color=CRIMSON, lw=0.6, mutation_scale=7,
                               shrinkA=2, shrinkB=5, connectionstyle="arc3,rad=-0.12"))
    a.plot([1.0], [2.0], marker="x", color=CRIMSON, ms=6, mew=1.3, zorder=5)
    a.text(0.30, 1.065, r"tie radius $r_{=}$ = bound $ng/2$", fontsize=7.4, color=TEAL, va="bottom")
    a.text(0.13, 1.40, r"$r_{<}=1+q$", fontsize=7.8, color=NAVY)
    a.text(0.80, 1.73, "no box", fontsize=7.0, color=MUTED, rotation=24)
    a.set_xlim(-0.04, 1.08)
    a.set_ylim(0.75, 2.35)
    a.set_xticks([0, 0.25, 0.5, 0.75, 1])
    a.set_xticklabels(["0", "1/4", "1/2", "3/4", "1"])
    a.set_yticks([1, 1.25, 1.5, 1.75, 2])
    a.set_xlabel(r"family parameter $q$")
    a.set_ylabel(r"revision cost $\|\delta\|_1$")
    despine(a)
    panel(a, "a")

    # (b) minimum cost to lower the total-error difference by R, within the box
    b.plot([0, 2], [0, 1], color=INK, lw=1.2)
    b.text(0.55, 0.42, "record 2 only,\nevery $q$", fontsize=7.2, color=INK, rotation=0, va="bottom")
    b.plot([2], [1], "o", color=INK, ms=3.4, zorder=5)
    b.text(1.93, 1.05, "tie", fontsize=7.2, ha="right", va="bottom")
    for qq, col, ls in ((0.0, NAVY, "-"), (0.5, OCHRE, "-"), (1.0, CRIMSON, "-")):
        cap1 = 2 * (1 - qq)
        if cap1 > 0:
            R2 = [2 + i / 100 for i in range(1, int(round(cap1 * 100)) + 1)]
            b.plot(R2, [r / 2 + qq for r in R2], color=col, lw=1.2)
            b.plot([2, 2], [1, 1 + qq], color=col, lw=0.6, ls=(0, (1, 1.4)))
    b.axvline(2, color=MUTED, lw=0.7, ls=(0, (4, 2)))
    b.text(2.04, 0.12, r"$R=N=2$", fontsize=7.4, color=MUTED)
    leg = [Line2D([0], [0], color=NAVY, lw=1.2, label=r"$q=0$"),
           Line2D([0], [0], color=OCHRE, lw=1.2, label=r"$q=1/2$"),
           Line2D([0], [0], color=CRIMSON, lw=1.2, label=r"$q=1$")]
    b.legend(handles=leg, loc="upper left", handlelength=1.6)
    b.set_xlim(0, 4.1)
    b.set_ylim(0, 2.6)
    b.set_xticks([0, 1, 2, 3, 4])
    b.set_xlabel(r"reduction $R$ of the total-error difference")
    b.set_ylabel(r"minimum revision cost")
    despine(b)
    panel(b, "b")
    return save(fig, "fig1-exact-family.png")


# ------------------------------------------------------------------ figure 3
def fig_catalog(res):
    v = res["v02_pair"]["three_week"]
    bound, exact = float(F(v["bound"])), float(F(v["strict"]))
    vintages = ["V1", "V2", "V3", "V4", "V5", "V6"]
    weeks = [3, 5, 6, 7, 8, 8]
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.35), gridspec_kw={"wspace": 0.34})
    cols = [NAVY if w == 8 else "#bdbdbd" for w in weeks]
    bars = a.bar(vintages, weeks, color=cols, width=0.62, edgecolor=INK, lw=0.5)
    for bar, w in zip(bars, weeks):
        a.text(bar.get_x() + bar.get_width() / 2, w + 0.18, str(w), ha="center", fontsize=7.6)
    a.axhline(8, color=CRIMSON, lw=0.8, ls=(0, (4, 2)))
    a.text(-0.42, 8.55, "eight-week window", fontsize=7.3, color=CRIMSON)
    a.set_ylim(0, 9.8)
    a.set_yticks([0, 2, 4, 6, 8])
    a.set_xlabel("ordered reference vintage")
    a.set_ylabel("complete target weeks")
    despine(a)
    panel(a, "a")

    scen = ["(0,0,0)", "(9,29,−19)", "(65,4,13)", "later\n(9,−2,35)"]
    costs = [0, 57, 82, 46]
    xs = list(range(len(scen)))
    b.axhline(bound, color=MUTED, lw=0.8, ls=(0, (4, 2)))
    b.axhline(exact, color=NAVY, lw=0.9)
    b.text(3.55, bound - 14, f"gap bound {bound:.1f}", ha="right", va="top", fontsize=7.2, color=MUTED)
    b.text(3.55, exact + 14, f"exact radius {exact:.1f}", ha="right", va="bottom", fontsize=7.2, color=NAVY)
    b.bar(xs[:3], costs[:3], width=0.5, color="#bdbdbd", edgecolor=INK, lw=0.5, zorder=3)
    b.bar([3], [46], width=0.5, color="white", edgecolor=CRIMSON, lw=0.9, hatch="////", zorder=3)
    for x, c in zip(xs, costs):
        b.annotate(str(c), (x, c), textcoords="offset points", xytext=(0, 3),
                   ha="center", va="bottom", fontsize=7.4)
    b.set_ylim(0, 700)
    b.set_xlim(-0.5, 3.6)
    b.set_xticks(xs)
    b.set_xticklabels(scen, fontsize=7.0)
    b.set_ylabel(r"revision cost $\|\delta\|_1$")
    b.set_yticks([0, 200, 400, 600])
    despine(b)
    panel(b, "b")
    return save(fig, "fig5-catalog-bound.png")


# ------------------------------------------------------------------ figure 4
def fig_coverage():
    fig, ax = plt.subplots(figsize=(4.4, 2.6))
    ax.add_patch(Rectangle((-65, -19), 130, 38, facecolor="#f2f2f2", edgecolor=NAVY, lw=0.8))
    scen = [(65, 13), (0, 0), (9, -19)]
    ax.scatter([s[0] for s in scen], [s[1] for s in scen], s=20, color=INK, zorder=4)
    ax.scatter([9], [35], s=34, marker="x", color=CRIMSON, linewidths=1.3, zorder=5)
    ax.annotate("later revision (9, −2, 35):\nweek-3 change 35 exceeds width 19",
                xy=(9, 35), xytext=(24, 37), fontsize=7.3, color=CRIMSON, va="center",
                arrowprops=dict(arrowstyle="-|>", color=CRIMSON, lw=0.6, mutation_scale=7, shrinkB=4))
    ax.text(-62, -16, "declared box", fontsize=7.3, color=NAVY)
    ax.axhline(0, color=LIGHT, lw=0.5, zorder=0)
    ax.axvline(0, color=LIGHT, lw=0.5, zorder=0)
    ax.set_xlim(-72, 76)
    ax.set_ylim(-26, 46)
    ax.set_xticks([-60, -30, 0, 30, 60])
    ax.set_yticks([-20, 0, 20, 40])
    ax.set_xlabel("revision, target week 1")
    ax.set_ylabel("revision, target week 3")
    despine(ax)
    return save(fig, "fig6-coverage-failure.png")


# ------------------------------------------------------------------ figure 5
def fig_ranking(res):
    from decimal import Decimal, ROUND_HALF_UP
    rk = res["ranking"]
    models = [r["model"] for r in rk]
    mae = [float(F(r["mae"])) for r in rk]

    def half_up(x):
        x = F(x)
        return (Decimal(x.numerator) / Decimal(x.denominator)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    labels = [f"{half_up(r['mae']):,}" for r in rk]
    n = len(models)
    fig, ax = plt.subplots(figsize=(W, 0.165 * n + 0.6))
    ys = list(range(n))[::-1]
    for y, m, v, lab in zip(ys, models, mae, labels):
        if m.startswith("COVIDhub-ensemble"):
            col, mk = CRIMSON, "D"
        elif m.startswith("COVIDhub-baseline"):
            col, mk = OCHRE, "D"
        elif m.startswith("CU-"):
            col, mk = NAVY, "o"
        else:
            col, mk = INK, "o"
        ax.plot([0, v], [y, y], color=LIGHT, lw=0.6, zorder=1)
        ax.plot([v], [y], marker=mk, color=col, ms=3.6 if mk == "o" else 3.3, zorder=3)
        ax.text(v + 45, y, lab, va="center", fontsize=6.6, color=MUTED)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{i + 1}. {m}" for i, m in enumerate(models)], fontsize=6.9)
    ax.set_ylim(-0.8, n - 0.2)
    ax.set_xlim(0, max(mae) * 1.12)
    ax.set_xlabel("mean absolute error of the weekly median (incident deaths per week)")
    ax.tick_params(axis="y", length=0)
    despine(ax)
    ax.spines["left"].set_visible(False)
    leg = [Line2D([0], [0], marker="D", color="w", markerfacecolor=CRIMSON, ms=4.5, label="Hub ensemble"),
           Line2D([0], [0], marker="D", color="w", markerfacecolor=OCHRE, ms=4.5, label="Hub baseline"),
           Line2D([0], [0], marker="o", color="w", markerfacecolor=NAVY, ms=4.5, label="CU scenario family"),
           Line2D([0], [0], marker="o", color="w", markerfacecolor=INK, ms=4.5, label="other models")]
    ax.legend(handles=leg, loc="center right", bbox_to_anchor=(1.0, 0.62), handletextpad=0.3)
    return save(fig, "fig3-ranking.png")


# ------------------------------------------------------------------ figure 6
def fig_bound_vs_exact(res):
    L = float(F(res["later_l1"]))
    xs, ys, cs, ss, ms = [], [], [], [], []
    for p in res["pairs"]:
        if p.get("tie_initially") or p["strict_radius"] is None:
            continue
        bnd, ex = float(F(p["bound"])), float(F(p["strict_radius"]))
        xs.append(bnd); ys.append(ex)
        if p["later_reversed"]:
            cs.append(CRIMSON); ss.append(30); ms.append("x")
        elif bnd < L <= ex:
            cs.append(NAVY); ss.append(14); ms.append("o")
        else:
            cs.append("#9a9a9a"); ss.append(7); ms.append("o")
    fig, ax = plt.subplots(figsize=(W * 0.72, 3.25))
    lo, hi = 0.3, 3e4
    ax.plot([lo, hi], [lo, hi], color=INK, lw=0.6)
    ax.axvline(L, color=MUTED, lw=0.7, ls=(0, (4, 2)))
    ax.axhline(L, color=MUTED, lw=0.7, ls=(0, (4, 2)))
    ax.fill_between([lo, L], [L, L], [hi, hi], color="#eef1f6", zorder=0)
    for m in ("o", "x"):
        idx = [i for i, mm in enumerate(ms) if mm == m]
        if not idx:
            continue
        if m == "x":
            ax.scatter([xs[i] for i in idx], [ys[i] for i in idx], c=[cs[i] for i in idx],
                       s=[ss[i] for i in idx], marker="x", linewidths=1.3, zorder=5)
        else:
            ax.scatter([xs[i] for i in idx], [ys[i] for i in idx], c=[cs[i] for i in idx],
                       s=[ss[i] for i in idx], marker="o", linewidths=0, alpha=0.9, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(r"score-gap bound $ng/2$")
    ax.set_ylabel(r"exact strict-reversal radius $r_{<}$")
    ax.text(0.42, 7000, "bound cannot certify,\nexact radius can", fontsize=7.2, color=NAVY, va="top")
    ax.text(L * 0.86, 0.42, f"observed revision, {L:.0f}", fontsize=7.0,
            color=MUTED, rotation=90, va="bottom", ha="right")
    ax.text(5000, 2600, "$r_{<}=ng/2$", fontsize=7.2, rotation=45, ha="left", va="top")
    rev = [p for p in res["pairs"] if p.get("later_reversed")]
    if rev:
        rx = float(F(rev[0]["bound"]))
        ax.annotate("the only pair that reversed\nat the later vintage", xy=(rx, rx), xytext=(0.42, 30),
                    fontsize=7.0, color=CRIMSON, va="center",
                    arrowprops=dict(arrowstyle="-|>", color=CRIMSON, lw=0.6, mutation_scale=7, shrinkB=5))
    despine(ax)
    return save(fig, "fig4-bound-vs-exact.png")


# ------------------------------------------------------------------ figure 7
def fig_history(res):
    import datetime as dt
    import matplotlib.dates as mdates
    v = res["vintages"]
    rows = v["rows"]
    t = [dt.datetime.fromisoformat(r["time"].replace("Z", "+00:00")) for r in rows]
    cost = [float(F(r["cost"])) for r in rows]
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.6), gridspec_kw={"wspace": 0.34})
    a.step(t, [max(c, 0.5) for c in cost], where="post", color=NAVY, lw=1.1)
    a.set_yscale("log")
    a.set_ylim(40, 2e4)
    a.axhline(141, color=MUTED, lw=0.7, ls=(0, (4, 2)))
    a.text(t[-1], 160, "141, the first-month revision", ha="right", va="bottom", fontsize=7.0, color=MUTED)
    imax = max(range(len(cost)), key=lambda i: cost[i])
    a.annotate(f"maximum {cost[imax]:,.0f}", xy=(t[imax], cost[imax]), xytext=(t[imax], 1.25e4),
               fontsize=7.0, ha="center", color=INK,
               arrowprops=dict(arrowstyle="-|>", lw=0.5, color=INK, mutation_scale=6, shrinkB=2))
    a.set_ylabel(r"revision cost $\|\delta\|_1$")
    a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    a.tick_params(axis="x", labelsize=7.0)
    despine(a)
    panel(a, "a")

    for key, col, lab, ls in (("permitted_bound", MUTED, "bound below revision", (0, (4, 2))),
                              ("permitted_exact", NAVY, "exact radius below revision", "-"),
                              ("permitted_upward", TEAL, "upward-only radius below", "-"),
                              ("reversed", CRIMSON, "actually reversed", "-")):
        b.step(t, [max(r[key], 0.7) for r in rows], where="post", color=col, lw=1.15, ls=ls, label=lab)
    b.set_yscale("log")
    b.set_ylim(0.7, 1200)
    b.set_yticks([1, 10, 100, 561])
    b.set_yticklabels(["1", "10", "100", "561"])
    b.set_ylabel("number of model pairs")
    b.legend(loc="lower right", bbox_to_anchor=(1.0, 0.04), handlelength=1.5, fontsize=6.7, borderaxespad=0.2)
    b.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    b.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    b.tick_params(axis="x", labelsize=7.0)
    despine(b)
    panel(b, "b")
    return save(fig, "fig7-revision-history.png")


def main() -> int:
    serif = journal_theme()
    res = json.loads((P1 / "data" / "results-v04.json").read_text(encoding="utf-8"))
    print(f"paper 1 v0.4 figures (font: {serif}) -> {OUT}")
    made = [fig_protocol(), fig_family(res), fig_catalog(res), fig_coverage(),
            fig_ranking(res), fig_bound_vs_exact(res), fig_history(res)]
    (OUT / "manifest.json").write_text(json.dumps({"paper": 1, "version": "v0.4", "font": serif,
                                                   "dpi": DPI, "generated": [p.name for p in made]},
                                                  indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
