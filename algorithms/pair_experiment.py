"""Custom pairwise baseline/ablation, NOT an implementation of CohTP.
Contract: run(train, test_inputs, config) -> models with score arrays in test row order.
Only train contains gold labels. Fixed thresholds; no test-label tuning.
"""
import html
import re
import unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import CategoricalNB


# Predeclared training-only tertiles. Each fitted edge is stored in the run.
COSINE_QUANTILES = (1.0 / 3.0, 2.0 / 3.0)


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', html.unescape(str(text)))).strip()


def canonical_role(text):
    # Case/space only. Use consistently annotated company IDs or names.
    # No automatic aliases, no label-derived company mapping.
    value = normalize(text).casefold()
    # Spreadsheet uploads can contain literal missing markers as strings.
    # Treat those as unknown, never as an agreeing company name.
    return '' if value in {'', 'unknown', 'n/a', 'none', 'null', 'nan', 'ไม่ทราบ', 'ไม่ระบุ', '-'} else value


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


def role_categories(frame):
    """0 = unknown, 1 = match/not-reversed, 2 = mismatch/reversed.

    Missing evidence never becomes a mismatch. Labels describe role agreement,
    not whether two news claims contradict each other.
    """
    values = []
    for row in frame.to_dict('records'):
        ba, ta, bb, tb = [canonical_role(row.get(k, '')) for k in
                          ('buyer_a', 'target_a', 'buyer_b', 'target_b')]
        def relation(a, b):
            return 0 if not a or not b else (1 if a == b else 2)
        reverse = 0 if not all((ba, ta, bb, tb)) else (2 if ba == tb and ta == bb else 1)
        values.append([relation(ba, bb), relation(ta, tb), reverse])
    return np.asarray(values, dtype=np.int64).reshape(-1, 3)


def time_categories(frame):
    """0 unknown, 1 same exact calendar day, 2 different exact calendar day.

    The category is a soft feature, never a rule asserting event identity.
    The caller must describe whether the dates are gold or predicted.
    """
    values = []
    for row in frame.to_dict('records'):
        a, b = str(row.get('event_date_a', '')).strip(), str(row.get('event_date_b', '')).strip()
        values.append([0 if not a or not b else (1 if a == b else 2)])
    return np.asarray(values, dtype=np.int64).reshape(-1, 1)


def run(train, test, config):
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
        # Round-off can produce 1 + epsilon for mathematically identical vectors.
        return np.clip(np.asarray(scores), 0.0, 1.0).reshape(-1, 1)
    cosine_train, cosine_test = cosine(train), cosine(test)
    # Keep the original continuous cosine for the simple reference only.
    # Deduplicate tied thresholds rather than invent bins absent in training.
    cosine_edges = np.unique(np.quantile(cosine_train.ravel(), COSINE_QUANTILES))
    x_train = np.digitize(cosine_train, cosine_edges).astype(np.int64)
    x_test = np.digitize(cosine_test, cosine_edges).astype(np.int64)
    y = train.label.to_numpy(dtype=int)
    def classify(a, b, names):
        # Explicitly reserve all 3 categories in every feature, even if a
        # category is absent in the training fold; additive smoothing handles it.
        clf = CategoricalNB(alpha=1.0, min_categories=3)
        clf.fit(a, y)
        return {'scores': clf.predict_proba(b)[:, 1].tolist(),
                'threshold': 0.5, 'features': names,
                'fitted_parameters': {'classifier': 'CategoricalNB', 'alpha': clf.alpha,
                    'min_categories': 3, 'cosine_cuts': cosine_edges.tolist(),
                    'classes': clf.classes_.tolist(), 'class_count': clf.class_count_.tolist(),
                    'class_log_prior': clf.class_log_prior_.tolist(),
                    'category_count': [x.tolist() for x in clf.category_count_],
                    'feature_log_prob': [x.tolist() for x in clf.feature_log_prob_]}}
    models = {
        'majority_reference': {'scores': [float(np.mean(y) >= 0.5)] * len(test),
                               'threshold': 0.5, 'features': ['training_majority_class'],
                               'score_kind': 'constant_class'},
        'cosine_reference': {'scores': cosine_test[:,0].tolist(), 'threshold': 0.5,
                             'features': ['tfidf_cosine'], 'score_kind': 'similarity'},
        'text_baseline': classify(x_train, x_test, ['tfidf_cosine_bin'])}
    warnings = []
    if len(np.unique(x_train)) < 3:
        warnings.append('Training cosine tertile bins have fewer than three populated categories because of ties.')
    role_names = ['buyer_relation', 'target_relation', 'role_reversed']
    r_train, r_test = role_categories(train), role_categories(test)
    coverage = {'train_complete_pairs': int((r_train[:,2] != 0).sum()),
                'test_complete_pairs': int((r_test[:,2] != 0).sum())}
    if all(coverage.values()) and config.get('role_source') in ('manual', 'predicted'):
        models['text_plus_roles'] = classify(np.hstack([x_train, r_train]),
                                             np.hstack([x_test, r_test]),
                                             ['tfidf_cosine_bin'] + role_names)
        if config['role_source'] == 'manual':
            warnings.append('Manual/oracle role features: evaluates supplied roles, not an automatic extractor.')
        if config['role_source'] == 'predicted':
            warnings.append('Predicted role features are supplied inputs; this run does not evaluate or verify their extraction.')
        if coverage['train_complete_pairs'] < len(train) or coverage['test_complete_pairs'] < len(test):
            warnings.append('Role coverage is partial; missing-role indicators may influence predictions.')
    else:
        warnings.append('Role experiment skipped: annotate roles in both splits and declare manual or predicted source.')
    t_train, t_test = time_categories(train), time_categories(test)
    time_coverage = {'train_complete_pairs': int((t_train[:,0] != 0).sum()),
                     'test_complete_pairs': int((t_test[:,0] != 0).sum())}
    if all(time_coverage.values()) and config.get('time_source') in ('oracle', 'predicted'):
        models['time_only'] = classify(t_train, t_test, ['event_day_relation'])
        models['text_plus_availability'] = classify(
            np.hstack([x_train, (t_train != 0).astype(np.int64)]),
            np.hstack([x_test, (t_test != 0).astype(np.int64)]),
            ['tfidf_cosine_bin', 'both_dates_available'])
        models['text_plus_time'] = classify(np.hstack([x_train, t_train]),
                                            np.hstack([x_test, t_test]),
                                            ['tfidf_cosine_bin', 'event_day_relation'])
        if config['time_source'] == 'oracle':
            warnings.append('Oracle event dates are supplied gold annotations; this does not evaluate automatic time extraction.')
        else:
            warnings.append('Predicted event dates are supplied inputs; this does not evaluate or verify time extraction.')
        if time_coverage['train_complete_pairs'] < len(train) or time_coverage['test_complete_pairs'] < len(test):
            warnings.append('Time coverage is partial; missingness may influence predictions. Compare Text + availability with Text + event date before attributing gains to dates.')
    else:
        warnings.append('Time experiment skipped: provide dates in both splits and declare oracle or predicted time source.')
    joint_coverage = {
        'train_complete_pairs': int(((r_train[:, 2] != 0) & (t_train[:, 0] != 0)).sum()),
        'test_complete_pairs': int(((r_test[:, 2] != 0) & (t_test[:, 0] != 0)).sum()),
    }
    joint_enabled = (config.get('joint_enabled', True) and 'text_plus_roles' in models and 'text_plus_time' in models
                     and all(joint_coverage.values()))
    if joint_enabled:
        models['text_plus_roles_availability'] = classify(
            np.hstack([x_train, r_train, (t_train != 0).astype(np.int64)]),
            np.hstack([x_test, r_test, (t_test != 0).astype(np.int64)]),
            ['tfidf_cosine_bin'] + role_names + ['both_dates_available'])
        models['text_plus_roles_time'] = classify(
            np.hstack([x_train, r_train, t_train]), np.hstack([x_test, r_test, t_test]),
            ['tfidf_cosine_bin'] + role_names + ['event_day_relation'])
        warnings.append('Joint role/time coverage may be sparse or correlated with topic/labels; results are exploratory and do not evaluate extraction.')
    elif config.get('joint_enabled', True):
        warnings.append('Joint role/time experiment skipped: need declared sources and at least one pair with complete roles and dates in both train and test.')
    return {'models': models, 'warnings': warnings, 'role_coverage': coverage,
            'time_coverage': time_coverage, 'joint_coverage': joint_coverage,
            'vectorizer': {'vocabulary': {k:int(v) for k,v in vectorizer.vocabulary_.items()},
                           'idf': vectorizer.idf_.tolist(), 'train_unique_contexts': len(corpus),
                           'cosine_bin_edges': cosine_edges.tolist(),
                           'cosine_bin_quantiles': list(COSINE_QUANTILES),
                           'category_codes': {'role_relation': {'unknown': 0, 'match': 1, 'mismatch': 2},
                                              'role_reversed': {'unknown': 0, 'no': 1, 'yes': 2}}},
            'method': 'TF-IDF word 1-2grams → training-only cosine tertile bins → Categorical Naive Bayes; ablations add buyer/target roles, event-day relation, or both when supplied.'}
