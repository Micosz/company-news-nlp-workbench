"""Look at a finished run without re-running it.

    python analyze.py topics runs/<run_id>
    python analyze.py topics runs/<run_id> --method OR_TFIDF --out or_tfidf_topics.csv
    python analyze.py significance runs/<run_id>
"""
import argparse
import csv
import sys
from pathlib import Path

from analysis import compare_topics, load_predictions
from significance import SEED, significance_rows, summary_markdown


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


def load_run(path):
    try:
        return load_predictions(path)
    except ValueError as err:
        sys.exit(str(err))


def run_folder(path):
    """Folder where reports go: the run folder itself, or the folder of a csv path."""
    path = Path(path)
    return path if path.is_dir() else path.parent


def topics(args):
    rows, methods = load_run(args.run)
    chosen = pick_methods(methods, args.method, args.baseline)
    if not chosen:
        sys.exit('Nothing to compare: the run only has the baseline.')
    if args.out and len(chosen) > 1:
        sys.exit('--out needs --method (each method gets its own csv otherwise)')
    for method in chosen:
        table = compare_topics(rows, method, args.baseline)
        out = Path(args.out) if args.out else run_folder(args.run) / f'topics_{method}_vs_{args.baseline}.csv'
        write_csv(table, out)
        print(f'{method}: {len(table)} topics -> {out}')
        for row in table:
            if row['FP_change'] or row['FN_change']:
                print(f"  topic {row['topic']:>4}: FP {row['FP_change']:+}, FN {row['FN_change']:+}")


def significance(args):
    rows, methods = load_run(args.run)
    chosen = pick_methods(methods, args.method, args.baseline)
    if not chosen:
        sys.exit('Nothing to compare: the run only has the baseline.')
    table = []
    print(f'{"method":<14}{"metric":<9}{"delta":>8}  {"95% interval":<18}{"p":>7}')
    for method in chosen:
        for row in significance_rows(rows, method, args.baseline, args.rounds, args.seed):
            interval = f"[{row['ci_low']:+.2f}, {row['ci_high']:+.2f}]"
            print(f"{method:<14}{row['metric']:<9}{row['delta']:>+8.2f}  {interval:<18}{row['p_value']:>7.4f}")
            table.append(row)
    folder = run_folder(args.run)
    write_csv(table, folder / 'significance.csv')
    (folder / 'significance.md').write_text(summary_markdown(table, folder.name), encoding='utf-8')
    print(f'\nwrote {folder / "significance.csv"} and significance.md')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('topics', help='per-topic changes against a baseline method')
    p.add_argument('run', help='run folder or predictions.csv')
    p.add_argument('--method', help='compare only this method (default: every method in the run)')
    p.add_argument('--baseline', default='OR')
    p.add_argument('--out', help='csv path, only with --method (default: <run>/topics_<method>_vs_<baseline>.csv)')
    p.set_defaults(func=topics)

    p = commands.add_parser('significance', help='bootstrap interval and permutation p-value against a baseline')
    p.add_argument('run', help='run folder or predictions.csv')
    p.add_argument('--method', help='test only this method (default: every method in the run)')
    p.add_argument('--baseline', default='OR')
    p.add_argument('--rounds', type=int, default=1000, help='bootstrap rounds (default: 1000)')
    p.add_argument('--seed', type=int, default=SEED)
    p.set_defaults(func=significance)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
