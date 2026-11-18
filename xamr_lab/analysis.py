"""Read saved run predictions so methods can be compared after a run."""
import csv
from pathlib import Path

# Columns written next to the method columns in predictions.csv
# (engine.py keeps the annotation fields, research_runner.py keeps only the first three).
INFO_COLUMNS = {'mention_id', 'topic', 'gold_cluster', 'doc_id', 'sentence_id',
                'lemma', 'roleset_id', 'arg0', 'arg1', 'argL', 'argT'}
NEEDED = ('mention_id', 'topic', 'gold_cluster')


def load_predictions(path):
    """Return (rows, methods) from a run folder or a predictions.csv file."""
    path = Path(path)
    if path.is_dir():
        path = path / 'predictions.csv'
    with path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f'{path} has no rows')
    missing = [c for c in NEEDED if c not in rows[0]]
    if missing:
        raise ValueError(f'{path} is missing columns: {", ".join(missing)}')
    methods = [c for c in rows[0] if c not in INFO_COLUMNS]
    if not methods:
        raise ValueError(f'{path} has no method columns')
    return rows, methods
