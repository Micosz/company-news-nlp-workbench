#!/usr/bin/env python3
"""Build the ECB+ / Event StoryLine option from verified sources, without TKGQA."""
import collections
import csv
import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path

from prepare_datasets import EXPECTED_HASHES, make_pairs, parse_ecb, split_topics, write_csv
from download_sources import URLS, HASHES
from download_research_sources import SOURCES
from build_story_time import build

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


def main():
    if (OUTPUT / 'ecb_story_pairs.csv').exists():
        raise FileExistsError(f'มีชุดข้อมูลอยู่แล้ว ไม่เขียนทับ: {OUTPUT}')
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
        build(RAW / name, RAW / 'ecbplus/ECB+.zip', full_root, OUTPUT)
    print('พร้อมใช้ในเว็บ: ECB+ + Event StoryLine · มีวันกำกับ', flush=True)


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f'เตรียมข้อมูลไม่สำเร็จ: {exc}')
