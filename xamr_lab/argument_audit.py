"""Sample temporal errors and evaluate a fixed ARG1 guard on author dev data."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from time import perf_counter
import unicodedata

from engine import BASE, c_clustering, csv_text, event_graphs, load_dataset, scores
from temporal_ablations import DEV_DATASETS, FIELDS

SEED = 20261115
ROLESET = re.compile(r'[\w-]+\.\d+')


def arguments(value):
    parts = [part.strip() for part in value.split('/') if part.strip()]
    if any(ROLESET.fullmatch(part) for part in parts):
        return set()
    return {normalized for part in parts
            if (normalized := ' '.join(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', part).casefold())))}


def prune(nested, location_time, inputs):
    graph = (nested + location_time).tolil()
    values = [arguments(row['arg1']) for row in inputs]
    removed = []
    rows, cols = location_time.nonzero()
    for i, j in zip(rows, cols):
        if i >= j or nested[i, j] or not values[i] or not values[j] or values[i] & values[j]:
            continue
        graph[i, j] = graph[j, i] = 0
        removed.append({'a': inputs[i]['mention_id'], 'b': inputs[j]['mention_id'],
                        'arg1_a': inputs[i]['arg1'], 'arg1_b': inputs[j]['arg1']})
    return graph.tocsr(), removed


def select_pairs(rows, dataset):
    winners = {}
    sizes = Counter()
    for row in rows:
        if row['method'] != 'OR':
            continue
        group = ('header' if row['header_candidate'] == 'True'
                 else 'near' if row['gap'] == '1–3 days' else 'other')
        stratum = (row['change_vs_temporal'], group)
        sizes[stratum] += 1
        ids = sorted((row['a'], row['b']))
        rank = sha256(f'{SEED}|{dataset}|{"|".join(ids)}'.encode()).hexdigest()
        if stratum not in winners or rank < winners[stratum][0]:
            winners[stratum] = (rank, row)
    return [{'dataset': dataset, 'outcome': outcome, 'stratum': group, 'population': sizes[outcome, group],
             'rank': rank, 'a': row['a'], 'b': row['b'], 'gap': row['gap']}
            for (outcome, group), (rank, row) in sorted(winners.items())]


def run(dataset, reference, output):
    tasks, digest = load_dataset(dataset)
    old = json.loads((reference / 'config.json').read_text())
    if (old['dataset'], old['dataset_sha256']) != (dataset, digest):
        raise ValueError('Reference dataset or checksum mismatch')
    for name in ('predictions.csv', 'metrics.csv', 'error_pairs_vs_temporal.csv'):
        if not (reference / name).is_file():
            raise ValueError(f'Missing reference file {name}')
    output.mkdir(parents=True, exist_ok=False)
    inputs = [{key: row[key] for key in FIELDS} for row in tasks]
    started = perf_counter()
    ids, nested, location_time = event_graphs(inputs)
    graph, removed = prune(nested, location_time, inputs)
    pred = [(mention, int(group)) for mention, group in c_clustering(graph, ids)]
    seconds = perf_counter() - started
    old_predictions = list(csv.DictReader((reference / 'predictions.csv').open()))
    direct_or = [str(cluster) for _, cluster in c_clustering(nested + location_time, ids)]
    if [r['mention_id'] for r in old_predictions] != ids or [r['OR'] for r in old_predictions] != direct_or:
        raise ValueError('OR predictions disagree with the reference run')
    metrics = list(csv.DictReader((reference / 'metrics.csv').open()))
    value = scores(tasks, pred, output, 'ARG1_Guard')
    metrics.append({'method': 'ARG1_Guard', 'CoNLL_F1': 100 * value['conll_f1'],
                    **{key: 100 * value[key] for key in ('pair_precision', 'pair_recall', 'pair_f1')},
                    'FP': value['fp'], 'FN': value['fn'], 'coverage': '',
                    'veto_or_cut': len(removed), 'clustering_seconds': seconds})
    opportunities = sum(i < j and not nested[i, j] and bool(arguments(inputs[i]['arg1']))
                        and bool(arguments(inputs[j]['arg1'])) for i, j in zip(*location_time.nonzero()))
    samples = select_pairs(csv.DictReader((reference / 'error_pairs_vs_temporal.csv').open()), dataset)
    selected = {sample[key] for sample in samples for key in ('a', 'b')}
    for name, rows in (
        ('sample', samples), ('metrics', metrics), ('removed_edges', removed),
        ('predictions', [{**row, 'ARG1_Guard': group} for row, (_, group) in zip(old_predictions, pred)]),
    ):
        (output / f'{name}.csv').write_text(csv_text(rows))
    (output / 'sample_context_local.json').write_text(json.dumps(
        [{key: row[key] for key in ('mention_id', 'argT', 'marked_sentence', 'marked_doc')}
         for row in inputs if row['mention_id'] in selected], ensure_ascii=False, indent=2))
    (output / 'config.json').write_text(json.dumps({
        'dataset': dataset, 'dataset_sha256': digest, 'sample_seed': SEED,
        'inference_randomness': None, 'reference_run': reference.name, 'eligible_edges': int(opportunities),
        'timing_scope': 'EID generation, edge filtering and clustering combined for ARG1_Guard',
        'checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip(),
        'source_sha256': {name: sha256((BASE / name).read_bytes()).hexdigest() for name in
                          ('argument_audit.py', 'temporal_ablations.py', 'engine.py',
                           'vendor/coreference.py', 'date_evidence.py', 'requirements.txt')},
        'reference_sha256': {name: sha256((reference / name).read_bytes()).hexdigest() for name in
                             ('config.json', 'predictions.csv', 'metrics.csv', 'error_pairs_vs_temporal.csv')},
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, choices=DEV_DATASETS)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.dataset, args.reference, args.output)
