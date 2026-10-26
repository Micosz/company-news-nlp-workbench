"""Custom pairwise baseline/ablation, NOT an implementation of CohTP.
Contract: run(train, test_inputs, config) -> models with score arrays in test row order.
Only train contains gold labels. Fixed thresholds; no test-label tuning.
"""
import html
import re
import unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', html.unescape(str(text)))).strip()


def canonical_role(text):
    # Case/space only. Use consistently annotated company IDs or names.
    # No automatic aliases, no label-derived company mapping.
    return normalize(text).casefold()


def role_features(frame):
    values = []
    for row in frame.to_dict('records'):
        ba, ta, bb, tb = [canonical_role(row.get(k, '')) for k in
                          ('buyer_a', 'target_a', 'buyer_b', 'target_b')]
        bk, tk = bool(ba and bb), bool(ta and tb)
        values.append([int(bk and ba == bb), int(tk and ta == tb),
                       int(bk and ba != bb), int(tk and ta != tb),
                       int(bk and tk and ba == tb and ta == bb),
                       int(bk), int(tk)])
    return np.asarray(values, dtype=float)


def run(train, test, config):
    seed = int(config['seed'])
    # Unique TRAIN contexts prevent repeated pairs from overweighting document IDF.
    corpus = list(dict.fromkeys(normalize(x) for col in ('text_a', 'text_b') for x in train[col]))
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                                 min_df=1, max_features=30000, norm='l2')
    vectorizer.fit(corpus)
    def cosine(frame):
        texts = list(dict.fromkeys(normalize(x) for col in ('text_a','text_b') for x in frame[col]))
        matrix = vectorizer.transform(texts)
        lookup = {t: i for i, t in enumerate(texts)}
        # Batch sparse indexing to avoid duplicating the full corpus for every pair.
        ia = [lookup[normalize(x)] for x in frame.text_a]
        ib = [lookup[normalize(x)] for x in frame.text_b]
        scores = []
        for start in range(0, len(frame), 1024):
            a = matrix[ia[start:start+1024]]
            b = matrix[ib[start:start+1024]]
            scores.extend(np.asarray(a.multiply(b).sum(axis=1)).ravel())
        return np.asarray(scores).reshape(-1, 1)
    x_train, x_test = cosine(train), cosine(test)
    y = train.label.to_numpy(dtype=int)
    def classify(a, b, names):
        scaler = StandardScaler().fit(a)
        clf = LogisticRegression(C=1.0, solver='liblinear', class_weight='balanced',
                                 random_state=seed, max_iter=1000)
        clf.fit(scaler.transform(a), y)
        return {'scores': clf.predict_proba(scaler.transform(b))[:, 1].tolist(),
                'threshold': 0.5, 'features': names,
                'fitted_parameters': {'coefficients': clf.coef_.tolist(),
                    'intercept': clf.intercept_.tolist(), 'scaler_mean': scaler.mean_.tolist(),
                    'scaler_scale': scaler.scale_.tolist(), 'classes': clf.classes_.tolist()}}
    models = {
        'majority_reference': {'scores': [float(np.mean(y) >= 0.5)] * len(test),
                               'threshold': 0.5, 'features': ['training_majority_class'],
                               'score_kind': 'constant_class'},
        'cosine_reference': {'scores': x_test[:,0].tolist(), 'threshold': 0.5,
                             'features': ['tfidf_cosine'], 'score_kind': 'similarity'},
        'text_baseline': classify(x_train, x_test, ['tfidf_cosine'])}
    warnings = []
    role_names = ['buyer_match', 'target_match', 'buyer_mismatch', 'target_mismatch',
                  'reversed_roles', 'buyer_both_known', 'target_both_known']
    r_train, r_test = role_features(train), role_features(test)
    coverage = {'train_complete_pairs': int(((r_train[:,-2:] == 1).all(axis=1)).sum()),
                'test_complete_pairs': int(((r_test[:,-2:] == 1).all(axis=1)).sum())}
    if all(coverage.values()) and config.get('role_source') in ('manual', 'predicted'):
        models['text_plus_roles'] = classify(np.hstack([x_train, r_train]),
                                             np.hstack([x_test, r_test]),
                                             ['tfidf_cosine'] + role_names)
        if config['role_source'] == 'manual':
            warnings.append('Manual/oracle role features: evaluates supplied roles, not an automatic extractor.')
        if coverage['train_complete_pairs'] < len(train) or coverage['test_complete_pairs'] < len(test):
            warnings.append('Role coverage is partial; missing-role indicators may influence predictions.')
    else:
        warnings.append('Role experiment skipped: annotate roles in both splits and declare manual or predicted source.')
    return {'models': models, 'warnings': warnings, 'role_coverage': coverage,
            'vectorizer': {'vocabulary': {k:int(v) for k,v in vectorizer.vocabulary_.items()},
                           'idf': vectorizer.idf_.tolist(), 'train_unique_contexts': len(corpus)},
            'method': 'TF-IDF word 1-2grams → cosine → Logistic Regression; ablation adds 7 role-compatibility features.'}
