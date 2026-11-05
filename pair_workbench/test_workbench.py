"""Integrity tests; synthetic role data are software tests, never research results."""
import importlib.util, io, json, tempfile, unittest
import numpy as np
from engine import builtin, validate, read_table
from server import excel
from algorithms.pair_experiment import run, role_features

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=validate(builtin('small_A'))
    def test_pilot_split(self):
        self.assertEqual(len(self.data),424)
        self.assertEqual(self.data[self.data.split=='test'].shape[0],171)
    def test_excel_roundtrip(self):
        self.assertEqual(len(validate(read_table(excel(self.data),'test.xlsx'))),424)
    def test_csv_roundtrip(self):
        raw=self.data.to_csv(index=False).encode('utf-8-sig')
        self.assertEqual(len(validate(read_table(raw,'test.csv'))),424)
    def test_leakage_rejected(self):
        f=self.data.copy(); i=f[f.split=='test'].index[0]; f.loc[i,'doc_a']=f[f.split=='train'].iloc[0].doc_a
        with self.assertRaisesRegex(ValueError,'group_id|leakage'):validate(f)
    def test_bad_label_rejected(self):
        f=self.data.copy(); f['label']=f.label.astype(str); f.loc[0,'label']='maybe'
        with self.assertRaisesRegex(ValueError,'label'):validate(f)
    def test_duplicate_rejected(self):
        import pandas as pd
        f=pd.concat([self.data,self.data.iloc[[0]].assign(pair_id='different-id')])
        with self.assertRaisesRegex(ValueError,'ซ้ำ'):validate(f)
    def test_role_branch_and_train_only_vocabulary(self):
        train=self.data[self.data.split=='train'].copy(); test=self.data[self.data.split=='test'].copy()
        # Artificial fixture checks wiring only; these roles have NO source/annotation claim.
        for frame in [train,test]:
            for k,v in [('buyer_a','Synthetic Acquirer'),('buyer_b','Synthetic Acquirer'),('target_a','Synthetic Target One'),('target_b','Synthetic Target Two')]:frame[k]=v
        test['text_a']=test.text_a+' heldoutuniquetoken'
        output=run(train,test.drop(columns=['label']),{'seed':374,'role_source':'manual'})
        self.assertNotIn('heldoutuniquetoken',output['vectorizer']['vocabulary'])
        self.assertIn('text_plus_roles',output['models'])
        self.assertEqual(len(output['models']['text_plus_roles']['scores']),len(test))
    def test_missing_roles_skipped_and_reproducible(self):
        train=self.data[self.data.split=='train']; test=self.data[self.data.split=='test'].drop(columns=['label'])
        a=run(train,test,{'seed':374,'role_source':'none'}); b=run(train,test,{'seed':374,'role_source':'none'})
        self.assertNotIn('text_plus_roles',a['models'])
        self.assertEqual(a['models']['text_baseline']['scores'],b['models']['text_baseline']['scores'])
    def test_role_direction(self):
        import pandas as pd
        f=pd.DataFrame([{'buyer_a':'A','target_a':'B','buyer_b':'B','target_b':'A'}])
        self.assertEqual(role_features(f)[0].tolist(),[0,0,1,1,1,1,1])

if __name__=='__main__': unittest.main(verbosity=2)
