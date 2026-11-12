# Exact study tables

Fractions preserve the submitted decimal values exactly. Counts and costs are not rounded.

## Selected rows

| Target week | CU median | BPagano median | Decision reference | Later reference | Later change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020-11-07 | 6882 | 318831841/50000 | 6964 | 6973 | 9 |
| 2020-11-14 | 8747 | 775599537/100000 | 7611 | 7609 | -2 |
| 2020-11-21 | 8708 | 45636297/5000 | 10264 | 10299 | 35 |
| 2020-11-28 | 10443 | 38902143/3125 | 10130 | 10127 | -3 |
| 2020-12-05 | 10808 | 42599742/3125 | 15052 | 15050 | -2 |
| 2020-12-12 | 12537 | 339348879/20000 | 16682 | 16679 | -3 |
| 2020-12-19 | 17666 | 403510553/20000 | 18255 | 18225 | -30 |
| 2020-12-26 | 18922 | 1002835023/50000 | 15750 | 15693 | -57 |

## Calibration completeness

| Reference identity | Complete weeks |
| --- | ---: |
| truth-885931af4e0c | 3 |
| truth-5f052abd160a | 5 |
| truth-eefbf0e79039 | 6 |
| truth-e4a9fe27c3c7 | 7 |
| truth-ae770bdd7b5d | 8 |
| truth-80bf182e77a1 | 8 |

## Exact scores

| Window | Vintage | CU MAE | BPagano MAE | Gap |
| --- | --- | ---: | ---: | ---: |
| common_support | initial | 2774/3 | 12460661/20000 | 18098017/60000 |
| common_support | later | 940 | 38301983/60000 | 18098017/60000 |
| primary | initial | 15237/8 | 1212053953/800000 | 311646047/800000 |
| primary | later | 3827/2 | 1225753953/800000 | 305046047/800000 |

## Revision scenarios and coverage

### common_support

Initial gap-cost bound: 18098017/40000.
Complete adjacent pairs: 5. Unique scenarios: 3.
Later L1 cost: 46. Later vector belongs to catalog: False.

| Scenario | L1 cost | Status |
| --- | ---: | --- |
| (0, 0, 0) | 0 | same_winner |
| (9, 29, -19) | 57 | same_winner |
| (65, 4, 13) | 82 | same_winner |

Box widths: (Fraction(65, 1), Fraction(29, 1), Fraction(19, 1)). Maximum L1: 113.
Later vector belongs to box: False.
Strict status: infeasible. Tie status: infeasible.

### primary

Initial gap-cost bound: 311646047/200000.
Complete adjacent pairs: 1. Unique scenarios: 1.
Later L1 cost: 141. Later vector belongs to catalog: False.

| Scenario | L1 cost | Status |
| --- | ---: | --- |
| (0, 0, 0, 0, 0, 0, 0, 0) | 0 | same_winner |

