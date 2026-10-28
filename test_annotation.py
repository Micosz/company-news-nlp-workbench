"""Checks for evidence-backed annotation and pair generation; no research results."""
import tempfile
import unittest
from pathlib import Path

from engine import builtin
from scripts.annotate_roles import apply_annotations, blank_annotation, check_annotations, read_sheet, write_sheet


class AnnotationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.frame = blank_annotation()

    def add_synthetic_annotation(self):
        # Marker values test routing only; they are not annotations of real companies.
        context = self.frame.loc[0, 'context']
        evidence = context.split()[0]
        self.frame.loc[0, ['buyer', 'buyer_evidence', 'target', 'target_evidence', 'annotator']] = [
            'UNIT_TEST_BUYER', evidence, 'UNIT_TEST_TARGET', evidence, 'unit test']

    def test_template_blinds_gold_and_starts_empty(self):
        self.assertEqual(len(self.frame), 42)
        self.assertTrue(self.frame.mention_id.is_unique)
        self.assertEqual(set(self.frame.columns), {'mention_id', 'context', 'buyer', 'buyer_evidence',
                                                    'target', 'target_evidence', 'annotator', 'notes'})
        self.assertTrue((self.frame[['buyer', 'target']] == '').all().all())

    def test_roles_map_to_pairs_in_both_folds_without_changing_labels_or_splits(self):
        self.add_synthetic_annotation()
        ident = self.frame.loc[0, 'mention_id']
        for mode in ('small_A', 'small_B'):
            with self.subTest(mode=mode):
                before = builtin(mode)
                after = apply_annotations(self.frame, mode)
                self.assertEqual(len(after), 424)
                for field in ('pair_id', 'text_a', 'text_b', 'label', 'split', 'doc_a', 'doc_b', 'group_id'):
                    self.assertEqual(before[field].tolist(), after[field].tolist())
                found = 0
                for side in ('a', 'b'):
                    selected = after[f'mention_{side}'] == ident
                    found += int(selected.sum())
                    self.assertTrue((after.loc[selected, f'buyer_{side}'] == 'UNIT_TEST_BUYER').all())
                    self.assertTrue((after.loc[~selected, f'buyer_{side}'] == '').all())
                self.assertGreater(found, 0)

    def test_missing_and_duplicate_mention_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ไม่ตรง'):
            check_annotations(self.frame.iloc[:-1])
        duplicate = self.frame.copy()
        duplicate.loc[1, 'mention_id'] = duplicate.loc[0, 'mention_id']
        with self.assertRaisesRegex(ValueError, 'ไม่ซ้ำ'):
            check_annotations(duplicate)

    def test_evidence_must_be_in_unchanged_context_and_annotator_required(self):
        self.add_synthetic_annotation()
        bad = self.frame.copy()
        bad.loc[0, 'buyer_evidence'] = 'invented evidence absent from the context'
        with self.assertRaisesRegex(ValueError, 'หลักฐาน'):
            check_annotations(bad)
        bad = self.frame.copy()
        bad.loc[0, 'context'] = 'invented replacement'
        with self.assertRaisesRegex(ValueError, 'บริบทถูกแก้ไข'):
            check_annotations(bad)
        bad = self.frame.copy()
        bad.loc[0, 'annotator'] = ''
        with self.assertRaisesRegex(ValueError, 'ผู้ทำ annotation'):
            check_annotations(bad)

    def test_unknown_must_be_blank_and_zero_role_evidence_stays_blank(self):
        bad = self.frame.copy()
        bad.loc[0, 'buyer'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'ให้เว้น'):
            check_annotations(bad)
        result = apply_annotations(self.frame, 'small_A')
        self.assertTrue((result[['buyer_a', 'target_a', 'buyer_b', 'target_b']] == '').all().all())

    def test_roundtrip_xlsx_csv_and_refuse_overwrite(self):
        self.add_synthetic_annotation()
        # Literal potentially formula-shaped text must not be made an Excel formula.
        self.frame.loc[0, 'notes'] = '=2+2'
        with tempfile.TemporaryDirectory() as tmp:
            for ext in ('csv', 'xlsx'):
                path = Path(tmp) / ('roles.' + ext)
                write_sheet(self.frame, path)
                saved = read_sheet(path)
                self.assertEqual(saved.loc[0, 'notes'], '=2+2')
                self.assertEqual(len(check_annotations(saved)), 42)
                before = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    write_sheet(self.frame, path)
                self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
