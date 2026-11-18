import unittest

from significance import (bootstrap_b3_f1, bootstrap_pair_f1, percentile,
                          permutation_b3_f1, permutation_pair_f1, permutation_test,
                          pooled_pair_f1, resample_topics)


def two_topic_rows():
    """Topic 1: OR is perfect, OR_TFIDF merges an extra mention.
    Topic 2: both systems agree."""
    rows = []
    for gold, old, new in [('a', 0, 0), ('a', 0, 0), ('b', 1, 0)]:
        rows.append({'topic': '1', 'gold_cluster': gold, 'OR': old, 'OR_TFIDF': new})
    for gold, old, new in [('c', 2, 2), ('c', 2, 2), ('d', 3, 3)]:
        rows.append({'topic': '2', 'gold_cluster': gold, 'OR': old, 'OR_TFIDF': new})
    return rows


class ResampleTest(unittest.TestCase):
    def test_same_seed_same_samples(self):
        topics = ['2', '5', '12', '35']
        self.assertEqual(list(resample_topics(topics, 20, seed=1)),
                         list(resample_topics(topics, 20, seed=1)))

    def test_order_of_input_does_not_matter(self):
        self.assertEqual(list(resample_topics(['35', '2', '12'], 5)),
                         list(resample_topics(['2', '12', '35'], 5)))

    def test_sample_size(self):
        for sample in resample_topics(['1', '2', '3'], 10):
            self.assertEqual(len(sample), 3)
            self.assertTrue(set(sample) <= {'1', '2', '3'})

    def test_no_topics(self):
        with self.assertRaises(ValueError):
            list(resample_topics([], 1))


class PercentileTest(unittest.TestCase):
    def test_ends_and_middle(self):
        values = [0, 10, 20, 30, 40]
        self.assertEqual(percentile(values, 0), 0)
        self.assertEqual(percentile(values, 100), 40)
        self.assertEqual(percentile(values, 50), 20)
        self.assertEqual(percentile(values, 25), 10)
        self.assertAlmostEqual(percentile(values, 10), 4)


class PairBootstrapTest(unittest.TestCase):
    def test_same_system_gives_zero(self):
        rows = two_topic_rows()
        result = bootstrap_pair_f1(rows, 'OR', 'OR', rounds=200)
        self.assertEqual((result['delta'], result['low'], result['high']), (0, 0, 0))

    def test_repeatable_with_seed(self):
        rows = two_topic_rows()
        self.assertEqual(bootstrap_pair_f1(rows, 'OR_TFIDF', rounds=200, seed=7),
                         bootstrap_pair_f1(rows, 'OR_TFIDF', rounds=200, seed=7))

    def test_worse_system_stays_below_zero(self):
        # OR_TFIDF only adds false links, so no sample can make it better.
        result = bootstrap_pair_f1(two_topic_rows(), 'OR_TFIDF', rounds=200)
        self.assertLess(result['delta'], 0)
        self.assertLessEqual(result['high'], 0)
        self.assertLessEqual(result['low'], result['delta'])


class B3BootstrapTest(unittest.TestCase):
    def test_same_system_gives_zero(self):
        result = bootstrap_b3_f1(two_topic_rows(), 'OR', 'OR', rounds=200)
        self.assertEqual((result['delta'], result['low'], result['high']), (0, 0, 0))

    def test_observed_gain_matches_direct_score(self):
        # Topic 1 for OR_TFIDF is the "all merged" case: B3 F1 = 5/7.
        # Topic 2 is perfect. Pooled over 6 mentions: P = (5/3 + 3) / 6, R = 1.
        result = bootstrap_b3_f1(two_topic_rows(), 'OR_TFIDF', rounds=50)
        p = (5 / 3 + 3) / 6
        self.assertAlmostEqual(result['delta'], 2 * p / (p + 1) - 1)
        self.assertLessEqual(result['high'], 0)


def same_mistake_everywhere(topics):
    """In every topic OR is perfect and OR_TFIDF merges one wrong mention."""
    rows = []
    for topic in topics:
        for gold, old, new in [('a', 0, 0), ('a', 0, 0), ('b', 1, 0)]:
            rows.append({'topic': topic, 'gold_cluster': topic + gold,
                         'OR': topic + str(old), 'OR_TFIDF': topic + str(new)})
    return rows


class PermutationTest(unittest.TestCase):
    def test_same_system_gives_p_one(self):
        rows = two_topic_rows()
        self.assertEqual(permutation_pair_f1(rows, 'OR', 'OR')['p'], 1.0)
        self.assertEqual(permutation_b3_f1(rows, 'OR', 'OR')['p'], 1.0)

    def test_tries_every_swap(self):
        self.assertEqual(permutation_pair_f1(two_topic_rows(), 'OR_TFIDF')['swaps'], 4)

    def test_worse_in_every_topic_gets_smallest_p(self):
        # Only "swap nothing" and "swap everything" are as extreme as the
        # real result, so p = 2 / 2**4.
        rows = same_mistake_everywhere(['1', '2', '3', '4'])
        for test in (permutation_pair_f1, permutation_b3_f1):
            result = test(rows, 'OR_TFIDF')
            self.assertLess(result['delta'], 0)
            self.assertAlmostEqual(result['p'], 2 / 16)

    def test_one_bad_topic_is_not_enough(self):
        # Same as above but three topics where both systems agree.
        rows = same_mistake_everywhere(['1']) + [
            row | {'OR_TFIDF': row['OR']} for row in same_mistake_everywhere(['2', '3', '4'])]
        self.assertGreaterEqual(permutation_pair_f1(rows, 'OR_TFIDF')['p'], 0.5)

    def test_too_many_topics(self):
        counts = {str(t): {'tp': 1, 'fp': 0, 'fn': 0} for t in range(21)}
        with self.assertRaises(ValueError):
            permutation_test(counts, counts, pooled_pair_f1)


if __name__ == '__main__':
    unittest.main()
