"""Read saved run predictions so methods can be compared after a run."""
import csv
from collections import Counter, defaultdict
from pathlib import Path

# Columns written next to the method columns in predictions.csv
# (engine.py keeps the annotation fields, research_runner.py keeps only the first three).
INFO_COLUMNS = {'mention_id', 'topic', 'gold_cluster', 'doc_id', 'sentence_id',
                'lemma', 'roleset_id', 'arg0', 'arg1', 'argL', 'argT'}
NEEDED = ('mention_id', 'topic', 'gold_cluster')


def load_predictions(path):
    """Return (rows, methods) from a run folder or a predictions.csv file."""
    path = Path(path)
    if path.is_dir():
        path = path / 'predictions.csv'
    with path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f'{path} has no rows')
    missing = [c for c in NEEDED if c not in rows[0]]
    if missing:
        raise ValueError(f'{path} is missing columns: {", ".join(missing)}')
    methods = [c for c in rows[0] if c not in INFO_COLUMNS]
    if not methods:
        raise ValueError(f'{path} has no method columns')
    return rows, methods


def links(sizes):
    """Number of mention pairs inside groups of the given sizes."""
    return sum(n * (n - 1) // 2 for n in sizes)


def topic_pair_counts(rows, method):
    """Pairwise TP/FP/FN for one method, counted inside each topic.

    Pairs that cross topics are left out, so the topic totals can be
    smaller than the FP count in metrics.csv when a method links topics.
    """
    by_topic = defaultdict(list)
    for row in rows:
        by_topic[row['topic']].append((row['gold_cluster'], row[method]))
    counts = {}
    for topic, pairs in by_topic.items():
        gold = links(Counter(g for g, _ in pairs).values())
        pred = links(Counter(p for _, p in pairs).values())
        tp = links(Counter(pairs).values())
        counts[topic] = {'tp': tp, 'fp': pred - tp, 'fn': gold - tp, 'mentions': len(pairs)}
    return counts


def topic_b3(rows, method):
    """B3 precision/recall sums per topic.

    Sums are kept instead of averages so topics can be added up later:
    B3 precision = sum of precision / number of mentions (same for recall).
    """
    by_topic = defaultdict(list)
    for row in rows:
        by_topic[row['topic']].append((row['gold_cluster'], row[method]))
    sums = {}
    for topic, pairs in by_topic.items():
        gold = Counter(g for g, _ in pairs)
        pred = Counter(p for _, p in pairs)
        both = Counter(pairs)
        sums[topic] = {
            'b3_p': sum(n * n / pred[p] for (_, p), n in both.items()),
            'b3_r': sum(n * n / gold[g] for (g, _), n in both.items()),
            'mentions': len(pairs),
        }
    return sums


def b3_f1(sums):
    """B3 F1 from a list of per-topic sums."""
    n = sum(s['mentions'] for s in sums)
    if not n:
        return 0.0
    p = sum(s['b3_p'] for s in sums) / n
    r = sum(s['b3_r'] for s in sums) / n
    return 2 * p * r / (p + r) if p + r else 0.0
