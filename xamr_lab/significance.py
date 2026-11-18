"""Check whether a method's gain over the baseline holds across topics.

ECB+ dev has only a handful of topics, so mentions inside one topic are
not independent. Every test here treats the topic as the unit: a
bootstrap sample is a list of topics drawn with replacement.
"""
import random

from analysis import pair_f1, topic_pair_counts

SEED = 374


def resample_topics(topics, rounds, seed=SEED):
    """Yield `rounds` bootstrap samples of the given topics.

    Each sample has the same length as `topics` and may repeat a topic.
    The same seed always gives the same samples, so reported intervals
    can be reproduced.
    """
    topics = sorted(topics, key=lambda t: (len(t), t))
    if not topics:
        raise ValueError('need at least one topic to resample')
    rng = random.Random(seed)
    for _ in range(rounds):
        yield rng.choices(topics, k=len(topics))


def percentile(values, q):
    """q-th percentile (0-100) of sorted values, linear between ranks."""
    pos = (len(values) - 1) * q / 100
    low = int(pos)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (pos - low)


def pooled_pair_f1(counts, topics):
    """Pair F1 after adding up TP/FP/FN of the listed topics (repeats count again)."""
    tp = sum(counts[t]['tp'] for t in topics)
    fp = sum(counts[t]['fp'] for t in topics)
    fn = sum(counts[t]['fn'] for t in topics)
    return pair_f1(tp, fp, fn)


def paired_bootstrap(base, new, score, rounds=1000, seed=SEED):
    """95% interval for score(new) - score(base) over resampled topics.

    Both systems are scored on the same sample in every round, which is
    what makes the test paired.
    """
    topics = list(base)
    observed = score(new, topics) - score(base, topics)
    deltas = sorted(score(new, sample) - score(base, sample)
                    for sample in resample_topics(topics, rounds, seed))
    return {
        'delta': observed,
        'low': percentile(deltas, 2.5),
        'high': percentile(deltas, 97.5),
        'rounds': rounds,
    }


def bootstrap_pair_f1(rows, method, baseline='OR', rounds=1000, seed=SEED):
    """Paired bootstrap of the Pair F1 gain of `method` over `baseline`."""
    return paired_bootstrap(topic_pair_counts(rows, baseline),
                            topic_pair_counts(rows, method),
                            pooled_pair_f1, rounds, seed)
