"""Meaningful checks for complete-candidate clustering and B³ accounting."""
import contextlib
import io
import itertools
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine import builtin, validate
from worker import evaluate_clusters, main, prepare_pilot_clustering


class ClusteringChecks(unittest.TestCase):
    def test_exact_overmerged_and_singletons(self):
        gold = {'a': 'left', 'b': 'left', 'c': 'right', 'd': 'right'}
        pairs = list(itertools.combinations(gold, 2))
        exact, labels = evaluate_clusters(gold, pairs, [int(gold[a] == gold[b]) for a, b in pairs])
        self.assertEqual(exact['b3_precision'], 1.0)
        self.assertEqual(exact['b3_recall'], 1.0)
        self.assertEqual(exact['b3_f1'], 1.0)
        self.assertEqual(exact['predicted_clusters'], 2)
        self.assertEqual(labels['a'], labels['b'])
        self.assertNotEqual(labels['a'], labels['c'])

        merged, _ = evaluate_clusters(gold, pairs, [1] * len(pairs))
        self.assertEqual(merged['b3_precision'], 0.5)
        self.assertEqual(merged['b3_recall'], 1.0)
        self.assertAlmostEqual(merged['b3_f1'], 2 / 3)
        singletons, _ = evaluate_clusters(gold, pairs, [0] * len(pairs))
        self.assertEqual(singletons['b3_precision'], 1.0)
        self.assertEqual(singletons['b3_recall'], 0.5)
        self.assertAlmostEqual(singletons['b3_f1'], 2 / 3)

    def test_positive_edges_are_transitive_and_singletons_are_kept(self):
        gold = {'a': 'x', 'b': 'x', 'c': 'y', 'd': 'z'}
        scores, groups = evaluate_clusters(gold, [('a', 'b'), ('b', 'c')], [1, 1])
        self.assertEqual(groups['a'], groups['c'])
        self.assertNotEqual(groups['a'], groups['d'])
        self.assertEqual(scores['predicted_clusters'], 2)

    def test_real_pilot_folds_have_complete_independent_reference(self):
        for mode, topic, count in [('small_A', '44', 19), ('small_B', '43', 23)]:
            with self.subTest(mode=mode):
                frame = validate(builtin(mode))
                test = frame[frame.split == 'test'].copy()
                reference, error = prepare_pilot_clustering(test)
                self.assertIsNone(error)
                self.assertEqual(reference['topic'], topic)
                self.assertEqual(len(reference['gold']), count)
                self.assertEqual(len(test), count * (count - 1) // 2)
                # Perfect predictions use only labels in this software test.
                scores, _ = evaluate_clusters(reference['gold'], list(zip(test.mention_a, test.mention_b)), test.label)
                self.assertAlmostEqual(scores['b3_f1'], 1.0)

    def test_sampled_missing_or_changed_pair_is_not_scored_as_negative(self):
        frame = validate(builtin('small_A'))
        test = frame[frame.split == 'test'].copy()
        for changed in (test.iloc[:-1], test.assign(mention_a='made_up')):
            ref, error = prepare_pilot_clustering(changed)
            self.assertIsNone(ref)
            self.assertIn('Clustering skipped', error)
        changed = test.copy()
        changed.iloc[0, changed.columns.get_loc('label')] = 1 - changed.iloc[0]['label']
        ref, error = prepare_pilot_clustering(changed)
        self.assertIsNone(ref)
        self.assertIn('labels disagree', error)

    def test_unsupported_data_and_invalid_predictions_are_not_silently_accepted(self):
        frame = validate(builtin('small_A'))
        test = frame[frame.split == 'test'].copy()
        ref, error = prepare_pilot_clustering(test.drop(columns=['mention_a', 'mention_b']))
        self.assertIsNone(ref)
        self.assertIn('lack original mention IDs', error)
        ref, error = prepare_pilot_clustering(test.assign(group_id='99'))
        self.assertIsNone(ref)
        self.assertIn('not Full or sampled', error)
        with self.assertRaises(ValueError):
            evaluate_clusters({'a': 'x', 'b': 'y'}, [('a', 'missing')], np.array([1]))

    def test_run_exports_verifiable_clusters_without_passing_gold_to_model(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            builtin('small_A').to_csv(folder / 'dataset.csv', index=False)
            (folder / 'manifest.json').write_text(json.dumps({'run_id': 'cluster_test',
                'source': 'small_A', 'status': 'running', 'limitations': []}))
            (folder / 'config.json').write_text('{}')
            (folder / 'algorithm.py').write_text('''def run(train, test, config):
    assert "label" not in test.columns
    assert "mention_a" not in test.columns and "mention_b" not in test.columns
    return {"models": {"my_baseline": {"scores": [1.0] * len(test), "features": []}}}
''')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main(folder)
            self.assertEqual(status, 0)
            metrics = json.loads((folder / 'metrics.json').read_text())
            clusters = metrics['clustering']
            self.assertEqual(clusters['status'], 'available')
            self.assertEqual(clusters['test_mentions'], 19)
            self.assertEqual(clusters['models']['my_baseline']['predicted_clusters'], 1)
            self.assertTrue((folder / 'clustering_reference.json').exists())
            self.assertTrue((folder / 'cluster_predictions.csv').exists())
            self.assertIn('B³', (folder / 'report.md').read_text())


if __name__ == '__main__':
    unittest.main()
