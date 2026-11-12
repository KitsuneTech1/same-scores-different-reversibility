#!/usr/bin/env python3.13
"""Build papers/paper-1/supplement.zip for v0.4, byte-reproducibly.

Every entry gets a fixed timestamp and the entries are written in sorted order, so the
same inputs always give the same archive bytes. The original pair's receipts are carried under provenance/.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "papers" / "paper-1"
STAMP = (2026, 11, 12, 0, 0, 0)

README = """# Paper 1 supplement, v1.0

Same scores, different reversibility. Working paper v1.0, 12 November 2026. Dominick Widger, Kitsune Technologies.

## Contents

- data/cohort-v04.json: one-week-ahead US incident-death medians for every model with an
  eligible file in the window, with file path and git blob SHA-1 for each model-week.
- data/truth.json: decision and later reference vectors, the three-week catalog and box.
- data/results-v04.json: every MAE, bound, tie radius and strict radius in the paper.
- data/truth-vintages.json: the US rows for the eight target weeks from all 155 versions of
  the Hub truth file committed through March 2023, with each version's content identity.
- raw/cohort-v04-extraction.json: the extraction record for all 462 streamed files,
  including the listed and recomputed blob SHA-1 and every matching row.
- verify/: verify.py (exact oracle, closed-form cross-check, every archive number and
  table row against claims.json and paper.md), bugtest.py (exhaustive lattice search),
  generality.py (Section 3.3).
- code/: cohort-v04.py (forecast extraction), truth-vintages.py (reference history),
  paper1-analysis.py (radii), paper1-figures.py.
- provenance/: acquisition and merge receipts for the original pair, the frozen analysis plan,
  exposure correction, and an offline replay verifier with tests.
- licenses/ and THIRD-PARTY-NOTICES.md: the license of every forecast used, with full texts
  where a license requires them.

## Check it

From the repository root, with Python 3.13:

    py bin/fulcrum_repro.py all 1

Raw Hub CSVs are not redistributed. The pinned commit, path and blob identity allow
re-acquisition, subject to the source terms.
"""


def main() -> int:
    files: dict[str, bytes] = {"fulcrum-paper1-v1.0/README.md": README.encode("utf-8")}
    for rel in ("data/cohort-v04.json", "data/truth.json", "data/results-v04.json", "data/truth-vintages.json",
                "verify/verify.py", "verify/bugtest.py", "verify/generality.py", "verify/claims.json"):
        files[f"fulcrum-paper1-v1.0/{rel}"] = (P1 / rel).read_bytes()
    for name in ("cohort-v04.py", "truth-vintages.py", "paper1-analysis.py", "paper1-figures.py"):
        files[f"fulcrum-paper1-v1.0/code/{name}"] = (ROOT / "bin" / name).read_bytes()
    raw = P1 / "data" / "raw" / "cohort-v04-extraction.json"
    if raw.is_file():
        files["fulcrum-paper1-v1.0/raw/cohort-v04-extraction.json"] = raw.read_bytes()
    for sub in ("provenance", "licenses"):
        for f in sorted((P1 / sub).rglob("*")):
            if f.is_file():
                files[f"fulcrum-paper1-v1.0/{sub}/{f.relative_to(P1 / sub).as_posix()}"] = f.read_bytes()
    files["fulcrum-paper1-v1.0/THIRD-PARTY-NOTICES.md"] = (P1 / "THIRD-PARTY-NOTICES.md").read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            zi = zipfile.ZipInfo(name, date_time=STAMP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, files[name])
    out = P1 / "supplement.zip"
    out.write_bytes(buf.getvalue())
    print(f"supplement: {out} ({out.stat().st_size} bytes, {len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
