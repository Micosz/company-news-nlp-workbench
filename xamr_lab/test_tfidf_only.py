import unittest

import numpy as np

from tfidf_only import edits, mutual_edges


class CosineOnlyTests(unittest.TestCase):
    def test_mutual_best_and_no_ambiguous_ties(self):
        self.assertEqual(mutual_edges([(0, 1, 0.9, 0, 1), (1, 2, 0.8, 1, 2)]), [(0, 1)])
        self.assertEqual(mutual_edges([(0, 1, 0.9, 0, 1), (1, 2, 0.9, 1, 2)]), [])

    def test_cut_protects_strong_edges_and_add_requires_same_role(self):
        rows = [dict(roleset_id='buy.01', arg0='Acme', arg1='One'),
                dict(roleset_id='buy.01', arg0='Acme', arg1='Two'),
                dict(roleset_id='sell.01', arg0='Acme', arg1='Two')]
        args = (rows, ['0', '1', '2'])
        pairs = np.array([(0, 1), (0, 2), (1, 2)])
        kept, _, cut = edits(*args, [(0, 1), (1, 2)], [(1, 2)], pairs,
                             np.array([0.02, 0.1, 0.01]), 'cut_0.05')
        self.assertEqual(kept, [(0, 1)])
        self.assertEqual(cut, [(1, 2)])
        _, added, _ = edits(*args, [], [], pairs, np.array([0.7, 0.95, 0.95]), 'add_0.50')
        self.assertEqual(added, [(0, 1)])
