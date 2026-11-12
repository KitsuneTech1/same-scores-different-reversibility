import unittest
from fractions import Fraction
from analysis import compare, paired_changes, catalog_radius


class AnalysisTests(unittest.TestCase):
    def test_compare_retains_fixed_candidate_identity(self):
        result = compare({'A': [Fraction(0)], 'B': [Fraction(2)]}, [Fraction(2)])
        self.assertEqual(result['winner'], 'B')
        self.assertEqual(result['mae'], {'A': '2', 'B': '0'})

    def test_tie_is_not_win(self):
        self.assertIsNone(compare({'A': [Fraction(0)], 'B': [Fraction(2)]}, [Fraction(1)])['winner'])

    def test_missing_pair_not_zero_padded(self):
        records = [{'id': 'old', 'weeks': {'x': {'status': 'complete', 'value': '1'}, 'y': {'status': 'missing_days'}}}, {'id': 'new', 'weeks': {'x': {'status': 'complete', 'value': '2'}, 'y': {'status': 'complete', 'value': '3'}}}]
        self.assertEqual(paired_changes(records, ['x', 'y']), [])
        self.assertEqual(paired_changes(records, ['x'])[0]['delta'], ['1'])

    def test_catalog_tie_and_no_reversal_remain_distinct(self):
        forecasts = {'A': [Fraction(0)], 'B': [Fraction(2)]}
        result = catalog_radius(forecasts, [Fraction(0)], 'A', [[Fraction(0)], [Fraction(1)]])
        self.assertEqual(result['status'], 'no_reversal_in_catalog')
        self.assertEqual(result['ties'], 1)
        self.assertIsNone(result['radius'])

    def test_finite_reversal_minimum_is_attained(self):
        result = catalog_radius({'A': [Fraction(0)], 'B': [Fraction(2)]}, [Fraction(0)], 'A', [[Fraction(3)], [Fraction(2)]])
        self.assertEqual(result['radius'], '2')
        self.assertEqual(result['status'], 'attained_in_catalog')


if __name__ == '__main__':
    unittest.main()
