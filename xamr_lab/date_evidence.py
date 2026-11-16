"""Conservative date provenance for archived English ECB+ annotations."""
from datetime import datetime
import re

POLICY = 'ecb-header-and-mention-v1'
MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
NAMED_DAY = rf'\b(?:{MONTH}\s+\d{{1,2}}\s+\d{{4}}|\d{{1,2}}\s+{MONTH}\s+\d{{4}})\b'
ISO_DAY = r'\b\d{4}-\d{2}-\d{2}\b'
DAY_PATTERN = re.compile(rf'{NAMED_DAY}|{ISO_DAY}', re.I)
METADATA = r'(?:published|posted|(?:last\s+)?updated)(?:\s+on)?'
HEADER_START = re.compile(rf'^(?:{METADATA}\b|on\b|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\b|{NAMED_DAY}|{ISO_DAY}|\d{{1,2}}/\d{{1,2}}/\d{{4}})', re.I)
HEADER_CLOCK = re.compile(r'\b\d{1,2}:\d{2}\b|\b\d{1,2}\.\d{2}\s+(?:GMT|BST|UTC)\b', re.I)
SLASH_HEADER = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')


def clean(value):
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'\s*/\s*', '/', value)
    value = re.sub(r'\s*:\s*(?=\d{2}\b)', ':', value)
    value = re.sub(rf'\b({MONTH})\s*\.', r'\1', value, flags=re.I)
    return ' '.join(value.replace(',', ' ').split())


def days_in(text):
    days = set()
    for match in DAY_PATTERN.finditer(text):
        value = re.sub(r'\bSept\b', 'Sep', match.group(), flags=re.I)
        for fmt in ('%B %d %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y', '%Y-%m-%d'):
            try:
                days.add(datetime.strptime(value, fmt).date())
                break
            except ValueError:
                continue
    return days


def publication_header(document):
    candidates = set()
    for block in document.split('<p/>')[:4]:
        line = clean(block)
        if len(line) > 100 or not HEADER_START.match(line):
            continue
        marker = re.match(rf'^{METADATA}\b', line, re.I)
        timestamp = HEADER_CLOCK.search(line)
        date_only = DAY_PATTERN.fullmatch(re.sub(r'^on\s+', '', line, flags=re.I))
        if not (marker or timestamp or date_only):
            continue
        candidates.update(days_in(line))
        slash = SLASH_HEADER.search(line)
        if slash:
            first, second, year = map(int, slash.groups())
            # The header alone cannot resolve ambiguous numeric dates. Keep both
            # interpretations as publication candidates, never as event dates.
            for day, month in ((first, second), (second, first)):
                try:
                    candidates.add(datetime(year, month, day).date())
                except ValueError:
                    continue
    return candidates


def classify(task, supplied):
    header = publication_header(task.get('marked_doc', ''))
    sentence = clean(task.get('marked_sentence') or task.get('text', ''))
    sentence_days = days_in(sentence)
    evidence = {
        'mention_id': task['mention_id'],
        'argT': task['argT'],
        'publication_candidates': ' | '.join(sorted(d.isoformat() for d in header)),
        'mention_sentence_days': ' | '.join(sorted(d.isoformat() for d in sentence_days)),
    }
    if supplied is None:
        category, reason = 'unknown', 'missing_or_unparsed_argT'
    elif supplied[0] != supplied[1]:
        category, reason = 'unknown', 'argT_not_day_precision'
    elif sentence_days == {supplied[0]} and not re.match(rf'^{METADATA}\b', sentence, re.I):
        category, reason = 'event', 'matching_full_date_in_mention_sentence'
    elif supplied[0] in header:
        category, reason = 'publication', 'argT_matches_header_candidate'
    else:
        category, reason = 'unknown', 'ambiguous_or_no_mention_sentence_support'
    return {**evidence, 'category': category, 'reason': reason,
            'veto_date': supplied[0].isoformat() if category == 'event' else ''}
