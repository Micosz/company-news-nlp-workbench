import tempfile
import unittest
from pathlib import Path

from analysis import load_predictions

SMALL_RUN = """mention_id,topic,gold_cluster,OR,OR_TFIDF
m1,1,a,0,0
m2,1,a,0,0
m3,1,b,1,0
m4,2,c,2,2
"""


def write(folder, text):
    path = Path(folder) / 'predictions.csv'
    path.write_text(text, encoding='utf-8')
    return path


class LoadPredictionsTest(unittest.TestCase):
    def test_reads_run_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, SMALL_RUN)
            rows, methods = load_predictions(folder)
        self.assertEqual(len(rows), 4)
        self.assertEqual(methods, ['OR', 'OR_TFIDF'])
        self.assertEqual(rows[2]['gold_cluster'], 'b')

    def test_skips_annotation_columns(self):
        text = 'mention_id,topic,doc_id,argT,gold_cluster,OR,OR_temporal\nm1,1,d1,2012,a,0,0\n'
        with tempfile.TemporaryDirectory() as folder:
            _, methods = load_predictions(write(folder, text))
        self.assertEqual(methods, ['OR', 'OR_temporal'])

    def test_missing_gold_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, 'mention_id,topic,OR\nm1,1,0\n')
            with self.assertRaisesRegex(ValueError, 'gold_cluster'):
                load_predictions(path)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, 'mention_id,topic,gold_cluster,OR\n')
            with self.assertRaisesRegex(ValueError, 'no rows'):
                load_predictions(path)


if __name__ == '__main__':
    unittest.main()
