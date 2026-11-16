"""Rebuild safe JSON model artifacts using the original train-only experiments."""
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import scipy
import numpy as np
import sklearn
import or_nb_hybrid as nb
import tfidf_only as tf
from engine import BASE, COMMIT, load_dataset


def prepare(annotation, target=BASE / 'models'):
    if sklearn.__version__ != '1.9.1':
        raise RuntimeError('Model preparation requires scikit-learn 1.9.1, the original CV runtime. See requirements-training.txt.')
    train, checksum = load_dataset(annotation + '-train')
    with tempfile.TemporaryDirectory() as root:
        a, b = Path(root) / 'text', Path(root) / 'nb'
        a.mkdir(); b.mkdir()
        threshold, policy, means, folds = tf.cv(train, a)
        fraction, nb_means, nb_folds = nb.cv(train, b)
    vectorizer, pair_count = tf.fit(train)
    model, cutoffs, details = nb.make_config(train)
    assert vectorizer.vocabulary_ == model[0].vocabulary_
    np.testing.assert_array_equal(vectorizer.idf_, model[0].idf_)
    sources = ('tfidf_only.py', 'tfidf_nb.py', 'or_nb_hybrid.py', 'argument_audit.py', 'engine.py', 'vendor/coreference.py')
    result = {'schema_version': 1, 'annotation': annotation, 'train_sha256': checksum,
              'upstream_commit': COMMIT, 'fit_pairs': pair_count,
              'source_sha256': {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in sources},
              'reference_experiment_commits': {'tfidf_only': 'e454783', 'or_nb_hybrid': 'd180c92', 'tfidf_nb': '745d2fa'},
              'training_environment': {'python': sys.version, 'sklearn': sklearn.__version__, 'numpy': np.__version__, 'scipy': scipy.__version__},
              'text_selection': {'threshold': threshold, 'policy': policy, 'cv_mean_conll': means, 'folds': folds},
              'nb_selection': {'fraction': fraction, 'cutoff': cutoffs[fraction], 'cv_mean_conll': nb_means, 'folds': nb_folds},
              'tfidf': {'vocabulary': {k: int(v) for k, v in vectorizer.vocabulary_.items()}, 'idf': vectorizer.idf_.tolist()},
              'nb': {'bins': model[1].tolist(), 'category_count': model[2].category_count_[0].tolist(),
                     'class_count': model[2].class_count_.tolist(), 'alpha': 1.0, 'class_prior': [0.5, 0.5]},
              'fit': details}
    target.mkdir(parents=True, exist_ok=True)
    (target / (annotation + '.json')).write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.glob('ann*.json'))}
    (target / 'checksums.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {k: result[k] for k in ('annotation', 'train_sha256', 'fit_pairs')} | {'threshold': threshold, 'policy': policy, 'fraction': fraction}

if __name__ == '__main__':
    for name in ('ann1', 'ann2'):
        print(prepare(name))
