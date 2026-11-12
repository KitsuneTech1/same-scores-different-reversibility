"""Exact bounded sensitivity analysis for two fixed MAE forecast vectors.

This module enumerates piecewise-affine cells and is deliberately limited to
three records. It is a proof and conformance oracle, not a scalable optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Iterable, Sequence


MAX_DIMENSIONS = 3


class SolverFailure(RuntimeError):
    """Raised when cell enumeration cannot certify an expected result."""


@dataclass(frozen=True)
class Radius:
    status: str
    radius: Fraction | None
    witness: tuple[Fraction, ...] | None


@dataclass(frozen=True)
class Audit:
    initial_winner: str | None
    initial_mae_a: Fraction | None
    initial_mae_b: Fraction | None
    strict: Radius
    tie: Radius


def _fraction(value: object) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("inputs must be exact integers, fractions, or strings")
    if isinstance(value, (int, str, Fraction)):
        return Fraction(value)
    raise ValueError("inputs must be exact integers, fractions, or strings")


def _vector(values: Iterable[object]) -> tuple[Fraction, ...]:
    return tuple(_fraction(value) for value in values)


def _invalid() -> Audit:
    radius = Radius("invalid_input", None, None)
    return Audit(None, None, None, radius, radius)


def _loss(forecast: Sequence[Fraction], actual: Sequence[Fraction]) -> Fraction:
    return sum((abs(forecast_i - actual_i) for forecast_i, actual_i in zip(forecast, actual)), Fraction())


def _cells(
    breakpoints: Sequence[Sequence[Fraction]],
) -> Iterable[tuple[tuple[Fraction, Fraction], ...]]:
    intervals = []
    for points in breakpoints:
        unique = tuple(sorted(set(points)))
        intervals.append(((unique[0], unique[0]),) if len(unique) == 1 else tuple(zip(unique, unique[1:])))
    return product(*intervals)


def _corners(cell: Sequence[tuple[Fraction, Fraction]]) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(product(*(bounds if bounds[0] != bounds[1] else (bounds[0],) for bounds in cell)))


def _cell_candidates(
    cell: Sequence[tuple[Fraction, Fraction]],
    difference,
) -> tuple[tuple[Fraction, ...], ...]:
    corners = _corners(cell)
    candidates = set(corners)
    for index, left in enumerate(corners):
        for right in corners[index + 1 :]:
            changed = [position for position, (a, b) in enumerate(zip(left, right)) if a != b]
            if len(changed) != 1:
                continue
            left_value = difference(left)
            right_value = difference(right)
            if left_value == 0 or right_value == 0 or left_value == right_value:
                continue
            if (left_value < 0) == (right_value < 0):
                continue
            weight = -left_value / (right_value - left_value)
            candidates.add(tuple(a + weight * (b - a) for a, b in zip(left, right)))
    return tuple(candidates)


def _best(candidates):
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1]))


def audit(
    a: Iterable[object],
    b: Iterable[object],
    y: Iterable[object],
    lower: Iterable[object],
    upper: Iterable[object],
) -> Audit:
    """Return exact strict-reversal and tie radii for a bounded MAE ranking.

    Inputs are exact values. ``lower <= delta <= upper`` is combined with
    ``y + delta >= 0``. If B initially wins, the calculation is normalized so
    that the reported strict radius reverses B rather than assuming A wins.
    """

    try:
        a_values, b_values, y_values = _vector(a), _vector(b), _vector(y)
        lower_values, upper_values = _vector(lower), _vector(upper)
    except (TypeError, ValueError, ZeroDivisionError):
        return _invalid()

    dimension = len(a_values)
    if (
        dimension == 0
        or dimension > MAX_DIMENSIONS
        or any(len(values) != dimension for values in (b_values, y_values, lower_values, upper_values))
    ):
        return _invalid()

    if any(low > high for low, high in zip(lower_values, upper_values)):
        return _invalid()
    effective_lower = tuple(max(low, -actual) for low, actual in zip(lower_values, y_values))
    if any(low > high for low, high in zip(effective_lower, upper_values)):
        unavailable = Radius("infeasible", None, None)
        return Audit(None, None, None, unavailable, unavailable)

    total_a = _loss(a_values, y_values)
    total_b = _loss(b_values, y_values)
    mae_a = total_a / dimension
    mae_b = total_b / dimension
    initial_tie = total_a == total_b
    winner, loser, winner_name = (
        (a_values, b_values, None)
        if initial_tie
        else (a_values, b_values, "A")
        if total_a < total_b
        else (b_values, a_values, "B")
    )

    def difference(delta: Sequence[Fraction]) -> Fraction:
        revised = tuple(actual + change for actual, change in zip(y_values, delta))
        return _loss(loser, revised) - _loss(winner, revised)

    breakpoint_sets = [
        tuple(max(low, min(high, point)) for point in (-actual, forecast_a - actual, forecast_b - actual, Fraction(), low, high))
        for low, high, actual, forecast_a, forecast_b in zip(effective_lower, upper_values, y_values, a_values, b_values)
    ]
    cells = _cells(breakpoint_sets)
    if cells is None:
        raise SolverFailure("cell enumeration returned no cells")

    strict_candidates = []
    tie_candidates = []
    for cell in cells:
        corners = _corners(cell)
        candidates = _cell_candidates(cell, difference)
        if not initial_tie and min(difference(corner) for corner in corners) < 0:
            strict_candidates.extend((sum(map(abs, point), Fraction()), point, difference(point)) for point in candidates if difference(point) <= 0)
        tie_candidates.extend((sum(map(abs, point), Fraction()), point) for point in candidates if difference(point) == 0)

    strict_best = _best(strict_candidates)
    if initial_tie:
        strict = Radius("initial_tie", None, None)
    elif strict_best is None:
        strict = Radius("infeasible", None, None)
    else:
        radius = strict_best[0]
        attained = [candidate for candidate in strict_candidates if candidate[0] == radius and candidate[2] < 0]
        strict = Radius("attained", radius, _best(attained)[1]) if attained else Radius("unattained_infimum", radius, None)

    tie_best = _best(tie_candidates)
    tie = Radius("infeasible", None, None) if tie_best is None else Radius("attained", tie_best[0], tie_best[1])
    return Audit(winner_name, mae_a, mae_b, strict, tie)
