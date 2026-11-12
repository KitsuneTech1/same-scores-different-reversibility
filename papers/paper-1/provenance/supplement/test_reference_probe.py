"""Deterministic differential probe for the exact MAE audit oracle.

This is bounded testing, not a proof. It samples 6,000 cases from a fixed
rational value pool in dimensions one through three. The reference solver is
independently written and parameterizes each cell edge by axis, while the
implementation under test compares corner pairs. Both solvers still rely on
the same piecewise-affine MAE argument, so a shared conceptual error could go
undetected. Malformed input shapes are covered by ``test_exact.py`` instead.
No study data or fixture files are read.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from random import Random
import unittest

from exact import audit


SEED = 7_600_908
CASE_COUNT = 6_000
VALUE_POOL = (
    Fraction(-2),
    Fraction(-1),
    Fraction(-1, 2),
    Fraction(0),
    Fraction(1, 2),
    Fraction(1),
    Fraction(2),
    Fraction(3),
)


@dataclass(frozen=True)
class ReferenceResult:
    initial_winner: str | None
    initial_mae_a: Fraction | None
    initial_mae_b: Fraction | None
    strict_status: str
    strict_radius: Fraction | None
    tie_status: str
    tie_radius: Fraction | None


def reference_loss(forecast, actual):
    return sum((abs(prediction - observation) for prediction, observation in zip(forecast, actual)), Fraction())


def reference_cells(a, b, y, lower, upper):
    per_axis = []
    for forecast_a, forecast_b, actual, low, high in zip(a, b, y, lower, upper):
        boundaries = {low, high}
        for point in (Fraction(), forecast_a - actual, forecast_b - actual):
            if low <= point <= high:
                boundaries.add(point)
        ordered = sorted(boundaries)
        intervals = [(ordered[0], ordered[0])] if len(ordered) == 1 else list(zip(ordered, ordered[1:]))
        per_axis.append(intervals)
    return product(*per_axis)


def cell_corners(cell):
    endpoints = [(low,) if low == high else (low, high) for low, high in cell]
    return tuple(product(*endpoints))


def edge_candidates(cell, difference):
    """Find zero crossings by parameterizing each axis-aligned edge."""

    candidates = set(cell_corners(cell))
    dimension = len(cell)
    for axis, (low, high) in enumerate(cell):
        if low == high:
            continue
        other_axes = [position for position in range(dimension) if position != axis]
        fixed_endpoints = [
            (cell[position][0],)
            if cell[position][0] == cell[position][1]
            else cell[position]
            for position in other_axes
        ]
        for fixed_values in product(*fixed_endpoints):
            left = [Fraction() for _ in range(dimension)]
            right = [Fraction() for _ in range(dimension)]
            for position, value in zip(other_axes, fixed_values):
                left[position] = value
                right[position] = value
            left[axis] = low
            right[axis] = high
            left_point = tuple(left)
            right_point = tuple(right)
            left_value = difference(left_point)
            right_value = difference(right_point)
            if left_value * right_value < 0:
                weight = -left_value / (right_value - left_value)
                candidates.add(
                    tuple(
                        left_value_at_axis + weight * (right_value_at_axis - left_value_at_axis)
                        for left_value_at_axis, right_value_at_axis in zip(left_point, right_point)
                    )
                )
    return candidates


def reference_audit(a, b, y, lower, upper):
    dimension = len(a)
    effective_lower = tuple(max(low, -actual) for low, actual in zip(lower, y))
    if any(low > high for low, high in zip(effective_lower, upper)):
        return ReferenceResult(None, None, None, "infeasible", None, "infeasible", None)

    total_a = reference_loss(a, y)
    total_b = reference_loss(b, y)
    initial_tie = total_a == total_b
    if initial_tie:
        winner = a
        loser = b
        winner_name = None
    elif total_a < total_b:
        winner = a
        loser = b
        winner_name = "A"
    else:
        winner = b
        loser = a
        winner_name = "B"

    def difference(delta):
        revised = tuple(actual + change for actual, change in zip(y, delta))
        return reference_loss(loser, revised) - reference_loss(winner, revised)

    strict_candidates = []
    tie_candidates = []
    for cell in reference_cells(a, b, y, effective_lower, upper):
        corners = cell_corners(cell)
        candidates = edge_candidates(cell, difference)
        cell_has_strict_point = not initial_tie and min(map(difference, corners)) < 0
        for point in candidates:
            difference_at_point = difference(point)
            radius = sum(map(abs, point), Fraction())
            if difference_at_point == 0:
                tie_candidates.append((radius, point))
            if cell_has_strict_point and difference_at_point <= 0:
                strict_candidates.append((radius, point, difference_at_point))

    if initial_tie:
        strict_status, strict_radius = "initial_tie", None
    elif not strict_candidates:
        strict_status, strict_radius = "infeasible", None
    else:
        strict_radius = min(candidate[0] for candidate in strict_candidates)
        strict_status = (
            "attained"
            if any(candidate[0] == strict_radius and candidate[2] < 0 for candidate in strict_candidates)
            else "unattained_infimum"
        )

    if tie_candidates:
        tie_status, tie_radius = "attained", min(tie_candidates)[0]
    else:
        tie_status, tie_radius = "infeasible", None

    return ReferenceResult(
        winner_name,
        total_a / dimension,
        total_b / dimension,
        strict_status,
        strict_radius,
        tie_status,
        tie_radius,
    )


class ReferenceDifferentialProbeTests(unittest.TestCase):
    def test_seeded_cases_match_independent_reference(self):
        random = Random(SEED)
        for case_index in range(CASE_COUNT):
            dimension = random.randrange(1, 4)
            a = tuple(random.choice(VALUE_POOL) for _ in range(dimension))
            b = tuple(random.choice(VALUE_POOL) for _ in range(dimension))
            y = tuple(random.choice(VALUE_POOL) for _ in range(dimension))
            bounds = [sorted((random.choice(VALUE_POOL), random.choice(VALUE_POOL))) for _ in range(dimension)]
            lower = tuple(bound[0] for bound in bounds)
            upper = tuple(bound[1] for bound in bounds)

            expected = reference_audit(a, b, y, lower, upper)
            observed = audit(a, b, y, lower, upper)
            message = f"seed={SEED}, case={case_index}, inputs={(a, b, y, lower, upper)}"
            self.assertEqual(
                (
                    observed.initial_winner,
                    observed.initial_mae_a,
                    observed.initial_mae_b,
                    observed.strict.status,
                    observed.strict.radius,
                    observed.tie.status,
                    observed.tie.radius,
                ),
                (
                    expected.initial_winner,
                    expected.initial_mae_a,
                    expected.initial_mae_b,
                    expected.strict_status,
                    expected.strict_radius,
                    expected.tie_status,
                    expected.tie_radius,
                ),
                message,
            )
            self._assert_witnesses(observed, a, b, y, lower, upper, message)

    def _assert_witnesses(self, result, a, b, y, lower, upper, message):
        effective_lower = tuple(max(low, -actual) for low, actual in zip(lower, y))
        if result.tie.status == "attained":
            self._assert_feasible_radius(result.tie, effective_lower, upper, message)
            revised = tuple(actual + change for actual, change in zip(y, result.tie.witness))
            self.assertEqual(reference_loss(a, revised), reference_loss(b, revised), message)
        else:
            self.assertIsNone(result.tie.witness, message)

        if result.strict.status == "attained":
            self._assert_feasible_radius(result.strict, effective_lower, upper, message)
            revised = tuple(actual + change for actual, change in zip(y, result.strict.witness))
            losses = {"A": reference_loss(a, revised), "B": reference_loss(b, revised)}
            loser_name = "B" if result.initial_winner == "A" else "A"
            self.assertLess(losses[loser_name], losses[result.initial_winner], message)
        else:
            self.assertIsNone(result.strict.witness, message)

    def _assert_feasible_radius(self, radius, lower, upper, message):
        self.assertIsNotNone(radius.witness, message)
        self.assertEqual(sum(map(abs, radius.witness), Fraction()), radius.radius, message)
        self.assertTrue(
            all(low <= value <= high for value, low, high in zip(radius.witness, lower, upper)),
            message,
        )


if __name__ == "__main__":
    unittest.main()
