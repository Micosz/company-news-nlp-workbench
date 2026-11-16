"""Train-select a conservative NB edge guard on X-AMR OR."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from uuid import uuid4

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import CategoricalNB

from engine import BASE, COMMIT, csv_text, event_graphs, load_dataset
from tfidf_nb import GRAPH_FIELDS, clustering, collisions, cosine, coverage, get_scores, gold_labels, normalize, pairs, scoped

FRACTIONS = (0, 0.10, 0.25)
QUANTILES = tuple(i / 10 for i in range(1, 10))


def graph_data(rows):
    _, nested, local_time = event_graphs([{key: row[key] for key in GRAPH_FIELDS} for row in rows])
    graph = (nested + local_time).tocoo()
    edges = np.asarray(sorted((i, j) for i, j in zip(graph.row, graph.col) if i < j), dtype=int).reshape(-1, 2)
    cross = np.asarray([rows[i]['doc_id'] != rows[j]['doc_id'] for i, j in edges], dtype=bool)
    weak = np.asarray([k for k, (i, j) in enumerate(edges) if cross[k] and not nested[i, j]], dtype=int)
    return edges, cross, weak


def fit(rows):
    edges = pairs(rows)
    texts = [normalize(row['text']) for row in rows]
    feature = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, max_features=30000, norm='l2')
    feature.fit(dict.fromkeys(texts[i] for i in np.unique(edges)))
    similarity = cosine(feature, texts, edges)
    bins = np.unique(np.quantile(similarity, QUANTILES))
    estimator = CategoricalNB(alpha=1.0, min_categories=10, class_prior=[0.5, 0.5])
    labels = gold_labels(rows, edges)
    estimator.fit(np.digitize(similarity, bins).reshape(-1, 1), labels)
    if estimator.classes_.tolist() != [0, 1]:
        raise ValueError('Training fold requires both classes')
    return (feature, bins, estimator), coverage(rows, edges, labels)


def rank(model, rows, edges):
    if not len(edges):
        return []
    feature, bins, estimator = model
    similarity = cosine(feature, [normalize(row['text']) for row in rows], edges)
    posterior = estimator.predict_proba(np.digitize(similarity, bins).reshape(-1, 1))[:, 1]
    return list(zip(map(float, posterior), map(float, similarity)))


def cutoff(ranking, fraction):
    if not fraction or not ranking:
        return None
    return sorted(ranking)[int(len(ranking) * fraction)]


def retained(edges, weak, ranking, boundary):
    removed = np.asarray([k for k, score in zip(weak, ranking)
                          if boundary is not None and score < boundary], dtype=int)
    keep = np.ones(len(edges), dtype=bool)
    keep[removed] = False
    return keep, removed


def make_config(rows):
    model, stats = fit(rows)
    edges, _, weak = graph_data(rows)
    candidates = rank(model, rows, edges[weak])
    boundaries = {f: cutoff(candidates, f) for f in FRACTIONS}
    feature, bins, nb = model
    details = {'fit': stats, 'fit_weak_edges': len(weak), 'vocabulary_size': len(feature.vocabulary_),
               'bin_edges': bins.tolist(), 'nb_class_prior': [0.5, 0.5],
               'nb_category_count': nb.category_count_[0].tolist(),
               'cutoffs': boundaries}
    return model, boundaries, details


def cv(train, out):
    details = []
    for fold, (a, b) in enumerate(GroupKFold(n_splits=5).split(train, groups=[r['topic'] for r in train]), 1):
        fit_rows, val = ([train[i] for i in ids] for ids in (a, b))
        model, limits, config = make_config(fit_rows)
        edges, _, weak = graph_data(val)
        scores = rank(model, val, edges[weak])
        ids = [r['mention_id'] for r in val]
        targets = scoped(val)
        folder = out / f'fold-{fold}'
        folder.mkdir()
        choices = {}
        for fraction in FRACTIONS:
            keep, removed = retained(edges, weak, scores, limits[fraction])
            prediction = clustering(ids, edges[keep])
            choices[fraction] = {**get_scores(targets, prediction, folder, f'guard_{fraction}'),
                                 'removed_edges': len(removed)}
        details.append({'fold': fold, 'fit_topics': sorted({r['topic'] for r in fit_rows}),
                        'validation_topics': sorted({r['topic'] for r in val}),
                        'validation_weak_edges': len(weak), 'config': config, 'metrics': choices})
    means = {f: float(np.mean([row['metrics'][f]['CoNLL_F1'] for row in details])) for f in FRACTIONS}
    return max(FRACTIONS, key=lambda f: (means[f], -f)), means, details


def run(annotator, root):
    train, train_sha = load_dataset(f'{annotator}-train')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid4().hex[:8]
    out = root / annotator / run_id
    out.mkdir(parents=True)
    start = perf_counter()
    chosen, means, folds = cv(train, out)
    model, limits, config = make_config(train)
    config = {**config, 'annotator': annotator, 'train_sha256': train_sha, 'upstream_commit': COMMIT,
              'checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip(),
              'source_sha256': {p: sha256((BASE / p).read_bytes()).hexdigest() for p in
                                ('or_nb_hybrid.py', 'tfidf_nb.py', 'engine.py', 'vendor/coreference.py', 'dataset_checksums.json')},
              'chosen_fraction': chosen, 'cv_mean_conll': means, 'seed': None, 'python': sys.version.split()[0],
              'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    (out / 'frozen_train_config.json').write_text(json.dumps(config, indent=2))
    (out / 'cv.json').write_text(json.dumps(folds, indent=2))
    train_time = perf_counter() - start
    dev, dev_sha = load_dataset(f'{annotator}-dev')
    for key in ('topic', 'doc_id', 'mention_id'):
        if {r[key] for r in train} & {r[key] for r in dev}:
            raise ValueError(f'Train/dev overlap in {key}')
    start = perf_counter()
    edges, cross, weak = graph_data(dev)
    ranking = rank(model, dev, edges[weak])
    keep, removed = retained(edges, weak, ranking, limits[chosen])
    ids = [r['mention_id'] for r in dev]
    groups = {method: clustering(ids, edges[selection]) for method, selection in
              [('OR', np.ones(len(edges), dtype=bool)), ('OR_cross', cross),
               ('OR_NB', keep), ('OR_NB_cross', keep & cross)]}
    infer_time = perf_counter() - start
    gold = scoped(dev)
    metrics = [get_scores(gold, pred, out, method) for method, pred in groups.items()]
    labels = {method: dict(pred) for method, pred in groups.items()}
    topics = []
    for topic in sorted({r['topic'] for r in dev}):
        rows = [r for r in gold if r['topic'] == topic]
        folder = out / f'topic-{topic}'
        folder.mkdir()
        for method, pred in labels.items():
            topics.append({'topic': topic, **get_scores(rows, [(r['mention_id'], pred[r['mention_id']])
                                                               for r in rows], folder, method)})
    removed_ids = set(removed)
    edge_rows = [{'a': ids[i], 'b': ids[j], 'topic': dev[i]['topic'], 'posterior_balanced': score[0],
                  'cosine': score[1], 'removed': k in removed_ids,
                  'gold_same': dev[i]['gold_cluster'] == dev[j]['gold_cluster']}
                 for k, score in zip(weak, ranking) for i, j in [edges[k]]]
    changes = []
    for i, j in combinations(range(len(dev)), 2):
        a, b = ids[i], ids[j]
        for first, second in (('OR', 'OR_NB'), ('OR_cross', 'OR_NB_cross')):
            if labels[first][a] == labels[first][b] and labels[second][a] != labels[second][b]:
                changes.append({'a': a, 'b': b, 'topic': dev[i]['topic'], 'comparison': second,
                                'gold_same': gold[i]['gold_cluster'] == gold[j]['gold_cluster']})
    for name, rows in [('metrics', metrics), ('topics', topics), ('ranked_edges', edge_rows), ('changed_pairs', changes),
                       ('predictions', [{'mention_id': r['mention_id'], 'topic': r['topic'],
                                         **{m: pred[r['mention_id']] for m, pred in labels.items()}} for r in dev])]:
        (out / f'{name}.csv').write_text(csv_text(rows))
    candidates = pairs(dev)
    (out / 'report.json').write_text(json.dumps({
        'run_id': run_id, 'dev_sha256': dev_sha, 'train_collisions': collisions(train), 'dev_collisions': collisions(dev),
        'dev_coverage': coverage(dev, candidates, gold_labels(dev, candidates)), 'dev_or_edges': len(edges),
        'dev_cross_edges': int(cross.sum()), 'dev_weak_edges': len(weak), 'dev_removed': len(removed),
        'changed_pairs': dict(Counter(f"{row['comparison']}:{row['gold_same']}" for row in changes)),
        'cv_and_fit_seconds': train_time, 'inference_seconds': infer_time,
    }, indent=2))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotator', choices=('ann1', 'ann2'), required=True)
    parser.add_argument('--output-root', type=Path, default=BASE / 'runs' / 'or-nb-hybrid')
    args = parser.parse_args()
    print(run(args.annotator, args.output_root))
