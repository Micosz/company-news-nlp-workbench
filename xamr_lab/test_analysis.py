import random
import tempfile
import unittest
from itertools import combinations
from pathlib import Path

from analysis import b3_f1, load_predictions, topic_b3, topic_pair_counts

SMALL_RUN = """mention_id,topic,gold_cluster,OR,OR_TFIDF
m1,1,a,0,0
m2,1,a,0,0
m3,1,b,1,0
m4,2,c,2,2
"""


def write(folder, text):
    path = Path(folder) / 'predictions.csv'
    path.write_text(text, encoding='utf-8')
    return path


class LoadPredictionsTest(unittest.TestCase):
    def test_reads_run_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, SMALL_RUN)
            rows, methods = load_predictions(folder)
        self.assertEqual(len(rows), 4)
        self.assertEqual(methods, ['OR', 'OR_TFIDF'])
        self.assertEqual(rows[2]['gold_cluster'], 'b')

    def test_skips_annotation_columns(self):
        text = 'mention_id,topic,doc_id,argT,gold_cluster,OR,OR_temporal\nm1,1,d1,2012,a,0,0\n'
        with tempfile.TemporaryDirectory() as folder:
            _, methods = load_predictions(write(folder, text))
        self.assertEqual(methods, ['OR', 'OR_temporal'])

    def test_missing_gold_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, 'mention_id,topic,OR\nm1,1,0\n')
            with self.assertRaisesRegex(ValueError, 'gold_cluster'):
                load_predictions(path)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, 'mention_id,topic,gold_cluster,OR\n')
            with self.assertRaisesRegex(ValueError, 'no rows'):
                load_predictions(path)


def toy(pairs, topic='1'):
    return [{'topic': topic, 'gold_cluster': g, 'OR': p} for g, p in pairs]


def slow_counts(rows):
    tp = fp = fn = 0
    for a, b in combinations(rows, 2):
        if a['topic'] != b['topic']:
            continue
        same_gold = a['gold_cluster'] == b['gold_cluster']
        same_pred = a['OR'] == b['OR']
        tp += same_gold and same_pred
        fp += same_pred and not same_gold
        fn += same_gold and not same_pred
    return tp, fp, fn


class TopicScoreTest(unittest.TestCase):
    def test_everything_merged(self):
        counts = topic_pair_counts(toy([('a', 0), ('a', 0), ('b', 0)]), 'OR')['1']
        self.assertEqual((counts['tp'], counts['fp'], counts['fn']), (1, 2, 0))

    def test_everything_split(self):
        counts = topic_pair_counts(toy([('a', 0), ('a', 1), ('b', 2)]), 'OR')['1']
        self.assertEqual((counts['tp'], counts['fp'], counts['fn']), (0, 0, 1))

    def test_cross_topic_pairs_ignored(self):
        rows = toy([('a', 0)], '1') + toy([('a', 0)], '2')
        counts = topic_pair_counts(rows, 'OR')
        self.assertEqual(counts['1']['fp'] + counts['2']['fp'], 0)

    def test_perfect_b3(self):
        rows = toy([('a', 0), ('a', 0), ('b', 1)])
        self.assertAlmostEqual(b3_f1(list(topic_b3(rows, 'OR').values())), 1.0)

    def test_merged_b3(self):
        rows = toy([('a', 0), ('a', 0), ('b', 0)])
        self.assertAlmostEqual(b3_f1(list(topic_b3(rows, 'OR').values())), 5 / 7)

    def test_matches_pair_by_pair_count(self):
        rng = random.Random(374)
        rows = [{'topic': rng.choice('12'), 'gold_cluster': rng.choice('abcd'), 'OR': rng.choice('wxyz')}
                for _ in range(40)]
        counts = topic_pair_counts(rows, 'OR').values()
        fast = tuple(sum(c[k] for c in counts) for k in ('tp', 'fp', 'fn'))
        self.assertEqual(fast, slow_counts(rows))


if __name__ == '__main__':
    unittest.main()
