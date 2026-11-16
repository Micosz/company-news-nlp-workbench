"""Numerical parity, safe API boundaries, and portable evidence replay."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from fastapi.testclient import TestClient
from app import app
from engine import BASE, load_dataset
import or_nb_hybrid as nb
import tfidf_only as tf
from research_runner import catalog, compute, model, run_online, validate_request, RUN_SLOTS


def partition(rows, method):
    groups = {}
    for row in rows:
        groups.setdefault(row[method], []).append(row['mention_id'])
    return hashlib.sha256(json.dumps(sorted(sorted(g) for g in groups.values())).encode()).hexdigest()


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {a: run_online({'dataset': a + '-dev', 'algorithm': 'compare'}) for a in ('ann1', 'ann2')}
        cls.reference = json.loads((BASE / 'research_reference.json').read_text())
        cls.client = TestClient(app)

    def test_original_metrics_and_cluster_partitions(self):
        for annotation, value in self.runs.items():
            report = value['report']
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(value['archive_base64']))) as archive:
                predictions = list(csv.DictReader(io.StringIO(archive.read('predictions.csv').decode())))
            for method, reference in self.reference[annotation]['methods'].items():
                self.assertEqual(partition(predictions, method), reference['partition_sha256'])
                metrics = report['metrics'][method]
                self.assertAlmostEqual(100 * metrics['conll_f1'], float(reference['metrics']['CoNLL_F1']), places=11)
                for key in ('pair_precision', 'pair_recall', 'pair_f1'):
                    self.assertAlmostEqual(100 * metrics[key], float(reference['metrics'][key]), places=11)
                for key in ('fp', 'fn', 'tp', 'tn'):
                    self.assertEqual(metrics[key], int(reference['metrics'][key.upper()]))
            self.assertEqual(partition(predictions, 'OR'), partition(predictions, 'OR_TFIDF_NB'))
            self.assertTrue(report['selection']['nb_no_op'])
            self.assertEqual(report['selection']['nb_fraction'], 0)
            self.assertEqual(report['metrics']['OR'], report['metrics']['OR_TFIDF_NB'])
        self.assertEqual(len(self.runs['ann1']['report']['edge_changes']), 8)
        self.assertEqual(len(self.runs['ann2']['report']['edge_changes']), 16)

    def test_json_models_match_original_fitted_statistics(self):
        for annotation in ('ann1', 'ann2'):
            train, checksum = load_dataset(annotation + '-train')
            frozen, vectorizer, restored, digest = model(annotation)
            original, _ = nb.fit(train)
            self.assertEqual(vectorizer.vocabulary_, original[0].vocabulary_)
            # ARM64 and x86 libm may differ by one ULP when recomputing log-IDF.
            # Frozen inference partitions and metrics remain exact in the parity test.
            np.testing.assert_allclose(vectorizer.idf_, original[0].idf_, rtol=0, atol=1e-14)
            np.testing.assert_array_equal(restored[2].category_count_[0], original[2].category_count_[0])
            dev, _ = load_dataset(annotation + '-dev_small')
            edges, _, _ = nb.graph_data(dev)
            np.testing.assert_allclose(nb.rank(restored, dev, edges), nb.rank(original, dev, edges), rtol=0, atol=1e-15)
            self.assertEqual(checksum, frozen['train_sha256'])
            for selection in ('text_selection', 'nb_selection'):
                self.assertEqual(frozen[selection]['cv_mean_conll'], self.reference[annotation][selection]['cv_mean_conll'])
                folds = frozen[selection]['folds']
                self.assertEqual(len(folds), 5)
                validation = []
                for fold in folds:
                    self.assertFalse(set(fold['fit_topics']) & set(fold['validation_topics']))
                    validation.extend(fold['validation_topics'])
                self.assertEqual(len(validation), len(set(validation)))
                self.assertEqual(len(validation), 25)

    def test_archive_provenance_and_replay(self):
        value = self.runs['ann1']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(value['archive_base64']))) as archive:
                archive.extractall(root)
            report = json.loads((root / 'report.json').read_text())
            self.assertEqual(report, value['report'])
            for name, digest in report['provenance']['source_sha256'].items():
                self.assertEqual(hashlib.sha256((root / 'source' / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(hashlib.sha256((root / 'source/models/ann1.json').read_bytes()).hexdigest(), report['provenance']['model_sha256'])
            subprocess.run([sys.executable, str(root / 'source/replay_research.py'), '--input', str(root / 'input.json'),
                            '--config', str(root / 'config.json'), '--output', str(root / 'replayed')],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            for filename in ('metrics.csv', 'predictions.csv', 'topics.csv', 'edge_changes.csv', 'pair_changes.csv'):
                self.assertEqual((root / filename).read_bytes(), (root / 'replayed' / filename).read_bytes())
            (root / 'input.json').write_text('[]')
            result = subprocess.run([sys.executable, str(root / 'source/replay_research.py'), '--input', str(root / 'input.json'),
                            '--config', str(root / 'config.json'), '--output', str(root / 'tampered')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Input checksum mismatch', result.stderr)

    def test_dataset_algorithm_switches_and_repeated_runs(self):
        for dataset in ('ann1-dev_small', 'ann2-dev_small'):
            for method in ('OR', 'TFIDF', 'OR_TFIDF', 'OR_TFIDF_NB', 'compare'):
                body = {'dataset': dataset, 'algorithm': method}
                response = self.client.post('/api/workbench/run', json=body)
                self.assertEqual(response.status_code, 200, response.text[:200])
                first = response.json()['report']
                second = self.client.post('/api/workbench/run', json=body).json()['report']
                self.assertEqual(first['metrics'], second['metrics'])
                self.assertEqual(first['dataset'], dataset)
                self.assertEqual(first['algorithm'], method)
                self.assertNotEqual(first['id'], second['id'])
                expected = {'OR', 'TFIDF', 'OR_TFIDF', 'OR_TFIDF_NB'} if method == 'compare' else {'OR', method}
                self.assertEqual(set(first['metrics']), expected)

    def test_api_validation_and_boundaries(self):
        for body in ([], None, {'algorithm': '__import__("os")'}, {'dataset': '../private'}, {'tasks': []},
                     {'dataset': ['ann1-dev']}, {'algorithm': {}}, {'dataset': 'ann1-train'},
                     {'dataset': 'ann1-test_common'}, {'dataset': 'ann1-test_common', 'acknowledge_test': 'yes'}):
            self.assertEqual(self.client.post('/api/workbench/run', content=json.dumps(body), headers={'Content-Type':'application/json'}).status_code, 400)
        self.assertEqual(self.client.post('/api/workbench/run', content='{', headers={'Content-Type':'application/json'}).status_code, 400)
        self.assertEqual(self.client.post('/api/workbench/run', content='x'*5000, headers={'Content-Type':'application/json'}).status_code, 413)
        self.assertEqual(self.client.post('/api/workbench/run', content='{}').status_code, 415)
        self.assertEqual(self.client.post('/api/workbench/run', json={}, headers={'Origin':'https://elsewhere.example'}).status_code, 403)
        with patch.dict(os.environ, {'XAMR_ACCESS_KEY':'test-key'}):
            self.assertEqual(self.client.post('/api/workbench/run', json={}).status_code, 401)
        RUN_SLOTS.acquire(); RUN_SLOTS.acquire()
        try:
            self.assertEqual(self.client.post('/api/workbench/run', json={}).status_code, 409)
        finally:
            RUN_SLOTS.release(); RUN_SLOTS.release()
        with patch('app.run_in_threadpool', side_effect=RuntimeError('test failure')), self.assertLogs(level='ERROR'):
            self.assertEqual(self.client.post('/api/workbench/run', json={}).status_code, 500)
        self.assertEqual(validate_request({'dataset':'ann1-test_common','acknowledge_test':True})[0], 'ann1-test_common')

    def test_checksum_rejected_before_inference(self):
        from research_runner import fetch_dataset
        with tempfile.TemporaryDirectory() as folder, patch('research_runner.BASE', Path(folder)), patch('research_runner.urllib.request.urlopen', return_value=io.BytesIO(b'[]')):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                fetch_dataset('ann1-dev', Path(folder) / 'cache')

    def test_original_routes_unchanged(self):
        self.assertEqual(hashlib.sha256((BASE/'static/legacy.html').read_bytes()).hexdigest(), '8d113bb889b1c788c4813a208ddbdf5647e282362bc678552c339088830efce9')
        self.assertEqual(hashlib.sha256((BASE/'static/paper.html').read_bytes()).hexdigest(), 'e650dd0bd3806ea2e23a9fd4085d07ec70ef441547c40bfb393110ca4fc401e3')
        self.assertEqual(self.client.get('/legacy').text, (BASE/'static/legacy.html').read_text())
        self.assertEqual(self.client.get('/paper').text.replace('<script>window.CLOUD_MODE=true;</script><script src="/cloud.js"></script><script>', '<script>', 1), (BASE/'static/paper.html').read_text())
        for route in ('/', '/demo', '/research.js', '/research.css', '/api/workbench/catalog'):
            self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(len(catalog()['datasets']), 6)

if __name__ == '__main__':
    unittest.main()
