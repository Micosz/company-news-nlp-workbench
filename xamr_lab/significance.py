"""Check whether a method's gain over the baseline holds across topics.

ECB+ dev has only a handful of topics, so mentions inside one topic are
not independent. Every test here treats the topic as the unit: a
bootstrap sample is a list of topics drawn with replacement.
"""
import random
from itertools import product

from analysis import b3_f1, pair_f1, topic_b3, topic_pair_counts

SEED = 374
MAX_EXACT_TOPICS = 20


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


def pooled_b3_f1(sums, topics):
    """B3 F1 after adding up the per-topic sums of the listed topics."""
    return b3_f1([sums[t] for t in topics])


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


def bootstrap_b3_f1(rows, method, baseline='OR', rounds=1000, seed=SEED):
    """Paired bootstrap of the B3 F1 gain of `method` over `baseline`."""
    return paired_bootstrap(topic_b3(rows, baseline), topic_b3(rows, method),
                            pooled_b3_f1, rounds, seed)


def permutation_test(base, new, score):
    """Two-sided p-value for score(new) - score(base) by swapping systems per topic.

    Under the null hypothesis the two systems are interchangeable inside
    each topic, so every way of swapping their outputs topic by topic is
    equally likely. With k topics there are 2**k ways, and all of them
    are scored (no sampling), so the p-value is exact for this data.
    The smallest possible p-value is 2 / 2**k: with 8 topics, 0.0078.
    """
    topics = sorted(base, key=lambda t: (len(t), t))
    if len(topics) > MAX_EXACT_TOPICS:
        raise ValueError(f'{len(topics)} topics is too many to try every swap')
    observed = score(new, topics) - score(base, topics)
    extreme = 0
    for swaps in product((False, True), repeat=len(topics)):
        a = {t: new[t] if swap else base[t] for t, swap in zip(topics, swaps)}
        b = {t: base[t] if swap else new[t] for t, swap in zip(topics, swaps)}
        if abs(score(b, topics) - score(a, topics)) >= abs(observed) - 1e-12:
            extreme += 1
    return {'delta': observed, 'p': extreme / 2 ** len(topics), 'swaps': 2 ** len(topics)}


def permutation_pair_f1(rows, method, baseline='OR'):
    return permutation_test(topic_pair_counts(rows, baseline),
                            topic_pair_counts(rows, method), pooled_pair_f1)


def permutation_b3_f1(rows, method, baseline='OR'):
    return permutation_test(topic_b3(rows, baseline), topic_b3(rows, method), pooled_b3_f1)


def significance_rows(rows, method, baseline='OR', rounds=1000, seed=SEED):
    """Bootstrap interval and permutation p-value for both metrics, one row each."""
    table = []
    for metric, boot, perm in [('pair_F1', bootstrap_pair_f1, permutation_pair_f1),
                               ('B3_F1', bootstrap_b3_f1, permutation_b3_f1)]:
        interval = boot(rows, method, baseline, rounds, seed)
        test = perm(rows, method, baseline)
        table.append({
            'method': method, 'baseline': baseline, 'metric': metric,
            'delta': round(interval['delta'] * 100, 2),
            'ci_low': round(interval['low'] * 100, 2),
            'ci_high': round(interval['high'] * 100, 2),
            'p_value': round(test['p'], 4),
            'topics': len({row['topic'] for row in rows}),
            'rounds': rounds, 'seed': seed,
        })
    return table
