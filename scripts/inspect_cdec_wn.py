#!/usr/bin/env python3
"""Inspect CDEC-WN release without turning unlabeled pairs into negatives."""
import argparse
import collections
import csv
import hashlib
import json
import tarfile
from pathlib import Path

EXPECTED = '7d5b1790145fc0603913aa24b60ce1bd8104196191289363fb6e2eb73c8d346d'
PREFIX = 'cdec-wn-dataset/'


def build(archive_path, output_dir):
    archive_path, output_dir = Path(archive_path), Path(output_dir)
    h=hashlib.sha256()
    with archive_path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''): h.update(block)
    if h.hexdigest()!=EXPECTED: raise ValueError('SHA-256 ของ CDEC-WN ไม่ตรงกับ release ที่ตรวจไว้')
    dest=output_dir/'cdec_positive_pairs.csv'; summary_path=output_dir/'cdec_summary.json'
    if any(p.exists() or p.is_symlink() for p in (dest,summary_path)): raise FileExistsError('ไฟล์ปลายทางมีอยู่แล้ว')
    doc_group={}
    with tarfile.open(archive_path,'r:gz') as archive:
        def read(name):
            member=archive.getmember(PREFIX+name)
            if not member.isfile(): raise ValueError('archive entry is not a regular file')
            return archive.extractfile(member).read()
        for split in ('train','test'):
            lines=read(f'dataset_splits/{split}_subtopics.txt').decode('utf-8').splitlines()
            for i,line in enumerate(lines):
                for doc in line.split():
                    if doc in doc_group: raise ValueError('source document repeated across subtopics')
                    doc_group[doc]=(split,f'{split}_{i:03d}')
        items=json.loads(read('dataset_labels/coref_pairs.json'))
    rows=[]
    for i, item in enumerate(items):
        spans, sentences=item['mention_spans'],item['sentences']
        a,b=str(spans[0][0]),str(spans[1][0])
        if a not in doc_group or b not in doc_group or doc_group[a]!=doc_group[b]:
            raise ValueError('cross-split or unknown source document')
        if item.get('label')!='coreference' or item.get('fine_grained_label') not in ('full','partial'):
            raise ValueError('unexpected source annotation')
        rows.append({'source_pair_id':f'cdecwn:{i:06d}', 'split':doc_group[a][0],
                     'source_subtopic':doc_group[a][1], 'doc_a':a, 'doc_b':b,
                     'mention_a_start':spans[0][1], 'mention_a_end':spans[0][2],
                     'mention_b_start':spans[1][1], 'mention_b_end':spans[1][2],
                     'sentence_a':sentences[0], 'sentence_b':sentences[1],
                     'source_label':'coreference', 'source_fine_grained_label':item['fine_grained_label']})
    output_dir.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'archive_sha256':EXPECTED,'source':'https://github.com/adithya7/cdec-wikinews',
             'documents':len(doc_group),'positive_pairs_only':len(rows),
             'split_counts':dict(collections.Counter(x['split'] for x in rows)),
             'source_fine_grained_labels':dict(collections.Counter(x['source_fine_grained_label'] for x in rows)),
             'warning':'Release contains only positive links. Absence is not a negative label; partial is not identical under all annotation schemes. Do not mix into binary training without harmonization and independent labels.'}
    with summary_path.open('x',encoding='utf-8') as f:json.dump(summary,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path);a=p.parse_args()
    try:build(a.archive,a.output_dir)
    except (OSError,ValueError,KeyError,tarfile.TarError) as exc:p.exit(2,f'ตรวจชุดข้อมูลไม่สำเร็จ: {exc}\n')
