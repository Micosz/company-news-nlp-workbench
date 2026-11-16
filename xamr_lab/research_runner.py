"""Bounded public inference using fixed experiments and non-executable JSON models."""
import base64
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from importlib.metadata import version
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import perf_counter
import urllib.request
from uuid import uuid4
import zipfile
import threading
import io

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import CategoricalNB
import or_nb_hybrid as nb
import tfidf_only as tf
from tfidf_nb import scoped, pairs, gold_labels, coverage
from engine import BASE, COMMIT, csv_text, load_dataset, scores
from setup_data import FILES

METHODS = {
    'OR': {'title': 'OR', 'description': 'Original X-AMR OR graph; syn_map disabled.'},
    'TFIDF': {'title': 'TF-IDF', 'description': 'Cosine-only cross-document links at train-CV threshold.'},
    'OR_TFIDF': {'title': 'OR + TF-IDF', 'description': 'One round of unique mutual-best cluster links; matching roleset and ARG0 or ARG1, cosine ≥ 0.50.'},
    'OR_TFIDF_NB': {'title': 'OR + TF-IDF + Naive Bayes', 'description': 'Original OR + NB edge guard using TF-IDF cosine deciles, balanced CategoricalNB. This is not TF-IDF addition followed by NB. Train CV selected no pruning on both annotation versions.'},
}
DATASETS = tuple(f'{a}-{s}' for a in ('ann1', 'ann2') for s in ('dev', 'dev_small', 'test_common'))
CHECKSUMS = json.loads((BASE / 'dataset_checksums.json').read_text())
SOURCE_FILES = ('research_runner.py', 'replay_research.py', 'prepare_models.py', 'tfidf_only.py', 'tfidf_nb.py',
                'or_nb_hybrid.py', 'argument_audit.py', 'temporal_ablations.py', 'date_evidence.py',
                'engine.py', 'setup_data.py', 'requirements.txt', 'dataset_checksums.json',
                'requirements-training.txt', 'vendor/coreference.py', 'vendor/utils.py', 'vendor/__init__.py', 'vendor/LICENSE', 'NOTICE.md')

@lru_cache(maxsize=2)
def model(annotation):
    raw = (BASE / 'models' / (annotation + '.json')).read_bytes()
    manifest = json.loads((BASE / 'models' / 'checksums.json').read_text())
    if hashlib.sha256(raw).hexdigest() != manifest[annotation + '.json']:
        raise ValueError('Model checksum mismatch; run stopped.')
    frozen = json.loads(raw)
    if frozen['annotation'] != annotation or frozen['train_sha256'] != CHECKSUMS[annotation + '-train']:
        raise ValueError('Training provenance mismatch.')
    text = frozen['tfidf']
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, max_features=30000,
                                 norm='l2', vocabulary=text['vocabulary'])
    vectorizer.idf_ = np.asarray(text['idf'])
    config = frozen['nb']
    estimator = CategoricalNB(alpha=config['alpha'], min_categories=10, class_prior=config['class_prior'])
    # Restore sufficient statistics without pickle or any executable model format.
    estimator.fit(np.tile(np.arange(10), 2).reshape(-1, 1), np.repeat([0, 1], 10),
                  sample_weight=np.asarray(config['category_count']).ravel())
    return frozen, vectorizer, (vectorizer, np.asarray(config['bins']), estimator), hashlib.sha256(raw).hexdigest()


def catalog():
    original = {d['name']: d for d in json.loads((BASE / 'dataset_catalog.json').read_text())}
    return {'datasets': [{**original[name], 'annotation': name.split('-')[0],
                          'split': name.split('-', 1)[1], 'previously_viewed': 'test_common' in name}
                         for name in DATASETS], 'methods': METHODS, 'max_mentions': 2000,
            'source_sha256': {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in SOURCE_FILES},
            'models_sha256': json.loads((BASE / 'models' / 'checksums.json').read_text()),
            'deployment_commit': os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local'),
            'protocol': 'Train-selected presets; topic-scoped gold; supplied semantic annotations; CPU inference.'}


def fetch_dataset(name, root):
    if name not in DATASETS:
        raise ValueError('Choose a supported ECB+ annotation dataset.')
    local = BASE / 'data' / (name + '.json')
    if local.exists():
        raw = local.read_bytes()
    else:
        url = f'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/{COMMIT}/project/annotations/ecb/{FILES[name]}'
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read(12_000_001)
    if hashlib.sha256(raw).hexdigest() != CHECKSUMS[name]:
        raise ValueError('Dataset checksum mismatch; run stopped.')
    root.mkdir(parents=True, exist_ok=True)
    (root / (name + '.json')).write_bytes(raw)
    return load_dataset(name, root)


def validate_request(body):
    if not isinstance(body, dict) or set(body) - {'dataset', 'algorithm', 'acknowledge_test'}:
        raise ValueError('Only dataset, algorithm and acknowledge_test are accepted.')
    name, algorithm = body.get('dataset', 'ann1-dev'), body.get('algorithm', 'compare')
    if not isinstance(name, str) or name not in DATASETS:
        raise ValueError('Unsupported dataset.')
    if not isinstance(algorithm, str) or algorithm not in (*METHODS, 'compare'):
        raise ValueError('Unsupported algorithm.')
    if 'test_common' in name and body.get('acknowledge_test') is not True:
        raise ValueError('test_common was previously viewed; acknowledge this before running.')
    return name, algorithm


def compute(body, tasks, output):
    name, algorithm = validate_request(body)
    if not 2 <= len(tasks) <= 2000:
        raise ValueError('Dataset must contain 2–2,000 mentions.')
    if any(not isinstance(r.get('text'), str) for r in tasks):
        raise ValueError('Supplied annotation text is required.')
    frozen, vectorizer, classifier, model_sha = model(name.split('-')[0])
    output.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    ids, candidates, similarities, base, cross, weak = tf.prepare(tasks, vectorizer)
    selected = list(METHODS) if algorithm == 'compare' else list(dict.fromkeys(('OR', algorithm)))
    edge_sets = {'OR': base}
    edits = []
    if 'TFIDF' in selected:
        edge_sets['TFIDF'] = candidates[similarities >= frozen['text_selection']['threshold']]
    if 'OR_TFIDF' in selected:
        links, added, cut = tf.edits(tasks, ids, base, weak, candidates, similarities, frozen['text_selection']['policy'])
        edge_sets['OR_TFIDF'] = links
        edits += [{'method': 'OR_TFIDF', 'operation': op, 'a': ids[i], 'b': ids[j], 'topic': tasks[i]['topic']}
                  for op, edges in [('add', added), ('cut', cut)] for i, j in edges]
    if 'OR_TFIDF_NB' in selected:
        ranking = nb.rank(classifier, tasks, np.asarray(weak, dtype=int).reshape(-1, 2))
        # Original retained() takes positions in the full OR edge array.
        index = {tuple(edge): k for k, edge in enumerate(base)}
        weak_indices = np.asarray([index[tuple(edge)] for edge in weak], dtype=int)
        keep, removed = nb.retained(np.asarray(base, dtype=int).reshape(-1, 2), weak_indices, ranking,
                                    tuple(frozen['nb_selection']['cutoff']) if frozen['nb_selection']['cutoff'] is not None else None)
        edge_sets['OR_TFIDF_NB'] = np.asarray(base, dtype=int).reshape(-1, 2)[keep]
        edits += [{'method': 'OR_TFIDF_NB', 'operation': 'cut', 'a': ids[base[k][0]], 'b': ids[base[k][1]],
                   'topic': tasks[base[k][0]]['topic']} for k in removed]
    predictions = {m: dict(tf.predict(ids, edge_sets[m])) for m in selected}
    inference_seconds = perf_counter() - start
    gold = scoped(tasks)
    metrics = {m: scores(gold, list(predictions[m].items()), output, m) for m in selected}
    topic_metrics = []
    for topic in sorted({r['topic'] for r in tasks}):
        local = [r for r in gold if r['topic'] == topic]
        directory = output / ('topic-' + str(len(topic_metrics)))
        directory.mkdir()
        for method in selected:
            value = scores(local, [(r['mention_id'], predictions[method][r['mention_id']]) for r in local], directory, method)
            topic_metrics.append({'topic': topic, 'method': method, 'CoNLL_F1': value['conll_f1'] * 100,
                                  'Pair_F1': value['pair_f1'] * 100, 'FP': value['fp'], 'FN': value['fn']})
    changes, examples, change_counts = [], [], {m: {'recovered_fn': 0, 'new_fp': 0, 'removed_fp': 0, 'new_fn': 0} for m in selected if m != 'OR'}
    for i, j in combinations(range(len(tasks)), 2):
        a, b = ids[i], ids[j]
        same = gold[i]['gold_cluster'] == gold[j]['gold_cluster']
        before = predictions['OR'][a] == predictions['OR'][b]
        for method in selected:
            after = predictions[method][a] == predictions[method][b]
            if method != 'OR' and before != after:
                kind = ('recovered_fn' if same else 'new_fp') if after else ('new_fn' if same else 'removed_fp')
                change_counts[method][kind] += 1
                changes.append({'method': method, 'a': a, 'b': b, 'gold_same': same, 'now_same': after, 'change': kind})
            if after != same and len(examples) < 100:
                examples.append({'method': method, 'a': a, 'b': b, 'gold_same': same, 'predicted_same': after,
                                 'text_a': tasks[i]['text'], 'text_b': tasks[j]['text']})
    revision = os.environ.get('VERCEL_GIT_COMMIT_SHA', '')
    if not revision:
        try:
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = 'unavailable'
    source_hashes = {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in SOURCE_FILES}
    now = datetime.now(timezone.utc)
    run_id = now.strftime('%Y%m%dT%H%M%S-') + uuid4().hex[:8]
    report = {'id': run_id, 'created': now.isoformat(), 'dataset': name, 'algorithm': algorithm,
              'phase': 'previously-viewed test subset' if 'test_common' in name else 'explored development',
              'metrics': metrics, 'coverage': coverage(tasks, candidates, gold_labels(tasks, candidates)),
              'edge_counts': {m: len(edge_sets[m]) for m in selected}, 'edge_changes': edits,
              'pair_changes': change_counts, 'examples': examples[:30], 'inference_seconds': inference_seconds,
              'duration_seconds': perf_counter() - start,
              'selection': {'tfidf_threshold': frozen['text_selection']['threshold'], 'tfidf_policy': frozen['text_selection']['policy'],
                            'nb_fraction': frozen['nb_selection']['fraction'], 'nb_cutoff': frozen['nb_selection']['cutoff'],
                            'nb_no_op': frozen['nb_selection']['fraction'] == 0},
              'provenance': {'dataset_sha256': CHECKSUMS[name], 'input_sha256': hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), 'train_sha256': frozen['train_sha256'],
                             'model_sha256': model_sha, 'upstream_commit': COMMIT, 'checkout_commit': revision,
                             'source_sha256': source_hashes, 'gold_scope': '(topic, gold_cluster)',
                             'python': sys.version, 'platform': platform.platform(),
                             'packages': {p: version(p) for p in ('numpy', 'scipy', 'scikit-learn', 'CoVal')}},
              'warnings': ['Ann1 and Ann2 are semantic annotation input versions of the same ECB+ corpus, not independent gold answer sets.',
                           'Development has been explored; test_common was previously viewed and is a partial subset, not an untouched test.',
                           'OR + TF-IDF is not consistently superior: Ann1 dev CoNLL and both dev Pair F1 scores decrease.',
                           'The NB preset is the original OR edge guard, not a cascade after TF-IDF addition. Train CV selected no pruning on both versions.',
                           'Raw-news event extraction has not been validated. No significance or generalization claim.']}
    metric_rows = [{'method': m, 'MUC_F1': v['muc']['f1'] * 100, 'B3_F1': v['b3']['f1'] * 100,
                    'CEAF_e_F1': v['ceafe']['f1'] * 100, 'CoNLL_F1': v['conll_f1'] * 100,
                    'Pair_P': v['pair_precision'] * 100, 'Pair_R': v['pair_recall'] * 100, 'Pair_F1': v['pair_f1'] * 100,
                    'FP': v['fp'], 'FN': v['fn'], 'clusters': v['clusters']} for m, v in metrics.items()]
    for filename, rows in [('metrics', metric_rows), ('topics', topic_metrics), ('edge_changes', edits),
                           ('pair_changes', changes), ('error_examples', examples),
                           ('predictions', [{'mention_id': r['mention_id'], 'topic': r['topic'], 'gold_cluster': gold[k]['gold_cluster'],
                                             **{m: predictions[m][r['mention_id']] for m in selected}} for k, r in enumerate(tasks)])]:
        (output / (filename + '.csv')).write_text(csv_text(rows), encoding='utf-8')
    (output / 'table.tex').write_text('\\begin{tabular}{lrr}\nMethod & CoNLL F1 & Pair F1 \\\\\n' +
        '\n'.join(f"{m.replace('_', ' ')} & {v['conll_f1']*100:.4f} & {v['pair_f1']*100:.4f} \\\\" for m, v in metrics.items()) + '\n\\end{tabular}\n')
    for filename, value in [('report', report), ('config', body), ('input', tasks)]:
        (output / (filename + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for filename in SOURCE_FILES:
        target = output / 'source' / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((BASE / filename).read_bytes())
    target = output / 'source' / 'models'
    target.mkdir()
    (target / 'checksums.json').write_bytes((BASE / 'models' / 'checksums.json').read_bytes())
    (target / (frozen['annotation'] + '.json')).write_bytes((BASE / 'models' / (frozen['annotation'] + '.json')).read_bytes())
    (output / 'REPLAY.txt').write_text('Install source/requirements.txt in Python 3.12. Then run:\npython source/replay_research.py --input input.json --config config.json --output replay\nCompare metrics.csv and predictions.csv. Timings, run IDs and host metadata vary.\nInput is the exact upstream snapshot, verified by SHA-256. Model is inspectable JSON, never pickle.\n')
    return report


class RunBusyError(ValueError):
    pass

RUN_SLOTS = threading.BoundedSemaphore(2)

def run_online(body):
    if not RUN_SLOTS.acquire(blocking=False):
        raise RunBusyError('Two experiments are already running. Please retry shortly.')
    try:
        return _run_online(body)
    finally:
        RUN_SLOTS.release()

def _run_online(body):
    name, _ = validate_request(body)
    with tempfile.TemporaryDirectory(prefix='xamr-research-') as tmp:
        root = Path(tmp)
        tasks, checksum = fetch_dataset(name, root / 'data')
        output = root / 'evidence'
        report = compute(body, tasks, output)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(output.rglob('*')):
                if p.is_file():
                    archive.write(p, p.relative_to(output))
        response = {'status': 'done', 'report': report, 'archive_base64': base64.b64encode(stream.getvalue()).decode()}
        if len(json.dumps(response).encode()) > 4_000_000:
            raise ValueError('Evidence exceeds the online response limit. Use the local replay runner.')
        return response
