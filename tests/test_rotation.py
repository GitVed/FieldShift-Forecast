import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from backend.rotation import rank_rotations, SAMPLE_SUITABILITY, load_trial_yields, load_prices, _revenue


def by_name(rows):
    return {r['name']: r for r in rows}


class RotationTests(unittest.TestCase):
    def sample(self, suitability=None, **kwargs):
        return rank_rotations(SAMPLE_SUITABILITY if suitability is None else suitability,
                              scoring_policy='sample_diversity', **kwargs)

    def test_default_does_not_invent_evidence_based_rank(self):
        rows = rank_rotations(SAMPLE_SUITABILITY)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r['status'] == 'pending rules' and r['overall_percent'] is None
                            and r['rank'] is None for r in rows))

    def test_missing_crop_kept_visible(self):
        suit = copy.deepcopy(SAMPLE_SUITABILITY)
        suit['wheat']['percent'] = None
        rows = by_name(self.sample(suit))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows['corn-soy-wheat']['not_scored_crops'], ['wheat'])
        self.assertEqual(rows['corn-soy-wheat']['status'], 'not scored')
        self.assertIsNone(rows['corn-soy-wheat']['rank'])
        self.assertEqual(rows['corn-soy']['status'], 'scored')

    def test_aliases_and_repeated_year_weight(self):
        suit = {'maize': {'percent': 60, 'source': 'fixture'},
                'soy': {'percent': 90, 'source': 'fixture'},
                'wheat': {'percent': 30, 'source': 'fixture'}}
        rows = by_name(self.sample(suit))
        self.assertEqual(rows['soy-soy-wheat']['breakdown']['average_suitability'], 70)
        self.assertEqual(rows['corn-soy-wheat']['breakdown']['average_suitability'], 60)
        self.assertEqual(rows['corn-soy-wheat']['overall_percent'], 80)
        self.assertAlmostEqual(rows['soy-soy-wheat']['breakdown']['soil_penalty'], 10/3)

    def test_red_clover_is_not_extra_cash_year_or_unsupported_bonus(self):
        rows = by_name(self.sample())
        a, b = rows['corn-soy-wheat'], rows['corn-soy-wheat plus red clover']
        self.assertEqual(a['crops'], b['crops'])
        self.assertEqual(a['overall_percent'], b['overall_percent'])
        self.assertEqual(a['rank'], b['rank'])
        self.assertEqual(b['yield_bu_ac']['soybean'], 'UNVERIFIED')

    def test_zero_valid_and_scores_clamped(self):
        for percent in (0, 100):
            suit = {c: {'percent': percent, 'source': 'fixture'} for c in ['corn','soybean','wheat']}
            self.assertTrue(all(r['status'] == 'scored' and 0 <= r['overall_percent'] <= 100
                                for r in self.sample(suit)))

    def test_bad_inputs_rejected(self):
        for bad in (-1, 101, float('nan'), float('inf'), True, '88'):
            suit = copy.deepcopy(SAMPLE_SUITABILITY)
            suit['wheat']['percent'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.sample(suit)
        with self.assertRaises(ValueError):
            self.sample({'corn': {'percent': 10, 'source': 'x'},
                         'maize': {'percent': 20, 'source': 'x'}})
        with self.assertRaises(ValueError):
            self.sample({'corn': {'percent': 10}})
        with self.assertRaises(ValueError):
            self.sample(scenario='typo')

    def test_sample_policy_cannot_be_relabeled_real(self):
        suit = {c: {'percent': 50, 'source': 'cached test', 'label': 'CACHED'}
                for c in ['corn','soybean','wheat']}
        self.assertTrue(all(r['label'] == 'SAMPLE' for r in self.sample(suit, label='CACHED')))

    def test_trial_reference_not_uplifted_twice(self):
        row = by_name(self.sample())['corn-soy-wheat']
        self.assertEqual(row['yield_bu_ac']['soybean'], 64)
        # Corn 164 is derived in the CSV (169 minus the stated 5 bu/ac red clover effect).
        self.assertEqual(row['yield_bu_ac']['corn'], 164)
        self.assertEqual(row['yield_references']['corn']['verification'], 'DERIVED')
        self.assertEqual(row['yield_bu_ac']['wheat'], 'UNVERIFIED')
        self.assertEqual(row['breakdown']['rotation_multiplier'], 1)
        self.assertEqual(row['yield_references']['soybean']['label'], 'CACHED')

    def test_scenarios_do_not_fabricate_yield_changes(self):
        baseline = by_name(self.sample())
        for scenario in ['dry','2035_dry','2012_replay']:
            for row in self.sample(scenario=scenario):
                self.assertEqual(row['scenario'], scenario)
                self.assertEqual(row['yield_bu_ac'], baseline[row['name']]['yield_bu_ac'])

    def test_no_partial_rotation_revenue(self):
        row = by_name(self.sample())['corn-soy-wheat']
        self.assertIsInstance(row['revenue_per_ac'], str)
        self.assertEqual(row['revenue_detail']['missing_yields'], ['wheat'])  # wheat has no sourced yield

    def test_annual_revenue_counts_each_year(self):
        prices = {c: {'value': v, 'unit': 'CAD/bu', 'currency': 'CAD',
                       'period': '2026-09', 'source': 'https://example.com/test'}
                  for c,v in [('soybean', 10), ('wheat', 5)]}
        value, detail = _revenue(['soybean','soybean','wheat'], {'soybean': 50, 'wheat': 60}, prices)
        self.assertAlmostEqual(value, 433.33)
        self.assertEqual(detail['by_crop_year'], [500, 500, 300])
        self.assertEqual(_revenue(['wheat'], {'wheat':60}, {})[0], 'price not chosen')

    def test_actual_cached_price_and_reference_revenue(self):
        prices = load_prices()
        self.assertAlmostEqual(prices['soybean']['value'], 604.86 / 36.744)
        row = by_name(self.sample())['continuous soybean']
        self.assertEqual(row['revenue_per_ac'], round(41 * 604.86 / 36.744, 2))

    def test_csv_gate_rejects_unverified_and_conflicting_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trial.csv'
            fields = ['rotation','crop','value','unit','verification','source','period']
            row = dict(zip(fields, ['test','corn','999','bu/ac','UNVERIFIED','https://example.com','test']))
            with path.open('w', newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(row)
            self.assertEqual(load_trial_yields(path), {})
            row['verification'] = 'VERIFIED'
            with path.open('w', newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([row,row])
            with self.assertRaises(ValueError):
                load_trial_yields(path)

    def test_json_and_contract(self):
        required = {'name','crops','status','not_scored_crops','overall_percent','breakdown',
                    'yield_bu_ac','revenue_per_ac','label'}
        rows = self.sample()
        json.dumps(rows, allow_nan=False)
        self.assertTrue(all(required <= row.keys() for row in rows))
        scores = [r['overall_percent'] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == '__main__':
    unittest.main()
