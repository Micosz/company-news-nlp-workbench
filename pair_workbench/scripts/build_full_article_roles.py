#!/usr/bin/env python3
"""Build locally sourced Pilot article-context pairs with provisional AI roles.

The original ECB+ archive is not downloaded or redistributed by this script.
It is verified against the pinned upstream digest before any articles are read.
"""
import argparse
import collections
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import builtin, csv_rows, validate  # noqa: E402
from scripts.prepare_datasets import EXPECTED_HASHES, normalize  # noqa: E402

DEFAULT_ROLES = ROOT / 'data/pilot/pilot_roles_ai_provisional.csv'
EXPECTED_SHA256 = EXPECTED_HASHES['ecbplus/ECB+.zip']


def load_roles(path):
    roles = pd.read_csv(path, dtype=str, keep_default_na=False).fillna('')
    needed = {'mention_id', 'buyer', 'target', 'buyer_evidence_start', 'buyer_evidence_end',
              'target_evidence_start', 'target_evidence_end', 'document_sha256', 'provenance'}
    if not needed.issubset(roles.columns):
        raise ValueError('ไฟล์บทบาทต้องมี mention_id, buyer, target, ตำแหน่งหลักฐาน, checksum และที่มา')
    optional = [c for c in ('buyer_evidence_start','buyer_evidence_end',
                             'target_evidence_start','target_evidence_end','document_sha256','provenance')
                if c in roles.columns]
    roles = roles[['mention_id', 'buyer', 'target'] + optional].copy()
    for column in roles:
        roles[column] = roles[column].str.strip()
    if (roles['mention_id'] == '').any() or roles['mention_id'].duplicated().any():
        raise ValueError('mention_id ต้องไม่ว่างและไม่ซ้ำ')
    if (roles[['buyer', 'target']] == '').any().any():
        raise ValueError('ข้อมูลบทบาทชุดนี้ยังไม่ครบ: เว้นว่างไว้และตรวจหลักฐานก่อนใช้ชุดสมบูรณ์')
    return roles.set_index('mention_id')


def load_articles(source_zip, doc_ids):
    sha256 = hashlib.sha256()
    with source_zip.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha256.update(chunk)
    if sha256.hexdigest() != EXPECTED_SHA256:
        raise ValueError('SHA-256 ของ ECB+.zip ไม่ตรงกับแหล่งข้อมูลที่ตรึงไว้ หยุดสร้างไฟล์')

    # Reproduce prepare_datasets.parse_ecb's token/sentence assembly and URL
    # exclusion. Only read XML in memory; never extract untrusted ZIP paths.
    articles = {}
    with zipfile.ZipFile(source_zip) as archive:
        for name in archive.namelist():
            if not name.endswith('.xml') or name.startswith('__MACOSX/'):
                continue
            original_id = Path(name).stem
            doc_id = 'ecbplus:' + original_id
            if doc_id not in doc_ids:
                continue
            if doc_id in articles:
                raise ValueError(f'พบเอกสารซ้ำใน archive: {doc_id}')
            tree = ET.fromstring(archive.read(name))
            tokens = {t.attrib['t_id']: t for t in tree.findall('token')}
            sentences = collections.defaultdict(list)
            for token in tokens.values():
                sentences[token.attrib['sentence']].append(token.text or '')
            sentence_ids = [s for s in sorted(sentences, key=int)
                            if not (original_id.endswith('plus') and s == '0')]
            articles[doc_id] = normalize('\n'.join(' '.join(sentences[s]) for s in sentence_ids))
            if not articles[doc_id]:
                raise ValueError(f'เอกสารไม่มีข้อความ: {doc_id}')
    if set(articles) != doc_ids:
        raise ValueError('ไม่พบเอกสาร Pilot ใน archive: ' + ', '.join(sorted(doc_ids - set(articles))))
    return articles


def build(source_zip, output_dir, roles_path=DEFAULT_ROLES):
    roles = load_roles(roles_path)
    folds = {fold: builtin('small_' + fold) for fold in ('A', 'B')}
    mention_ids = set(folds['A']['mention_a']) | set(folds['A']['mention_b'])
    if set(roles.index) != mention_ids:
        raise ValueError('รหัส mention ของข้อมูลบทบาทไม่ตรงกับข้อมูล Pilot')
    doc_ids = set(folds['A']['doc_a']) | set(folds['A']['doc_b'])
    articles = load_articles(Path(source_zip).expanduser(), doc_ids)

    # A checksum identifies the source article used when the role was proposed;
    # offsets locate its supporting passage without redistributing full news.
    # Bounds/checksums do not establish that an AI interpretation is correct.
    evidence_cols = {'buyer_evidence_start', 'buyer_evidence_end',
                     'target_evidence_start', 'target_evidence_end'}
    if evidence_cols & set(roles.columns) and not evidence_cols.issubset(roles.columns):
        raise ValueError('คอลัมน์ตำแหน่งหลักฐานไม่ครบ')
    for mention_id, record in roles.iterrows():
        doc = ':'.join(mention_id.split(':')[:2])
        article = articles[doc]
        if 'document_sha256' in roles.columns:
            actual = hashlib.sha256(article.encode('utf-8')).hexdigest()
            if actual != record['document_sha256']:
                raise ValueError(f'ข้อความต้นฉบับไม่ตรงกับหลักฐาน: {mention_id}')
        if evidence_cols.issubset(roles.columns):
            for role in ('buyer', 'target'):
                try:
                    start = int(record[f'{role}_evidence_start'])
                    end = int(record[f'{role}_evidence_end'])
                except ValueError as exc:
                    raise ValueError(f'ตำแหน่งหลักฐานไม่ถูกต้อง: {mention_id}') from exc
                if not 0 <= start < end <= len(article):
                    raise ValueError(f'ตำแหน่งหลักฐานอยู่นอกเอกสาร: {mention_id}')

    output_dir = Path(output_dir).expanduser()
    targets = {fold: output_dir / f'pilot_{fold}_AI_FULL_ARTICLE_REVIEW_PENDING.csv' for fold in folds}
    evidence_path = output_dir / 'pilot_roles_AI_ARTICLE_EVIDENCE_REVIEW_PENDING.csv'
    if any(path.exists() or path.is_symlink() for path in [*targets.values(), evidence_path]):
        raise FileExistsError('ไฟล์ปลายทางมีอยู่แล้ว กรุณาเลือก --output-dir ใหม่เพื่อไม่เขียนทับ')

    # Complete all validation before writing either file.
    for fold, frame in folds.items():
        for side in ('a', 'b'):
            for role in ('buyer', 'target'):
                frame[f'{role}_{side}'] = frame[f'mention_{side}'].map(roles[role])
            frame[f'text_{side}'] = [
                f'Event context: {context}\n\nFull article: {articles[doc]}'
                for context, doc in zip(frame[f'text_{side}'], frame[f'doc_{side}'])
            ]
        if frame[['buyer_a','target_a','buyer_b','target_b']].isna().any().any():
            raise ValueError(f'มี mention ที่ไม่พบข้อมูลบทบาทใน Pilot {fold}')
        validate(frame)

    contexts = {row['mention_id']: row['context_normalized']
                for row in csv_rows(ROOT / 'data/pilot/event_mentions.csv')}
    if set(contexts) != mention_ids:
        raise ValueError('รหัส mention ของข้อความต้นฉบับไม่ตรงกับข้อมูล Pilot')
    evidence_rows = []
    for mention_id, record in roles.iterrows():
        doc = ':'.join(mention_id.split(':')[:2])
        article = articles[doc]
        evidence_rows.append({
            'mention_id': mention_id, 'context': contexts[mention_id],
            'buyer': record['buyer'],
            'buyer_evidence': article[int(record['buyer_evidence_start']):int(record['buyer_evidence_end'])],
            'target': record['target'],
            'target_evidence': article[int(record['target_evidence_start']):int(record['target_evidence_end'])],
            'annotator': 'AI-assisted annotation; human review pending',
            'notes': 'Evidence from the same ECB+ article; AI interpretation not human-verified.',
            'source_document_id': doc, 'document_sha256': record['document_sha256'],
            'provenance': record['provenance'],
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    for fold, frame in folds.items():
        # Exclusive creation also prevents accidental overwrites if files appear
        # after the pre-check. Preserve original labels and train/test splits.
        with targets[fold].open('x', encoding='utf-8-sig', newline='') as dest:
            frame.to_csv(dest, index=False)
        counts = frame['split'].value_counts().to_dict()
        print(f'Pilot {fold}: {targets[fold]} ({len(frame)} คู่; {counts})')
    with evidence_path.open('x', encoding='utf-8-sig', newline='') as dest:
        pd.DataFrame(evidence_rows).to_csv(dest, index=False)
    print(f'หลักฐานบทบาท: {evidence_path} ({len(evidence_rows)} ข้อความ)')
    print('บทบาทสร้างโดย AI และยังรอคนตรวจ; เลือก predicted และบันทึกที่มาเมื่อรัน')


def main():
    parser = argparse.ArgumentParser(description='สร้าง Pilot แบบข่าวเต็มจาก ECB+ ที่ผู้ใช้จัดหาเอง')
    parser.add_argument('--source-zip', required=True, type=Path, help='ไฟล์ ECB+.zip ต้นฉบับ')
    parser.add_argument('--output-dir', default=ROOT / 'local_data', type=Path, help='โฟลเดอร์ผลลัพธ์; ไม่เขียนทับ')
    args = parser.parse_args()
    try:
        build(args.source_zip, args.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.exit(2, f'สร้างข้อมูลไม่สำเร็จ: {exc}\n')


if __name__ == '__main__':
    main()
