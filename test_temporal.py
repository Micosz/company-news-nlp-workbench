"""Temporal feature contracts: fair ablation, source declaration and missingness."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pandas as pd

from algorithms.pair_experiment import run, time_categories
from engine import builtin, summary, validate, prepare_run
from worker import choose_dev_threshold


class TemporalChecks(unittest.TestCase):
    def test_unavailable_role_or_time_cannot_be_recorded_as_supplied(self):
        frame = builtin('small_A')
        for config in ({'role_source':'manual'}, {'role_source':'predicted'},
                       {'role_source':'none','time_source':'oracle'},
                       {'role_source':'none','time_source':'predicted'}):
            with self.assertRaisesRegex(ValueError, 'ไม่มีคู่ที่ข้อมูลครบ'):
                prepare_run(frame, '', config, 'small_A')

    def test_dev_threshold_requires_both_classes_and_does_not_use_test(self):
        frame = builtin('small_A')
        with self.assertRaisesRegex(ValueError, 'ต้องมีข้อมูล dev'):
            prepare_run(frame, '', {'role_source':'none','threshold_mode':'dev_f1'}, 'small_A')
        threshold, score = choose_dev_threshold([0, 0, 1, 1], [0.1, 0.3, 0.4, 0.8])
        self.assertEqual(threshold, 0.4)
        self.assertEqual(score, 1.0)
    def test_coverage_distinguishes_complete_partial_and_missing(self):
        frame = pd.DataFrame([
            {'event_date_a':'2020-01-01','event_date_b':'2020-01-02'},
            {'event_date_a':'2020-01-01','event_date_b':''},
            {'event_date_a':'','event_date_b':'2020-01-02'},
            {'event_date_a':'','event_date_b':''},
        ])
        self.assertEqual(summary(frame)['time_coverage'], {'both':1,'one':2,'neither':1})
        self.assertEqual(time_categories(frame).tolist(), [[2],[0],[0],[0]])

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
        self.assertIn('text_plus_availability', timed['models'])
        self.assertEqual(base['models']['text_baseline']['scores'], timed['models']['text_baseline']['scores'])
        self.assertEqual(timed['time_coverage'], {'train_complete_pairs':253, 'test_complete_pairs':171})
        self.assertTrue(any('Oracle event dates' in msg for msg in timed['warnings']))


if __name__ == '__main__': unittest.main(verbosity=2)
