#!/usr/bin/env python3.13
"""Render a Fulcrum paper Markdown file into a publication-grade HTML and PDF.

Zero non-stdlib dependency for the common path: uses Chrome/Edge headless for PDF
and a print-quality CSS stylesheet. Math is rendered from the source Markdown's
$$...$$ / $...$ spans into MathML-free HTML using a lightweight TeX subset, so the
output does not depend on MathJax being reachable.

Usage:
  py bin/render-paper.py papers/paper-1.md --out build/paper-1 --title "..."

Exit codes: 0 ok, 2 input error, 3 render error.
"""
from __future__ import annotations

import argparse
import base64
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    import shutil
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return str(mac) if mac.exists() else None


CSS = """
@page {
  size: Letter;
  margin: 22mm 20mm 22mm 20mm;
  @top-left  { content: string(paperhead); font-size: 8pt; color: #666;
               font-family: "Charter", "Georgia", serif; letter-spacing: .02em; }
  @top-right { content: string(sectionhead); font-size: 8pt; color: #666;
               font-style: italic; font-family: "Charter", "Georgia", serif; }
  @bottom-center { content: counter(page); font-size: 9pt; color: #444;
                   font-family: "Charter", "Georgia", serif; }
}
@page :first { @top-left { content: none; } @top-right { content: none; }
               @bottom-center { content: none; } }
html { font-size: 10.5pt; }
body {
  font-family: "Charter", "Source Serif Pro", "Georgia", serif;
  line-height: 1.38; color: #141414; max-width: 100%;
  margin: 0; padding: 0; text-align: justify; hyphens: auto;
  font-variant-numeric: oldstyle-nums proportional-nums;
  font-feature-settings: "onum" 1, "pnum" 1, "kern" 1, "liga" 1;
  orphans: 2; widows: 2;
}

/* ---------- title block, journal style ---------- */
.titleblock { border: none; padding: 0; margin: 0 0 1.6em 0;
              border-bottom: 3px double #141414; padding-bottom: 1.1em; }
h1 {
  font-size: 1.72rem; line-height: 1.16; margin: 0 0 .30em 0; text-align: left;
  font-weight: 700; letter-spacing: -0.015em; color: #000;
  string-set: paperhead content();
}
h1.subtitle {
  font-size: 1.02rem; font-weight: 400; color: #3a3a3a; margin: 0 0 .95em 0;
  font-style: italic; line-height: 1.32; letter-spacing: 0;
}
h1 + h1 { margin-top: 0; }
.byline { font-size: .96em; margin: .1em 0 .15em 0; color: #111; text-align: left; }
.byline .name { font-weight: 640; }
.affil { font-size: .84em; color: #444; margin: 0 0 .1em 0; text-align: left;
         font-style: italic; }
.dateline { font-size: .82em; color: #555; margin: .55em 0 0 0; text-align: left; }

/* ---------- section headings ---------- */
h2 {
  font-size: 1.02rem; margin: 1.55em 0 .42em 0; text-align: left;
  font-weight: 700; border-bottom: none; padding-bottom: 0;
  string-set: sectionhead content(); page-break-after: avoid;
}
h3 { font-size: .97rem; margin: 1.18em 0 .30em 0; text-align: left;
     font-weight: 680; font-style: italic; page-break-after: avoid; }
h4 { font-size: .94rem; margin: 1.0em 0 .28em 0; font-style: italic;
     font-weight: 600; page-break-after: avoid; }
p { margin: 0 0 .58em 0; }
p + p { text-indent: 1.35em; margin-top: 0; }
ul, ol { margin: .35em 0 .7em 0; padding-left: 1.35em; }
li { margin-bottom: .16em; }

/* ---------- abstract ---------- */
.abstract {
  font-size: .90em; line-height: 1.34; margin: 1.4em 0 1.5em 0;
  padding: .95em 1.5em; background: #fafaf9;
  border-top: 1px solid #d8d8d6; border-bottom: 1px solid #d8d8d6;
}
.abstract p { margin-bottom: .48em; text-indent: 0; }
.abstract p:last-child { margin-bottom: 0; }
.abstract-head { font-size: .76em; font-weight: 700; letter-spacing: .13em;
                 text-transform: uppercase; color: #333; margin: 0 0 .55em 0;
                 display: block; }

/* ---------- code, tables, math ---------- */
code, pre { font-family: "SFMono-Regular", "Cascadia Mono", "Consolas", monospace; }
code { font-size: .86em; background: #f3f3f4; padding: .06em .26em; border-radius: 2px; }
pre { font-size: .78em; background: #f8f8f8; border: 1px solid #e2e2e4;
      border-radius: 3px; padding: .6em .8em; overflow-x: auto; text-align: left;
      line-height: 1.32; }
pre code { background: none; padding: 0; font-size: 1em; }
table { border-collapse: collapse; width: 100%; margin: .8em 0 1.0em 0;
        font-size: .82em; page-break-inside: avoid; font-variant-numeric: tabular-nums; }
th, td { border: none; border-bottom: 1px solid #e4e4e6; padding: .32em .48em;
         text-align: left; vertical-align: top; }
thead th { border-top: 1.3px solid #141414; border-bottom: 1.0px solid #141414;
           font-weight: 660; }
tbody tr:last-child td { border-bottom: 1.3px solid #141414; }
td[align="right"], th[align="right"] { text-align: right; }
td[align="center"], th[align="center"] { text-align: center; }

/* ---------- figures ---------- */
.figure { margin: 1.15em 0 1.3em 0; text-align: center; page-break-inside: avoid; }
.figure img { max-width: 100%; height: auto; }
.figure .caption { font-size: .80em; color: #2c2c2c; margin-top: .5em;
                   text-align: justify; line-height: 1.30; }
.figure .caption b, .figure .caption .fignum { font-weight: 680; }
.eq { text-align: center; margin: .72em 0; page-break-inside: avoid; }
.eq .eqbody { display: inline-block; text-align: left; }
.eq .eqnum { float: right; color: #333; font-size: .9em; }
hr { border: none; border-top: 1px solid #dedee0; margin: 1.4em 0; }
blockquote { margin: .6em 0 .8em 0; padding-left: .9em;
             border-left: 2.5px solid #d0d0d4; color: #242424; font-size: .94em; }
a { color: #0b4a94; text-decoration: none; }
sup { font-size: .70em; line-height: 0; }
.small { font-size: .84em; color: #444; }
.nobreak { page-break-inside: avoid; }
@media print {
  a { color: #0b4a94; }
  h2, h3, h4 { page-break-after: avoid; }
  pre, table, .figure, .eq { page-break-inside: avoid; }
}
"""


# ---------------------------------------------------------------- math subset
GREEK = {
    r"\alpha": "&alpha;", r"\beta": "&beta;", r"\gamma": "&gamma;", r"\delta": "&delta;",
    r"\epsilon": "&epsilon;", r"\varepsilon": "&epsilon;", r"\zeta": "&zeta;", r"\eta": "&eta;",
    r"\theta": "&theta;", r"\kappa": "&kappa;", r"\lambda": "&lambda;", r"\mu": "&mu;",
    r"\nu": "&nu;", r"\xi": "&xi;", r"\pi": "&pi;", r"\rho": "&rho;", r"\sigma": "&sigma;",
    r"\tau": "&tau;", r"\phi": "&phi;", r"\varphi": "&phi;", r"\chi": "&chi;",
    r"\psi": "&psi;", r"\omega": "&omega;",
    r"\Gamma": "&Gamma;", r"\Delta": "&Delta;", r"\Theta": "&Theta;", r"\Lambda": "&Lambda;",
    r"\Xi": "&Xi;", r"\Pi": "&Pi;", r"\Sigma": "&Sigma;", r"\Phi": "&Phi;",
    r"\Psi": "&Psi;", r"\Omega": "&Omega;",
}
SYMBOLS = {
    r"\infty": "&infin;", r"\cdot": "&middot;", r"\times": "&times;", r"\div": "&divide;",
    r"\pm": "&plusmn;", r"\le": "&le;", r"\leq": "&le;", r"\ge": "&ge;", r"\geq": "&ge;",
    r"\ne": "&ne;", r"\neq": "&ne;", r"\approx": "&asymp;", r"\equiv": "&equiv;",
    r"\subset": "&sub;", r"\subseteq": "&sube;", r"\in": "&isin;", r"\notin": "&notin;",
    r"\cup": "&cup;", r"\cap": "&cap;", r"\emptyset": "&empty;", r"\varnothing": "&empty;",
    r"\to": "&rarr;", r"\rightarrow": "&rarr;", r"\Rightarrow": "&rArr;",
    r"\leftrightarrow": "&harr;", r"\sum": "&sum;", r"\prod": "&prod;",
    r"\int": "&int;", r"\partial": "&part;", r"\forall": "&forall;", r"\exists": "&exist;",
    r"\land": "&and;", r"\lor": "&or;", r"\neg": "&not;", r"\mid": "|",
    r"\lceil": "&#8968;", r"\rceil": "&#8969;", r"\lfloor": "&#8970;", r"\rfloor": "&#8971;",
    r"\langle": "&lang;", r"\rangle": "&rang;", r"\star": "&#8902;",
    r"\ell": "&#8467;", r"\hbar": "&#8463;", r"\Re": "&#8475;", r"\Im": "&#8465;",
    r"\prime": "&#8242;", r"\circ": "&#8728;", r"\bullet": "&bull;",
    r"\subsetneq": "&sub;", r"\supset": "&sup;", r"\supseteq": "&supe;",
    r"\setminus": "&#8726;", r"\triangle": "&#9651;", r"\Delta": "&Delta;",
    r"\propto": "&prop;", r"\sim": "&sim;", r"\simeq": "&simeq;",
    r"\ll": "&lt;&lt;", r"\gg": "&gt;&gt;", r"\mapsto": "&#8614;",
    r"\nabla": "&nabla;", r"\sqrt": "&radic;", r"\perp": "&perp;",
    r"\parallel": "&#8741;", r"\cong": "&cong;", r"\doteq": "&#8784;",
    r"\quad": "&nbsp;&nbsp;&nbsp;", r"\qquad": "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;",
    r"\,": "&thinsp;", r"\;": "&thinsp;", r"\:": "&thinsp;", r"\!": "",
    r"\log": "log", r"\exp": "exp", r"\max": "max", r"\min": "min", r"\inf": "inf",
    r"\sup": "sup", r"\arg": "arg", r"\lim": "lim", r"\cos": "cos", r"\sin": "sin",
    r"\{": "{", r"\}": "}", r"\|": "&#8214;", r"\cdots": "&#8943;", r"\ldots": "&hellip;",
    r"\dots": "&hellip;", r"\downarrow": "&darr;", r"\uparrow": "&uarr;",
    r"\lvert": "|", r"\rvert": "|", r"\lVert": "&#8214;", r"\rVert": "&#8214;",
}
DOUBLE_STRUCK = {"R": "&#8477;", "N": "&#8469;", "Z": "&#8484;", "Q": "&#8474;", "C": "&#8450;"}
# Set by md_to_html from the front matter. "journal" switches on italic math letters,
# theorem environments, numbered equations and the journal stylesheet.
THEME = {"journal": False}
FRONT_MATTER: dict[str, str] = {}
LARGE_OPS = {"sum", "prod", "int", "bigcup", "bigcap", "lim"}


def _read_group(s: str, i: int):
    """Read a {..} group or a single token starting at i. Returns (inner, next_i)."""
    if i < len(s) and s[i] == "{":
        depth, j = 1, i + 1
        start = j
        while j < len(s):
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    return s[start:j], j + 1
            j += 1
        return s[start:], len(s)
    if i < len(s) and s[i] == "\\":
        m = re.match(r"\\\\[A-Za-z]+|\\\\[^A-Za-z]", s[i:])
        if m:
            return m.group(0), i + m.end()
    if i < len(s):
        return s[i], i + 1
    return "", i


def _split_rows(body: str) -> list[str]:
    """Split a TeX environment body on top-level \\\\ row separators."""
    rows, depth, buf, i = [], 0, [], 0
    while i < len(body):
        if body[i] == "\\":
            if body.startswith("\\\\", i) and depth == 0:
                rows.append("".join(buf)); buf = []; i += 2; continue
            m = re.match(r"\\[A-Za-z]+", body[i:])
            if m:
                buf.append(m.group(0)); i += m.end(); continue
            buf.append(body[i]); i += 1; continue
        c = body[i]
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        buf.append(c)
        i += 1
    rows.append("".join(buf))
    return [r for r in rows if r.strip() != ""]


def _render_cases(body: str) -> str:
    """cases / array with a left brace, rendered as a stacked block."""
    rows = _split_rows(body)
    cells = []
    for r in rows:
        parts = re.split(r"&", r, maxsplit=1)
        lhs = tex_to_html(parts[0].strip())
        rhs = tex_to_html(parts[1].strip()) if len(parts) > 1 else ""
        cells.append(f'<div class="cases-row"><span class="cases-lhs">{lhs}</span>'
                     f'<span class="cases-rhs">{rhs}</span></div>')
    return '<span class="cases"><span class="cases-brace">{</span><span class="cases-body">' \
           + "".join(cells) + "</span></span>"


def _render_matrix(body: str, kind: str) -> str:
    rows = _split_rows(body)
    grid = []
    for r in rows:
        grid.append([tex_to_html(p.strip()) for p in re.split(r"&", r)])
    lb, rb = {"pmatrix": ("(", ")"), "bmatrix": ("[", "]"), "matrix": ("", ""),
              "vmatrix": ("|", "|")}.get(kind, ("", ""))
    body_html = "".join(
        "<div class='mx-row'>" + "".join(f"<span class='mx-cell'>{c}</span>" for c in row) + "</div>"
        for row in grid
    )
    return (f"<span class='matrix'><span class='mx-delim'>{lb}</span>"
            f"<span class='mx-body'>{body_html}</span>"
            f"<span class='mx-delim'>{rb}</span></span>")


def _typeset(tex: str, display: bool = False) -> str:
    """Typeset TeX to HTML, protecting already-produced HTML from re-parsing."""
    s = tex.strip()
    hold: list[str] = []

    def stash(html_frag: str) -> str:
        hold.append(html_frag)
        return f"\x00{len(hold) - 1}\x00"

    # 1. named text commands -> stashed literal text
    def text_cmd(m):
        cmd, val = m.group(1), m.group(2) or ""
        esc = html.escape(val)
        if cmd in ("texttt",):
            return stash(f'<code style="font-size:.88em">{esc}</code>')
        if cmd in ("operatorname", "mathrm"):
            return stash(f'<span style="font-style:normal">{esc}</span>')
        if cmd == "textsf":
            return stash(f'<span style="font-family:sans-serif">{esc}</span>')
        return stash(esc)

    s = re.sub(r"\\(text|texttt|mathrm|operatorname|textnormal|textsf|textrm)\{([^{}]*)\}",
               text_cmd, s)

    # 2. environments
    for _ in range(8):
        m = re.search(r"\\begin\{(cases|pmatrix|bmatrix|matrix|vmatrix|array|aligned|split|gathered)\}"
                      r"(\{[^}]*\})?", s)
        if not m:
            break
        kind = m.group(1)
        start = m.end()
        endm = re.search(r"\\end\{" + kind + r"\}", s[start:])
        if not endm:
            break
        inner = s[start:start + endm.start()]
        if kind == "cases":
            rep = _render_cases(inner)
        else:
            rep = _render_matrix(inner, kind)
        s = s[:m.start()] + stash(rep) + s[start + endm.end():]

    # 3. \frac
    for _ in range(16):
        m = re.search(r"\\frac", s)
        if not m:
            break
        num, i = _read_group(s, m.end())
        den, j = _read_group(s, i)
        if i == m.end():
            break
        rep = (f'<span class="frac"><span class="num">{_typeset(num)}</span>'
               f'<span class="den">{_typeset(den)}</span></span>')
        s = s[:m.start()] + stash(rep) + s[j:]

    # 4. one-token wrapper commands
    WRAP = {"mathbf": ("<b>", "</b>"), "boldsymbol": ("<b>", "</b>"), "bm": ("<b>", "</b>"),
            "mathbb": ("<b>", "</b>"), "mathcal": ("<i>", "</i>"), "mathsf": ("", ""),
            "overline": ('<span style="text-decoration:overline">', "</span>"),
            "underline": ("<u>", "</u>"), "vec": ("", "&#8407;"), "hat": ("", "&#770;"),
            "bar": ("", "&#772;"), "tilde": ("", "&#771;"), "dot": ("", "&#775;")}
    for _ in range(16):
        m = re.search(r"\\(mathbf|boldsymbol|bm|mathbb|mathcal|mathsf|overline|underline"
                      r"|vec|hat|bar|tilde|dot)\b", s)
        if not m:
            break
        name = m.group(1)
        inner, j = _read_group(s, m.end())
        if j == m.end():
            break
        op, cl = WRAP[name]
        if name == "mathbb" and inner.strip() in DOUBLE_STRUCK:
            s = s[:m.start()] + stash(DOUBLE_STRUCK[inner.strip()]) + s[j:]
            continue
        s = s[:m.start()] + stash(f"{op}{_typeset(inner)}{cl}") + s[j:]

    # \sqrt{a}
    for _ in range(16):
        m = re.search(r"\\sqrt\b", s)
        if not m:
            break
        inner, j = _read_group(s, m.end())
        if j == m.end():
            break
        s = s[:m.start()] + stash(
            f"&radic;<span style='border-top:1px solid #111'>{_typeset(inner)}</span>"
        ) + s[j:]

    # 5. remaining symbol/command table, longest-name-first
    names = sorted({k[1:] for k in list(GREEK) + list(SYMBOLS)}, key=len, reverse=True)
    pattern = re.compile(r"\\(?:" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z])")
    out: list[str] = []
    i = 0
    while i < len(s):
        m = pattern.match(s, i)
        if m:
            key = "\\" + m.group(0)[1:]
            out.append(GREEK.get(key, SYMBOLS.get(key, m.group(0))))
            i = m.end()
            continue
        ch = s[i]
        if ch == "\\":
            m2 = re.match(r"\\([A-Za-z]+)", s[i:])
            if m2:
                name = m2.group(1)
                i += m2.end()
                if name in ("left", "right", "big", "Big", "bigg", "Bigg", "displaystyle",
                            "textstyle", "limits", "nolimits", "mathstrut", "mathrm"):
                    continue
                out.append(html.escape("\\" + name))
                continue
            i += 1
            continue
        if ch in "_^":
            operand, i = _read_group(s, i + 1)
            inner = _typeset(operand)
            out.append(f"<{'sub' if ch == '_' else 'sup'}>{inner}</{'sub' if ch == '_' else 'sup'}>")
            continue
        if ch == "{":
            inner, i = _read_group(s, i)
            out.append(_typeset(inner))
            continue
        if ch in "}&":
            i += 1
            continue
        if ch == " ":
            out.append(" ")
            i += 1
            continue
        if THEME["journal"] and ch.isascii() and ch.isalpha():
            out.append(f"<i>{ch}</i>")
        elif THEME["journal"] and ch == "-":
            out.append("&minus;")
        else:
            out.append(html.escape(ch))
        i += 1

    res = "".join(out).replace("\\\\", "<br>")
    for idx, frag in enumerate(hold):
        res = res.replace(f"\x00{idx}\x00", frag)
    return res


def tex_to_html(tex: str, display: bool = False) -> str:
    return _typeset(tex, display)


FRAC_CSS = """
.frac { display: inline-block; vertical-align: middle; text-align: center;
        font-size: .92em; line-height: 1.05; margin: 0 .12em; }
.frac .num { display: block; padding: 0 .28em; border-bottom: 1px solid #111; }
.frac .den { display: block; padding: 0 .28em; }
.cases { display: inline-block; vertical-align: middle; }
.cases-brace { display: inline-block; vertical-align: middle; font-size: 2.3em;
               line-height: .82; padding-right: .12em; font-weight: 300; }
.cases-body { display: inline-block; vertical-align: middle; text-align: left; font-size: .94em; }
.cases-row { display: flex; align-items: baseline; gap: .7em; line-height: 1.5; }
.cases-lhs { min-width: 2.1em; }
.matrix { display: inline-block; vertical-align: middle; white-space: nowrap; }
.mx-delim { display: inline-block; vertical-align: middle; font-size: 1.9em;
            line-height: .78; padding: 0 .1em; font-weight: 300; }
.mx-body { display: inline-block; vertical-align: middle; text-align: center; }
.mx-row { display: block; line-height: 1.45; }
.mx-cell { display: inline-block; padding: 0 .55em; }
"""


JOURNAL_CSS = """
@page {
  size: Letter;
  margin: 0.95in 1.1in 0.9in 1.1in;
}
@page :left {
  @top-left { content: counter(page); font: 8.6pt "Palatino Linotype", "Book Antiqua", Palatino, serif;
              vertical-align: bottom; padding-bottom: 9pt; }
  @top-center { content: "@@RUNAUTHOR@@"; font: 8.6pt "Palatino Linotype", "Book Antiqua", Palatino, serif;
                font-variant: small-caps; letter-spacing: .09em; vertical-align: bottom; padding-bottom: 9pt; }
}
@page :right {
  @top-center { content: "@@RUNTITLE@@"; font: 8.6pt "Palatino Linotype", "Book Antiqua", Palatino, serif;
                font-variant: small-caps; letter-spacing: .09em; vertical-align: bottom; padding-bottom: 9pt; }
  @top-right { content: counter(page); font: 8.6pt "Palatino Linotype", "Book Antiqua", Palatino, serif;
               vertical-align: bottom; padding-bottom: 9pt; }
}
@page :first {
  @top-left { content: none; } @top-center { content: none; } @top-right { content: none; }
  @bottom-center { content: counter(page); font: 8.6pt "Palatino Linotype", "Book Antiqua", Palatino, serif; }
}
html { font-size: 10.6pt; }
body {
  font-family: "Palatino Linotype", "Book Antiqua", Palatino, "STIXGeneral", serif;
  line-height: 1.43; color: #121212; margin: 0; padding: 0;
  text-align: justify; hyphens: auto; -webkit-hyphens: auto;
  font-variant-numeric: oldstyle-nums proportional-nums;
  font-feature-settings: "kern" 1, "liga" 1, "onum" 1, "pnum" 1;
  orphans: 3; widows: 3; text-rendering: geometricPrecision;
}
a { color: inherit; text-decoration: none; overflow-wrap: anywhere; }

/* ---------- title page ---------- */
.masthead { display: flex; justify-content: space-between; font-size: 7.6pt; letter-spacing: .16em;
            text-transform: uppercase; color: #222; border-top: 1.1pt solid #111;
            border-bottom: .4pt solid #111; padding: 3.5pt 0 3pt 0; margin: 0 0 30pt 0; }
.jtitle { text-align: center; }
h1.title { font-size: 20.5pt; font-weight: 400; line-height: 1.16; margin: 0 0 7pt 0;
           letter-spacing: -.005em; text-align: center; color: #000; }
.jtitle .subtitle { font-size: 11.6pt; font-style: italic; line-height: 1.3; margin: 0 auto 17pt auto;
                    max-width: 5.1in; text-align: center; text-indent: 0; }
.jtitle .author { font-size: 11.4pt; font-variant: small-caps; letter-spacing: .1em; margin: 0 0 2pt 0;
                  text-indent: 0; text-align: center; }
.jtitle .affil { font-size: 9.4pt; font-style: italic; margin: 0; text-indent: 0; text-align: center; }
.jtitle .email { font-size: 8.4pt; margin: 2pt 0 0 0; text-indent: 0; text-align: center; color: #333; }
.jabstract { margin: 24pt 0.42in 0 0.42in; font-size: 9.35pt; line-height: 1.38; }
.jabstract .abs-head { text-align: center; font-variant: small-caps; letter-spacing: .12em; font-size: 9.8pt;
                       margin: 0 0 4pt 0; text-indent: 0; }
.jabstract p { margin: 0; text-indent: 1.2em; }
.jabstract .abs-head + p { text-indent: 0; }
.jabstract .kw { font-size: 8.6pt; text-indent: 0; margin-top: 6pt; text-align: left; line-height: 1.32; }
.jabstract .kw + .kw { margin-top: 1.5pt; }
.jabstract .kw-head { font-style: italic; margin-right: .45em; }
.jabstract::after { content: ""; display: block; width: 1.25in; margin: 18pt auto 6pt auto;
                    border-top: .5pt solid #111; }

/* ---------- headings ---------- */
h2 { font-size: 10.6pt; font-weight: 400; font-variant: small-caps; letter-spacing: .08em;
     text-align: center; margin: 19pt 0 7pt 0; break-after: avoid; page-break-after: avoid; }
h2 .secnum { margin-right: .4em; letter-spacing: 0; }
h3 { font-size: 10.6pt; font-weight: 400; font-style: italic; text-align: left; margin: 12pt 0 4pt 0;
     break-after: avoid; page-break-after: avoid; }
h3 .secnum { font-style: normal; margin-right: .35em; }
h4 { font-size: 10.6pt; font-weight: 400; font-style: italic; margin: 9pt 0 3pt 0; }

/* ---------- running text ---------- */
p { margin: 0; text-indent: 1.4em; }
h2 + p, h3 + p, h4 + p, .jbody > p:first-child { text-indent: 0; }
ul, ol { margin: 4pt 0 6pt 0; padding-left: 1.7em; }
li { margin-bottom: 2.4pt; }
li p { text-indent: 0; }
code { font-family: "Consolas", "Cascadia Mono", monospace; font-size: .84em; }
pre { font-size: 8.6pt; margin: 6pt 2.2em 8pt 2.2em; text-align: left; white-space: pre-wrap; }
pre code { font-size: 1em; }
sub, sup { font-size: .72em; line-height: 0; }
.math, .eqbody { font-variant-numeric: lining-nums proportional-nums; white-space: nowrap; }
.eqbody { white-space: normal; }

/* ---------- theorem environments ---------- */
.env { margin: 9pt 0 9pt 0; }
.env p { text-indent: 0; margin: 0 0 3pt 0; }
.env-proposition p, .env-corollary p, .env-lemma p, .env-theorem p { font-style: italic; }
.env-proposition .math, .env-corollary .math, .env-lemma .math { font-style: normal; }
.env-head { font-style: normal; font-variant: small-caps; letter-spacing: .045em; margin-right: .35em;
            font-weight: 700; }
.env-proof .env-head { font-style: italic; font-variant: normal; letter-spacing: 0; font-weight: 400; }
.env-proof p { font-style: normal; }
.env-proof p:last-child::after { content: "\\220E"; float: right; padding-left: 1em; }
.env-lead { margin-bottom: 0; }

/* ---------- display equations ---------- */
.jbody { counter-reset: eqn; }
.eq { position: relative; text-align: center; margin: 7pt 0 7pt 0; font-style: normal;
      break-inside: avoid; padding: 0 2.6em; }
.eq::after { counter-increment: eqn; content: "(" counter(eqn) ")"; position: absolute; right: 0;
             top: 50%; transform: translateY(-50%); font-style: normal;
             font-variant-numeric: lining-nums; }

/* ---------- tables ---------- */
.tcap { text-indent: 0; text-align: center; font-size: 8.9pt; line-height: 1.36; margin: 13pt auto 4pt auto;
        max-width: 92%; break-after: avoid; page-break-after: avoid; }
.tlabel { font-variant: small-caps; letter-spacing: .06em; margin-right: .35em; font-weight: 400; }
table { border-collapse: collapse; margin: 3pt auto 13pt auto; font-size: 8.8pt; line-height: 1.3;
        font-variant-numeric: lining-nums tabular-nums; break-inside: avoid; page-break-inside: avoid; }
th, td { border: none; padding: 2pt 7pt; vertical-align: baseline; text-align: left; }
td { white-space: nowrap; }
thead th { border-top: 1pt solid #111; border-bottom: .5pt solid #111; font-weight: 400;
           font-style: italic; padding-top: 3.5pt; padding-bottom: 3pt; }
tbody tr:first-child td { padding-top: 3.5pt; }
tbody tr:last-child td { border-bottom: 1pt solid #111; padding-bottom: 3.5pt; }
td[align="right"], th[align="right"] { text-align: right; }
td[align="center"], th[align="center"] { text-align: center; }

table.long { break-inside: auto; page-break-inside: auto; }
table.long tr { break-inside: avoid; }

/* ---------- figures ---------- */
.figure { margin: 12pt 0 13pt 0; text-align: center; break-inside: avoid; page-break-inside: avoid; }
.figure img { max-width: 100%; height: auto; }
.figure .caption { font-size: 8.9pt; line-height: 1.36; text-align: justify; margin: 6pt 0 0 0;
                   text-indent: 0; }
.flabel { font-variant: small-caps; letter-spacing: .06em; margin-right: .3em; }

/* ---------- references ---------- */
h2.refs-head + ol { font-size: 8.8pt; line-height: 1.34; padding-left: 2.3em; text-align: left;
                    hyphens: manual; }
h2.refs-head + ol li { margin-bottom: 2.6pt; padding-left: .2em; }
h2.refs-head + ol li::marker { content: "[" counter(list-item) "]\\2002"; font-variant-numeric: lining-nums; }
"""


# ---------------------------------------------------------------- md subset
def inline_md(t: str, math_cb) -> str:
    # inline TeX commands that appear in prose outside math mode
    t = re.sub(r"\\(?:texttt|texttt|texttt)\{([^{}]*)\}",
               lambda m: f"<code>{html.escape(m.group(1))}</code>", t)
    t = re.sub(r"\\(?:emph|textit)\{([^{}]*)\}",
               lambda m: f"<i>{html.escape(m.group(1))}</i>", t)
    t = re.sub(r"\\textbf\{([^{}]*)\}",
               lambda m: f"<b>{html.escape(m.group(1))}</b>", t)
    t = html.escape(t, quote=False)
    # un-escape the code/italic wrappers we just inserted
    t = t.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    t = t.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    t = t.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    # restore math placeholders later; first protect stashes
    t = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", t)

    def link(m):
        label, url = m.group(1), m.group(2)
        label = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", label)
        label = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", label)
        return f'<a href="{url}">{label}</a>'

    t = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|[^)]+)\)", link, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"(?<![A-Za-z0-9_])_([^_]+)_(?![A-Za-z0-9_])", r"<i>\1</i>", t)
    return t


MATH_TOKEN = "\x01M"


def md_to_html(md: str, base_dir: Path) -> str:
    lines = md.split("\n")
    # front matter
    fm: dict[str, str] = {}
    if lines and lines[0].strip() == "---":
        block_key = None
        for k, ln in enumerate(lines[1:], start=1):
            if ln.strip() == "---":
                lines = lines[k + 1:]
                break
            # YAML-style block scalar: "key: |" followed by indented lines
            if block_key is not None and (ln.startswith("  ") or not ln.strip()):
                fm[block_key] += ln[2:] + "\n"
                continue
            block_key = None
            if ":" in ln:
                key, _, val = ln.partition(":")
                key = key.strip().lower()
                if val.strip() == "|":
                    block_key = key
                    fm[key] = ""
                else:
                    fm[key] = val.strip().strip('"').strip("'")
        THEME["journal"] = fm.get("theme", "").lower() == "journal"
        FRONT_MATTER.clear()
        FRONT_MATTER.update(fm)

    math_store: list[tuple[str, bool, str | None]] = []
    eq_counter = [0]

    def pre_math(text: str) -> str:
        """Replace math with tokens; display math lines become their own block marker."""
        # display $$...$$ (may be multiline)
        def d(m):
            inner = m.group(1)
            # join wrapped display-math lines with a space so trailing/leading
            # spacing commands do not fuse into the next identifier
            inner = re.sub(r"\n\s*", " ", inner)
            math_store.append((inner, True, None))
            return f"\n{MATH_TOKEN}{len(math_store) - 1}{MATH_TOKEN}\n"

        text = re.sub(r"\$\$(.+?)\$\$", d, text, flags=re.S)

        def i_(m):
            math_store.append((m.group(1), False, None))
            return f"{MATH_TOKEN}{len(math_store) - 1}{MATH_TOKEN}"

        text = re.sub(r"(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)", i_, text)
        return text

    def resolve_math(text: str) -> str:
        def r(m):
            tex, display, _ = math_store[int(m.group(1))]
            body = tex_to_html(tex, display)
            if display:
                eq_counter[0] += 1
                ref = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                return (f'<div class="eq" id="eq{eq_counter[0]}">'
                        f'<span class="eqbody">{body}</span></div>')
            return f'<span class="math">{body}</span>'
        return re.sub(f"{MATH_TOKEN}(\\d+){MATH_TOKEN}", r, text)

    body_md = pre_math("\n".join(lines))

    out: list[str] = []
    i = 0
    blines = body_md.split("\n")
    n = len(blines)
    in_ul = in_ol = False
    pending_head: list[str | None] = [None]   # theorem-environment head for the next paragraph
    while i < n:
        raw = blines[i]
        line = raw.strip()
        if in_ul and not line.startswith(("- ", "* ")):
            out.append("</ul>"); in_ul = False
        if in_ol and not re.match(r"^\d+\.\s", line):
            out.append("</ol>"); in_ol = False
        if not line:
            i += 1
            continue
        if line == "---":
            out.append("<hr>")
            i += 1
            continue
        if line.startswith("```"):
            buf = []
            i += 1
            while i < n and not blines[i].strip().startswith("```"):
                buf.append(blines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue
        m = re.match(r"^:::\s*(.*)$", line)
        if m:
            head = m.group(1).strip()
            if head:
                kind = re.sub(r"[^a-z]", "", head.split()[0].lower())
                out.append(f'<div class="env env-{kind}">')
                pending_head[0] = head
            else:
                out.append("</div>")
            i += 1
            continue
        m = re.fullmatch(f"{MATH_TOKEN}(\\d+){MATH_TOKEN}", line)
        if m:
            if pending_head[0]:
                out.append(f'<p class="env-lead"><span class="env-head">'
                           f'{resolve_math(inline_md(pending_head[0], None))}</span></p>')
                pending_head[0] = None
            out.append(resolve_math(line))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            raw_h = m.group(2)
            num = ""
            if THEME["journal"]:
                mm = re.match(r"^((?:\d+\.)+\d*|Appendix [A-Z]\.)\s+(.*)$", raw_h)
                if mm:
                    num, raw_h = mm.group(1), mm.group(2)
            txt = resolve_math(inline_md(raw_h, None))
            if num:
                txt = f'<span class="secnum">{html.escape(num)}</span> {txt}'
            cls = ' class="refs-head"' if raw_h.strip() == "References" else ""
            out.append(f"<h{lvl}{cls}>{txt}</h{lvl}>")
            i += 1
            continue
        if line.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", blines[i + 1].strip()):
            header = [c.strip() for c in line.strip("|").split("|")]
            aligns = []
            for c in blines[i + 1].strip().strip("|").split("|"):
                c = c.strip()
                aligns.append("right" if c.endswith(":") and c.startswith(":") or c.endswith(":") and not c.startswith(":")
                              else ("center" if c.startswith(":") and c.endswith(":") else "left"))
            aligns = []
            for c in blines[i + 1].strip().strip("|").split("|"):
                c = c.strip()
                if c.startswith(":") and c.endswith(":"):
                    aligns.append("center")
                elif c.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            i += 2
            rows = []
            while i < n and blines[i].strip().startswith("|"):
                rows.append([c.strip() for c in blines[i].strip().strip("|").split("|")])
                i += 1
            t = ['<table class="long"><thead><tr>' if len(rows) > 14 else '<table><thead><tr>']
            for k, h in enumerate(header):
                al = aligns[k] if k < len(aligns) else "left"
                t.append(f'<th align="{al}">{resolve_math(inline_md(h, None))}</th>')
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>")
                for k in range(len(header)):
                    cell = r[k] if k < len(r) else ""
                    al = aligns[k] if k < len(aligns) else "left"
                    t.append(f'<td align="{al}">{resolve_math(inline_md(cell, None))}</td>')
                t.append("</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{resolve_math(inline_md(line[2:], None))}</li>")
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            if not in_ol:
                out.append("<ol>"); in_ol = True
            out.append(f"<li>{resolve_math(inline_md(m.group(2), None))}</li>")
            i += 1
            continue
        if line.startswith(">"):
            buf = []
            while i < n and blines[i].strip().startswith(">"):
                buf.append(blines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>" + resolve_math(inline_md(" ".join(buf), None)) + "</blockquote>")
            continue
        # figure directive:  ![[path|Caption]]  or  ![Caption](path)
        m = re.fullmatch(r"!\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", line)
        if m:
            out.append(figure_html(m.group(1), m.group(2), base_dir,
                                   resolve_math(inline_md(m.group(2), None)) if m.group(2) else None))
            i += 1
            continue
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if m:
            out.append(figure_html(m.group(2), m.group(1), base_dir))
            i += 1
            continue
        # paragraph
        buf = [line]
        i += 1
        while i < n:
            nx = blines[i].strip()
            if (not nx or nx.startswith("#") or nx.startswith("|") or nx.startswith("- ")
                    or nx.startswith("* ") or re.match(r"^\d+\.\s", nx) or nx == "---"
                    or nx.startswith(">") or re.fullmatch(f"{MATH_TOKEN}(\\d+){MATH_TOKEN}", nx)
                    or re.fullmatch(r"!\[\[[^\]]+\]\]", nx) or nx.startswith(":::")
                    or nx.startswith("```")):
                break
            buf.append(nx)
            i += 1
        txt = resolve_math(inline_md(" ".join(buf), None))
        cls = ""
        if THEME["journal"] and re.match(r"<b>Table [A-Z]?\.?\d", txt):
            cls = ' class="tcap"'
            txt = re.sub(r"^<b>(Table [^<]+)</b>", r'<span class="tlabel">\1</span>', txt)
        if pending_head[0]:
            txt = (f'<span class="env-head">{resolve_math(inline_md(pending_head[0], None))}</span> ' + txt)
            pending_head[0] = None
        out.append(f"<p{cls}>{txt}</p>")

    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")

    title = fm.get("title", "")
    subtitle = fm.get("subtitle", "")
    author = fm.get("author", "")
    author2 = fm.get("author2", "")
    affil = fm.get("affiliation", "")
    email = fm.get("email", "")
    date = fm.get("date", "")
    abstract = fm.get("abstract", "") or fm.get("abstract_text", "")
    head = ""
    if THEME["journal"] and (title or author):
        e = html.escape
        head = ['<header class="jtitle">',
                f'<div class="masthead"><span>{e(fm.get("version", "Working paper"))}</span>'
                f'<span>{e(date)}</span></div>']
        if title:
            head.append(f'<h1 class="title">{e(title)}</h1>')
        if subtitle:
            head.append(f'<p class="subtitle">{e(subtitle)}</p>')
        if author:
            head.append(f'<p class="author">{e(author)}</p>')
        if affil:
            head.append(f'<p class="affil">{e(affil)}</p>')
        if email:
            head.append(f'<p class="email">Correspondence: <a href="mailto:{e(email)}">{e(email)}</a></p>')
        head.append("</header>")
        if abstract:
            head.append('<section class="jabstract"><p class="abs-head">Abstract</p>')
            head.append(md_to_html(abstract.strip(), base_dir))
            if fm.get("keywords"):
                head.append(f'<p class="kw"><span class="kw-head">Keywords</span> {e(fm["keywords"])}</p>')
            if fm.get("classification"):
                head.append(f'<p class="kw"><span class="kw-head">Classification</span> {e(fm["classification"])}</p>')
            head.append("</section>")
        return "".join(head) + '<div class="jbody">' + "".join(out) + "</div>"
    if title or author:
        head = ['<div class="titleblock">']
        if title:
            head.append(f"<h1>{html.escape(title)}</h1>")
        if subtitle:
            head.append(f'<h1 class="subtitle">{html.escape(subtitle)}</h1>')
        if author:
            head.append(f'<p class="byline"><span class="name">{html.escape(author)}</span>')
            if author2:
                head.append(f' and <span class="name">{html.escape(author2)}</span>')
            head.append('</p>')
        if affil:
            head.append(f'<p class="affil">{html.escape(affil)}</p>')
        if email:
            head.append(f'<p class="affil">{html.escape(email)}</p>')
        if date:
            head.append(f'<p class="dateline">{html.escape(date)}</p>')
        head.append("</div>")
        if abstract:
            head.append('<div class="abstract">')
            head.append('<span class="abstract-head">Abstract</span>')
            # inline MD for the abstract block (no section headings inside)
            head.append(md_to_html(abstract.strip(), base_dir))
            head.append("</div>")
    return "".join(head) + "".join(out)


def figure_html(src: str, caption: str | None, base_dir: Path, cap_html: str | None = None) -> str:
    p = Path(src)
    if not p.is_absolute():
        cand = (base_dir / src)
        if cand.exists():
            p = cand
    style = ""
    if p.exists() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"):
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif"}[p.suffix.lower()]
        raw = p.read_bytes()
        if THEME["journal"] and raw[:8] == b"\x89PNG\r\n\x1a\n":
            # print figures at their physical size (300 dpi) so type sizes match across figures
            w = int.from_bytes(raw[16:20], "big")
            style = f' style="width:{w / 300:.3f}in"'
        data = base64.b64encode(raw).decode("ascii")
        img = f'<img src="data:{mime};base64,{data}"{style} alt="{html.escape(caption or p.name)}">'
    else:
        img = f'<img src="{html.escape(src)}" alt="{html.escape(caption or src)}">'
    cap = ""
    if caption:
        ctext = cap_html if cap_html is not None else inline_md(caption, None)
        if THEME["journal"]:
            ctext = re.sub(r"^(Figure\s+[A-Z]?\.?\d+\.)", r'<span class="flabel">\1</span>', ctext)
        cap = f'<div class="caption">{ctext}</div>'
    return f'<div class="figure">{img}{cap}</div>'


def build_html(md_text: str, base_dir: Path) -> str:
    body = md_to_html(md_text, base_dir)
    css = CSS
    if THEME["journal"]:
        q = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
        css = (JOURNAL_CSS.replace("@@RUNTITLE@@", q(FRONT_MATTER.get("running_title", FRONT_MATTER.get("title", ""))))
                          .replace("@@RUNAUTHOR@@", q(FRONT_MATTER.get("running_author", FRONT_MATTER.get("author", "")))))
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(FRONT_MATTER.get('title', 'paper'))}</title>"
        f"<style>{css}{FRAC_CSS}</style></head><body>{body}</body></html>"
    )


def normalize_pdf_dates(pdf_path: Path, date_text: str) -> None:
    """Replace Chrome's creation and modification timestamps with a fixed value of the same
    length, so repeated builds give identical bytes. Byte offsets do not move."""
    import datetime as _dt
    stamp = b"20000101000000"
    for fmt in ("%d %B %Y", "%Y-%m-%d"):
        try:
            stamp = _dt.datetime.strptime(date_text.split(",")[0].strip(), fmt).strftime("%Y%m%d000000").encode()
            break
        except ValueError:
            pass
    data = pdf_path.read_bytes()
    def fix(m):
        tz = m.group(2)
        tz = b"+00'00'" if len(tz) == 7 else tz
        return b"/" + m.group(1) + b" (D:" + stamp + tz + b")"

    new = re.sub(rb"/(CreationDate|ModDate) \(D:\d{14}([^)]*)\)", fix, data)
    if len(new) == len(data):
        pdf_path.write_bytes(new)


def render_pdf(chrome: str, html_path: Path, pdf_path: Path, timeout: int = 180) -> tuple[bool, str]:
    profile = Path(tempfile.mkdtemp(prefix="dsh-chrome-"))
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--virtual-time-budget=12000", "--run-all-compositor-stages-before-draw",
        f"--user-data-dir={profile}",
        "--print-to-pdf-no-header", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "chrome pdf render timed out"
    if pdf_path.exists() and pdf_path.stat().st_size > 2000:
        return True, (r.stderr or "")[-600:]
    return False, (r.stderr or r.stdout or "no output")[-1500:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--out", required=True, help="output basename, e.g. build/paper-1")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    src = Path(a.markdown)
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2
    out_base = Path(a.out).resolve()
    out_base.parent.mkdir(parents=True, exist_ok=True)
    html_doc = build_html(src.read_text(encoding="utf-8"), src.parent)
    html_path = out_base.with_suffix(".html")
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"html: {html_path} ({len(html_doc)} bytes)")
    if a.no_pdf:
        return 0
    chrome = find_chrome()
    if not chrome:
        print("no chrome/edge found; html only", file=sys.stderr)
        return 3
    pdf_path = out_base.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    ok, msg = render_pdf(chrome, html_path, pdf_path)
    if not ok:
        print(f"pdf render failed: {msg}", file=sys.stderr)
        return 3
    normalize_pdf_dates(pdf_path, FRONT_MATTER.get("date", ""))
    print(f"pdf:  {pdf_path} ({pdf_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())