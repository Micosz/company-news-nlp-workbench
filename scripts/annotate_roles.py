"""Create a blinded mention-level annotation sheet and apply it to pilot pairs.

Only an independently reviewed evidence span from the provided event context is
accepted. This utility never infers roles or uses a gold cluster to fill them.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import builtin, csv_rows, validate  # noqa: E402

ANNOTATION_COLUMNS = [
    'mention_id', 'context', 'buyer', 'buyer_evidence', 'target',
    'target_evidence', 'annotator', 'notes',
]
ROLE_FIELDS = ('buyer', 'target')
BLANK_TOKENS = {'unknown', 'unk', 'null', 'none', 'n/a', 'na', 'ไม่ทราบ'}


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(text))).strip()


def pilot_mentions():
    result = {}
    for row in csv_rows(ROOT / 'data/pilot/event_mentions.csv'):
        ident = row['mention_id']
        if not ident or ident in result:
            raise ValueError('Pilot contains duplicate or empty mention IDs')
        result[ident] = row['context_normalized']
    if not result:
        raise ValueError('Pilot mention data is empty')
    return result


def blank_annotation():
    return pd.DataFrame([
        dict(mention_id=ident, context=context, buyer='', buyer_evidence='',
             target='', target_evidence='', annotator='', notes='')
        for ident, context in pilot_mentions().items()
    ], columns=ANNOTATION_COLUMNS)


def read_sheet(path):
    path = Path(path)
    if path.suffix.lower() == '.xlsx':
        return pd.read_excel(path, dtype=str, keep_default_na=False).fillna('')
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna('')
    raise ValueError('รองรับไฟล์ .xlsx หรือ .csv')


def check_annotations(frame):
    missing = set(ANNOTATION_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError('ขาดคอลัมน์ annotation: ' + ', '.join(sorted(missing)))
    result = frame[ANNOTATION_COLUMNS].copy().fillna('')
    for key in ANNOTATION_COLUMNS:
        result[key] = result[key].astype(str).str.strip()
    if (result.mention_id == '').any() or result.mention_id.duplicated().any():
        raise ValueError('mention_id ต้องไม่ว่างและไม่ซ้ำ')
    expected = pilot_mentions()
    actual = set(result.mention_id)
    if actual != set(expected):
        raise ValueError(f'mention_id ไม่ตรงกับ pilot: ขาด {len(set(expected)-actual)}, เกิน {len(actual-set(expected))}')
    for row in result.to_dict('records'):
        context = expected[row['mention_id']]
        if normalize(row['context']) != normalize(context):
            raise ValueError(f"บริบทถูกแก้ไข: {row['mention_id']}")
        has_role = False
        for role in ROLE_FIELDS:
            value, evidence = row[role], row[role + '_evidence']
            if value.casefold() in BLANK_TOKENS:
                raise ValueError(f"{row['mention_id']}: ไม่ทราบให้เว้น {role} ว่าง")
            if value:
                has_role = True
                if not evidence or normalize(evidence).casefold() not in normalize(context).casefold():
                    raise ValueError(f"{row['mention_id']}: {role} ต้องมีหลักฐานที่คัดจาก context")
            elif evidence:
                raise ValueError(f"{row['mention_id']}: {role}_evidence มีค่าแต่ {role} ว่าง")
        if has_role and not row['annotator']:
            raise ValueError(f"{row['mention_id']}: ระบุผู้ทำ annotation")
    return result


def apply_annotations(frame, mode):
    if mode not in ('small_A', 'small_B'):
        raise ValueError('รองรับเฉพาะ small_A และ small_B')
    checked = check_annotations(frame)
    annotations = checked.set_index('mention_id')[['buyer', 'target']]
    pairs = builtin(mode)
    for side in ('a', 'b'):
        for role in ROLE_FIELDS:
            pairs[f'{role}_{side}'] = pairs[f'mention_{side}'].map(annotations[role])
            if pairs[f'{role}_{side}'].isna().any():
                raise ValueError('มีคู่ข้อความที่ไม่พบ mention annotation')
    validate(pairs)
    return pairs


def write_sheet(frame, path):
    path = Path(path).expanduser()
    if path.suffix.lower() not in ('.csv', '.xlsx'):
        raise ValueError('ไฟล์ผลลัพธ์ต้องลงท้าย .csv หรือ .xlsx')
    if path.exists() or path.is_symlink():
        raise FileExistsError('ไฟล์ปลายทางมีอยู่แล้ว: เลือกชื่อใหม่เพื่อไม่เขียนทับ')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents clobbering annotation or existing source files.
    with path.open('xb') as dest:
        if path.suffix.lower() == '.csv':
            dest.write(frame.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'))
        else:
            book = Workbook()
            sheet = book.active
            sheet.title = 'annotations' if 'context' in frame.columns else 'pairs'
            sheet.append(list(frame.columns))
            for row in frame.itertuples(index=False, name=None):
                sheet.append([str(v) for v in row])
                for cell in sheet[sheet.max_row]:
                    cell.data_type = 's'  # User text is literal, never a formula.
            sheet.freeze_panes = 'A2'
            sheet.auto_filter.ref = sheet.dimensions
            for col in sheet.columns:
                sheet.column_dimensions[col[0].column_letter].width = 26
            book.save(dest)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Manual, evidence-backed pilot role annotation')
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export', help='Create blank mention annotation template')
    export.add_argument('--output', required=True, type=Path)
    apply = commands.add_parser('apply', help='Build labeled pairs from a completed template')
    apply.add_argument('--input', required=True, type=Path)
    apply.add_argument('--fold', choices=('A', 'B'), required=True)
    apply.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            frame = blank_annotation()
            write_sheet(frame, args.output)
            print(f'สร้างแบบฟอร์ม {len(frame)} mentions: {args.output}')
        else:
            annotations = read_sheet(args.input)
            frame = apply_annotations(annotations, 'small_' + args.fold)
            write_sheet(frame, args.output)
            known = (frame[['buyer_a', 'buyer_b', 'target_a', 'target_b']] != '').all(axis=1)
            print(f'สร้าง {len(frame)} คู่: {args.output}')
            for split in ('train', 'test'):
                mask = frame.split == split
                print(f'{split}: บทบาทครบ {int((known & mask).sum())} จาก {int(mask.sum())} คู่')
            print('ยังไม่ใช่ผลทดลอง: นำไฟล์เข้าเว็บ เลือก manual roles และรันเพื่อวัดผล')
    except (ValueError, OSError) as exc:
        parser.exit(2, f'ผิดพลาด: {exc}\n')


if __name__ == '__main__':
    main()
