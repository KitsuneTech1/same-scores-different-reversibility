import unittest
from fractions import Fraction
from audit import extract_median, weekly_values, source_identity


class ExtractionTests(unittest.TestCase):
    header = 'forecast_date,target,target_end_date,location,type,quantile,value\n'
    row = '2020-11-01,1 wk ahead inc death,2020-11-07,US,quantile,0.500,10.25\n'

    def test_median_is_exact(self):
        self.assertEqual(extract_median(self.header + self.row, '2020-11-01', '2020-11-07'), Fraction(41, 4))

    def test_missing_median_not_point_substitution(self):
        with self.assertRaisesRegex(ValueError, 'median count'):
            extract_median(self.header + self.row.replace('quantile,0.500', 'point,NA'), '2020-11-01', '2020-11-07')

    def test_lexical_duplicate(self):
        with self.assertRaisesRegex(ValueError, 'median count'):
            extract_median(self.header + self.row + self.row.replace('0.500', '0.5'), '2020-11-01', '2020-11-07')

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            extract_median(self.header + self.row.replace('10.25', '-1'), '2020-11-01', '2020-11-07')

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            extract_median(self.header + self.row.replace('10.25', 'NaN'), '2020-11-01', '2020-11-07')

    def test_week_requires_seven_days(self):
        text = 'date,location,location_name,value\n' + ''.join(f'2020-11-0{i},US,US,{i}\n' for i in range(1, 8))
        self.assertEqual(weekly_values(text, ['2020-11-07'])['2020-11-07'], {'status': 'complete', 'value': '28', 'days': 7})
        self.assertEqual(weekly_values(text.replace('2020-11-01,US,US,1\n', ''), ['2020-11-07'])['2020-11-07']['status'], 'missing_days')

    def test_duplicate_day_rejected(self):
        text = 'date,location,value\n2020-11-01,US,1\n2020-11-01,US,1\n'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            weekly_values(text, ['2020-11-07'])

    def test_out_of_scope_values_not_parsed(self):
        text = 'date,location,value\n2099-01-01,US,NaN\n2020-11-01,CA,garbage\n'
        self.assertEqual(weekly_values(text, ['2020-11-07'])['2020-11-07']['status'], 'missing_days')

    def test_git_blob_hash(self):
        self.assertEqual(source_identity(b'hello\n')['git_blob_sha1'], 'ce013625030ba8dba906f756967f9e9ca394464a')


if __name__ == '__main__':
    unittest.main()
