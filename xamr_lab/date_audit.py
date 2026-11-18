"""How much of argT the date parser actually reads, split by split.

engine.interval() returns None for text it will not guess (slash dates,
"NA", decades ...). OR_temporal can only block a merge when both sides
have a date, so a split full of unread dates quietly turns OR_temporal
back into OR. This module counts those cases before anyone changes the
parser.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

SLASH = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')


def shape(value):
    """Rough pattern of a date string: digits -> 9, words -> A.

    '07/02/2013' -> '99/99/9999', 'AFTER 4 January 2009' -> 'A 9 A 9999'.
    """
    return re.sub(r'[A-Za-z]+', 'A', re.sub(r'\d', '9', value.strip()))


def audit(values, parse):
    """Count empty, read and unread values, and group unread ones by shape.

    `parse` is the date parser to check (normally engine.interval).
    Each shape keeps its most common example so the table is readable.
    """
    empty = read = 0
    unread = Counter()
    for value in values:
        value = str(value).strip()
        if not value:
            empty += 1
        elif parse(value) is None:
            unread[value] += 1
        else:
            read += 1
    shapes = Counter()
    example = {}
    for value, n in unread.most_common():
        key = shape(value)
        shapes[key] += n
        example.setdefault(key, value)
    return {
        'total': empty + read + sum(unread.values()),
        'empty': empty,
        'read': read,
        'unread': sum(unread.values()),
        'shapes': [(key, n, example[key]) for key, n in shapes.most_common()],
    }


def slash_order(values):
    """Evidence for month/day versus day/month in nn/nn/yyyy values.

    A number above 12 can only be a day, so '12/18/2008' must be
    month first and '18/12/2008' must be day first. Values where both
    numbers are 12 or less ('02/01/2008') could be read either way.
    """
    counts = Counter({'month_first': 0, 'day_first': 0, 'either': 0, 'invalid': 0})
    for value in values:
        match = SLASH.fullmatch(str(value).strip())
        if not match:
            continue
        first, second = int(match[1]), int(match[2])
        if first == 0 or second == 0 or (first > 12 and second > 12):
            counts['invalid'] += 1
        elif first > 12:
            counts['day_first'] += 1
        elif second > 12:
            counts['month_first'] += 1
        else:
            counts['either'] += 1
    return dict(counts)


def read_slash(value, month_first):
    """Read nn/nn/yyyy one way, or None if it is not a real date that way."""
    match = SLASH.fullmatch(str(value).strip())
    if not match:
        return None
    first, second, year = map(int, match.groups())
    month, day = (first, second) if month_first else (second, first)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def cross_check(slash_by_id, reference_by_id, parse):
    """Compare slash dates with another annotation of the same mentions.

    For every mention that has a slash date and a single-day reference
    date, record which reading of the slash date matches the reference.
    A reading that agrees far more often is the order the annotator used.
    """
    counts = Counter({'month_first_only': 0, 'day_first_only': 0, 'same_either_way': 0,
                      'neither': 0, 'no_day_reference': 0})
    for mention, value in slash_by_id.items():
        md, dm = read_slash(value, True), read_slash(value, False)
        if md is None and dm is None:
            continue
        ref = parse(str(reference_by_id.get(mention, '')).strip() or ' ')
        if ref is None or ref[0] != ref[1]:
            counts['no_day_reference'] += 1
        elif md == dm == ref[0]:
            counts['same_either_way'] += 1
        elif md == ref[0]:
            counts['month_first_only'] += 1
        elif dm == ref[0]:
            counts['day_first_only'] += 1
        else:
            counts['neither'] += 1
    return dict(counts)


def load_split(path):
    with open(path, encoding='utf-8') as f:
        tasks = json.load(f)
    if not isinstance(tasks, list) or not tasks or 'argT' not in tasks[0]:
        return None
    return {str(t['mention_id']): t['argT'] for t in tasks}


def report(folder, parse):
    """Markdown report of parser coverage for every split json in `folder`."""
    splits = {}
    for path in sorted(Path(folder).glob('*.json')):
        dates = load_split(path)
        if dates is not None:
            splits[path.stem] = dates
    if not splits:
        raise ValueError(f'no split json with argT in {folder}')

    lines = ['# argT coverage of the date parser', '',
             '| split | mentions | empty | read | unread | most common unread shape |',
             '|---|---:|---:|---:|---:|---|']
    for name, dates in splits.items():
        r = audit(dates.values(), parse)
        top = f"`{r['shapes'][0][0]}` ×{r['shapes'][0][1]} (e.g. `{r['shapes'][0][2]}`)" if r['shapes'] else ''
        lines.append(f"| {name} | {r['total']} | {r['empty']} | {r['read']} | {r['unread']} | {top} |")

    lines += ['', '## Slash dates', '',
              '| split | month first | day first | either | invalid | agrees with other annotator: month first / day first |',
              '|---|---:|---:|---:|---:|---|']
    for name, dates in splits.items():
        order = slash_order(dates.values())
        if not sum(order.values()):
            continue
        other = None
        if name.startswith(('ann1-', 'ann2-')):
            other = splits.get(('ann2-' if name.startswith('ann1-') else 'ann1-') + name[5:])
        agree = ''
        if other is not None:
            check = cross_check(dates, other, parse)
            agree = f"{check['month_first_only']} / {check['day_first_only']}"
        lines.append(f"| {name} | {order['month_first']} | {order['day_first']} | "
                     f"{order['either']} | {order['invalid']} | {agree} |")
    lines.append('')
    return '\n'.join(lines)
