"""Deletion safety tests use isolated temporary records, never real experiments."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server


class HistoryDeletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'runs').mkdir()
        self.root_patch = patch.object(server, 'ROOT', self.root)
        self.active_patch = patch.object(server, 'ACTIVE', None)
        self.root_patch.start(); self.active_patch.start()

    def tearDown(self):
        self.active_patch.stop(); self.root_patch.stop(); self.temp.cleanup()

    def record(self, run_id, status='completed'):
        folder = self.root / 'runs' / run_id
        folder.mkdir()
        (folder / 'manifest.json').write_text(json.dumps({'run_id':run_id,'status':status}))
        (folder / 'dataset.csv').write_text('original research evidence')
        return folder

    def test_delete_one_preserves_other_runs_and_dataset(self):
        one=self.record('20261028T120000Z_aaaaaa')
        other=self.record('20261028T120001Z_bbbbbb')
        data=self.root/'source.csv'; data.write_text('source data')
        result=server.delete_runs('one',one.name)
        self.assertEqual(result['deleted'],[one.name])
        self.assertFalse(one.exists()); self.assertTrue(other.exists()); self.assertTrue(data.exists())

    def test_all_covers_more_than_50_but_skips_unrelated_directories_and_symlinks(self):
        for i in range(55): self.record(f'20261028T12{i//60:02}{i%60:02}Z_{i:06x}')
        other=self.root/'runs'/'notes';other.mkdir();(other/'notes.txt').write_text('keep')
        outside=self.root/'outside';outside.mkdir();(outside/'manifest.json').write_text('{}')
        (self.root/'runs'/'20261028T130000Z_ffffff').symlink_to(outside, target_is_directory=True)
        self.assertEqual(server.delete_runs('all')['count'],55)
        self.assertTrue(other.exists()); self.assertTrue(outside.exists())

    def test_running_record_blocks_all_without_partial_deletion(self):
        complete=self.record('20261028T120000Z_aaaaaa')
        running=self.record('20261028T120001Z_bbbbbb','running')
        with self.assertRaisesRegex(ValueError,'กำลังรัน'):server.delete_runs('all')
        self.assertTrue(complete.exists());self.assertTrue(running.exists())
        with self.assertRaisesRegex(ValueError,'กำลังรัน'):server.delete_runs('one',running.name)

    def test_active_record_and_invalid_paths_are_rejected(self):
        folder=self.record('20261028T120000Z_aaaaaa')
        with patch.object(server,'ACTIVE',folder.name), self.assertRaisesRegex(ValueError,'กำลังรัน'):
            server.delete_runs('one',folder.name)
        for value in ('../source.csv', '', '20261028T120000Z_aaaaaa/..'):
            with self.assertRaises(ValueError):server.delete_runs('one',value)
        self.assertTrue(folder.exists())


if __name__ == '__main__': unittest.main()
