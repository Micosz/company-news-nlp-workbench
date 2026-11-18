"""How much of argT the date parser actually reads, split by split.

engine.interval() returns None for text it will not guess (slash dates,
"NA", decades ...). OR_temporal can only block a merge when both sides
have a date, so a split full of unread dates quietly turns OR_temporal
back into OR. This module counts those cases before anyone changes the
parser.
"""
import re
from collections import Counter

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
