"""Train the Pair Workbench text model and evaluate it as X-AMR clustering."""
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
from hashlib import sha256
import html
from itertools import combinations
import json
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter
import unicodedata
from uuid import uuid4

import numpy as np
import scipy
from scipy.sparse import csr_matrix
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import CategoricalNB

from engine import BASE, COMMIT, c_clustering, csv_text, event_graphs, load_dataset, scores

THRESHOLDS = (0.01, 0.05, 0.10, 0.25, 0.50)
QUANTILES = (1 / 3, 2 / 3)
GRAPH_FIELDS = ('mention_id', 'topic', 'doc_id', 'sentence_id', 'roleset_id', 'arg0', 'arg1', 'argL', 'argT')


def normalize(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', html.unescape(value))).strip()


def pairs(tasks):
    topics = defaultdict(list)
    for i, row in enumerate(tasks):
        topics[row['topic']].append(i)
    return np.asarray([(i, j) for group in topics.values() for i, j in combinations(group, 2)
                       if tasks[i]['doc_id'] != tasks[j]['doc_id']], dtype=int).reshape(-1, 2)


def gold_labels(tasks, edges):
    return np.asarray([tasks[i]['gold_cluster'] == tasks[j]['gold_cluster']
                       and tasks[i]['topic'] == tasks[j]['topic'] for i, j in edges], dtype=int)


def scoped(tasks):
    return [{**row, 'gold_cluster': f"{row['topic']}:{row['gold_cluster']}"} for row in tasks]


def collisions(tasks):
    topics = defaultdict(set)
    for row in tasks:
        topics[row['gold_cluster']].add(row['topic'])
    return {key: sorted(value) for key, value in sorted(topics.items()) if len(value) > 1}


def cosine(vectorizer, texts, edges):
    matrix = vectorizer.transform(texts)
    result = np.empty(len(edges))
    for start in range(0, len(edges), 1024):
        batch = edges[start:start + 1024]
        result[start:start + len(batch)] = np.asarray(
            matrix[batch[:, 0]].multiply(matrix[batch[:, 1]]).sum(axis=1)).ravel()
    return np.clip(result, 0, 1)


def fit(texts, edges, labels):
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, max_features=30000, norm='l2')
    # In this all-pairs task some mentions have no cross-document candidate.
    # Match Pair Workbench by fitting from contexts that participate in training pairs.
    vectorizer.fit(dict.fromkeys(texts[i] for i in np.unique(edges)))
    cuts = np.unique(np.quantile(cosine(vectorizer, texts, edges), QUANTILES))
    model = CategoricalNB(alpha=1.0, min_categories=3)
    model.fit(np.digitize(cosine(vectorizer, texts, edges), cuts).reshape(-1, 1), labels)
    return vectorizer, cuts, model


def predict(model, texts, edges):
    vectorizer, cuts, nb = model
    bins = np.digitize(cosine(vectorizer, texts, edges), cuts)
    return nb.predict_proba(bins.reshape(-1, 1))[:, list(nb.classes_).index(1)], bins


def clustering(ids, edges):
    if len(edges):
        left, right = edges.T
        graph = csr_matrix((np.ones(len(edges)), (left, right)), shape=(len(ids), len(ids)))
        graph = graph + graph.T
    else:
        graph = csr_matrix((len(ids), len(ids)))
    return [(key, int(value)) for key, value in c_clustering(graph, ids)]


def coverage(tasks, edges, labels):
    gold = defaultdict(list)
    for row in tasks:
        gold[row['topic'], row['gold_cluster']].append(row['doc_id'])
    gold_total = sum(len(group) * (len(group) - 1) // 2 for group in gold.values())
    return {'mentions': len(tasks), 'documents': len({r['doc_id'] for r in tasks}),
            'topics': len({r['topic'] for r in tasks}), 'candidate_mentions': len(np.unique(edges)),
            'candidate_pairs': len(edges), 'positive_candidates': int(labels.sum()),
            'negative_candidates': int(len(labels) - labels.sum()), 'gold_pairs_all': gold_total,
            'positive_pair_coverage': float(labels.sum() / gold_total)}


def get_scores(tasks, pred, out, method):
    row = scores(tasks, pred, out, method)
    return {'method': method, 'CoNLL_F1': 100 * row['conll_f1'],
            **{key: 100 * row[key] for key in ('pair_precision', 'pair_recall', 'pair_f1')},
            **{key.upper(): row[key] for key in ('tp', 'fp', 'fn', 'tn')}, 'clusters': row['clusters']}


def train_cv(train, out):
    topics = [r['topic'] for r in train]
    details = []
    for fold, (fit_idx, val_idx) in enumerate(GroupKFold(n_splits=5).split(train, groups=topics), 1):
        a, b = ([train[i] for i in idx] for idx in (fit_idx, val_idx))
        ea, eb = pairs(a), pairs(b)
        y = gold_labels(a, ea)
        ta, tb = ([normalize(r['text']) for r in split] for split in (a, b))
        model = fit(ta, ea, y)
        posterior, _ = predict(model, tb, eb)
        ids = [r['mention_id'] for r in b]
        validation = scoped(b)
        directory = out / f'fold-{fold}'
        directory.mkdir()
        fold_info = {'fold': fold, 'fit_topics': sorted({r['topic'] for r in a}),
                     'validation_topics': sorted({r['topic'] for r in b}),
                     'fit_pairs': len(ea), 'fit_positive': int(y.sum()), 'validation_pairs': len(eb),
                     'validation_positive': int(gold_labels(b, eb).sum()),
                     'cosine_cuts': model[1].tolist(), 'vocabulary_size': len(model[0].vocabulary_)}
        for threshold in THRESHOLDS:
            prediction = clustering(ids, eb[posterior >= threshold])
            result = get_scores(validation, prediction, directory, f'NB_{threshold}')
            details.append({**fold_info, 'threshold': threshold, **result})
    means = {threshold: float(np.mean([r['CoNLL_F1'] for r in details if r['threshold'] == threshold]))
             for threshold in THRESHOLDS}
    return max(THRESHOLDS, key=lambda t: (means[t], t)), means, details


def run(annotator, output):
    train, train_sha = load_dataset(f'{annotator}-train')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid4().hex[:8]
    out = output / annotator / run_id
    out.mkdir(parents=True)
    started = perf_counter()
    threshold, means, folds = train_cv(train, out)
    train_pairs = pairs(train)
    train_y = gold_labels(train, train_pairs)
    model = fit([normalize(r['text']) for r in train], train_pairs, train_y)
    vectorizer, cuts, nb = model
    config = {'annotator': annotator, 'train_sha256': train_sha, 'upstream_commit': COMMIT,
              'checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip(),
              'source_sha256': {name: sha256((BASE / name).read_bytes()).hexdigest() for name in
                                ('tfidf_nb.py', 'engine.py', 'vendor/coreference.py', 'dataset_checksums.json',
                                 '../pair_workbench/algorithms/pair_experiment.py')},
              'threshold': threshold, 'threshold_grid': THRESHOLDS, 'cv_mean_conll': means,
              'model': {'quantiles': QUANTILES, 'cuts': cuts.tolist(), 'vocabulary_size': len(vectorizer.vocabulary_),
                        'alpha': nb.alpha, 'class_count': nb.class_count_.tolist(),
                        'category_count': nb.category_count_[0].tolist()},
              'seed': None, 'python': sys.version.split()[0], 'sklearn': sklearn.__version__,
              'numpy': np.__version__, 'scipy': scipy.__version__}
    (out / 'frozen_train_config.json').write_text(json.dumps(config, indent=2))
    (out / 'cv.json').write_text(json.dumps(folds, indent=2))
    training_time = perf_counter() - started
    dev, dev_sha = load_dataset(f'{annotator}-dev')
    for field in ('topic', 'doc_id', 'mention_id'):
        if {r[field] for r in train} & {r[field] for r in dev}:
            raise ValueError(f'Train/dev overlap in {field}')
    started = perf_counter()
    dev_pairs = pairs(dev)
    dev_y = gold_labels(dev, dev_pairs)
    posterior, bins = predict(model, [normalize(row['text']) for row in dev], dev_pairs)
    ids, nested, local_time = event_graphs([{key: row[key] for key in GRAPH_FIELDS} for row in dev])
    graph = nested + local_time
    left, right = graph.nonzero()
    cross = np.asarray([(i, j) for i, j in zip(left, right) if i < j and dev[i]['doc_id'] != dev[j]['doc_id']],
                       dtype=int).reshape(-1, 2)
    predictions = {'OR': [(key, int(value)) for key, value in c_clustering(graph, ids)],
                   'OR_cross_document': clustering(ids, cross),
                   'NB_0.50': clustering(ids, dev_pairs[posterior >= 0.5]),
                   'NB_CV': clustering(ids, dev_pairs[posterior >= threshold])}
    evaluation_time = perf_counter() - started
    evaluation_gold = {'benchmark_raw': dev}
    if collisions(dev):
        evaluation_gold['topic_scoped'] = scoped(dev)
    metrics = [{'gold_scope': scope, **get_scores(reference, result, out, f'{name}_{scope}')}
               for scope, reference in evaluation_gold.items() for name, result in predictions.items()]
    (out / 'metrics.csv').write_text(csv_text(metrics))
    labels = {method: dict(result) for method, result in predictions.items()}
    (out / 'predictions.csv').write_text(csv_text([
        {'mention_id': row['mention_id'], 'topic': row['topic'], 'gold_cluster': row['gold_cluster'],
         **{method: result[row['mention_id']] for method, result in labels.items()}} for row in dev]))
    with (out / 'dev_pairs.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(('a', 'b', 'gold_same', 'bin', 'posterior'))
        writer.writerows((ids[i], ids[j], y, bin_id, prob)
                         for (i, j), y, bin_id, prob in zip(dev_pairs, dev_y, bins, posterior))
    (out / 'report.json').write_text(json.dumps({
        'run_id': run_id, 'dev_sha256': dev_sha, 'train': coverage(train, train_pairs, train_y),
        'dev': coverage(dev, dev_pairs, dev_y), 'train_gold_collisions': collisions(train),
        'dev_gold_collisions': collisions(dev), 'selected_edges': {'NB_0.50': int((posterior >= 0.5).sum()),
          'NB_CV': int((posterior >= threshold).sum()), 'OR_cross_document': len(cross)},
        'cv_and_fit_seconds': training_time, 'dev_inference_seconds': evaluation_time,
    }, indent=2))
    return out


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--annotator', choices=('ann1', 'ann2'), required=True)
    cli.add_argument('--output-root', type=Path, default=BASE / 'runs' / 'tfidf-nb')
    args = cli.parse_args()
    print(run(args.annotator, args.output_root))
