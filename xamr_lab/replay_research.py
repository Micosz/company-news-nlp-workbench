"""Replay a downloaded evidence package using its input, config and source snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
from research_runner import compute

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tasks = json.loads(args.input.read_text())
    report = json.loads((args.input.parent / 'report.json').read_text())
    digest = hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if digest != report['provenance']['input_sha256']:
        raise SystemExit('Input checksum mismatch; replay stopped.')
    print(json.dumps(compute(json.loads(args.config.read_text()), tasks, args.output), indent=2))
