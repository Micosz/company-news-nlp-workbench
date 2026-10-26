#!/usr/bin/env python3
"""Prepare frozen public ECB+ and TKGQA files without inventing coreference labels.

Python 3.10+, standard library only. Source files are data, never executable code.
"""
import argparse
import collections
import csv
import hashlib
import html
import itertools
import json
import random
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SEED = 374
ANCHORS = {
    '43ecb': ('AMD / ATI', 'ACT17774320253942795'),
    '43ecbplus': ('AMD / SeaMicro', 'ACT17773499018825369'),
    '44ecb': ('HP / EDS', 'ACT18222897859726438'),
    '44ecbplus': ('HP / EYP Mission Critical Facilities', 'ACT18185002852018286'),
}
EXPECTED_HASHES = {
    'ecbplus/ECB+.zip': 'fe6ac2d76d8f7015f773ccc969927d7f3c33b331ed643b71efe31f28373eca90',
    'tkgqa/new_sentence_df_0509.csv': '2ab8adb301a33f55b471511a45c7dab6ac1ce00051be3a48b07b93449a7f0e27',
    'tkgqa/sentence_df_articleId_to_url.csv': 'd50ded9961e9e0cb2269982533a0546a69ef22bea981f798c03e8e0414c1a3f2',
}


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', html.unescape(text))).strip()


def write_csv(path, rows, fields=None):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        if not rows:
            raise ValueError(f'No schema for empty table {path}')
        fields = list(rows[0])
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def parse_ecb(source):
    selected = collections.defaultdict(set)
    for row in read_csv(source / 'ecbplus/ECBplus_coreference_sentences.csv'):
        selected[row['Topic'] + '_' + row['File']].add(row['Sentence Number'])
    documents, mentions, exclusions = [], [], []
    with zipfile.ZipFile(source / 'ecbplus/ECB+.zip') as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith('.xml') or name.startswith('__MACOSX/'):
                continue
            root = ET.fromstring(archive.read(name))
            original_id = Path(name).stem
            topic = int(original_id.split('_')[0])
            subtopic = str(topic) + ('ecbplus' if original_id.endswith('plus') else 'ecb')
            document_id = 'ecbplus:' + original_id
            tokens = {t.attrib['t_id']: t for t in root.findall('token')}
            sentences = collections.defaultdict(list)
            for token in tokens.values():
                sentences[token.attrib['sentence']].append(token.text or '')
            marks = {m.attrib['m_id']: m for m in root.find('Markables')}
            clusters = {}
            # Original CROSS_DOC_COREF note identifies the actual event instance.
            for relation in root.find('Relations'):
                if relation.tag == 'CROSS_DOC_COREF':
                    for item in relation.findall('source'):
                        clusters[item.attrib['m_id']] = relation.attrib['note']
            content_ids = [s for s in sorted(sentences, key=int)
                           if not (original_id.endswith('plus') and s == '0')]
            text_raw = '\n'.join(' '.join(sentences[s]) for s in content_ids)
            documents.append({
                'document_id': document_id, 'source_document_id': original_id,
                'source_dataset': 'ECB+', 'topic_id': topic, 'source_subtopic': subtopic,
                'is_mna_topic': int(subtopic in ANCHORS), 'text_raw': text_raw,
                'text_normalized': normalize(text_raw),
                'source_url_tokenized': ' '.join(sentences.get('0', [])) if original_id.endswith('plus') else '',
                'selected_sentence_ids': ','.join(sorted(selected[original_id], key=int)),
            })
            for mid, mark in marks.items():
                if not mark.tag.startswith(('ACTION', 'NEG_ACTION')):
                    continue
                anchors = [tokens[a.attrib['t_id']] for a in mark.findall('token_anchor')]
                if not anchors:
                    continue  # Event-instance descriptors have no text anchor.
                sentence_ids = {a.attrib['sentence'] for a in anchors}
                if not sentence_ids.issubset(selected[original_id]):
                    exclusions.append({'document_id': document_id, 'source_mention_id': mid,
                                       'reason': 'outside_official_selected_sentences'})
                    continue
                source_cluster = clusters.get(mid, '')
                cluster = (f'ecbplus:{topic}:{source_cluster}' if source_cluster else
                           f'ecbplus:{topic}:singleton:{original_id}:{mid}')
                # Only cross-document pairs are produced; a local singleton cannot
                # create a positive relation to a different document.
                available = [int(s) for s in content_ids]
                context_ids = [str(s) for s in available
                               if min(map(int, sentence_ids)) - 1 <= s <= max(map(int, sentence_ids)) + 1]
                context_raw = '\n'.join(' '.join(sentences[s]) for s in context_ids)
                focal = subtopic in ANCHORS and source_cluster == ANCHORS[subtopic][1]
                mentions.append({
                    'mention_id': f'{document_id}:m{mid}', 'document_id': document_id,
                    'source_mention_id': mid, 'topic_id': topic, 'source_subtopic': subtopic,
                    'sentence_ids': ','.join(sorted(sentence_ids, key=int)),
                    'token_ids': ','.join(a.attrib['t_id'] for a in anchors),
                    'event_type': mark.tag, 'trigger': ' '.join(a.text or '' for a in anchors),
                    'context_raw': context_raw, 'context_normalized': normalize(context_raw),
                    'gold_event_cluster': cluster,
                    'gold_cluster_kind': 'cross_document' if source_cluster else 'document_local_singleton',
                    'is_mna_focal_event': int(focal),
                })
    return documents, mentions, exclusions


def split_topics(documents):
    topics = sorted({r['topic_id'] for r in documents})
    random.Random(SEED).shuffle(topics)
    n = len(topics)
    train_end, dev_end = int(n * .7), int(n * .7) + int(n * .15)
    return {t: 'train' if i < train_end else 'dev' if i < dev_end else 'test'
            for i, t in enumerate(topics)}


def make_pairs(mentions, ratio=3, keep_all=False):
    grouped = collections.defaultdict(list)
    for row in mentions:
        grouped[row['topic_id']].append(row)
    pairs = []
    for topic, group in sorted(grouped.items()):
        positives, negatives = [], []
        for left, right in itertools.combinations(group, 2):
            if left['document_id'] == right['document_id']:
                continue
            label = int(left['gold_event_cluster'] == right['gold_event_cluster'])
            (positives if label else negatives).append((left, right, label))
        rng = random.Random(SEED + int(topic))
        if not keep_all:
            # Fixed negative sampling; the resulting ratio is not news prevalence.
            negatives = rng.sample(negatives, min(len(negatives), ratio * len(positives)))
        candidates = positives + negatives
        rng.shuffle(candidates)
        for left, right, label in candidates:
            pairs.append({'pair_id': f'ecbpair:{topic}:{len(pairs):07d}',
                          'mention_id_a': left['mention_id'], 'mention_id_b': right['mention_id'],
                          'document_id_a': left['document_id'], 'document_id_b': right['document_id'],
                          'topic_id': topic, 'label_same_event': label,
                          'split': left.get('split', 'pilot_only'),
                          'label_origin': 'original_ECB+_event_coreference'})
    return pairs


def tkg_records(source):
    url_rows = read_csv(source / 'tkgqa/sentence_df_articleId_to_url.csv')
    url_sets = collections.defaultdict(set)
    for row in url_rows:
        url_sets[row['article_id']].add(row['url'])
    if any(len(values) != 1 for values in url_sets.values()):
        raise ValueError('Conflicting URLs for one TKGQA source article ID')
    urls = {key: next(iter(values)) for key, values in url_sets.items()}
    records = []
    for i, row in enumerate(read_csv(source / 'tkgqa/new_sentence_df_0509.csv'), 1):
        aid = row['article_id'].removesuffix('.0')
        records.append({
            'record_id': f'tkgqa:s{i:06d}', 'document_id': f'tkgqa:article:{aid}',
            'source_article_id': aid, 'text_raw': row['sentences'],
            'text_normalized': normalize(row['sentences']),
            'text_grain': 'selected_sentence_or_excerpt',
            'published_at_source': row['publishedAt'], 'source_url': urls.get(row['article_id'], ''),
            'source_buyer': row['lowered_head'], 'source_target': row['lowered_tail'],
            'source_stage': row['relation'], 'source_mentions_serialized': row['mentions'],
            'candidate_company_pair': row['final_company_deal'],
            'role_label_status': 'source_annotation_mixed_human_and_model;not_independently_reviewed',
            'gold_event_cluster': '', 'coreference_label_status': 'not_provided',
        })
    return records


def make_review_queue(records):
    by_pair, by_buyer = collections.defaultdict(list), collections.defaultdict(list)
    for row in records:
        by_pair[row['candidate_company_pair']].append(row)
        by_buyer[row['source_buyer']].append(row)
    candidates = {}
    for group in by_pair.values():
        for a, b in itertools.combinations(group, 2):
            if a['document_id'] != b['document_id']:
                candidates[tuple(sorted((a['record_id'], b['record_id'])))] = (a, b, 'same_source_company_pair;not_a_label')
    extra = []
    rng = random.Random(SEED)
    for group in by_buyer.values():
        # Bound the review queue, not the available raw data.
        shuffled = list(group)
        rng.shuffle(shuffled)
        for a, b in zip(shuffled, shuffled[1:]):
            if a['document_id'] != b['document_id'] and a['source_target'] != b['source_target']:
                extra.append((a, b, 'same_source_buyer_different_target;not_a_label'))
    rng.shuffle(extra)
    for a, b, reason in extra[:300]:
        candidates.setdefault(tuple(sorted((a['record_id'], b['record_id']))), (a, b, reason))
    rows = []
    for i, (a, b, reason) in enumerate(candidates.values(), 1):
        rows.append({'review_pair_id': f'tkg_review:{i:05d}', 'record_id_a': a['record_id'],
                     'record_id_b': b['record_id'], 'document_id_a': a['document_id'],
                     'document_id_b': b['document_id'], 'text_a': a['text_raw'], 'text_b': b['text_raw'],
                     'url_a': a['source_url'], 'url_b': b['source_url'], 'candidate_reason': reason,
                     'label_same_event': '', 'label_same_deal': '', 'annotator': '',
                     'evidence_and_reason': '', 'review_status': 'pending'})
    return rows


def annotation_template(docs, primary):
    focal = {m['document_id']: m for m in primary}
    return [{'document_id': d['document_id'],
             'focal_mention_id': focal[d['document_id']]['mention_id'],
             'focal_trigger': focal[d['document_id']]['trigger'],
             'focal_context': focal[d['document_id']]['context_raw'],
             'text': d['text_raw'], 'buyer': '', 'target': '',
             'buyer_evidence': '', 'target_evidence': '', 'annotator': '', 'review_status': 'pending'}
            for d in docs]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source_root.resolve(), args.output_root.resolve()
    csv.field_size_limit(100_000_000)
    for rel, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256((source / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Source changed: {rel}; inspect before rebuilding')
    full, small = output / 'full', output / 'small'
    documents, mentions, exclusions = parse_ecb(source)
    topic_splits = split_topics(documents)
    for row in documents + mentions:
        row['split'] = topic_splits[row['topic_id']]
    # Prevent exact model-input context from appearing in different splits.
    context_splits = collections.defaultdict(set)
    for row in mentions:
        context_splits[row['context_normalized']].add(row['split'])
    contaminated = {text for text, splits in context_splits.items() if len(splits) > 1}
    pair_mentions = [m for m in mentions if m['context_normalized'] not in contaminated]
    full_pairs = make_pairs(pair_mentions)
    records = tkg_records(source)
    review = make_review_queue(records)
    focal = [dict(m, split='pilot_only') for m in mentions if m['is_mna_focal_event']]
    by_document = collections.defaultdict(list)
    for row in focal:
        by_document[row['document_id']].append(row)
    # One original gold acquisition mention per document gives a simple pilot.
    primary = [sorted(group, key=lambda r: int(r['source_mention_id']))[0]
               for _, group in sorted(by_document.items())]
    # Pilot pairs deliberately cross the two deals of each buyer/topic. They
    # include difficult negatives rather than trivial AMD-versus-HP negatives.
    small_pairs = make_pairs(primary, keep_all=True)
    small_docs = [dict(d, split='pilot_only') for d in documents if d['document_id'] in by_document]
    write_csv(full / 'ecbplus/documents.csv', documents)
    write_jsonl(full / 'ecbplus/documents.jsonl', documents)
    write_csv(full / 'ecbplus/event_mentions.csv', mentions)
    write_csv(full / 'ecbplus/pairs.csv', full_pairs)
    write_csv(full / 'ecbplus/excluded_mentions.csv', exclusions)
    write_json(full / 'ecbplus/topic_split.json', {
        'type': 'custom_topic_holdout;not_the_official_paper_split', 'seed': SEED,
        'topics': topic_splits,
        'context_values_excluded_from_pairs_for_cross_split_duplication': len(contaminated),
    })
    write_csv(full / 'tkgqa/records.csv', records)
    write_jsonl(full / 'tkgqa/records.jsonl', records)
    write_csv(full / 'tkgqa/pairs_to_annotate.csv', review)
    write_csv(small / 'documents.csv', small_docs)
    write_jsonl(small / 'documents.jsonl', small_docs)
    write_csv(small / 'event_mentions.csv', primary)
    write_csv(small / 'all_focal_event_mentions.csv', focal)
    write_csv(small / 'pairs.csv', small_pairs)
    roles = annotation_template(small_docs, primary)
    write_csv(small / 'roles_to_annotate.csv', roles)
    write_csv(full / 'finance_pilot_roles_to_annotate.csv', roles)
    folds = [{'document_id': d['document_id'], 'topic_id': d['topic_id'],
              'fold_A': 'train' if d['topic_id'] == 43 else 'test',
              'fold_B': 'test' if d['topic_id'] == 43 else 'train'} for d in small_docs]
    write_csv(small / 'pilot_two_fold_assignments.csv', folds)
    for package in (full, small):
        for name in ('LICENSEDATA.TXT', 'COPYING-CC.TXT', 'SOURCE_README.txt'):
            dest = package / 'licenses/ecbplus' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / 'ecbplus' / name, dest)
    for src in [*EXPECTED_HASHES, 'ecbplus/ECBplus_coreference_sentences.csv',
                'ecbplus/LICENSEDATA.TXT', 'ecbplus/COPYING-CC.TXT', 'ecbplus/SOURCE_README.txt']:
        dest = full / 'raw' / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / src, dest)
    stats = {
        'prepared_on': '2026-10-26', 'seed': SEED,
        'full': {'ecbplus_documents': len(documents), 'ecbplus_selected_event_mentions': len(mentions),
                 'ecbplus_topics': len(topic_splits), 'ecbplus_pairs': len(full_pairs),
                 'pair_labels': dict(collections.Counter(r['label_same_event'] for r in full_pairs)),
                 'pairs_by_split': dict(collections.Counter(r['split'] for r in full_pairs)),
                 'tkgqa_records': len(records), 'tkgqa_unique_articles': len({r['document_id'] for r in records}),
                 'tkgqa_pending_review_pairs': len(review)},
        'small': {'documents': len(small_docs), 'primary_event_mentions': len(primary),
                  'focal_event_mentions': len(focal), 'focal_event_clusters': len({r['gold_event_cluster'] for r in primary}),
                  'pairs': len(small_pairs), 'pair_labels': dict(collections.Counter(r['label_same_event'] for r in small_pairs)),
                  'groups': dict(collections.Counter(r['source_subtopic'] for r in small_docs)),
                  'purpose': 'pipeline_pilot;not_sufficient_for_conclusive_finance_improvement'},
        'sources': {
            'ecbplus': {'url': 'https://github.com/cltl/ecbPlus',
                        'download': 'https://raw.githubusercontent.com/cltl/ecbPlus/master/ECB%2B_LREC2014/ECB%2B.zip',
                        'citation': 'Cybulska and Vossen (2014), Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution.',
                        'annotation_license': 'CC BY 3.0; original news copyright is separate'},
            'tkgqa': {'url': 'https://osf.io/xqwa4/', 'paper': 'https://doi.org/10.3390/data8030061',
                      'csv_download': 'https://osf.io/download/y65b9/',
                      'url_mapping_download': 'https://osf.io/download/swrn9/',
                      'citation': 'Ong, Sun, Serban and Guo (2023), TKGQA Dataset: Using Question Answering to Guide and Validate the Evolution of Temporal Knowledge Graph.',
                      'dataset_license_as_stated_by_authors': 'CC BY 4.0'}},
        'source_sha256': EXPECTED_HASHES,
        'not_downloaded': 'Large TKGQA temporal-graph pickle files are unnecessary for this task; no pickle is loaded.',
        'label_boundaries': [
            'ECB+ coreference labels come from original event IDs, not buyer/target agreement.',
            'TKGQA source roles/stages include model predictions and are not independent coreference gold.',
            'No buyer-target labels were invented; roles_to_annotate.csv intentionally contains blanks.',
            'Full ECB+ is mixed-domain; the finance subset still has only four focal deal groups.',
            'Small pairs are within the same buyer/topic; cross-topic easy negatives are omitted.',
            'All train/dev/test assignments in full are custom topic-grouped splits, not published benchmark splits.',
        ],
    }
    write_json(output / 'dataset_summary.json', stats)
    for package in (full, small):
        write_json(package / 'dataset_summary.json', stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
