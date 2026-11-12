from fractions import Fraction
from itertools import product
import unittest

from exact import audit


def expected_family_radius(q):
    return None if q == 1 else 1 + q


class ExactAuditTests(unittest.TestCase):
    def test_proof_family_has_fixed_scores_and_expected_strict_statuses(self):
        a = (2, 0, 0)
        b = (0, 2, 0)
        for q in (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1)):
            with self.subTest(q=q):
                result = audit(a, b, (2 + q, 1, 3 - q), (-1, -1, -1), (1, 1, 1))
                self.assertEqual(result.initial_winner, "A")
                self.assertEqual(result.initial_mae_a, Fraction(4, 3))
                self.assertEqual(result.initial_mae_b, Fraction(2))
                self.assertEqual(result.tie.status, "attained")
                self.assertEqual(result.tie.radius, Fraction(1))
                if q == 1:
                    self.assertEqual(result.strict.status, "infeasible")
                    self.assertIsNone(result.strict.radius)
                else:
                    self.assertEqual(result.strict.status, "unattained_infimum")
                    self.assertEqual(result.strict.radius, expected_family_radius(q))

    def test_attained_strict_reversal_has_an_exact_witness(self):
        result = audit((0,), (2,), (0,), (2,), (2,))
        self.assertEqual(result.initial_winner, "A")
        self.assertEqual(result.strict.status, "attained")
        self.assertEqual(result.strict.radius, Fraction(2))
        self.assertEqual(result.strict.witness, (Fraction(2),))

    def test_swapped_initial_winner_is_normalized(self):
        result = audit((2,), (0,), (0,), (2,), (2,))
        self.assertEqual(result.initial_winner, "B")
        self.assertEqual(result.strict.status, "attained")
        self.assertEqual(result.strict.radius, Fraction(2))

    def test_initial_tie_has_no_selected_winner(self):
        result = audit((0,), (2,), (1,), (-1,), (1,))
        self.assertIsNone(result.initial_winner)
        self.assertEqual(result.strict.status, "initial_tie")
        self.assertEqual(result.tie.status, "attained")
        self.assertEqual(result.tie.radius, Fraction(0))

    def test_initial_tie_respects_a_box_that_excludes_zero_revision(self):
        result = audit((0,), (2,), (1,), (1,), (1,))
        self.assertIsNone(result.initial_winner)
        self.assertEqual(result.strict.status, "initial_tie")
        self.assertEqual(result.tie.status, "infeasible")
        self.assertIsNone(result.tie.radius)

    def test_initial_tie_finds_the_constrained_tie_radius(self):
        a, b, y = (0, 0), (2, 2), (0, 2)
        lower, upper = (1, -1), (1, -1)
        result = audit(a, b, y, lower, upper)
        self.assertIsNone(result.initial_winner)
        self.assertEqual(result.strict.status, "initial_tie")
        self.assertEqual(result.tie.status, "attained")
        self.assertEqual(result.tie.radius, Fraction(2))
        self._assert_tie_witness(result, a, b, y, lower, upper)

    def _assert_tie_witness(self, result, a, b, y, lower, upper):
        self.assertIsNotNone(result.tie.witness)
        witness = result.tie.witness
        self.assertEqual(sum(map(abs, witness), Fraction()), result.tie.radius)
        self.assertTrue(all(Fraction(low) <= delta <= Fraction(high) for delta, low, high in zip(witness, lower, upper)))
        self.assertTrue(all(Fraction(actual) + delta >= 0 for actual, delta in zip(y, witness)))
        total_a = sum(abs(Fraction(forecast) - Fraction(actual) - delta) for forecast, actual, delta in zip(a, y, witness))
        total_b = sum(abs(Fraction(forecast) - Fraction(actual) - delta) for forecast, actual, delta in zip(b, y, witness))
        self.assertEqual(total_a, total_b)

    def test_nonnegativity_clips_the_box_before_solving(self):
        result = audit((0,), (2,), (0,), (-2,), (2,))
        self.assertEqual(result.strict.status, "unattained_infimum")
        self.assertEqual(result.strict.radius, Fraction(1))
        self.assertIsNone(result.strict.witness)

    def test_degenerate_box_is_handled_exactly(self):
        result = audit((0,), (2,), (0,), (0,), (0,))
        self.assertEqual(result.strict.status, "infeasible")
        self.assertEqual(result.tie.status, "infeasible")

    def test_box_with_no_nonnegative_revised_value_is_infeasible(self):
        result = audit((0,), (2,), (0,), (-2,), (-1,))
        self.assertEqual(result.strict.status, "infeasible")
        self.assertEqual(result.tie.status, "infeasible")

    def test_invalid_inputs_return_invalid_input_not_a_fake_radius(self):
        cases = [
            ((0,), (1, 2), (0,), (-1,), (1,)),
            ((0, 0, 0, 0), (1, 1, 1, 1), (0, 0, 0, 0), (-1,) * 4, (1,) * 4),
            ((0,), (1,), (0,), (1,), (0,)),
            ((0,), (1,), (0,), (-1,), (1.0,)),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = audit(*args)
                self.assertEqual(result.strict.status, "invalid_input")
                self.assertIsNone(result.strict.radius)

    def test_missing_internal_enumeration_is_a_failure_not_infinity(self):
        import exact

        original = exact._cells
        exact._cells = lambda *_: None
        try:
            with self.assertRaises(exact.SolverFailure):
                audit((0,), (2,), (0,), (-2,), (2,))
        finally:
            exact._cells = original


if __name__ == "__main__":
    unittest.main()
