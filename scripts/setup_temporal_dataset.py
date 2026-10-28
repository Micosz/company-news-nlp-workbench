#!/usr/bin/env python3
"""Build the ECB+ / Event StoryLine option from verified sources, without TKGQA."""
import collections
import csv
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

from prepare_datasets import EXPECTED_HASHES, make_pairs, parse_ecb, split_topics, write_csv
from download_sources import URLS, HASHES
from download_research_sources import SOURCES
from build_story_time import build
import pandas as pd
from engine import builtin, validate

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'local_data' / 'temporal_sources'
OUTPUT = ROOT / 'local_data' / 'ecb_story_time'


def obtain(path, url, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'ไฟล์ต้นทาง SHA-256 ไม่ตรง: {path}')
        print('ตรวจแล้ว:', path, flush=True)
        return
    partial = path.with_suffix(path.suffix + '.part')
    print('กำลังดาวน์โหลด:', path.name, flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open('xb') as out:
            shutil.copyfileobj(response, out)
        data = partial.read_bytes()
        # The official CSV has also been served without its final LF. Accept
        # only that exact known variant, then restore the pinned byte sequence.
        if (path.name == 'ECBplus_coreference_sentences.csv' and
                hashlib.sha256(data).hexdigest() == 'afee49e0f5fe5084eec690e934aaade842d5eeff7a5704a36f59e7a49505f434'):
            data += b'\n'
            partial.write_bytes(data)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'ไฟล์ดาวน์โหลด SHA-256 ไม่ตรง: {partial}')
        partial.replace(path)
    except Exception:
        if partial.exists(): partial.unlink()
        raise


def build_mixed(full_root, story_dir, output_path):
    if output_path.exists():
        raise FileExistsError(f'มีชุด mixed อยู่แล้ว ไม่เขียนทับ: {output_path}')
    metadata = pd.read_csv(story_dir / 'ecb_story_mentions.csv', dtype=str, keep_default_na=False)
    if metadata.mention_id.duplicated().any(): raise ValueError('รหัส mention ที่มีเวลาซ้ำ')
    dates = metadata.set_index('mention_id')['event_date']
    old = os.environ.get('NLP_DATASET_ROOT')
    try:
        os.environ['NLP_DATASET_ROOT'] = str(full_root.resolve())
        frame = builtin('full')
    finally:
        if old is None: os.environ.pop('NLP_DATASET_ROOT', None)
        else: os.environ['NLP_DATASET_ROOT'] = old
    for side in ('a', 'b'):
        frame[f'event_date_{side}'] = frame[f'mention_{side}'].map(dates).fillna('')
    frame = validate(frame)
    complete = frame.event_date_a.ne('') & frame.event_date_b.ne('')
    selected = pd.read_csv(story_dir / 'ecb_story_pairs.csv', dtype=str, keep_default_na=False).set_index('pair_id')
    check = frame.loc[complete].set_index('pair_id')
    if set(check.index) != set(selected.index): raise ValueError('คู่วันครบไม่ตรงกับชุด StoryLine ที่ตรวจต้นฉบับแล้ว')
    for col in ('mention_a','mention_b','event_date_a','event_date_b','split','label'):
        if not check[col].astype(str).sort_index().equals(selected[col].astype(str).sort_index()):
            raise ValueError(f'คู่วันครบไม่ตรงกัน: {col}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', encoding='utf-8-sig', newline='') as out:
        frame.to_csv(out, index=False)
    summary = {}
    for split, part in frame.groupby('split'):
        a, b = part.event_date_a.ne(''), part.event_date_b.ne('')
        summary[split] = {'pairs':len(part), 'both':int((a & b).sum()),
                          'one':int((a ^ b).sum()), 'neither':int((~a & ~b).sum())}
    print('ชุด mixed แบ่งตามข้อมูลเวลา:', json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main():
    mixed = OUTPUT / 'ecb_story_mixed_pairs.csv'
    if mixed.exists():
        raise FileExistsError(f'มีชุด mixed อยู่แล้ว ไม่เขียนทับ: {mixed}')
    for relative in ('ecbplus/ECB+.zip', 'ecbplus/ECBplus_coreference_sentences.csv'):
        obtain(RAW / relative, URLS[relative], HASHES[relative])
    name = 'eventstoryline-46edefee.zip'
    obtain(RAW / name, *SOURCES[name])
    csv.field_size_limit(100_000_000)
    documents, mentions, _ = parse_ecb(RAW)
    splits = split_topics(documents)
    for row in documents + mentions: row['split'] = splits[row['topic_id']]
    context_splits = collections.defaultdict(set)
    for row in mentions: context_splits[row['context_normalized']].add(row['split'])
    contaminated = {text for text, found in context_splits.items() if len(found) > 1}
    pairs = make_pairs([row for row in mentions if row['context_normalized'] not in contaminated])
    with tempfile.TemporaryDirectory(prefix='ecb-story-') as temp:
        full_root = Path(temp)
        dataset = full_root / 'full' / 'ecbplus'
        write_csv(dataset / 'event_mentions.csv', mentions)
        write_csv(dataset / 'pairs.csv', pairs)
        story_dir = full_root / 'story'
        build(RAW / name, RAW / 'ecbplus/ECB+.zip', full_root, story_dir)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for filename in ('ecb_story_mentions.csv', 'ecb_story_pairs.csv', 'ecb_story_summary.json'):
            src, dst = story_dir / filename, OUTPUT / filename
            if dst.exists():
                if hashlib.sha256(src.read_bytes()).digest() != hashlib.sha256(dst.read_bytes()).digest():
                    raise ValueError(f'ไฟล์ชุดเวลาที่มีอยู่ไม่ตรงกับต้นทาง: {dst}')
            else:
                with dst.open('xb') as dest, src.open('rb') as source: shutil.copyfileobj(source, dest)
        build_mixed(full_root, story_dir, mixed)
    print('พร้อมใช้ในเว็บ: ชุดวันครบ และ Full + เวลาบางส่วน', flush=True)


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f'เตรียมข้อมูลไม่สำเร็จ: {exc}')
