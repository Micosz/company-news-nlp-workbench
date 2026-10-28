"""Temporal feature contracts: fair ablation, source declaration and missingness."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pandas as pd

from algorithms.pair_experiment import run, time_categories
from engine import builtin, validate


class TemporalChecks(unittest.TestCase):
    def test_builtin_temporal_option_and_missing_setup(self):
        with TemporaryDirectory() as directory, patch('engine.ROOT', Path(directory)):
            with self.assertRaisesRegex(ValueError, 'setup_temporal_dataset'):
                builtin('story_time')
            target = Path(directory) / 'local_data' / 'ecb_story_time'
            target.mkdir(parents=True)
            pd.DataFrame([{'event_date_a':'2020-01-01', 'event_date_b':'2020-01-02'}]).to_csv(target / 'ecb_story_pairs.csv', index=False)
            loaded = builtin('story_time')
            self.assertEqual(loaded.iloc[0]['event_date_b'], '2020-01-02')

    def test_unknown_same_and_different_are_separate(self):
        frame = pd.DataFrame([
            {'event_date_a':'', 'event_date_b':'2020-01-01'},
            {'event_date_a':'2020-01-01', 'event_date_b':'2020-01-01'},
            {'event_date_a':'2020-01-01', 'event_date_b':'2020-02-02'},
        ])
        self.assertEqual(time_categories(frame).tolist(), [[0], [1], [2]])

    def test_date_validation_rejects_invalid_values(self):
        frame = builtin('small_A')
        frame['event_date_a'] = ''
        frame['event_date_b'] = ''
        validate(frame)
        for bad in ('2020-02-30', 'yesterday', '2020-1-1'):
            altered = frame.copy()
            altered.loc[0, 'event_date_a'] = bad
            with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
                validate(altered)

    def test_time_features_keep_the_same_baseline_and_require_provenance(self):
        data = validate(builtin('small_A'))
        data['event_date_a'] = '2020-01-01'
        data['event_date_b'] = '2020-01-01'
        data.loc[data.index[::2], 'event_date_b'] = '2020-01-02'
        train = data[data.split == 'train']
        test = data[data.split == 'test'].drop(columns=['label'])
        base = run(train, test, {'seed':374, 'role_source':'none', 'time_source':'none'})
        timed = run(train, test, {'seed':374, 'role_source':'none', 'time_source':'oracle'})
        self.assertNotIn('text_plus_time', base['models'])
        self.assertIn('text_plus_time', timed['models'])
        self.assertIn('time_only', timed['models'])
        self.assertEqual(base['models']['text_baseline']['scores'], timed['models']['text_baseline']['scores'])
        self.assertEqual(timed['time_coverage'], {'train_complete_pairs':253, 'test_complete_pairs':171})
        self.assertTrue(any('Oracle event dates' in msg for msg in timed['warnings']))


if __name__ == '__main__': unittest.main(verbosity=2)
