import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import analyze
from test_analysis import SMALL_RUN, write

THREE_METHODS = """mention_id,topic,gold_cluster,OR,OR_TFIDF,OR_temporal
m1,1,a,0,0,0
m2,1,a,0,0,1
"""


def run(*argv):
    out = io.StringIO()
    with redirect_stdout(out):
        analyze.main(list(argv))
    return out.getvalue()


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class TopicsCommandTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def test_writes_csv_next_to_run(self):
        write(self.folder, SMALL_RUN)
        printed = run('topics', self.folder)
        table = read_csv(Path(self.folder) / 'topics_OR_TFIDF_vs_OR.csv')
        self.assertEqual([r['topic'] for r in table], ['1', '2'])
        self.assertEqual(table[0]['FP_change'], '2')
        self.assertEqual(table[1]['FP_change'], '0')
        self.assertIn('topic    1: FP +2, FN +0', printed)

    def test_csv_path_writes_beside_it(self):
        path = write(self.folder, SMALL_RUN)
        run('topics', str(path))
        self.assertTrue((Path(self.folder) / 'topics_OR_TFIDF_vs_OR.csv').exists())

    def test_out_path_with_method(self):
        write(self.folder, SMALL_RUN)
        target = Path(self.folder) / 'mine.csv'
        run('topics', self.folder, '--method', 'OR_TFIDF', '--out', str(target))
        self.assertTrue(target.exists())
        self.assertIn('pair_F1_OR_TFIDF', read_csv(target)[0])

    def test_one_csv_per_method(self):
        write(self.folder, THREE_METHODS)
        run('topics', self.folder)
        names = sorted(p.name for p in Path(self.folder).glob('topics_*.csv'))
        self.assertEqual(names, ['topics_OR_TFIDF_vs_OR.csv',
                                 'topics_OR_temporal_vs_OR.csv'])

    def test_unknown_method(self):
        write(self.folder, SMALL_RUN)
        with self.assertRaises(SystemExit):
            run('topics', self.folder, '--method', 'AND')

    def test_missing_run_exits(self):
        with self.assertRaises(SystemExit) as stop:
            run('topics', str(Path(self.folder) / 'runs' / 'typo'))
        self.assertIn('not found', str(stop.exception.code))

    def test_out_needs_method(self):
        write(self.folder, THREE_METHODS)
        with self.assertRaises(SystemExit):
            run('topics', self.folder, '--out', 'x.csv')


class SignificanceCommandTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        write(self.folder, THREE_METHODS)

    def test_writes_csv_and_summary(self):
        printed = run('significance', self.folder, '--rounds', '50')
        table = read_csv(Path(self.folder) / 'significance.csv')
        self.assertEqual([(r['method'], r['metric']) for r in table], [
            ('OR_TFIDF', 'pair_F1'), ('OR_TFIDF', 'B3_F1'),
            ('OR_temporal', 'pair_F1'), ('OR_temporal', 'B3_F1')])
        # OR_TFIDF matches OR here, OR_temporal splits the only gold pair.
        self.assertEqual(table[0]['p_value'], '1.0')
        self.assertEqual(table[2]['delta'], '-100.0')
        self.assertEqual(table[0]['rounds'], '50')
        summary = (Path(self.folder) / 'significance.md').read_text(encoding='utf-8')
        self.assertIn('| OR_temporal | pair_F1 | -100.00 |', summary)
        self.assertIn('Topics: 1.', summary)
        self.assertIn('OR_temporal', printed)

    def test_same_seed_same_files(self):
        run('significance', self.folder, '--rounds', '50', '--seed', '9')
        first = (Path(self.folder) / 'significance.csv').read_text()
        run('significance', self.folder, '--rounds', '50', '--seed', '9')
        self.assertEqual((Path(self.folder) / 'significance.csv').read_text(), first)

    def test_unknown_baseline(self):
        with self.assertRaises(SystemExit):
            run('significance', self.folder, '--baseline', 'AND')


if __name__ == '__main__':
    unittest.main()
