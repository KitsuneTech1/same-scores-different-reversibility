# Same scores, different reversibility

Code and data for the paper **Same scores, different reversibility: exact reversal radii for
mean-absolute-error rankings, with an audit of the US COVID-19 Forecast Hub** by Dominick Widger
(Kitsune Technologies).

The paper is [`Widger-2026-same-scores-different-reversibility.pdf`](Widger-2026-same-scores-different-reversibility.pdf).

## What it shows

Two forecasts can have the same pair of scores while the data revision needed to flip their
ranking varies freely. For mean absolute error with revisions measured in the L1 norm, the exact
cost of a reversal is the simple score-gap bound `ng/2` plus the cheapest set of *dead zones*,
the distances realized values must travel before they fall between the two forecasts.

Applied to the 34 models in the US COVID-19 Forecast Hub with complete eight-week national
forecasts (561 model pairs) and all 155 versions of the Hub's reference data through March 2023:

- In the first month, revisions were small, and the exact radius certifies 12 pairs the bound cannot.
- Later revisions reached 5,713 deaths. 49 pairs ended reversed, including first place.
- No pair reversed before the revision passed its exact radius.
- Restricting revisions to the upward direction the data took proves 299 pairs immune.

## Reproduce everything

You need Python 3.13 and matplotlib. Rendering the PDF also needs Chrome, Chromium or Edge.

```
python3.13 bin/fulcrum_repro.py all 1        # macOS or Linux
py bin/fulcrum_repro.py all 1                # Windows
```

That runs the three verification programs, recomputes every radius from the data, redraws all
seven figures, rebuilds the supplement archive, renders the paper, and writes a SHA-256 manifest.
It takes about 15 seconds. To run only the checks, which need the standard library and nothing else:

```
python3 papers/paper-1/verify/verify.py
python3 papers/paper-1/verify/bugtest.py
python3 papers/paper-1/verify/generality.py
```

`verify.py` recomputes Table 1 with an exact polyhedral oracle, cross-checks the closed form on
random instances, and recomputes every archive number and every table row in `paper.md` from the
data files. It exits non-zero on any mismatch.

## Layout

| Path | Contents |
|:---|:---|
| `papers/paper-1/paper.md` | Manuscript source |
| `papers/paper-1/data/` | Cohort medians with file paths and git blob identities, reference series, all 155 truth-file versions for the study window, every computed radius |
| `papers/paper-1/verify/` | The three verification programs and the claims file |
| `papers/paper-1/figures/` | All seven figures |
| `papers/paper-1/provenance/` | Receipts, frozen analysis plan and replay verifier for the original two-model audit |
| `papers/paper-1/licenses/`, `THIRD-PARTY-NOTICES.md` | Licenses of every forecast used |
| `bin/` | Analysis, figures, renderer, build harness, and the two acquisition scripts |

`bin/cohort-v04.py` and `bin/truth-vintages.py` re-acquire the raw data from the pinned Forecast
Hub commit. Together they stream about 8 GB, so run them on a server, not a laptop.

## Licenses

- Code: MIT, see [LICENSE](LICENSE).
- Paper text and figures: CC BY 4.0.
- Forecast and reference data: the licenses of their original publishers, listed in
  [THIRD-PARTY-NOTICES.md](papers/paper-1/THIRD-PARTY-NOTICES.md).

## Citation

See [CITATION.cff](CITATION.cff). Until the arXiv identifier is assigned, cite the repository.

## AI assistance

The analysis code, checks and manuscript were developed with substantial AI assistance, as the
paper's Declarations section describes. Every number is recomputed by the verification programs,
and the author takes full responsibility for the content.
