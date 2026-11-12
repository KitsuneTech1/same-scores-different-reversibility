---
title: Same scores, different reversibility
subtitle: Exact reversal radii for mean-absolute-error rankings, with an audit of the US COVID-19 Forecast Hub
author: Dominick Widger
affiliation: Kitsune Technologies
email: founder@kitsunetechnologies.org
date: 12 November 2026
version: Working paper v1.0
theme: journal
running_title: Same scores, different reversibility
running_author: Dominick Widger
keywords: forecast evaluation, data revision, ranking stability, mean absolute error, sensitivity analysis, exact computation, reproducibility
classification: JEL C52, C53 · MSC 2020 62M20, 90C27, 68Q17
abstract: |
  A pair of forecast scores does not determine how far the reference data must move before the ranking of the two forecasts reverses. For forecasts scored by mean absolute error, with revisions measured in the $L_1$ norm, we show that the exact tie radius and the exact strict-reversal infimum both equal the elementary score-gap bound $ng/2$ plus the cheapest set of dead zones, the distances that reference values must travel before they enter the interval spanned by the two forecasts. The strict infimum is never attained and coincides with the tie radius outside a set of measure zero, and computing the tie radius is weakly NP-hard but trivial at practical sizes. A three-record family holds both scores fixed while the strict-reversal cost runs from the bound to infinity. We apply the result to the 34 models in the US COVID-19 Forecast Hub with complete eight-week national median forecasts, 561 pairs, scored against all 155 versions of the Hub's reference data committed through March 2023. Against the first month's revision the bound cannot rule out a reversal for 30 pairs, and the exact radius clears 12 of them. Later revisions reached 5,713 deaths and 49 pairs ended reversed, including first place, yet no pair reversed before the revision passed its exact radius. Restricting revisions to the upward direction the data took proves 299 pairs immune.
---

## 1. Introduction

A historical forecast ranking depends on the reference values used to score it, and those values are revised. That rankings can move with the data vintage is long established. The real-time data literature in macroeconomics documents it in detail and builds tests around it [1, 2, 3, 4], versioned public-health data now make the same point for epidemiology [5], and a recent analysis [6] shows the stakes plainly by tracing a reported advantage of an AI forecasting system over the CDC ensemble [7] to information leaking from undetected revisions in a retrospective setup. A second literature treats the reference as a noisy proxy and asks which loss functions preserve expected orderings or test size under measurement error [8, 9, 10, 11]. A broad novelty claim about revision-sensitive evaluation would be untenable, and we make none.

Our object is narrower and deterministic. The forecasts are fixed, the realized reference vector is fixed, a set of admissible revisions is declared, and the question is how much revision, measured in $L_1$, would reverse a given pairwise ranking. It is the forecast-evaluation analogue of the fragility index for clinical trials [12], of the smallest data perturbation that overturns an empirical conclusion [13], of minimum-change sensitivity in multi-criteria decision methods [14, 15], and of the margin certificates used for classifiers [16]. It is not an expected ranking under a stochastic proxy model, not a test-power statement, and not a probability of future reversal.

The paper makes four contributions. First, for mean absolute error (MAE) it gives the exact tie radius and the exact strict-reversal infimum in closed form (Proposition 2), with three consequences: the strict infimum is never attained, it differs from the tie radius only on a measure-zero set, and computing the tie radius is weakly NP-hard (Proposition 3). Second, a three-record family shows that the two scores alone do not determine either quantity (Proposition 1). Third, an audit of all 34 complete-coverage models in the US COVID-19 Forecast Hub [17], scored against all 155 versions of the reference data committed through March 2023, shows where the exact radius matters in practice. It matters when the realized value lies outside the interval spanned by two forecasts, which during the late-2020 surge was the usual case, and it matters most when the admissible revisions are restricted to the directions real revisions take. Fourth, every analytical claim and every archive number is recomputed by programs that do not import the analysis code.

The archive demonstration concerns reported national incident-death counts over one eight-week window. It is a computational-methods example, not an evaluation of clinical decisions, public-health policy, or general model quality.

## 2. Setup and the score-gap bound

Let $A, B \in \mathbb{R}^n$ be fixed forecast vectors and $y \in \mathbb{R}^n$ a reference vector, and define

$$
L_A(y)=\frac{1}{n}\sum_{i=1}^{n}|A_i-y_i|, \qquad L_B(y)=\frac{1}{n}\sum_{i=1}^{n}|B_i-y_i|.
$$

Suppose $A$ wins strictly, with gap $g = L_B(y) - L_A(y) > 0$, and write $N = ng$ for the gap in total absolute error. Let $U$ be a declared set of admissible revisions $\delta$, with $y + \delta \ge 0$ throughout, and let the cost of a revision be $\|\delta\|_1$. The two radii are

$$
r_{<} = \inf\{\|\delta\|_1 : \delta \in U,\ L_B(y+\delta) < L_A(y+\delta)\}, \qquad r_{=} = \inf\{\|\delta\|_1 : \delta \in U,\ L_B(y+\delta) = L_A(y+\delta)\},
$$

with $\inf\varnothing = +\infty$. The loss is a mean and the cost is a sum, so their units differ by a factor of $n$. Every cost below is a total over records, in the units of the reference data.

The triangle inequality gives, record by record, $|A_i - y_i - \delta_i| \le |A_i - y_i| + |\delta_i|$ and $|B_i - y_i - \delta_i| \ge |B_i - y_i| - |\delta_i|$. Summing,

$$
n\{L_B(y+\delta)-L_A(y+\delta)\} \ \ge\ N - 2\|\delta\|_1 .
$$

So every strict reversal costs more than $N/2 = ng/2$, every tie costs at least $ng/2$, and $r_{<} \ge r_{=} \ge ng/2$. This is the standard margin-over-Lipschitz-constant argument [16] and we claim nothing new for it. The constant is tight: with $n = 1$, $A = y$ and $B = y + c$, moving $y$ by $c/2 + \epsilon$ reverses the ranking. The bound gives no converse, and Sections 3 and 6 show how loose it can be.

Three objects stay separate throughout. The *decision ranking* scores a fixed pair against one reference vintage. The *counterfactual audit* varies that reference over $U$. The *later-vintage comparison* rescores the same pair against a later vintage. A counterfactual radius is not a probability that a later vintage will reverse the ranking.

## 3. Exact reversal radii

### 3.1 A constant-score family

::: Proposition 1 (Same scores, different reversibility).
Let $A = (2,0,0)$, $B = (0,2,0)$ and $y(q) = (2+q,\ 1,\ 3-q)$ for $0 \le q \le 1$, with admissible revisions $|\delta_i| \le 1$ and $y_i(q) + \delta_i \ge 0$. Then $L_A = 4/3$ and $L_B = 2$ for every $q$, the tie radius is $r_{=}(q) = 1$, attained at $\delta = (0,1,0)$, and the strict-reversal radius is $r_{<}(q) = 1 + q$ for $0 \le q < 1$, never attained, and $r_{<}(1) = +\infty$.
:::

The total errors are $q + 1 + (3-q) = 4$ for $A$ and $(2+q) + 1 + (3-q) = 6$ for $B$, independent of $q$, so $N = 2$ and the bound is $ng/2 = 1$ for every member of the family. The radii follow from Proposition 2 below. Record 2 sits inside the interval between its two forecasts and can lower the total-error difference by exactly 2 at cost 1, which produces the tie. Record 1 sits a distance $q$ beyond the better forecast, so it must first travel that distance before it lowers the difference at all. A strict reversal needs a little more than record 2 can supply, so it pays record 1's dead zone, giving $1 + q$. At $q = 1$ the box $|\delta_1| \le 1$ leaves record 1 no room to move past its dead zone, and strict reversal becomes infeasible. Without the box the infimum at $q = 1$ is 2. The jump to infinity is a property of the declared box, while the variation in $q$ is not.

**Table 1.** Exact values for the family of Proposition 1, recomputed by the polyhedral oracle of Section 4. All finite strict entries are unattained.

| $q$ | $L_A$ | $L_B$ | Bound $ng/2$ | Tie radius $r_{=}$ | Strict infimum $r_{<}$ | $r_{<}$ without the box |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 4/3 | 2 | 1 | 1 | 1 | 1 |
| 1/4 | 4/3 | 2 | 1 | 1 | 5/4 | 5/4 |
| 1/2 | 4/3 | 2 | 1 | 1 | 3/2 | 3/2 |
| 3/4 | 4/3 | 2 | 1 | 1 | 7/4 | 7/4 |
| 1 | 4/3 | 2 | 1 | 1 | $+\infty$ | 2 |

![[figures/fig1-exact-family.png|Figure 1. The family of Proposition 1. (a) Both scores are constant in $q$, yet the strict-reversal infimum rises from the bound to 7/4 and is infeasible at $q = 1$ inside the box (dotted: without the box). The tie radius equals the bound throughout. (b) Minimum revision cost needed to lower the total-error difference by $R$. Record 2 supplies the first two units at slope 1/2 for every $q$. Beyond the tie at $R = N = 2$, record 1 must first cross its dead zone of length $q$, which is the jump that separates the strict infimum from the tie radius.]]

### 3.2 Closed form

Write $D_i(t) = |B_i - t| - |A_i - t|$ for the contribution of record $i$ to the total-error difference, so that $\sum_i D_i(y_i) = N$. As a function of $t$, $D_i$ is flat outside the interval between $A_i$ and $B_i$ and has slope $\pm 2$ inside it. Moving $t$ toward $B_i$ is the only way to lower $D_i$. Three quantities describe each record.

- The *dead zone* $z_i$ is the distance $y_i$ must travel toward $B_i$ before $D_i$ starts to fall: $z_i = 0$ when $y_i$ lies between $A_i$ and $B_i$, and $z_i = |y_i - A_i|$ when $A_i$ lies between $y_i$ and $B_i$. When $B_i$ lies between $A_i$ and $y_i$, or $A_i = B_i$, the record cannot lower the difference and is dropped.
- The *reach* $\rho_i$ is the largest admissible move toward $B_i$, given by the coordinate bounds of $U$ and by $y_i + \delta_i \ge 0$, and $\rho_i = \infty$ when unbounded.
- The *capacity* $\kappa_i = \min\{D_i(y_i) + |A_i - B_i|,\ 2(\rho_i - z_i)\}$ is how much the record can lower the difference. The record is *usable* when $\rho_i > z_i$ and $\kappa_i > 0$.

Let $I$ be the set of usable records.

::: Proposition 2 (Exact radii under MAE).
Let $U$ be a coordinate box intersected with $\{y + \delta \ge 0\}$. Then
$$ r_{=} = \frac{N}{2} + \min\Big\{\sum_{i\in S} z_i : S \subseteq I,\ \sum_{i\in S}\kappa_i \ge N\Big\}, \qquad r_{<} = \frac{N}{2} + \min\Big\{\sum_{i\in S} z_i : S \subseteq I,\ \sum_{i\in S}\kappa_i > N\Big\}, $$
with $\min\varnothing = +\infty$.
:::

The proof is in Appendix A. Lowering $D_i$ by an amount $u \in (0, \kappa_i]$ costs at least $z_i + u/2$, and moving $y_i$ straight toward $B_i$ achieves exactly that. The cost is separable across records, so for a fixed set $S$ of records that move, the cost is $\sum_{S} z_i$ plus half the total reduction. Three consequences follow.

::: Corollary 1 (Nonattainment).
When $r_{<}$ is finite it is never attained, and $r_{=}$ is attained whenever it is finite.
:::

::: Corollary 2 (Ties and strict reversals differ only on a knife edge).
$r_{<} > r_{=}$ only if every set $S$ that attains the minimum in the tie formula has $\sum_{S}\kappa_i = N$ exactly. Such an equality fails under arbitrarily small perturbations of the data, so $r_{<} = r_{=}$ outside a set of measure zero.
:::

::: Corollary 3 (When the bound is exact).
$r_{=} = ng/2$ if and only if the usable records with no dead zone have total capacity at least $N$. Otherwise the excess of each radius over the bound is the cheapest dead-zone cover.
:::

Proposition 1 is the knife edge of Corollary 2 made explicit: record 2 has $z_2 = 0$ and $\kappa_2 = 2 = N$, so it covers the tie alone and leaves nothing over for a strict reversal. Corollary 1 also settles a design question for software. Under MAE with $L_1$ cost, an "attained strict minimum" never occurs, so a report needs only three outcomes for each event: attained tie radius, unattained strict infimum, or infeasible. The verifier still tests for the fourth.

::: Proposition 3 (Complexity).
Deciding whether $r_{=} \le \tau$ for given rational data and threshold $\tau$ is NP-complete, and remains so without coordinate bounds. It admits a pseudo-polynomial dynamic program over integer capacities.
:::

Membership in NP is immediate from Proposition 2, since a set $S$ is a certificate. For hardness, take positive integers $w_1, \dots, w_n$ with sum $W$ and set $A_i = w_i$, $B_i = 2w_i$, $y_i = 0$. Then $z_i = w_i$, $\kappa_i = 2w_i$ and $N = W$, so $r_{=} = W/2 + \min\{\sum_S w_i : \sum_S w_i \ge W/2\}$, and $r_{=} \le W$ holds exactly when some subset sums to $W/2$. That is PARTITION [18]. The hardness is weak and does not bind in practice. The archive below has $n = 8$, where all $2^8$ subsets are enumerated exactly.

### 3.3 What carries over

The family is not a numerical accident of three records, but the honest list of what generalizes is short. Appending records with $A_i = B_i = y_i$ leaves every radius unchanged, since such records contribute nothing to the difference. That is true and also trivial. Rescaling forecasts, reference values and the box by $\lambda > 0$ multiplies every radius by $\lambda$. At $q = 1/2$ the strict infimum is 3/2, 3 and 15 for $\lambda = 1, 2, 10$, which is positive homogeneity and nothing more.

The phenomenon does not survive a change to squared error. Under mean squared error the same family has a score gap of $4(1+q)/3$ that moves with $q$. Inside the box the strict infimum is still $1 + q$ for $q < 1$ and infeasible at $q = 1$, but it now equals exactly one quarter of the total squared-error gap, so the score gap determines the cost. Constant scores with varying reversal cost depend on the flat regions of the absolute-error loss. Quantile (pinball) losses share those flat regions, and so does the weighted interval score built from them [19], so we expect a version of Proposition 2 to hold there. We do not prove it here.

## 4. Computational contract and verification

![[figures/fig2-protocol.png|Figure 2. Protocol. Evidence bundles pass through a frozen admissibility policy to a deterministic ranking core, and the reversal radii are computed from the same frozen inputs. Replay recomputes the ranking and the radii without a live web request or a new model call. Agent tools may collect evidence or request judgment, but only the deterministic core produces a ranking.]]

The analysis computes Proposition 2 in exact rational arithmetic from serialized decimal strings, with no interpolation, rounding or substitution. Invalid input or a solver failure is reported as such and never as a stability result. Three programs check the manuscript, and none imports the analysis code.

The first, `verify.py`, contains an exact polyhedral oracle. For $n \le 3$ it splits the admissible box at every breakpoint of $|A_i - y_i - \delta_i|$, $|B_i - y_i - \delta_i|$ and $|\delta_i|$. On each closed cell the loss difference and the cost are affine, so it enumerates the vertices of the cell intersected with the tie hyperplane or the closed strict region, and records whether any minimizer is strict. The oracle reproduces Table 1 and the $n = 1$ example with $A = y = 5$ and $B = 23$, where the tie radius and the strict infimum are both 9 and the infimum is unattained. On 380 random instances with random coordinate boxes the oracle and an independently written closed form agree exactly. In none of them is a strict infimum attained or a radius below the bound. The same program then recomputes, from the raw medians and reference vectors, every archive number stated in Sections 5 and 6 and every row of Tables 2 to 5, B.1 and B.2, which it reads from this manuscript's source, and it fails on any mismatch.

The second, `bugtest.py`, tries to break the claims by exhaustive search of integer lattices: the Lipschitz property, the bound over 949,741 reversal and tie points, tightness, Table 1, nonattainment, Proposition 2 against lattice minima on 172 random instances, and the squared-error remark. A lattice search can refute a claim but not prove it, which is why the oracle exists. A greedy minimiser that skips dead zones is an easy mistake to make here. Pointed at Proposition 1 it returns 1 for every $q$, and the lattice search catches it. The third program, `generality.py`, checks Section 3.3.

## 5. Archive design

### 5.1 Source and cohort

We use the United States COVID-19 Forecast Hub [17] at a single pinned commit, \texttt{52f10b79f02a}, whose cutoff merge receipt is 5 January 2021, 01:57:23 UTC. The target is the one-week-ahead national incident-death median for the eight Saturdays from 7 November to 26 December 2020. Absolute error elicits the median [20], so only the submitted 0.5 quantile is used. Quantile strings are compared numerically, because archives mix "0.5", "0.500" and "0.5000".

Under the Hub's convention a forecast dated on the Sunday or the Monday that opens a target week has that week's Saturday as its one-week-ahead target. A file therefore counts for a target week when it is dated on either day. When both exist, the Monday file is used, matching the Hub ensemble's rule of taking the latest submission by Monday. The selected row must have location US, the one-week-ahead incident-death target, type quantile, quantile 0.5, and the matching target end date. Of the 87 model directories at the cutoff commit, 67 hold at least one file dated on an eligible day, 46 supply at least one eligible median, and 34 supply all eight. Those 34 models give 561 pairs. Matching Sunday filenames alone would silently exclude the Hub ensemble, the Hub baseline and 16 other models that filed on Mondays.

Eligibility depends on coverage at one pinned commit, not on performance, so the cohort does not select on the outcome. It is still not a sample of independent forecasters. Five models are scenario branches of one CU codebase, and one of them, CU-select, reproduces CU-scenario_mid in weeks 1 to 3 and CU-scenario_low in weeks 3 to 8. The Hub ensemble aggregates submissions that include other cohort members. No two models submitted identical vectors. We count pairs, we do not test them, and no conclusion below treats the 561 pairs as independent comparisons.

### 5.2 Receipts and reference data

Each selected forecast file is identified by path and git blob SHA-1, recomputed from the downloaded bytes. For all 462 files streamed, it equals the blob identity in the commit tree. Hashes identify content at the pinned commit, not first publication, and Git timestamps identify versions, not past public availability [21]. Pull-request and merge-time receipts exist only for the two models of the original pair, CU-select and BPagano-RtDriven. All 16 of their files merged within their target weeks. Five CU receipts and the first BPagano receipt are later than the historical Monday 18:00 Eastern ensemble cutoff, so we make no full-week-ahead availability claim.

The reference series sums exactly seven unique daily rows, Sunday to Saturday, from the Hub's pinned truth producer, which clips negative daily cumulative differences to zero [22]. The underlying source is the JHU CSSE repository [23]. Missing days are never zero-filled. Six retained reference commits, ordered by verified ancestry, cover 3, 5, 6, 7, 8 and 8 of the target weeks. The decision vintage is the last of them, with reported Git time 3 January 2021. The later vintage is \texttt{b276f442e33d}, dated 31 January 2021, the last path commit no later than 2 February 2021, 02:00 UTC. It is a release-relative selector, not verified first availability. Its revision of the eight weekly values is $(9, -2, 35, -3, -2, -3, -30, -57)$, with $L_1$ cost 141.

For the full revision history we read every version of the Hub truth file committed from 1 November 2020 to 6 March 2023, 155 in all. The 111 versions committed before 24 May 2022 were streamed whole, and each matches its git blob SHA-1. From 24 May 2022 the file is stored in Git LFS. For those 44 versions we read the LFS pointer, which records the SHA-256 and size of the content, and then only the final 250 kB of the content by HTTP range request. That tail holds the complete US block, because rows are sorted by location and "US" sorts after every numeric code, and the extractor rejects any read in which the US block does not start at the first date of the series. A full download of the final version matched its pointer's SHA-256, and the tail method reproduced the rows of three fully streamed versions exactly. Of the 155 versions, 139 cover all eight target weeks. The decision and later vintages are among them and reproduce the vectors above exactly, and 136 complete versions follow the decision vintage.

### 5.3 Scenario catalogs for the original pair

For the pair that motivated the study, CU-select and BPagano-RtDriven, revision catalogs were declared in an analysis plan frozen before the later extraction. The primary catalog collects new-minus-old vectors between adjacent retained vintages that both cover all eight weeks. Only the final pair does, and its vector is zero. A post-extraction secondary analysis uses the first three weeks, the common support of all six vintages. There the adjacent revisions are $(65, 4, 13)$, $(0,0,0)$, $(9, 29, -19)$, $(0,0,0)$ and $(0,0,0)$, with costs 82, 0 and 57, and the symmetric box with widths $(65, 29, 19)$ has maximum cost 113. The box relaxes joint patterns and may contain combinations never observed together. The analysis manifest was frozen before the later extraction, but earlier work had viewed related January outcomes, so all historical material is treated as exposed development data.

## 6. Results

### 6.1 Ranking

Figure 3 gives the decision-vintage ranking, and Appendix Table B.1 gives every value. Columbia_UNC-SurvCon leads with an MAE of 1301.1 deaths per week, followed by Karlen-pypm (1311.2) and OliverWyman-Navigator (1327.2). The Hub ensemble ranks 11th at 1728.1 and the Hub baseline 22nd at 1981.4. The pair that motivated the study sits at ranks 6 (BPagano-RtDriven, 1515.1) and 18 (CU-select). At the later vintage the ranking is identical except that ranks 6 and 7 swap. These ranks describe one target and one window. The Hub's own evaluation of these models covers far more targets, locations and weeks [24], and nothing here substitutes for it.

![[figures/fig3-ranking.png|Figure 3. Decision-vintage ranking of the 34 complete-coverage models by MAE of the one-week-ahead national median, eight target weeks ending 7 November to 26 December 2020. Diamonds mark the Hub ensemble and baseline. The five CU scenario variants lie within 8 deaths per week of one another.]]

### 6.2 Bound and exact radius

For 295 of the 561 pairs the exact strict radius equals the bound, the case of Corollary 3 with zero dead-zone cost. For the other 266 it is larger: by more than 25 percent in 170 pairs, by a factor of more than 2 in 41, and by a factor of more than 10 in 9. The largest ratio, 2273, belongs to CU-select and CU-scenario_low, whose MAEs differ by one eighth of a death per week. Their bound is 0.5, but the two forecasts differ only in weeks where the realized value lies far outside both, so a reversal needs 1136.5 deaths of revision. The tie radius equals the strict radius in all 561 pairs, as Corollary 2 predicts for generic data.

The source of the gap is visible in the data. On average the realized weekly value lies outside the interval spanned by a pair's two forecasts in 6.38 of the 8 weeks, and in 102 pairs it does so in every week. In six of the eight weeks at least 29 of the 34 models missed on the same side of the realized value, below it while deaths rose and above it in the two holiday weeks when reported deaths dipped. A week in which both forecasts of a pair miss on the same side is a dead zone for that pair.

![[figures/fig4-bound-vs-exact.png|Figure 4. Score-gap bound $ng/2$ against the exact strict-reversal radius $r_{<}$ for all 561 pairs, logarithmic axes. Points on the diagonal are pairs where the bound is exact. Dashed lines mark the $L_1$ cost of the revision observed at the later vintage, 141. Dark points are pairs the bound cannot certify against a revision of that size but the exact radius can. The cross is the only pair that reversed at the later vintage.]]

**Table 2.** Number of pairs, out of 561, certified against every revision of $L_1$ cost up to the threshold. The bound certifies a pair when $ng/2$ is at least the threshold, and the exact radius when $r_{<}$ exceeds it. Thresholds are descriptive, and 141 is the cost of the revision observed one month later.

| Threshold | 50 | 100 | 141 | 150 | 300 | 500 | 1000 |
|:---|---:|---:|---:|---:|---:|---:|---:|
| Certified by the bound | 544 | 537 | 531 | 531 | 511 | 475 | 395 |
| Certified by the exact radius | 556 | 547 | 543 | 542 | 523 | 489 | 424 |

### 6.3 Against the first month's revision

The later vintage revised the eight weekly values by an $L_1$ cost of 141. Measured against a revision of that size, the bound cannot certify 30 pairs. The exact radius certifies 12 of them (Table 3), leaving 18 pairs whose ranking some revision of cost at most 141 could reverse (Appendix Table B.2). The 12 include the lead of the top-ranked model over both of its nearest rivals, the Hub ensemble's lead over MOBS-GLEAM_COVID, and the Hub baseline's lead over UCLA-SuEIR.

**Table 3.** The 12 pairs that the bound cannot certify against a revision of cost 141 but the exact radius can. Gap is in deaths per week, and both radii are total $L_1$ revision in deaths.

| Better model | Worse model | MAE gap | Bound $ng/2$ | Exact $r_{<}$ |
|:---|:---|---:|---:|---:|
| Columbia_UNC-SurvCon | Karlen-pypm | 10.06 | 40.25 | 175.25 |
| Columbia_UNC-SurvCon | OliverWyman-Navigator | 26.07 | 104.28 | 1023.28 |
| JCB-PRM | UCSD_NEU-DeepGLEAM | 32.16 | 128.65 | 289.08 |
| COVIDhub-ensemble | MOBS-GLEAM_COVID | 33.90 | 135.59 | 889.59 |
| COVIDhub-baseline | UCLA-SuEIR | 2.46 | 9.85 | 149.85 |
| CU-scenario_high | CU-nochange | 3.50 | 14.00 | 325.00 |
| CU-scenario_high | CU-scenario_mid | 7.50 | 30.00 | 4173.00 |
| CU-scenario_high | CU-select | 7.88 | 31.50 | 4637.50 |
| CU-scenario_high | CU-scenario_low | 8.00 | 32.00 | 5224.00 |
| CU-scenario_mid | CU-select | 0.38 | 1.50 | 560.50 |
| CU-scenario_mid | CU-scenario_low | 0.50 | 2.00 | 561.00 |
| CU-select | CU-scenario_low | 0.13 | 0.50 | 1136.50 |

Exactly one pair reversed at the later vintage: BPagano-RtDriven and JCB-PRM, ranks 6 and 7, separated by 1.41 deaths per week. Its exact radius is 5.62, equal to its bound, and it is the smallest exact radius in the cohort. A reversal by a revision of cost 141 requires $r_{<} < 141$, and the observed reversal satisfies it, as it must. The converse does not hold: of the 18 pairs a revision of that size could have reversed, the actual revision reversed one. The realized revision was not adversarial, and a radius is a distance, not a forecast of what the next vintage will do.

### 6.4 The original pair, revisited

**Table 4.** The original pair. Scores are rounded to three decimals for display. Gap is CU-select minus BPagano-RtDriven. Exact values are in the supplement.

| Window and vintage | CU-select MAE | BPagano MAE | MAE gap | Bound $ng/2$ | Exact $r_{<}$ |
|:---|---:|---:|---:|---:|---:|
| Eight weeks, decision | 1904.625 | 1515.067 | 389.558 | 1558.23 | 1558.23 |
| Eight weeks, later | 1913.500 | 1532.192 | 381.308 | | |
| Three weeks, decision | 924.667 | 623.033 | 301.634 | 452.45 | 597.45 |
| Three weeks, later | 940.000 | 638.366 | 301.634 | | |

Over eight weeks the bound is exact for this pair. The primary catalog contains only the zero vector, so its no-reversal verdict is correct and empty. On three weeks, every catalog vector costs far less than the bound and the box's maximum cost of 113 does too, so the bound alone already excludes both reversal and tie (Figure 5). The exact radius adds a sharper fact. The realized value lies outside both forecasts in all three weeks, so revisions this small cannot move the gap at all, and in fact the gap is identical, to the last digit, under every catalog vector and under the later revision. The bound allows a change of up to 92 in total error, while the dead-zone structure predicts none, and none occurred.

![[figures/fig5-catalog-bound.png|Figure 5. The original pair. (a) Complete target-week coverage of the six ordered reference vintages: only the final adjacent pair supports an eight-week revision vector, and that vector is zero. (b) $L_1$ cost of the three-week catalog vectors and of the later three-week revision (hatched), against the score-gap bound and the exact radius.]]

The later three-week revision, $(9, -2, 35)$, is absent from the catalog and outside the box, since its third coordinate exceeds the width 19 (Figure 6). An unchanged winner therefore does not validate the declared revision model. Reporting only "no reversal" would hide both the empty primary catalog and the coverage failure of the secondary box.

![[figures/fig6-coverage-failure.png|Figure 6. Projection of the declared three-week box onto target weeks 1 and 3, with the observed catalog vectors (dots) and the later revision (cross), which lies outside the box.]]

### 6.5 Against the full revision history

The first month was not representative. Revisions stayed at or below 141 through January 2021, reached 936 on 14 February 2021 and 5,454 two days later, peaked at 5,713 in June 2022, and ended at 5,348 in the final version of March 2023 (Figure 7a). The final revision is upward in every week, by 496 to 937 deaths, or 3.7 to 9.2 percent of the decision values, and 127 of the 136 later versions lie on or above the decision vintage in every week.

Against this history, 61 pairs reversed in at least one version and 49 are reversed in the final data (Table 5). The decision-vintage leader lost first place on 14 February 2021, when a revision of cost 936 passed the exact radius of 274 that protected its lead over UMass-MechBayes, the leader in the final data. The Hub ensemble stays 11th and the baseline falls from 22nd to 25th. In every one of the 136 versions, every reversed pair had an exact radius below that version's revision cost, as Proposition 2 requires.

**Table 5.** The decision ranking against selected later versions of the reference data. Revision cost is $\|\delta\|_1$ in deaths against the decision vintage. The next three columns count the pairs, out of 561, whose bound, exact radius, or upward-only exact radius lies below that cost, and so could have reversed. The last two give the pairs that did reverse and the leader in that version.

| Version | Commit | Revision cost | Bound below | Exact radius below | Upward-only radius below | Reversed | Leader |
|:---|:---|---:|---:|---:|---:|---:|:---|
| 2021-01-10 | 7e41898 | 113 | 26 | 15 | 8 | 1 | Columbia_UNC-SurvCon |
| 2021-01-31 | b276f44 | 141 | 30 | 18 | 9 | 1 | Columbia_UNC-SurvCon |
| 2021-02-14 | 0800603 | 936 | 158 | 130 | 70 | 8 | UMass-MechBayes |
| 2021-02-16 | b31ead2 | 5,454 | 488 | 468 | 205 | 44 | UMass-MechBayes |
| 2021-12-26 | 9808d47 | 5,340 | 487 | 466 | 203 | 43 | UMass-MechBayes |
| 2022-06-19 | 9ca61ee | 5,713 | 491 | 472 | 207 | 57 | UMass-MechBayes |
| 2023-03-06 | 88052f3 | 5,348 | 487 | 466 | 203 | 49 | UMass-MechBayes |

A radius is a worst-case distance, and Table 5 shows what that costs once revisions are large. Against the final revision the bound leaves 487 pairs open and the exact radius 466, while 49 reversed. The realized revisions were far from worst case. They were nearly uniform and upward, and Proposition 2 can use that information directly through its coordinate bounds. Restricting revisions to be nonnegative, a post hoc choice suggested by 127 of the 136 versions, makes 299 pairs immune to every upward revision of any size and leaves 203 open against the final revision. The informativeness of a radius depends on the admissible set as much as on the score gap.

The dense history also fills the catalog that Section 6.4 found empty. Among the 139 complete versions there are 45 distinct nonzero revisions between consecutive versions, where the declared eight-week catalog held only the zero vector. Because these come from after the decision date, they describe what happened rather than a revision model declared in advance.

![[figures/fig7-revision-history.png|Figure 7. The full revision history of the reference data, 136 versions from January 2021 to March 2023. (a) $L_1$ revision cost of each version against the decision vintage, logarithmic scale. (b) Pairs whose score-gap bound, exact radius, or upward-only exact radius lies below that cost, against the pairs that actually reversed. The actual count never exceeds any of the three, as the theory requires.]]

## 7. Discussion and limitations

The practical message is about where the elementary bound misleads. When the realized value lies between two forecasts, a revision moves the score gap at full speed and the bound is exact. When it lies outside both, as it did in most weeks of the late-2020 surge, small revisions do not move the gap at all, and the bound overstates fragility. A near-tie in score is not necessarily a fragile ranking. Twelve of the 30 pairs that the bound flags against the first month's revision have exact radii at least twice their bounds, and within the CU family the factor runs from 23 to 2273.

The full history adds two lessons. First, early revisions said little about late ones: a month in, the largest change was 141, and within six weeks it was 5,454. A radius computed against early revisions would have badly understated the risk, which is why a radius should be read as a distance, never as a forecast of the next vintage. Second, worst-case radii become uninformative once revisions are large, because almost every pair is then within reach. The remedy is a better admissible set rather than a better bound. Here a single sign restriction, suggested by the data, separated 299 provably immune pairs from the rest. Declaring such restrictions in advance, from revision histories of earlier periods or other locations [5, 23], is the natural next step, and we have not tested one prospectively.

The thresholds in Table 2 are descriptive, and the primary eight-week catalog contains only the zero vector because sparse overlap among six retained pre-decision vintages collapses it. The dense post-decision history in Section 6.5 has real support, but it was observed after the fact and is not a pre-declared revision model.

The study is one exposed historical window with post-extraction secondary analyses, including the upward-only restriction of Section 6.5. It fits no predictor, estimates no reversal probability, and reports no p-values, confidence intervals or independence-based sample-size claims. Statistical procedures for comparing forecasts, from pairwise tests of predictive accuracy [25] to model confidence sets [26], answer a different question, namely whether a gap could be noise, and transformed scales change rankings for reasons of their own [27]. Clipped daily reporting counts are not deaths by date of occurrence, even the final version of March 2023 is not presumed error-free, and filename dates do not prove issuance time. Forecast dependence, voluntary participation and external validity remain open.

## 8. Reproducibility

The code and data are at [github.com/KitsuneTech1/same-scores-different-reversibility](https://github.com/KitsuneTech1/same-scores-different-reversibility). One command recomputes everything:

```
py bin/fulcrum_repro.py all 1
```

It runs the three verification programs, regenerates all seven figures from the data files, renders this manuscript to PDF, and writes a SHA-256 manifest of every artifact. The manifest is unsigned, and the PDF's date metadata is normalized so that repeated builds produce identical bytes on the same machine. All tooling is standard-library Python 3.13 plus matplotlib, and the scripts name Python 3.13 in their first line so the launcher cannot pick another interpreter.

The data files hold the cohort medians with their paths and blob identities (`data/cohort-v04.json`), the reference vectors (`data/truth.json`), the US rows of all 155 versions of the truth file with their content identities (`data/truth-vintages.json`) and every computed radius (`data/results-v04.json`). The supplement adds the acquisition and merge receipts for the original pair, the exposure correction, and an offline replay verifier. Raw archive CSVs are not redistributed. Pinned commit, path and blob identity allow re-acquisition, subject to the source terms. `bin/cohort-v04.py` re-acquires the forecasts and `bin/truth-vintages.py` the reference history.

## 9. Conclusion

Under mean absolute error, the cost of reversing a ranking is the score-gap bound plus the cheapest set of dead zones. That one sentence explains the constant-score family, says when ties and strict reversals differ, and says when the elementary bound can be trusted. In the Forecast Hub archive it can be trusted for most pairs and not for the near-ties that matter most. There the exact radius clears the top-ranked model's lead and twelve pairs in all against the first month's revision, while the one pair that did reverse is the pair with the smallest exact radius. Over the next two years the data moved up to forty times as far, first place changed hands, and 49 pairs ended reversed, every one only after the revision passed its radius. A radius is a guarantee about a distance. Its value in practice comes from pairing it with an admissible set that reflects how the data are actually revised.

## Declarations

**Funding.** This research received no external funding.

**Competing interests.** The author is the founder of Kitsune Technologies, the affiliation listed above, which uses the methods described here in internal automation software and may offer products based on them in the future. The author has no financial or professional ties to any of the forecasting teams, the COVID-19 Forecast Hub or the CDC, holds no stock in any organization whose model is ranked, and declares no other competing interests.

**Author contributions.** Dominick Widger is the sole author and conceived the study, wrote the software, carried out the analysis, and wrote and revised the manuscript.

**Data and code availability.** All code and data are openly available at [github.com/KitsuneTech1/same-scores-different-reversibility](https://github.com/KitsuneTech1/same-scores-different-reversibility) and in the supplementary archive submitted with this paper. Together they contain every input and program needed to reproduce each number, table and figure: the cohort medians with their file paths and git blob identities, the reference series and all 155 versions of the truth file restricted to the study window, every computed radius, the analysis and figure code, and the three verification programs. Forecasts are attributed to their teams (Columbia, Karlen, Oliver Wyman, UMass, CU, Bob Pagano and the others listed in Table B.1) through the COVID-19 Forecast Hub [17], and the reference data to the JHU CSSE repository [23]. Third-party source terms are listed in the repository. Raw archive CSVs are not redistributed, and the pinned commits, paths and identities allow re-acquisition. Median values for three partial-coverage models whose licenses do not clearly permit redistribution are withheld, and no result depends on them.

**Use of generative AI.** This manuscript and its computations were developed with substantial assistance from AI tools for drafting, algebraic checking, source inspection, code generation, figure production and automated review. Every reference was checked against Crossref or arXiv, every reported number is recomputed from the data by the verification programs of Section 4, and the author reviewed the final text. Automated review is not independent human peer review. The author takes full responsibility for the content.

## Appendix A. Proofs

::: Lemma A.1.
Fix a record $i$ and an admissible move $\delta_i$, and let $u = D_i(y_i) - D_i(y_i + \delta_i)$ be the reduction it achieves. If $u > 0$ then the record is usable, $u \le \kappa_i$, and $|\delta_i| \ge z_i + u/2$. Conversely, every $u \in (0, \kappa_i]$ is achieved by a move toward $B_i$ of length exactly $z_i + u/2$.
:::

::: Proof.
As a function of $t$, $D_i(t) = |B_i - t| - |A_i - t|$ equals $|A_i - B_i|$ on the side of $A_i$, equals $-|A_i - B_i|$ on the side of $B_i$, and is linear with slope of magnitude 2 between them, decreasing toward $B_i$. A move away from $B_i$ cannot decrease it. A move toward $B_i$ leaves it unchanged until $t$ enters the interval between the forecasts, which takes distance $z_i$, then lowers it at rate 2 until $t$ reaches $B_i$, after which it is constant at its minimum $-|A_i - B_i|$. Hence a reduction $u > 0$ needs a move toward $B_i$ of length at least $z_i + u/2$, which must not exceed the reach $\rho_i$, and the total available reduction is $D_i(y_i) + |A_i - B_i|$. Both limits together give $u \le \kappa_i$ and require $\rho_i > z_i$. The converse is the same computation read backwards.
:::

::: Proof of Proposition 2.
By Lemma A.1 and separability of the cost, a revision $\delta \in U$ with reductions $u_i$ costs at least $\sum_{i: u_i > 0} (z_i + u_i/2)$, the bound is achieved by moving each record straight toward $B_i$, and records with $u_i \le 0$ only raise the difference. A tie needs $\sum_i u_i = N$ and a strict reversal needs $\sum_i u_i > N$. Fix the support $S = \{i : u_i > 0\}$. The cost is $\sum_S z_i + \frac12 \sum_S u_i$ with $0 < u_i \le \kappa_i$. For a tie it is minimized at $\sum_S u_i = N$, feasible exactly when $\sum_S \kappa_i \ge N$, giving $\sum_S z_i + N/2$. For a strict reversal the infimum over $\sum_S u_i > N$ is the same expression, approached as $\sum_S u_i \downarrow N$, and is feasible exactly when $\sum_S \kappa_i > N$. Minimizing over $S$ gives both formulas.
:::

::: Proof of the corollaries.
For Corollary 1, any strict reversal with support $S$ costs $\sum_S z_i + \frac12\sum_S u_i > \sum_S z_i + N/2 \ge r_{<}$, so no strict reversal attains $r_{<}$. A tie at cost $r_{=}$ is constructed directly. For Corollary 2, if some minimizing $S$ for the tie has $\sum_S \kappa_i > N$, it is also feasible for the strict formula with the same dead-zone sum, so $r_{<} = r_{=}$. Equality of a finite sum of data-dependent capacities with $N$ is a single linear equation in the data, which fails under arbitrarily small perturbation. Corollary 3 is the case where the minimizing $S$ has $\sum_S z_i = 0$.
:::

::: Proof of Proposition 3.
With $A_i = w_i$, $B_i = 2w_i$ and $y_i = 0$, $A_i$ lies between $y_i$ and $B_i$, so $z_i = w_i$, $D_i(0) = w_i$, $\kappa_i = 2w_i$, and $N = W$. Proposition 2 gives $r_{=} = W/2 + \min\{\sum_S w_i : \sum_S w_i \ge W/2\}$, which is at most $W$ exactly when some subset sums to $W/2$. The construction is polynomial and uses no coordinate bounds. For integer data, the minimum dead-zone sum for each attainable capacity total is computed by a knapsack dynamic program in time polynomial in $n$ and $N$.
:::

## Appendix B. Tables

**Table B.1.** All 34 complete-coverage models, MAE in deaths per week at the decision and later vintages.

| Rank | Model | MAE, decision vintage | MAE, later vintage | Rank, later |
|---:|:---|---:|---:|---:|
| 1 | Columbia_UNC-SurvCon | 1,301.1 | 1,310.0 | 1 |
| 2 | Karlen-pypm | 1,311.2 | 1,320.1 | 2 |
| 3 | OliverWyman-Navigator | 1,327.2 | 1,336.1 | 3 |
| 4 | UMass-MechBayes | 1,369.6 | 1,377.3 | 4 |
| 5 | GT-DeepCOVID | 1,385.1 | 1,393.5 | 5 |
| 6 | BPagano-RtDriven | 1,515.1 | 1,532.2 | 7 |
| 7 | JCB-PRM | 1,516.5 | 1,524.8 | 6 |
| 8 | UCSD_NEU-DeepGLEAM | 1,548.6 | 1,557.0 | 8 |
| 9 | JHUAPL-Bucky | 1,609.5 | 1,617.2 | 9 |
| 10 | LANL-GrowthRate | 1,688.3 | 1,704.1 | 10 |
| 11 | COVIDhub-ensemble | 1,728.1 | 1,736.5 | 11 |
| 12 | MOBS-GLEAM_COVID | 1,762.0 | 1,770.4 | 12 |
| 13 | LNQ-ens1 | 1,806.9 | 1,824.0 | 13 |
| 14 | UA-EpiCovDA | 1,817.8 | 1,826.1 | 14 |
| 15 | CU-scenario_high | 1,896.8 | 1,905.6 | 15 |
| 16 | CU-nochange | 1,900.3 | 1,909.1 | 16 |
| 17 | CU-scenario_mid | 1,904.3 | 1,913.1 | 17 |
| 18 | CU-select | 1,904.6 | 1,913.5 | 18 |
| 19 | CU-scenario_low | 1,904.8 | 1,913.6 | 19 |
| 20 | UMich-RidgeTfReg | 1,924.3 | 1,940.2 | 20 |
| 21 | RPI_UW-Mob_Collision | 1,977.5 | 1,970.9 | 21 |
| 22 | COVIDhub-baseline | 1,981.4 | 1,989.8 | 22 |
| 23 | UCLA-SuEIR | 1,983.8 | 1,992.2 | 23 |
| 24 | CEID-Walk | 2,045.0 | 2,053.4 | 24 |
| 25 | JHU_CSSE-DECOM | 2,156.7 | 2,165.1 | 25 |
| 26 | SteveMcConnell-CovidComplete | 2,190.8 | 2,200.1 | 26 |
| 27 | IowaStateLW-STEM | 2,198.0 | 2,213.9 | 27 |
| 28 | PSI-DRAFT | 2,413.9 | 2,429.1 | 28 |
| 29 | DDS-NBDS | 2,504.3 | 2,520.1 | 29 |
| 30 | CovidAnalytics-DELPHI | 2,518.5 | 2,526.9 | 30 |
| 31 | UT-Mobility | 2,785.2 | 2,792.8 | 31 |
| 32 | RobertWalraven-ESG | 2,993.4 | 3,008.3 | 32 |
| 33 | JHU_IDD-CovidSP | 3,763.1 | 3,771.5 | 33 |
| 34 | UCM_MESALab-FoGSEIR | 4,841.4 | 4,857.3 | 34 |

**Table B.2.** The 18 pairs whose exact strict radius is below 141, the cost of the observed later revision. The starred pair reversed at the later vintage.

| Better model | Worse model | MAE gap | Bound $ng/2$ | Exact $r_{<}$ |
|:---|:---|---:|---:|---:|
| BPagano-RtDriven * | JCB-PRM | 1.41 | 5.62 | 5.62 |
| RPI_UW-Mob_Collision | COVIDhub-baseline | 3.87 | 15.49 | 15.49 |
| RPI_UW-Mob_Collision | UCLA-SuEIR | 6.33 | 25.33 | 25.33 |
| SteveMcConnell-CovidComplete | IowaStateLW-STEM | 7.25 | 29.00 | 29.00 |
| LNQ-ens1 | UA-EpiCovDA | 10.87 | 43.47 | 43.47 |
| DDS-NBDS | CovidAnalytics-DELPHI | 14.25 | 57.00 | 57.00 |
| UMass-MechBayes | GT-DeepCOVID | 15.51 | 62.05 | 62.05 |
| CU-nochange | CU-scenario_mid | 4.00 | 16.00 | 69.00 |
| CU-nochange | CU-select | 4.38 | 17.50 | 70.50 |
| CU-nochange | CU-scenario_low | 4.50 | 18.00 | 71.00 |
| CU-scenario_low | UMich-RidgeTfReg | 19.56 | 78.23 | 78.23 |
| CU-select | UMich-RidgeTfReg | 19.68 | 78.73 | 78.73 |
| CU-scenario_mid | UMich-RidgeTfReg | 20.06 | 80.23 | 80.23 |
| CU-nochange | UMich-RidgeTfReg | 24.06 | 96.23 | 96.23 |
| CU-scenario_high | UMich-RidgeTfReg | 27.56 | 110.23 | 110.23 |
| Karlen-pypm | OliverWyman-Navigator | 16.01 | 64.03 | 130.03 |
| BPagano-RtDriven | UCSD_NEU-DeepGLEAM | 33.57 | 134.27 | 134.27 |
| JHU_CSSE-DECOM | SteveMcConnell-CovidComplete | 34.03 | 136.12 | 136.12 |

## References

1. Croushore, D., and Stark, T. (2001). A real-time data set for macroeconomists. *Journal of Econometrics*, 105(1), 111-130. [doi:10.1016/S0304-4076(01)00072-0](https://doi.org/10.1016/S0304-4076%2801%2900072-0).
2. Stark, T., and Croushore, D. (2002). Forecasting with a real-time data set for macroeconomists. *Journal of Macroeconomics*, 24(4), 507-531. [doi:10.1016/S0164-0704(02)00062-9](https://doi.org/10.1016/S0164-0704%2802%2900062-9).
3. Croushore, D. (2011). Frontiers of real-time data analysis. *Journal of Economic Literature*, 49(1), 72-100. [doi:10.1257/jel.49.1.72](https://doi.org/10.1257/jel.49.1.72).
4. Clark, T. E., and McCracken, M. W. (2009). Tests of equal predictive ability with real-time data. *Journal of Business and Economic Statistics*, 27(4), 441-454. [doi:10.1198/jbes.2009.07204](https://doi.org/10.1198/jbes.2009.07204).
5. Reinhart, A., et al. (2021). An open repository of real-time COVID-19 indicators. *Proceedings of the National Academy of Sciences*, 118(51), e2111452118. [doi:10.1073/pnas.2111452118](https://doi.org/10.1073/pnas.2111452118).
6. Bracher, J., and Funk, S. (2026). Information leakage from data revisions in retrospective forecasts. arXiv:2608.05883. [arxiv.org/abs/2608.05883](https://arxiv.org/abs/2608.05883).
7. Aygün, E., et al. (2026). An AI system to help scientists write expert-level empirical software. *Nature*, 654, 909-916. [doi:10.1038/s41586-026-10658-6](https://doi.org/10.1038/s41586-026-10658-6).
8. Patton, A. J. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics*, 160(1), 246-256. [doi:10.1016/j.jeconom.2010.03.034](https://doi.org/10.1016/j.jeconom.2010.03.034).
9. Hoga, Y., and Dimitriadis, T. (2023). On testing equal conditional predictive ability under measurement error. *Journal of Business and Economic Statistics*, 41(2), 364-376. [doi:10.1080/07350015.2021.2021923](https://doi.org/10.1080/07350015.2021.2021923).
10. Kleen, O. (2024). Scaling and measurement error sensitivity of scoring rules for distribution forecasts. *Journal of Applied Econometrics*, 39(5), 833-849. [doi:10.1002/jae.3056](https://doi.org/10.1002/jae.3056).
11. Ferro, C. A. T. (2017). Measuring forecast performance in the presence of observation error. *Quarterly Journal of the Royal Meteorological Society*, 143(708), 2665-2676. [doi:10.1002/qj.3115](https://doi.org/10.1002/qj.3115).
12. Walsh, M., et al. (2014). The statistical significance of randomized controlled trial results is frequently fragile: a case for a Fragility Index. *Journal of Clinical Epidemiology*, 67(6), 622-628. [doi:10.1016/j.jclinepi.2013.10.019](https://doi.org/10.1016/j.jclinepi.2013.10.019).
13. Broderick, T., Giordano, R., and Meager, R. (2020). An automatic finite-sample robustness metric: when can dropping a little data make a big difference? arXiv:2011.14999. [arxiv.org/abs/2011.14999](https://arxiv.org/abs/2011.14999).
14. Triantaphyllou, E., and Sánchez, A. (1997). A sensitivity analysis approach for some deterministic multi-criteria decision-making methods. *Decision Sciences*, 28(1), 151-194. [doi:10.1111/j.1540-5915.1997.tb01306.x](https://doi.org/10.1111/j.1540-5915.1997.tb01306.x).
15. Wolters, W. T. M., and Mareschal, B. (1995). Novel types of sensitivity analysis for additive MCDM methods. *European Journal of Operational Research*, 81(2), 281-290. [doi:10.1016/0377-2217(93)E0343-V](https://doi.org/10.1016/0377-2217%2893%29E0343-V).
16. Hein, M., and Andriushchenko, M. (2017). Formal guarantees on the robustness of a classifier against adversarial manipulation. *Advances in Neural Information Processing Systems*, 30. [arxiv.org/abs/1705.08475](https://arxiv.org/abs/1705.08475).
17. Cramer, E. Y., et al. (2022). The United States COVID-19 Forecast Hub dataset. *Scientific Data*, 9, 462. [doi:10.1038/s41597-022-01517-w](https://doi.org/10.1038/s41597-022-01517-w). Archive: [reichlab/covid19-forecast-hub](https://github.com/reichlab/covid19-forecast-hub).
18. Garey, M. R., and Johnson, D. S. (1979). *Computers and Intractability: A Guide to the Theory of NP-Completeness*. W. H. Freeman, San Francisco.
19. Bracher, J., Ray, E. L., Gneiting, T., and Reich, N. G. (2021). Evaluating epidemic forecasts in an interval format. *PLOS Computational Biology*, 17(2), e1008618. [doi:10.1371/journal.pcbi.1008618](https://doi.org/10.1371/journal.pcbi.1008618).
20. Gneiting, T. (2011). Making and evaluating point forecasts. *Journal of the American Statistical Association*, 106(494), 746-762. [doi:10.1198/jasa.2011.r10138](https://doi.org/10.1198/jasa.2011.r10138).
21. W3C (2013). PROV-Overview: an overview of the PROV family of documents. W3C Working Group Note. [w3.org/TR/prov-overview](https://www.w3.org/TR/prov-overview/).
22. COVID-19 Forecast Hub. Historical daily truth producer and documentation at commit 52f10b79f02af0af7940a0a9a02314a563c04569. [Pinned truth directory](https://github.com/reichlab/covid19-forecast-hub/tree/52f10b79f02af0af7940a0a9a02314a563c04569/data-truth).
23. Dong, E., Du, H., and Gardner, L. (2020). An interactive web-based dashboard to track COVID-19 in real time. *The Lancet Infectious Diseases*, 20(5), 533-534. [doi:10.1016/S1473-3099(20)30120-1](https://doi.org/10.1016/S1473-3099%2820%2930120-1). Data: [JHU CSSE COVID-19 repository](https://github.com/CSSEGISandData/COVID-19).
24. Cramer, E. Y., et al. (2022). Evaluation of individual and ensemble probabilistic forecasts of COVID-19 mortality in the United States. *Proceedings of the National Academy of Sciences*, 119(15), e2113561119. [doi:10.1073/pnas.2113561119](https://doi.org/10.1073/pnas.2113561119).
25. Diebold, F. X., and Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business and Economic Statistics*, 13(3), 253-263. [doi:10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599).
26. Hansen, P. R., Lunde, A., and Nason, J. M. (2011). The model confidence set. *Econometrica*, 79(2), 453-497. [doi:10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771).
27. Bosse, N. I., et al. (2023). Scoring epidemiological forecasts on transformed scales. *PLOS Computational Biology*, 19(8), e1011393. [doi:10.1371/journal.pcbi.1011393](https://doi.org/10.1371/journal.pcbi.1011393).
