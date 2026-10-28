"""Validation, dataset loading and research record persistence."""
import csv, hashlib, html, io, json, os, platform, re, sys, uuid, unicodedata
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
REQUIRED = ['pair_id','text_a','text_b','label','split','doc_a','doc_b','group_id']
ROLES = ['buyer_a','target_a','buyer_b','target_b']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def read_table(data, filename):
    if filename.lower().endswith('.xlsx'):
        return pd.read_excel(io.BytesIO(data), dtype=str, keep_default_na=False).fillna('')
    if filename.lower().endswith('.csv'):
        return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False).fillna('')
    raise ValueError('รองรับ .xlsx และ .csv เท่านั้น (Excel ใช้ชีตแรก)')


def validate(frame):
    missing = set(REQUIRED) - set(frame.columns)
    if missing: raise ValueError('ขาดคอลัมน์: ' + ', '.join(sorted(missing)))
    frame = frame.copy().fillna('')
    for c in REQUIRED + ROLES:
        if c not in frame: frame[c] = ''
        frame[c] = frame[c].astype(str).str.strip()
    for c in REQUIRED:
        if (frame[c] == '').any(): raise ValueError(f'{c} มีค่าว่าง')
    if not frame.label.isin(['0','1']).all(): raise ValueError('label ต้องเป็น 0 หรือ 1 เท่านั้น')
    frame.label = frame.label.astype(int)
    frame.split = frame.split.str.lower()
    if not frame.split.isin(['train','dev','test']).all(): raise ValueError('split ต้องเป็น train, dev หรือ test')
    if not {'train','test'}.issubset(set(frame.split)): raise ValueError('ต้องมี train และ test')
    if frame.pair_id.duplicated().any(): raise ValueError('pair_id ซ้ำ')
    if (frame.doc_a == frame.doc_b).any(): raise ValueError('พบคู่ที่มาจากเอกสารเดียวกัน')
    # Prefer exact event mention IDs: one context can contain several events.
    if {'mention_a','mention_b'}.issubset(frame.columns) and (frame[['mention_a','mention_b']] != '').all().all():
        pairs=[tuple(sorted((a,b))) for a,b in zip(frame.mention_a,frame.mention_b)]
    else:
        pairs=[tuple(sorted(((a,t),(b,u)))) for a,t,b,u in zip(frame.doc_a,frame.text_a,frame.doc_b,frame.text_b)]
    if len(pairs) != len(set(pairs)):
        raise ValueError('คู่ข้อมูลซ้ำ: ใช้คู่ mention ที่ไม่ซ้ำ หรือระบุ mention_a/mention_b หากหนึ่งข่าวมีหลายเหตุการณ์')
    doc_groups={}
    for r in frame.to_dict('records'):
        for c in ('doc_a','doc_b'):
            if r[c] in doc_groups and doc_groups[r[c]] != r['group_id']:
                raise ValueError('เอกสารเดียวกันอยู่หลาย group_id')
            doc_groups[r[c]]=r['group_id']
    for label in ('train','test'):
        part = frame[frame.split == label]
        if set(part.label) != {0,1}: raise ValueError(f'{label} ต้องมีทั้ง label 0 และ 1')
    sets = {}
    for name, part in frame.groupby('split'):
        sets[name] = {'doc':set(part.doc_a)|set(part.doc_b), 'group':set(part.group_id),
                      'text':{re.sub(r'\s+',' ',unicodedata.normalize('NFC', html.unescape(str(x)))).strip().casefold() for c in ('text_a','text_b') for x in part[c]}}
    for a in sets:
        for b in sets:
            if a >= b: continue
            for field in ('doc','group','text'):
                overlap = sets[a][field] & sets[b][field]
                if overlap: raise ValueError(f'Data leakage: {field} ซ้ำระหว่าง {a}/{b} ({len(overlap)} ค่า)')
    return frame


def summary(frame):
    return {'rows':len(frame), 'columns':list(frame.columns),
            'preview':frame.head(6).to_dict('records'),
            'splits': {str(k):int(v) for k,v in frame.get('split',pd.Series(dtype=str)).value_counts().items()}}


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
        yield from csv.DictReader(handle)


def load_provisional_roles(path=None):
    """Load AI-assisted article-level role labels, not human-reviewed gold.

    Offsets are half-open Unicode character indices in the source document's
    normalized full text. The document hash permits later offline verification;
    matching an offset alone does not establish semantic correctness.
    """
    pilot = ROOT / 'data' / 'pilot'
    expected = {row['mention_id'] for row in csv_rows(pilot / 'event_mentions.csv')}
    rows = list(csv_rows(path if path is not None else pilot / 'pilot_roles_ai_provisional.csv'))
    roles = {}
    for row in rows:
        ident = row.get('mention_id', '')
        if not ident or ident in roles:
            raise ValueError('ข้อมูลบทบาท AI มี mention_id ว่างหรือซ้ำ')
        if not row.get('buyer', '').strip() or not row.get('target', '').strip():
            raise ValueError(f'ข้อมูลบทบาท AI ไม่ครบ: {ident}')
        if row.get('provenance') != 'AI-assisted_from_ECB+_full_article_human_review_pending':
            raise ValueError(f'ข้อมูลที่มาบทบาท AI ไม่ถูกต้อง: {ident}')
        if not re.fullmatch(r'[0-9a-f]{64}', row.get('document_sha256', '')):
            raise ValueError(f'ค่า checksum ของเอกสารไม่ถูกต้อง: {ident}')
        try:
            for role in ('buyer', 'target'):
                start, end = int(row[role+'_evidence_start']), int(row[role+'_evidence_end'])
                if start < 0 or end <= start: raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ValueError(f'ตำแหน่งหลักฐานไม่ถูกต้อง: {ident}') from None
        roles[ident] = row
    if set(roles) != expected:
        raise ValueError('ข้อมูลบทบาท AI ไม่ตรงกับ mention IDs ของ Pilot')
    return roles


def builtin(mode):
    if mode not in ('small_A','small_B','small_A_ai','small_B_ai','full'): raise ValueError('unknown dataset')
    ai_roles = mode.endswith('_ai')
    pilot_mode = mode.removesuffix('_ai')
    # Portable pilot is bundled; full package remains alongside the app.
    configured = os.environ.get('NLP_DATASET_ROOT')
    base = Path(configured).expanduser().resolve() if configured else ROOT.parent / 'nlp_datasets_2026-10-26'
    if mode == 'full':
        dataset = base / 'full' / 'ecbplus'
        if not dataset.exists(): raise ValueError('ไม่พบ full dataset: ตั้ง NLP_DATASET_ROOT ให้ชี้ไปโฟลเดอร์ที่มี full/ecbplus (ดู docs/DATA_SOURCES_TH.md)')
        assignments = None
    else:
        dataset = ROOT / 'data' / 'pilot'
        assignments = {r['document_id']:r['fold_'+pilot_mode[-1]] for r in csv_rows(dataset/'pilot_two_fold_assignments.csv')}
    mentions = {r['mention_id']:r for r in csv_rows(dataset/'event_mentions.csv')}
    roles = load_provisional_roles() if ai_roles else None
    rows=[]
    for p in csv_rows(dataset/'pairs.csv'):
        a,b=mentions[p['mention_id_a']],mentions[p['mention_id_b']]
        role_fields = ({f'{role}_{side}': roles[mention['mention_id']][role]
                        for side, mention in (('a', a), ('b', b)) for role in ('buyer', 'target')}
                       if roles is not None else {c:'' for c in ROLES})
        rows.append({'pair_id':p['pair_id'],'text_a':a['context_normalized'],'text_b':b['context_normalized'],
                     'label':p['label_same_event'],'split':assignments[p['document_id_a']] if assignments else p['split'],
                     'doc_a':p['document_id_a'],'doc_b':p['document_id_b'],'group_id':p['topic_id'],
                     'mention_a':p['mention_id_a'],'mention_b':p['mention_id_b'], **role_fields})
    return pd.DataFrame(rows)


def prepare_run(frame, code, config, source):
    if source in ('small_A_ai', 'small_B_ai') and config.get('role_source') == 'manual':
        raise ValueError('ชุดบทบาท AI ยังไม่ได้ผ่านการตรวจโดยคน โปรดเลือกโมเดลทำนาย')
    frame = validate(frame)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    folder = ROOT/'runs'/stamp
    folder.mkdir(parents=True)
    frame.to_csv(folder/'dataset.csv',index=False,encoding='utf-8-sig')
    (folder/'algorithm.py').write_text(code,encoding='utf-8')
    # Snapshot execution/validation logic as well as user algorithm.
    for name in ('engine.py','worker.py'):
        (folder/name).write_bytes((ROOT/name).read_bytes())
    dump(folder/'config.json',config)
    manifest={'run_id':stamp,'created_utc':datetime.now(timezone.utc).isoformat(),
        'source':source,'config':config,'counts':summary(frame)['splits'],
        'positive_counts':{s:int(p.label.sum()) for s,p in frame.groupby('split')},
        'groups':{s:sorted(p.group_id.unique().tolist()) for s,p in frame.groupby('split')},
        'sha256':{name:digest((folder/name).read_bytes()) for name in ('dataset.csv','algorithm.py','config.json','engine.py','worker.py')},
        'status':'running', 'evaluation':'Pairwise binary classification on supplied/gold event contexts, not clustering CoNLL or end-to-end extraction.',
        'limitations':['Pilot has only 4 deals / 2 topics; no conclusive generalization claim.',
                      'Small pilot overlaps full package test topics; do not tune on pilot then claim full test is untouched.',
                      'Dev rows are archived but default fixed-parameter algorithm does not use them.',
                      'Custom code has local filesystem access; frozen test labels are withheld by API contract only.']}
    if source in ('small_A_ai', 'small_B_ai'):
        manifest['limitations'].extend([
            'AI-assisted buyer/target annotations from full articles are not human-reviewed gold.',
            'Role annotations can use full-article context beyond the short text given to the baseline.',
            'In this small pilot, buyer/target identity can act as an event-label shortcut; do not generalize.'
        ])
    dump(folder/'manifest.json',manifest)
    return folder
