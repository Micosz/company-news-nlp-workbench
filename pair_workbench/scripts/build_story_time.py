#!/usr/bin/env python3
"""Join ECB+ coreference pairs with Event StoryLine v1.0 date annotations.

This builds an exploratory oracle-time subset. It never derives coreference
labels from dates and does not redistribute source news text in the repository.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import builtin, validate  # noqa: E402
from scripts.prepare_datasets import EXPECTED_HASHES  # noqa: E402

STORY_COMMIT = '46edefee5e82e0917b823abe0a18bf8c7770f15c'
STORY_SHA = 'bb3574fc793fceb79e281ca182adf7a52890b5869ccbf4f2f28512d4272eff58'
STORY_PREFIX = f'EventStoryLine-{STORY_COMMIT}/annotated_data/v1.0/'


def check_hash(path, expected):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != expected:
        raise ValueError(f'SHA-256 ไม่ตรงกับ source version ที่ระบุ: {path}')


def build(story_zip, ecb_zip, full_root, output_dir):
    story_zip, ecb_zip, full_root, output_dir = map(Path, (story_zip, ecb_zip, full_root, output_dir))
    check_hash(story_zip, STORY_SHA)
    check_hash(ecb_zip, EXPECTED_HASHES['ecbplus/ECB+.zip'])
    files = [output_dir / x for x in ('ecb_story_mentions.csv', 'ecb_story_pairs.csv', 'ecb_story_summary.json')]
    if any(p.exists() or p.is_symlink() for p in files):
        raise FileExistsError('ไฟล์ปลายทางมีอยู่แล้ว โปรดเลือก output-dir ใหม่')
    full = full_root / 'full' / 'ecbplus'
    mentions = pd.read_csv(full / 'event_mentions.csv', dtype=str, keep_default_na=False)
    raw_pairs = pd.read_csv(full / 'pairs.csv', dtype=str, keep_default_na=False)
    if mentions.mention_id.duplicated().any(): raise ValueError('รหัส mention ของ ECB+ ซ้ำ')
    anchors = collections.defaultdict(list)
    for row in mentions.to_dict('records'):
        anchors[(row['document_id'], row['token_ids'])].append(row['mention_id'])
    candidates, counts = collections.defaultdict(list), collections.Counter()
    original_clusters = {}
    with zipfile.ZipFile(story_zip) as story, zipfile.ZipFile(ecb_zip) as ecb:
        names = sorted(x for x in story.namelist() if x.startswith(STORY_PREFIX)
                       and x.endswith('.xml.xml') and x[len(STORY_PREFIX):].split('/')[0].isdigit())
        for name in names:
            topic = name[len(STORY_PREFIX):].split('/')[0]
            original = Path(name).name[:-len('.xml.xml')]
            docid = 'ecbplus:' + original
            root = ET.fromstring(story.read(name))
            source = ET.fromstring(ecb.read(f'ECB+/{topic}/{original}.xml'))
            def token_map(tree):
                return {x.get('t_id'): (x.get('sentence'), x.get('number'), x.text or '')
                        for x in tree.findall('token')}
            if token_map(root) != token_map(source):
                raise ValueError(f'คำหรือตำแหน่ง token ของสองชุดไม่ตรงกัน: {docid}')
            original_marks = {x.get('m_id'): x for x in source.find('Markables')}
            original_relations = {}
            for relation in source.find('Relations'):
                if relation.tag == 'CROSS_DOC_COREF':
                    for entry in relation.findall('source'):
                        original_relations[entry.get('m_id')] = relation.get('note', '')
            marks = {x.get('m_id'): x for x in root.find('Markables')}
            for rel in root.find('Relations'):
                if rel.tag != 'TLINK' or rel.get('relType') != 'CONTAINS': continue
                src, dst = rel.find('source'), rel.find('target')
                if src is None or dst is None: continue
                time_mark, event_mark = marks.get(src.get('m_id')), marks.get(dst.get('m_id'))
                if time_mark is None or event_mark is None: continue
                if time_mark.tag != 'TIME_DATE' or not event_mark.tag.startswith(('ACTION', 'NEG_ACTION')): continue
                val = time_mark.get('value', '')
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', val): continue
                try: date.fromisoformat(val)
                except ValueError: counts['invalid_calendar_date'] += 1; continue
                modality = rel.get('contextualModality', '')
                if modality not in ('ACT', ''): continue
                token_ids = ','.join(x.get('t_id') for x in event_mark.findall('token_anchor'))
                matched = anchors.get((docid, token_ids), [])
                if len(matched) != 1:
                    counts['unmatched_or_ambiguous_token_span'] += 1
                    continue
                original_mid = matched[0].rsplit(':m', 1)[-1]
                original_event = original_marks.get(original_mid)
                if original_event is None or ','.join(x.get('t_id') for x in original_event.findall('token_anchor')) != token_ids:
                    raise ValueError(f'event mention ไม่ตรงกับ ECB+ ต้นฉบับ: {matched[0]}')
                original_note = original_relations.get(original_mid, '')
                original_clusters[matched[0]] = (f'ecbplus:{topic}:{original_note}' if original_note
                    else f'ecbplus:{topic}:singleton:{original}:{original_mid}')
                candidates[matched[0]].append({
                    'mention_id': matched[0], 'document_id': docid, 'token_ids': token_ids,
                    'event_date': val, 'story_event_id': event_mark.get('m_id'),
                    'story_time_id': time_mark.get('m_id'), 'story_tlink_id': rel.get('r_id'),
                    'relation': 'CONTAINS', 'modality': modality,
                    'time_is_document_creation_date': time_mark.get('DCT', ''),
                    'source_xml': name[len(STORY_PREFIX):],
                })
    records = []
    for mention_id, rows in sorted(candidates.items()):
        if len({r['event_date'] for r in rows}) != 1:
            counts['ambiguous_date_mentions'] += 1
            continue
        # Multiple annotations can support the same day; retain one stable source.
        records.append(sorted(rows, key=lambda x: (x['source_xml'], x['story_tlink_id']))[0])
    metadata = pd.DataFrame(records)
    if metadata.empty or metadata.mention_id.duplicated().any(): raise ValueError('ข้อมูลเวลาไม่ครบหรือ mention ซ้ำ')
    times = metadata.set_index('mention_id')['event_date']
    keep = raw_pairs.mention_id_a.isin(times.index) & raw_pairs.mention_id_b.isin(times.index)
    selected = raw_pairs[keep]
    # Preserve original project pairs, source labels and topic-grouped splits.
    # builtin() reads from NLP_DATASET_ROOT; make selection explicit and verify IDs.
    import os
    old = os.environ.get('NLP_DATASET_ROOT')
    try:
        os.environ['NLP_DATASET_ROOT'] = str(full_root.resolve())
        pairs = builtin('full')
    finally:
        if old is None: os.environ.pop('NLP_DATASET_ROOT', None)
        else: os.environ['NLP_DATASET_ROOT'] = old
    pairs = pairs[pairs.pair_id.isin(set(selected.pair_id))].copy()
    if set(pairs.pair_id) != set(selected.pair_id): raise ValueError('คู่ ECB+ ไม่ตรงกับต้นฉบับที่เตรียมไว้')
    for side in ('a', 'b'):
        pairs[f'event_date_{side}'] = pairs[f'mention_{side}'].map(times)
    valid = validate(pairs)
    original = selected.set_index('pair_id')['label_same_event'].astype(int)
    if any(int(r.label) != original.loc[r.pair_id] or
           int(r.label) != int(original_clusters[r.mention_a] == original_clusters[r.mention_b])
           for r in valid.itertuples()):
        raise ValueError('พบป้าย coreference เปลี่ยนจาก ECB+')
    labels = pairs.label.value_counts().to_dict()
    date_match = pairs.event_date_a == pairs.event_date_b
    summary = {
        'storyline_commit': STORY_COMMIT, 'storyline_sha256': STORY_SHA,
        'ecb_archive_sha256': EXPECTED_HASHES['ecbplus/ECB+.zip'],
        'matching': 'exact document ID plus unique event token-span; original token maps verified',
        'selection': 'TIME_DATE exact day, time CONTAINS event, ACT or unannotated modality; one unique day per mention',
        'note': 'Time labels are gold/oracle annotations; missing modality is unknown, not confirmed factual.',
        'news_documents_checked': len(names), 'dated_mentions': len(metadata),
        'dated_documents': int(metadata.document_id.nunique()),
        'topic_count': int(pairs.group_id.nunique()), 'pairs': len(pairs),
        'split_counts': pairs.split.value_counts().to_dict(), 'label_counts': labels,
        'date_match_vs_label': {f'{lab}_{same}': int(((pairs.label == lab) & (date_match == same)).sum())
                                for lab in ('0','1') for same in (True,False)},
        'exclusions': dict(counts),
        'limitations': ['Date links include document creation dates only when source annotates CONTAINS; not a blanket publication-date proxy.',
                        'A date disagreement is not automatically a different event; event identity labels remain those of ECB+.',
                        'Time feature is source-annotated oracle, not an automatically extracted date.',
                        'Only the complete-date subset is selected; results do not generalize to missing or implicit times.',
                        'Existing ECB+ pilot overlaps with full test; these splits are project-specific and already explored.',
                        'Event StoryLine overlaps ECB+; do not count the two as independent sets.'],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for data, path in ((metadata, files[0]), (pairs, files[1])):
        with path.open('x', encoding='utf-8-sig', newline='') as dest: data.to_csv(dest, index=False)
    with files[2].open('x', encoding='utf-8') as dest:
        json.dump(summary, dest, ensure_ascii=False, indent=2)
        dest.write('\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description='สร้างชุด ECB+ + Event StoryLine สำหรับทดลองเวลาที่รู้คำตอบแล้ว')
    p.add_argument('--story-zip', required=True, type=Path)
    p.add_argument('--ecb-zip', required=True, type=Path)
    p.add_argument('--full-root', required=True, type=Path, help='โฟลเดอร์ที่มี full/ecbplus')
    p.add_argument('--output-dir', required=True, type=Path)
    a = p.parse_args()
    try: build(a.story_zip, a.ecb_zip, a.full_root, a.output_dir)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        p.exit(2, f'สร้างข้อมูลไม่สำเร็จ: {exc}\n')


if __name__ == '__main__': main()
