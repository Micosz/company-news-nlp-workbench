"""Look at a finished run without re-running it.

    python analyze.py topics runs/<run_id>
    python analyze.py topics runs/<run_id> --method OR_TFIDF --out or_tfidf_topics.csv
"""
import argparse
import csv
import sys
from pathlib import Path

from analysis import compare_topics, load_predictions


def write_csv(rows, path):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pick_methods(methods, chosen, baseline):
    if baseline not in methods:
        sys.exit(f'{baseline} is not in this run (found: {", ".join(methods)})')
    if chosen:
        if chosen not in methods:
            sys.exit(f'{chosen} is not in this run (found: {", ".join(methods)})')
        return [chosen]
    return [m for m in methods if m != baseline]


def topics(args):
    rows, methods = load_predictions(args.run)
    chosen = pick_methods(methods, args.method, args.baseline)
    if not chosen:
        sys.exit('Nothing to compare: the run only has the baseline.')
    if args.out and len(chosen) > 1:
        sys.exit('--out needs --method (each method gets its own csv otherwise)')
    for method in chosen:
        table = compare_topics(rows, method, args.baseline)
        out = Path(args.out) if args.out else Path(args.run) / f'topics_{method}_vs_{args.baseline}.csv'
        write_csv(table, out)
        print(f'{method}: {len(table)} topics -> {out}')
        for row in table:
            if row['FP_change'] or row['FN_change']:
                print(f"  topic {row['topic']:>4}: FP {row['FP_change']:+}, FN {row['FN_change']:+}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('topics', help='per-topic changes against a baseline method')
    p.add_argument('run', help='run folder or predictions.csv')
    p.add_argument('--method', help='compare only this method (default: every method in the run)')
    p.add_argument('--baseline', default='OR')
    p.add_argument('--out', help='csv path, only with --method (default: <run>/topics_<method>_vs_<baseline>.csv)')
    p.set_defaults(func=topics)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
