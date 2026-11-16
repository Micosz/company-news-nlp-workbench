import unittest
from unittest.mock import patch

import numpy as np
from scipy.sparse import csr_matrix

from or_nb_hybrid import cutoff, graph_data, retained
from tfidf_nb import GRAPH_FIELDS


class HybridTests(unittest.TestCase):
    def test_only_cross_document_time_only_edges_are_ranked(self):
        nested = csr_matrix([[0, 0, 1], [0, 0, 0], [1, 0, 0]])
        time = csr_matrix([[0, 1, 1], [1, 0, 1], [1, 1, 0]])
        rows = [{**dict.fromkeys(GRAPH_FIELDS, ''), 'doc_id': name, 'gold_cluster': 'hidden'}
                for name in ('a', 'a', 'b')]
        with patch('or_nb_hybrid.event_graphs', return_value=([], nested, time)) as build:
            edges, cross, weak = graph_data(rows)
        self.assertEqual(edges.tolist(), [[0, 1], [0, 2], [1, 2]])
        self.assertEqual(cross.tolist(), [False, True, True])
        self.assertEqual(weak.tolist(), [2])
        self.assertTrue(all('gold_cluster' not in row for row in build.call_args.args[0]))

    def test_noop_and_boundary_ties_preserve_edges(self):
        edges = np.array([[0, 1], [1, 2], [2, 3]])
        weak = np.array([0, 2])
        ranks = [(0.3, 0.1), (0.3, 0.2)]
        self.assertIsNone(cutoff(ranks, 0))
        self.assertEqual(cutoff(ranks * 2, 0.25), (0.3, 0.1))
        self.assertEqual(retained(edges, weak, ranks, None)[0].tolist(), [True, True, True])
        self.assertEqual(retained(edges, weak, ranks, (0.3, 0.2))[1].tolist(), [0])
