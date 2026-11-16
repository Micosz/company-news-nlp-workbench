import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from tfidf_nb import clustering, fit, gold_labels, normalize, pairs, predict


class TextNBTests(unittest.TestCase):
    def test_candidates_and_gold_are_topic_scoped(self):
        tasks = [
            dict(doc_id='a', topic='1', gold_cluster='9'),
            dict(doc_id='b', topic='1', gold_cluster='9'),
            dict(doc_id='c', topic='2', gold_cluster='9'),
            dict(doc_id='a', topic='1', gold_cluster='8'),
        ]
        edges = pairs(tasks)
        self.assertEqual(edges.tolist(), [[0, 1], [1, 3]])
        self.assertEqual(gold_labels(tasks, edges).tolist(), [1, 0])
        self.assertEqual(gold_labels(tasks, np.array([[0, 2]])).tolist(), [0])

    def test_empty_graph_keeps_singletons(self):
        pred = clustering(['one', 'two', 'three'], np.empty((0, 2), dtype=int))
        self.assertEqual(len({cluster for _, cluster in pred}), 3)

    def test_posteriors_match_existing_pair_workbench(self):
        path = Path(__file__).resolve().parents[1] / 'pair_workbench/algorithms/pair_experiment.py'
        spec = importlib.util.spec_from_file_location('pair_reference', path)
        source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source)
        texts = ['Auto company buys rival', 'Company buys smaller rival',
                 'Oil prices rise', 'Auto company buys rival in deal']
        edges = np.array([[0, 1], [0, 2], [1, 2], [0, 3]])
        y = np.array([1, 0, 0, 1])
        frame = pd.DataFrame({'text_a': [texts[i] for i, _ in edges],
                              'text_b': [texts[j] for _, j in edges], 'label': y})
        expected = source.run(frame, frame.drop(columns='label'), {})['models']['text_baseline']['scores']
        texts = [normalize(s) for s in texts]
        actual, _ = predict(fit(texts, edges, y), texts, edges)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)
