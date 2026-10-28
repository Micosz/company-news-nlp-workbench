"""Synthetic checks for the combined feature pipeline; not research results."""
import unittest
import numpy as np
import pandas as pd
import json, tempfile, contextlib, io, shutil
from pathlib import Path
import worker
from algorithms.pair_experiment import run
from engine import builtin, validate


class JointFeatureTests(unittest.TestCase):
    def setUp(self):
        data=validate(builtin('small_A'))
        for c,v in {'buyer_a':'Buyer','buyer_b':'Buyer','target_a':'Target',
                    'target_b':'Target','event_date_a':'2020-01-01',
                    'event_date_b':'2020-01-01'}.items():
            data[c]=v
        data.loc[data.index[::2],'event_date_b']='2020-01-02'
        self.train=data[data.split=='train'].copy()
        self.test=data[data.split=='test'].drop(columns=['label']).copy()
        self.config={'role_source':'manual','time_source':'oracle'}

    def test_combination_and_control_keep_same_baseline_and_classifier(self):
        plain=run(self.train,self.test,{'role_source':'none','time_source':'none'})
        joint=run(self.train,self.test,self.config)
        self.assertEqual(plain['models']['text_baseline']['scores'],joint['models']['text_baseline']['scores'])
        self.assertEqual(plain['vectorizer'],joint['vectorizer'])
        self.assertEqual(joint['joint_coverage'],{'train_complete_pairs':253,'test_complete_pairs':171})
        for name in ('text_baseline','text_plus_roles','text_plus_time','text_plus_roles_time','text_plus_roles_availability'):
            model=joint['models'][name]
            self.assertEqual(model['fitted_parameters']['classifier'],'CategoricalNB')
            self.assertEqual(model['fitted_parameters']['class_count'],joint['models']['text_baseline']['fitted_parameters']['class_count'])
            self.assertTrue(np.isfinite(model['scores']).all())
            self.assertEqual(len(model['scores']),len(self.test))
        self.assertIn('event_day_relation',joint['models']['text_plus_roles_time']['features'])
        self.assertIn('both_dates_available',joint['models']['text_plus_roles_availability']['features'])

    def test_missing_or_non_overlapping_joint_data_skip_combination(self):
        test=self.test.copy();test['event_date_b']=''
        out=run(self.train,test,self.config)
        self.assertNotIn('text_plus_roles_time',out['models'])
        self.assertNotIn('text_plus_roles_availability',out['models'])
        self.assertEqual(out['joint_coverage']['test_complete_pairs'],0)
        self.assertTrue(any('Joint role/time experiment skipped' in w for w in out['warnings']))
        test=self.test.copy();test.loc[test.index[::2],'target_a']='';test.loc[test.index[1::2],'event_date_b']=''
        out=run(self.train,test,self.config)
        self.assertGreater(out['role_coverage']['test_complete_pairs'],0)
        self.assertGreater(out['time_coverage']['test_complete_pairs'],0)
        self.assertEqual(out['joint_coverage']['test_complete_pairs'],0)
        self.assertNotIn('text_plus_roles_time',out['models'])

    def test_source_declarations_are_required(self):
        for config in ({'role_source':'none','time_source':'oracle'}, {'role_source':'manual','time_source':'none'}):
            out=run(self.train,self.test,config)
            self.assertNotIn('text_plus_roles_time',out['models'])

    def test_dev_coverage_does_not_count_as_joint_test_evidence(self):
        rows=[]
        for split in ('train','dev','test'):
            for label in (0,1):
                key=f'{split}_{label}'
                row={'pair_id':key,'text_a':f'{key} alpha','text_b':f'{key} beta',
                     'doc_a':key+'a','doc_b':key+'b','group_id':key,'split':split,'label':label,
                     'buyer_a':'Buyer','buyer_b':'Buyer','target_a':'Target','target_b':'Target',
                     'event_date_a':'2020-01-01','event_date_b':'2020-01-02'}
                if split=='test' and label==0: row['event_date_b']=''
                if split=='test' and label==1: row['target_b']=''
                rows.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            pd.DataFrame(rows).to_csv(folder/'dataset.csv',index=False)
            (folder/'manifest.json').write_text(json.dumps({'run_id':'synthetic-check','source':'synthetic','limitations':[]}))
            (folder/'config.json').write_text(json.dumps({**self.config,'threshold_mode':'dev_f1'}))
            shutil.copy(Path('algorithms/pair_experiment.py'),folder/'algorithm.py')
            with contextlib.redirect_stdout(io.StringIO()): worker.main(folder)
            manifest=json.loads((folder/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'completed',manifest.get('error'))
            result=json.loads((folder/'metrics.json').read_text())
            self.assertEqual(result['joint_coverage']['test_complete_pairs'],0)
            self.assertNotIn('text_plus_roles_time',result['models'])
            self.assertNotIn('text_plus_roles_availability',result['models'])
            self.assertTrue(any('no test pair' in w for w in result['warnings']))


if __name__=='__main__': unittest.main()
