"""Run the fixed, dev-only temporal ablation matrix with local artifacts."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
from itertools import combinations
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from uuid import uuid4

import numpy as np
from scipy.sparse import csr_matrix

from date_evidence import classify, POLICY
from engine import BASE, COMMIT, c_clustering, conflict, constrained, csv_text, event_graphs, interval, load_dataset, scores

DEV_DATASETS = ('ann1-dev', 'ann2-dev')
FIELDS = ('mention_id', 'topic', 'doc_id', 'sentence_id', 'roleset_id',
          'arg0', 'arg1', 'argL', 'argT', 'marked_doc', 'marked_sentence', 'text')
SETTINGS = {
    'OR': ('raw', 0, 'none'),
    'Temporal_0': ('raw', 0, 'cluster'),
    'Date_Evidence': ('sentence', 0, 'cluster'),
    'Header_Mask': ('header_mask', 0, 'cluster'),
    'Gap_3': ('raw', 3, 'cluster'),
    'Header_Mask_Gap_3': ('header_mask', 3, 'cluster'),
    'Edge_Only': ('raw', 0, 'edge'),
}


def edge_filter(graph, ids, dates, tolerance):
    rows, cols = graph.nonzero()
    rejected = {(i, j) for i, j in zip(rows, cols) if i < j and conflict(dates[i], dates[j], tolerance)}
    keep = np.array([(min(i, j), max(i, j)) not in rejected for i, j in zip(rows, cols)], dtype=bool)
    filtered = csr_matrix((np.ones(keep.sum()), (rows[keep], cols[keep])), shape=graph.shape)
    return c_clustering(filtered, ids), [
        {'edge_a': ids[i], 'edge_b': ids[j], 'witness_a': ids[i], 'witness_b': ids[j]}
        for i, j in sorted(rejected)
    ]


def infer(inputs):
    started = perf_counter()
    ids, nested, location_time = event_graphs(inputs)
    graph = nested + location_time
    raw = [interval(task['argT']) for task in inputs]
    evidence = [classify(task, span) for task, span in zip(inputs, raw)]
    dates = {
        'raw': raw,
        'sentence': [span if row['category'] == 'event' else None for span, row in zip(raw, evidence)],
        'header_mask': [span if row['category'] != 'publication' else None for span, row in zip(raw, evidence)],
    }
    preparation_time = perf_counter() - started
    results = {}
    for method, (source, tolerance, scope) in SETTINGS.items():
        started = perf_counter()
        if scope == 'none':
            prediction, rejected = c_clustering(graph, ids), []
        elif scope == 'edge':
            prediction, rejected = edge_filter(graph, ids, dates[source], tolerance)
        else:
            prediction, rejected = constrained(graph, ids, dates[source], tolerance)
        results[method] = (
            dict((mention, int(group)) for mention, group in prediction),
            rejected, perf_counter() - started, sum(span is not None for span in dates[source]),
        )
    return results, evidence, raw, preparation_time


def gap_bucket(left, right):
    if left is None or right is None:
        return 'unknown'
    days = max(0, (left[0] - right[1]).days, (right[0] - left[1]).days)
    return 'overlap' if not days else '1–3 days' if days <= 3 else '>3 days'


def differences(tasks, evidence, raw, results):
    summary = Counter()
    rows = []
    for i, j in combinations(range(len(tasks)), 2):
        a, b = tasks[i], tasks[j]
        left, right = a['mention_id'], b['mention_id']
        same_gold = a['gold_cluster'] == b['gold_cluster']
        predicted = {method: groups[left] == groups[right] for method, (groups, *_) in results.items()}
        baseline = predicted['Temporal_0']
        if all(value == baseline for value in predicted.values()):
            continue
        gap = gap_bucket(raw[i], raw[j])
        header = any(evidence[k]['category'] == 'publication' for k in (i, j))
        for method, same in predicted.items():
            if same == baseline:
                continue
            change = ('recovered_fn' if same_gold else 'reintroduced_fp') if same else ('new_fn' if same_gold else 'removed_fp')
            summary[method, change, gap, header] += 1
            rows.append({'method': method, 'a': left, 'b': right, 'change_vs_temporal': change,
                         'gap': gap, 'header_candidate': header, 'argT_a': a['argT'], 'argT_b': b['argT'],
                         'gold_same': same_gold, 'prediction_same': same})
    counts = [{'method': m, 'change': change, 'gap': gap, 'header_candidate': header, 'count': n}
              for (m, change, gap, header), n in sorted(summary.items())]
    return rows, counts


def run(dataset, output_root):
    if dataset not in DEV_DATASETS:
        raise ValueError('This matrix requires Ann1 dev or Ann2 dev')
    tasks, checksum = load_dataset(dataset)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid4().hex[:8]
    output = output_root / dataset / run_id
    output.mkdir(parents=True)
    inputs = [{key: task[key] for key in FIELDS} for task in tasks]
    results, evidence, raw, prepare_seconds = infer(inputs)
    files = ('temporal_ablations.py', 'engine.py', 'date_evidence.py', 'additional_data.py', 'setup_data.py',
             'dataset_checksums.json', 'requirements.txt', 'vendor/coreference.py', 'vendor/utils.py')
    config = {
        'dataset': dataset, 'dataset_sha256': checksum, 'upstream_commit': COMMIT,
        'checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip(),
        'sources_sha256': {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest() for name in files},
        'settings': SETTINGS, 'seed': None, 'date_policy': POLICY,
        'edge_order': 'lexical mention ID for cluster veto', 'phase': 'development',
        'python': sys.version, 'platform': platform.platform(),
    }
    metrics, rejections = [], []
    for method, (groups, rejected, seconds, coverage) in results.items():
        values = scores(tasks, list(groups.items()), output, method)
        metrics.append({'method': method, 'CoNLL_F1': 100 * values['conll_f1'],
                        **{key: 100 * values[key] for key in ('pair_precision', 'pair_recall', 'pair_f1')},
                        'FP': values['fp'], 'FN': values['fn'], 'coverage': coverage,
                        'veto_or_cut': len(rejected), 'clustering_seconds': seconds})
        rejections.extend({'method': method, **edge} for edge in rejected)
    rows, counts = differences(tasks, evidence, raw, results)
    predictions = [{'mention_id': task['mention_id'], 'gold_cluster': task['gold_cluster'],
                    **{method: groups[task['mention_id']] for method, (groups, *_) in results.items()}}
                   for task in tasks]
    for name, data in [('metrics', metrics), ('predictions', predictions), ('date_evidence', evidence),
                       ('vetoes', rejections), ('error_pairs_vs_temporal', rows), ('error_counts_vs_temporal', counts)]:
        (output / f'{name}.csv').write_text(csv_text(data))
    (output / 'environment.txt').write_text('\n'.join(sorted(
        f"{d.metadata['Name']}=={d.version}" for d in distributions() if d.metadata['Name']
    )) + '\n')
    (output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    (output / 'report.json').write_text(json.dumps({
        'run_id': run_id, 'metrics': metrics, 'date_categories': dict(Counter(r['category'] for r in evidence)),
        'graph_and_date_seconds': prepare_seconds,
    }, indent=2) + '\n')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, choices=DEV_DATASETS)
    parser.add_argument('--output-root', type=Path, default=BASE / 'runs' / 'temporal-ablations')
    args = parser.parse_args()
    print(run(args.dataset, args.output_root))
