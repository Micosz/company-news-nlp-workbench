"""Contract checks for the portable, AI-assisted Pilot role metadata."""
import csv
import tempfile
import unittest
from pathlib import Path

from algorithms.pair_experiment import run
from engine import ROOT, builtin, load_provisional_roles, prepare_run, validate
from worker import prepare_pilot_clustering


class ProvisionalRoleTests(unittest.TestCase):
    def test_builtin_ai_roles_cannot_be_recorded_as_manual(self):
        with self.assertRaisesRegex(ValueError, 'ยังไม่ได้ผ่านการตรวจโดยคน'):
            prepare_run(builtin('small_A_ai'), '', {'role_source': 'manual'}, 'small_A_ai')

    def test_folds_only_add_roles_and_preserve_original_splits_and_contexts(self):
        for fold in ('A', 'B'):
            plain = builtin('small_' + fold)
            annotated = builtin('small_' + fold + '_ai')
            cols = ['pair_id', 'text_a', 'text_b', 'label', 'split', 'doc_a',
                    'doc_b', 'group_id', 'mention_a', 'mention_b']
            self.assertTrue(plain[cols].equals(annotated[cols]))
            self.assertTrue((plain[['buyer_a','target_a','buyer_b','target_b']] == '').all().all())
            self.assertTrue((annotated[['buyer_a','target_a','buyer_b','target_b']] != '').all().all())
            valid = validate(annotated)
            self.assertEqual(len(valid), 424)
            reference, error = prepare_pilot_clustering(valid[valid.split == 'test'])
            self.assertIsNone(error)
            self.assertIsNotNone(reference)

    def test_real_pilot_uses_same_text_baseline_for_ablation(self):
        data = validate(builtin('small_A_ai'))
        train = data[data.split == 'train']
        test = data[data.split == 'test'].drop(columns=['label'])
        baseline = run(train, test, {'seed': 374, 'role_source': 'none'})
        proposed = run(train, test, {'seed': 374, 'role_source': 'predicted'})
        self.assertEqual(baseline['models']['text_baseline']['scores'],
                         proposed['models']['text_baseline']['scores'])
        self.assertEqual(baseline['vectorizer'], proposed['vectorizer'])
        self.assertIn('text_plus_roles', proposed['models'])
        self.assertEqual(proposed['role_coverage'], {'train_complete_pairs':253, 'test_complete_pairs':171})
        self.assertTrue(any('does not evaluate or verify' in w for w in proposed['warnings']))

    def test_metadata_is_provisional_and_has_evidence_offsets(self):
        roles = load_provisional_roles()
        self.assertEqual(len(roles), 42)
        for row in roles.values():
            self.assertIn('human_review_pending', row['provenance'])
            self.assertEqual(len(row['document_sha256']), 64)
            for role in ('buyer','target'):
                self.assertLess(int(row[role+'_evidence_start']), int(row[role+'_evidence_end']))

    def test_duplicate_or_missing_mention_is_rejected(self):
        path = ROOT / 'data/pilot/pilot_roles_ai_provisional.csv'
        with path.open(encoding='utf-8', newline='') as src:
            reader = csv.DictReader(src)
            fields, rows = reader.fieldnames, list(reader)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'roles.csv'
            for bad in (rows[:-1], rows + [rows[0]]):
                with dest.open('w', encoding='utf-8', newline='') as out:
                    writer = csv.DictWriter(out, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(bad)
                with self.assertRaises(ValueError):
                    load_provisional_roles(dest)


if __name__ == '__main__':
    unittest.main(verbosity=2)
