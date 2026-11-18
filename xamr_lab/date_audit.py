"""How much of argT the date parser actually reads, split by split.

engine.interval() returns None for text it will not guess (slash dates,
"NA", decades ...). OR_temporal can only block a merge when both sides
have a date, so a split full of unread dates quietly turns OR_temporal
back into OR. This module counts those cases before anyone changes the
parser.
"""
import re
from collections import Counter


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
