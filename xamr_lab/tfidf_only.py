"""Evaluate cosine-only event clustering and bounded edits to X-AMR OR."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import subprocess
from time import perf_counter
from uuid import uuid4

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupKFold

from argument_audit import arguments
from engine import BASE, COMMIT, csv_text, load_dataset
from or_nb_hybrid import graph_data
from tfidf_nb import clustering, collisions, cosine, coverage, get_scores, gold_labels, normalize, pairs, scoped

TEXT = (0.15, 0.30, 0.50, 0.70)
HYBRID = {'no_op': ('keep', 0), 'cut_0.05': ('cut', 0.05), 'cut_0.10': ('cut', 0.10),
          'add_0.70': ('add', 0.70), 'add_0.50': ('add', 0.50)}


def texts(rows):
    return [normalize(row['text']) for row in rows]


def fit(rows):
    pool = pairs(rows)
    inputs = texts(rows)
    model = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, max_features=30000, norm='l2')
    model.fit(dict.fromkeys(inputs[i] for i in np.unique(pool)))
    return model, len(pool)


def mutual_edges(proposals):
    options = defaultdict(dict)
    for left, right, score, i, j in proposals:
        for a, b in ((left, right), (right, left)):
            previous = options[a].get(b)
            if previous is None or score > previous[0]:
                options[a][b] = (score, i, j)
    best = {}
    for a, neighbors in options.items():
        score = max(choice[0] for choice in neighbors.values())
        tied = [b for b, choice in neighbors.items() if choice[0] == score]
        if len(tied) == 1:
            best[a] = tied[0]
    return [(i, j) for a, b in sorted(best.items()) if a < b and best.get(b) == a
            for _, i, j in [options[a][b]]]


def edits(rows, identifiers, base, weak, candidates, sims, policy):
    action, threshold = HYBRID[policy]
    by_pair = {(i, j): sim for (i, j), sim in zip(candidates, sims)}
    if action == 'cut':
        cut = [(i, j) for i, j in weak if by_pair[i, j] < threshold]
        rejected = set(cut)
        return [edge for edge in base if edge not in rejected], [], cut
    if action == 'add':
        groups = [c for _, c in clustering(identifiers, np.asarray(base, dtype=int).reshape(-1, 2))]
        roles = [(row['roleset_id'], arguments(row['arg0']), arguments(row['arg1'])) for row in rows]
        proposals = []
        for (i, j), similarity in by_pair.items():
            if similarity < threshold or groups[i] == groups[j]:
                continue
            name_a, arg0_a, arg1_a = roles[i]
            name_b, arg0_b, arg1_b = roles[j]
            if name_a and name_a == name_b and (arg0_a & arg0_b or arg1_a & arg1_b):
                proposals.append((groups[i], groups[j], similarity, i, j))
        added = mutual_edges(proposals)
        return base + added, added, []
    return base, [], []


def prepare(rows, model):
    ids = [row['mention_id'] for row in rows]
    candidates = pairs(rows)
    sims = cosine(model, texts(rows), candidates)
    edges, cross, weak = graph_data(rows)
    edge_list = [tuple(e) for e in edges]
    return ids, candidates, sims, edge_list, [edge for edge, yes in zip(edge_list, cross) if yes], [edge_list[i] for i in weak]


def predict(ids, edges):
    return clustering(ids, np.asarray(edges, dtype=int).reshape(-1, 2))


def cv(train, out):
    details = []
    for fold, (fit_idx, val_idx) in enumerate(GroupKFold(n_splits=5).split(train, groups=[r['topic'] for r in train]), 1):
        a, b = ([train[i] for i in indices] for indices in (fit_idx, val_idx))
        model, training_pairs = fit(a)
        ids, candidates, sims, edges, _, weak = prepare(b, model)
        folder = out / f'fold-{fold}'
        folder.mkdir()
        gold = scoped(b)
        metrics = {}
        for value in TEXT:
            name = f'text_{value:.2f}'
            picked = candidates[sims >= value]
            metrics[name] = {**get_scores(gold, predict(ids, picked), folder, name), 'edges': len(picked)}
        for policy in HYBRID:
            picked, added, cut = edits(b, ids, edges, weak, candidates, sims, policy)
            metrics[policy] = {**get_scores(gold, predict(ids, picked), folder, policy),
                               'added': len(added), 'cut': len(cut)}
        details.append({'fold': fold, 'fit_topics': sorted({r['topic'] for r in a}),
                        'validation_topics': sorted({r['topic'] for r in b}), 'fit_pairs': training_pairs,
                        'vocabulary_size': len(model.vocabulary_), 'validation_pairs': len(candidates), 'metrics': metrics})
    means = {name: float(np.mean([row['metrics'][name]['CoNLL_F1'] for row in details]))
             for name in details[0]['metrics']}
    threshold = max(TEXT, key=lambda n: (means[f'text_{n:.2f}'], n))
    policy = max(HYBRID, key=means.get)
    return threshold, policy, means, details


def run(annotator, output):
    train, train_sha = load_dataset(f'{annotator}-train')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid4().hex[:8]
    out = output / annotator / run_id
    out.mkdir(parents=True)
    start = perf_counter()
    threshold, policy, means, folds = cv(train, out)
    model, train_pairs = fit(train)
    filenames = ('tfidf_only.py', 'or_nb_hybrid.py', 'tfidf_nb.py', 'argument_audit.py',
                 'engine.py', 'vendor/coreference.py', 'dataset_checksums.json')
    config = {'annotator': annotator, 'train_sha256': train_sha, 'upstream_commit': COMMIT,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip(),
              'sha256_sources': {f: sha256((BASE / f).read_bytes()).hexdigest() for f in filenames},
              'threshold_grid': TEXT, 'hybrid_grid': HYBRID, 'threshold': threshold, 'policy': policy,
              'cv_means': means, 'vocabulary_size': len(model.vocabulary_), 'seed': None,
              'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    (out / 'frozen_train_config.json').write_text(json.dumps(config, indent=2))
    (out / 'cv.json').write_text(json.dumps(folds, indent=2))
    training_time = perf_counter() - start
    dev, dev_sha = load_dataset(f'{annotator}-dev')
    for field in ('topic', 'doc_id', 'mention_id'):
        if {r[field] for r in train} & {r[field] for r in dev}:
            raise ValueError(f'Train/dev overlap in {field}')
    start = perf_counter()
    ids, pool, sims, base, cross, weak = prepare(dev, model)
    all_edges, added, cut = edits(dev, ids, base, weak, pool, sims, policy)
    cross_edges, cross_added, cross_cut = edits(dev, ids, cross, weak, pool, sims, policy)
    by_method = {'OR': base, 'OR_cross': cross, 'TFIDF': pool[sims >= threshold],
                 'OR_TFIDF': all_edges, 'OR_cross_TFIDF': cross_edges}
    groups = {name: dict(predict(ids, edges)) for name, edges in by_method.items()}
    infer_time = perf_counter() - start
    gold = scoped(dev)
    metrics = [get_scores(gold, list(group.items()), out, method) for method, group in groups.items()]
    topic_metrics = []
    for topic in sorted({r['topic'] for r in dev}):
        local = [r for r in gold if r['topic'] == topic]
        folder = out / f'topic-{topic}'
        folder.mkdir()
        for method, group in groups.items():
            stats = get_scores(local, [(r['mention_id'], group[r['mention_id']]) for r in local], folder, method)
            topic_metrics.append({'topic': topic, **stats})
    edge_rows = []
    for method, tag, changes in [('OR_TFIDF', 'add', added), ('OR_TFIDF', 'cut', cut),
                                 ('OR_cross_TFIDF', 'add', cross_added), ('OR_cross_TFIDF', 'cut', cross_cut)]:
        edge_rows.extend({'method': method, 'operation': tag, 'a': ids[i], 'b': ids[j], 'topic': dev[i]['topic'],
                          'gold_same': gold[i]['gold_cluster'] == gold[j]['gold_cluster']} for i, j in changes)
    changed_pairs = []
    for i, j in combinations(range(len(ids)), 2):
        a, b = ids[i], ids[j]
        for first, second in [('OR', 'OR_TFIDF'), ('OR_cross', 'OR_cross_TFIDF')]:
            pre, post = groups[first][a] == groups[first][b], groups[second][a] == groups[second][b]
            if pre != post:
                changed_pairs.append({'method': second, 'a': a, 'b': b, 'topic': dev[i]['topic'], 'now_same': post,
                                      'gold_same': gold[i]['gold_cluster'] == gold[j]['gold_cluster']})
    predictions = [{'mention_id': r['mention_id'], 'topic': r['topic'],
                    **{m: p[r['mention_id']] for m, p in groups.items()}} for r in dev]
    for name, rows in [('metrics', metrics), ('topics', topic_metrics), ('edge_changes', edge_rows),
                       ('pair_changes', changed_pairs), ('predictions', predictions)]:
        (out / f'{name}.csv').write_text(csv_text(rows))
    (out / 'report.json').write_text(json.dumps({
        'run_id': run_id, 'dev_sha256': dev_sha, 'dev_gold_collisions': collisions(dev), 'train_pairs': train_pairs,
        'dev_coverage': coverage(dev, pool, gold_labels(dev, pool)), 'eligible_cut_edges': len(weak),
        'edge_counts': {m: len(e) for m, e in by_method.items()},
        'added': len(added), 'cut': len(cut), 'cross_added': len(cross_added), 'cross_cut': len(cross_cut),
        'cv_and_fit_seconds': training_time, 'dev_inference_seconds': infer_time,
    }, indent=2))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotator', required=True, choices=('ann1', 'ann2'))
    parser.add_argument('--output-root', type=Path, default=BASE / 'runs' / 'tfidf-only')
    args = parser.parse_args()
    print(run(args.annotator, args.output_root))
