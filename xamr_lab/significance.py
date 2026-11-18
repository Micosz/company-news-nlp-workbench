"""Check whether a method's gain over the baseline holds across topics.

ECB+ dev has only a handful of topics, so mentions inside one topic are
not independent. Every test here treats the topic as the unit: a
bootstrap sample is a list of topics drawn with replacement.
"""
import random

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
