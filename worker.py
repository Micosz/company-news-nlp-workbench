"""Execute one saved experiment: python worker.py /absolute/run/folder"""
import importlib.util, importlib.metadata, json, sys, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, accuracy_score
from engine import dump, validate


def main(folder):
    started=time.perf_counter()
    manifest=json.loads((folder/'manifest.json').read_text())
    try:
        data=validate(pd.read_csv(folder/'dataset.csv',dtype=str,keep_default_na=False))
        train=data[data.split=='train'].reset_index(drop=True)
        test=data[data.split=='test'].reset_index(drop=True)
        config=json.loads((folder/'config.json').read_text())
        spec=importlib.util.spec_from_file_location('user_algorithm',folder/'algorithm.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        inputs=['text_a','text_b','buyer_a','target_a','buyer_b','target_b']
        output=module.run(train[inputs+['label']].copy(),test[inputs].copy(),config)
        models=output.pop('models')
        fitted=output.pop('vectorizer',{})
        dump(folder/'vectorizer.json',fitted)
        result={'models':{},'warnings':output.get('warnings',[]),'role_coverage':output.get('role_coverage',{}),
                'method':output.get('method','custom'), 'test_pairs':len(test)}
        exports=[]
        for name, model in models.items():
            scores=np.asarray(model['scores'],dtype=float)
            if scores.shape!=(len(test),) or not np.isfinite(scores).all(): raise ValueError(f'{name}: invalid scores')
            if ((scores<0)|(scores>1)).any(): raise ValueError('Scores must lie in [0,1]')
            threshold=float(model.get('threshold',0.5))
            if not 0<=threshold<=1: raise ValueError('Invalid threshold')
            pred=(scores>=threshold).astype(int)
            p,r,f,_=precision_recall_fscore_support(test.label,pred,average='binary',zero_division=0)
            _,_,macro,_=precision_recall_fscore_support(test.label,pred,average='macro',zero_division=0)
            tn,fp,fn,tp=confusion_matrix(test.label,pred,labels=[0,1]).ravel().tolist()
            result['models'][name]={'precision':float(p),'recall':float(r),'f1':float(f),'macro_f1':float(macro),
                'accuracy':float(accuracy_score(test.label,pred)),'confusion':{'tn':tn,'fp':fp,'fn':fn,'tp':tp},
                'threshold':threshold,'features':model.get('features',[])}
            predframe=test.copy(); predframe['model']=name; predframe['score']=scores; predframe['prediction']=pred
            predframe['error']=predframe.label!=predframe.prediction; exports.append(predframe)
            safe_name=''.join(x for x in name if x.isalnum() or x=='_')[:80]
            dump(folder/f'model_{safe_name}.json',{k:v for k,v in model.items() if k!='scores'})
        if not exports: raise ValueError('Algorithm returned no models')
        predictions=pd.concat(exports,ignore_index=True)
        predictions.to_csv(folder/'predictions.csv',index=False,encoding='utf-8-sig')
        predictions[predictions.error].to_csv(folder/'errors.csv',index=False,encoding='utf-8-sig')
        if {'text_baseline','text_plus_roles'}.issubset(result['models']):
            result['delta_f1']=result['models']['text_plus_roles']['f1']-result['models']['text_baseline']['f1']
        result['elapsed_seconds']=round(time.perf_counter()-started,3)
        dump(folder/'metrics.json',result)
        manifest.update(status='completed', elapsed_seconds=result['elapsed_seconds'])
        manifest['environment']={'python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','openpyxl']}}
        lines=['# Experiment record',f"Run: {manifest['run_id']}",f"Source: {manifest['source']}",
               'Custom pairwise baseline; NOT a reproduction of CohTP.',result['method'],
               '| Model | Precision | Recall | F1 | Macro F1 |','|---|---:|---:|---:|---:|']
        for n,m in result['models'].items(): lines.append(f"| {n} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['macro_f1']:.4f} |")
        lines+=['','Warnings:']+['- '+x for x in result['warnings']+manifest['limitations']]
        (folder/'report.md').write_text('\n'.join(lines),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        manifest.update(status='failed',error=str(exc)); traceback.print_exc()
    dump(folder/'manifest.json',manifest)
    return 0 if manifest['status']=='completed' else 1

if __name__=='__main__': sys.exit(main(Path(sys.argv[1]).resolve()))
