"""Categorical NB behavior tests. Synthetic examples are not research results."""
import unittest
import numpy as np
import pandas as pd

from algorithms.pair_experiment import role_categories, run
from engine import builtin, validate


class CategoricalNBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = validate(builtin('small_A'))
        cls.train = data[data.split == 'train'].copy()
        cls.test = data[data.split == 'test'].drop(columns=['label']).copy()

    def test_unknown_roles_are_distinct_from_disagreement_and_reversal(self):
        examples = pd.DataFrame([
            dict(buyer_a='Acme', target_a='Beta', buyer_b='acme', target_b=' beta '),
            dict(buyer_a='Acme', target_a='Beta', buyer_b='Acme', target_b='Gamma'),
            dict(buyer_a='Acme', target_a='', buyer_b='Acme', target_b='Gamma'),
            dict(buyer_a='Acme', target_a='Beta', buyer_b='Beta', target_b='Acme'),
            dict(buyer_a='Acme', target_a='Unknown', buyer_b='N/A', target_b='null'),
            dict(buyer_a='None', target_a='ไม่ทราบ', buyer_b='unknown', target_b='nan'),
        ])
        self.assertEqual(role_categories(examples).tolist(),
                         [[1, 1, 1], [1, 2, 1], [1, 0, 0], [2, 2, 2], [0, 0, 0], [0, 0, 0]])

    def test_role_ablation_keeps_identical_text_baseline_and_classifier(self):
        train, test = self.train.copy(), self.test.copy()
        # Artificial roles exercise software only and do not describe the news.
        for data in (train, test):
            data['buyer_a'] = data['buyer_b'] = 'Synthetic Buyer'
            data['target_a'] = data['target_b'] = 'Synthetic Target'
        text_only = run(train, test, {'seed': 374, 'role_source': 'none'})
        added = run(train, test, {'seed': 374, 'role_source': 'manual'})
        self.assertNotIn('text_plus_roles', text_only['models'])
        self.assertEqual(text_only['models']['text_baseline']['scores'],
                         added['models']['text_baseline']['scores'])
        self.assertEqual(text_only['vectorizer'], added['vectorizer'])
        for name in ('text_baseline', 'text_plus_roles'):
            model = added['models'][name]
            self.assertEqual(model['fitted_parameters']['classifier'], 'CategoricalNB')
            self.assertEqual(model['fitted_parameters']['alpha'], 1.0)
            self.assertEqual(model['threshold'], 0.5)
            self.assertEqual(len(model['scores']), len(test))
            self.assertTrue(np.isfinite(model['scores']).all())
        self.assertEqual(added['models']['text_baseline']['fitted_parameters']['class_count'],
                         added['models']['text_plus_roles']['fitted_parameters']['class_count'])
        self.assertTrue(any('Manual/oracle' in w for w in added['warnings']))

    def test_unseen_test_role_categories_are_handled_and_test_text_not_fitted(self):
        train, test = self.train.copy(), self.test.copy()
        for data in (train, test):
            data['buyer_a'] = data['buyer_b'] = 'Buyer'
            data['target_a'] = 'Target A'
            data['target_b'] = 'Target B'
        # Capture original training-derived bins before mutating held-out data.
        initial = run(train, test, {'seed': 374, 'role_source': 'manual'})
        # Test introduces match and unknown categories absent in training.
        test.loc[test.index[0], 'target_b'] = 'Target A'
        test.loc[test.index[1], 'target_b'] = ''
        test['text_a'] = test.text_a + ' heldoutuniquevalidationterm'
        result = run(train, test, {'seed': 374, 'role_source': 'manual'})
        self.assertIn('text_plus_roles', result['models'])
        self.assertTrue(np.isfinite(result['models']['text_plus_roles']['scores']).all())
        self.assertNotIn('heldoutuniquevalidationterm', result['vectorizer']['vocabulary'])
        self.assertEqual(initial['vectorizer']['cosine_bin_edges'], result['vectorizer']['cosine_bin_edges'])
        self.assertTrue(any('coverage is partial' in w for w in result['warnings']))

    def test_blank_real_roles_skip_ablation(self):
        result = run(self.train, self.test, {'seed': 374, 'role_source': 'manual'})
        self.assertNotIn('text_plus_roles', result['models'])
        self.assertEqual(result['role_coverage'], {'train_complete_pairs': 0, 'test_complete_pairs': 0})
        self.assertTrue(any('skipped' in w for w in result['warnings']))

    def test_tied_training_cosines_do_not_invent_distinct_bins(self):
        train = pd.DataFrame([{'text_a': 'alpha', 'text_b': 'beta', 'label': 0},
                              {'text_a': 'alpha', 'text_b': 'beta', 'label': 1}])
        test = pd.DataFrame([{'text_a': 'alpha', 'text_b': 'beta'}])
        result = run(train, test, {'seed': 374, 'role_source': 'none'})
        self.assertEqual(result['vectorizer']['cosine_bin_edges'], [0.0])
        self.assertTrue(any('fewer than three populated' in w for w in result['warnings']))
        self.assertTrue(np.isfinite(result['models']['text_baseline']['scores']).all())


if __name__ == '__main__':
    unittest.main(verbosity=2)
