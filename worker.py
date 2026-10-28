"""Execute one saved experiment: python worker.py /absolute/run/folder"""
import csv, hashlib, html, importlib.util, importlib.metadata, json, re, sys, time, traceback, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, accuracy_score
from engine import ROOT, dump, validate


def _normal_text(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', html.unescape(str(value)))).strip()


def _read_reference(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def prepare_pilot_clustering(test, pilot_dir=None):
    """Verify a complete, unmodified held-out Pilot topic, independent of predictions.

    Gold labels are read only for evaluation, after candidate pairs have already
    been selected in the supplied dataset. Full ECB+ has sampled pairs and is
    intentionally ineligible: missing pairs may not be presumed negative.
    """
    pilot_dir = Path(pilot_dir) if pilot_dir is not None else ROOT / 'data' / 'pilot'
    if not {'mention_a', 'mention_b'}.issubset(test.columns):
        return None, 'Clustering skipped: test rows lack original mention IDs.'
    groups = set(test.group_id.astype(str))
    if len(groups) != 1 or not groups.issubset({'43', '44'}):
        return None, 'Clustering skipped: supported only for one complete Pilot test topic, not Full or sampled pairs.'
    topic = next(iter(groups))
    paths = {'mentions': pilot_dir / 'event_mentions.csv', 'pairs': pilot_dir / 'pairs.csv'}
    if not all(path.is_file() for path in paths.values()):
        return None, 'Clustering skipped: Pilot reference files are not available.'
    mentions = {row['mention_id']: row for row in _read_reference(paths['mentions']) if row['topic_id'] == topic}
    reference_pairs = {row['pair_id']: row for row in _read_reference(paths['pairs']) if row['topic_id'] == topic}
    n = len(mentions)
    if n < 2 or len(reference_pairs) != n * (n - 1) // 2:
        return None, 'Clustering skipped: Pilot reference is not a complete set of mention pairs.'
    if len(test) != len(reference_pairs) or set(test.pair_id.astype(str)) != set(reference_pairs):
        return None, 'Clustering skipped: test does not contain every reference pair in the Pilot topic.'
    if any(not row.get('gold_event_cluster') for row in mentions.values()):
        return None, 'Clustering skipped: reference gold clusters are incomplete.'
    seen = set()
    for row in test.to_dict('records'):
        a, b = str(row['mention_a']), str(row['mention_b'])
        original = reference_pairs[str(row['pair_id'])]
        if a not in mentions or b not in mentions or a == b:
            return None, 'Clustering skipped: test mention IDs do not match the Pilot reference.'
        pair = tuple(sorted((a, b)))
        original_pair = tuple(sorted((original['mention_id_a'], original['mention_id_b'])))
        if pair != original_pair or pair in seen:
            return None, 'Clustering skipped: duplicated or mismatched mention pairs.'
        seen.add(pair)
        if any(str(row[f'doc_{side}']) != mentions[mention]['document_id'] or
               _normal_text(row[f'text_{side}']) != _normal_text(mentions[mention]['context_normalized'])
               for side, mention in (('a', a), ('b', b))):
            return None, 'Clustering skipped: test context or document does not match the Pilot reference.'
        gold_same = int(mentions[a]['gold_event_cluster'] == mentions[b]['gold_event_cluster'])
        if int(row['label']) != gold_same or str(original['label_same_event']) != str(gold_same):
            return None, 'Clustering skipped: pair labels disagree with the reference gold clusters.'
    if len(seen) != n * (n - 1) // 2:
        return None, 'Clustering skipped: pair coverage is incomplete.'
    gold = {mention: row['gold_event_cluster'] for mention, row in mentions.items()}
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    return {'topic': topic, 'gold': gold, 'reference_sha256': hashes}, None


def evaluate_clusters(gold, pairs, predictions):
    """Connected components on predicted-positive edges and mention-weighted B³."""
    if not gold or len(pairs) != len(predictions):
        raise ValueError('Clustering requires gold mention IDs and one prediction per pair')
    parent = {mention: mention for mention in gold}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    for (a, b), prediction in zip(pairs, predictions):
        if a not in parent or b not in parent or a == b or int(prediction) not in (0, 1):
            raise ValueError('Invalid clustering pair or prediction')
        if int(prediction) == 1:
            union(a, b)
    predicted = {mention: find(mention) for mention in gold}
    predicted_sets, gold_sets = {}, {}
    for mention in gold:
        predicted_sets.setdefault(predicted[mention], set()).add(mention)
        gold_sets.setdefault(gold[mention], set()).add(mention)
    precision, recall = 0.0, 0.0
    for mention in gold:
        p, g = predicted_sets[predicted[mention]], gold_sets[gold[mention]]
        overlap = len(p & g)
        precision += overlap / len(p)
        recall += overlap / len(g)
    precision /= len(gold)
    recall /= len(gold)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {'b3_precision': precision, 'b3_recall': recall, 'b3_f1': f1,
            'predicted_clusters': len(predicted_sets)}, predicted


def choose_dev_threshold(labels, scores):
    """Maximise positive F1 on dev only; deterministic tie closest to 0.5."""
    from sklearn.metrics import precision_recall_curve
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    denom=precision[:-1]+recall[:-1]
    f1=np.divide(2*precision[:-1]*recall[:-1],denom,out=np.zeros_like(denom),where=denom!=0)
    best=np.flatnonzero(np.isclose(f1,f1.max(),rtol=0,atol=1e-12))
    index=best[np.argmin(np.abs(thresholds[best]-0.5))]
    return float(thresholds[index]),float(f1[index])


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
        inputs=['text_a','text_b','buyer_a','target_a','buyer_b','target_b','event_date_a','event_date_b']
        dev=data[data.split=='dev'].reset_index(drop=True)
        tune=config.get('threshold_mode','fixed') == 'dev_f1'
        eval_inputs=pd.concat([dev[inputs],test[inputs]],ignore_index=True) if tune else test[inputs].copy()
        output=module.run(train[inputs+['label']].copy(),eval_inputs,config)
        models=output.pop('models')
        # Calculate joint coverage on held-out test alone, never dev+test.
        if 'joint_coverage' in output:
            unknown={'','unknown','unk','n/a','na','none','null','nan','ไม่ทราบ','ไม่ระบุ','-'}
            cols=['buyer_a','target_a','buyer_b','target_b','event_date_a','event_date_b']
            known=pd.concat([~test[c].astype(str).str.strip().str.casefold().isin(unknown) for c in cols],axis=1).all(axis=1)
            output['joint_coverage']['test_complete_pairs']=int(known.sum())
            if not known.any():
                for name in ('text_plus_roles_time','text_plus_roles_availability'):
                    models.pop(name,None)
                output.setdefault('warnings',[]).append('Joint role/time experiment skipped: no test pair has both complete roles and dates.')
        if tune:
            # Algorithm saw dev + test inputs; coverage must still describe test only.
            unknown={'','unknown','unk','n/a','na','none','null','nan','ไม่ทราบ','ไม่ระบุ','-'}
            for key, cols in (('role_coverage',['buyer_a','target_a','buyer_b','target_b']),
                              ('time_coverage',['event_date_a','event_date_b'])):
                if 'test_complete_pairs' in output.get(key, {}):
                    known=pd.concat([~test[c].astype(str).str.strip().str.casefold().isin(unknown) for c in cols],axis=1).all(axis=1)
                    output[key]['test_complete_pairs']=int(known.sum())
            for name, model in models.items():
                scores=np.asarray(model['scores'],dtype=float)
                if scores.shape!=(len(dev)+len(test),) or not np.isfinite(scores).all() or ((scores<0)|(scores>1)).any():
                    raise ValueError(f'{name}: invalid dev/test scores')
                model['scores']=scores[len(dev):].tolist()
                if name == 'majority_reference': continue
                model['threshold'],model['dev_f1']=choose_dev_threshold(dev.label.to_numpy(),scores[:len(dev)])
        fitted=output.pop('vectorizer',{})
        dump(folder/'vectorizer.json',fitted)
        result={'models':{},'warnings':output.get('warnings',[]),'role_coverage':output.get('role_coverage',{}), 'time_coverage':output.get('time_coverage',{}), 'joint_coverage':output.get('joint_coverage',{}),
                'method':output.get('method','custom'), 'test_pairs':len(test)}
        # The model has already produced all scores before the gold clustering
        # reference is inspected. The reference is never passed as a feature.
        try:
            cluster_reference, cluster_error = prepare_pilot_clustering(test)
        except (OSError, UnicodeError, csv.Error, KeyError, ValueError, TypeError) as exc:
            # A broken optional reference must not destroy valid pairwise results.
            cluster_reference, cluster_error = None, f'Clustering skipped: cannot verify Pilot reference ({exc}).'
        cluster_rows = []
        if cluster_reference:
            result['clustering'] = {'status': 'available', 'method': 'connected_components',
                'reference': 'ECB+ Pilot gold event clusters', 'test_topic': cluster_reference['topic'],
                'test_mentions': len(cluster_reference['gold']),
                'gold_clusters': len(set(cluster_reference['gold'].values())),
                'reference_sha256': cluster_reference['reference_sha256'], 'models': {},
                'limitations': ['Pilot only: one test topic and two gold clusters.',
                    'Positive edges are grouped with connected components; chains can merge distinct events.',
                    'B³ is not CoNLL F1 and cannot be compared directly to CohTP without matching protocol.',
                    'Manual roles are oracle inputs and may act as shortcuts on this small Pilot.']}
            dump(folder/'clustering_reference.json', {'topic': cluster_reference['topic'],
                'mention_gold_clusters': cluster_reference['gold'],
                'reference_sha256': cluster_reference['reference_sha256']})
        else:
            result['clustering'] = {'status': 'unavailable', 'reason': cluster_error}
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
            if 'dev_f1' in model: result['models'][name]['dev_f1']=model['dev_f1']
            if cluster_reference:
                pair_ids = list(zip(test.mention_a.astype(str), test.mention_b.astype(str)))
                cluster_scores, assignments = evaluate_clusters(cluster_reference['gold'], pair_ids, pred)
                result['clustering']['models'][name] = cluster_scores
                for mention in sorted(assignments):
                    cluster_rows.append({'model': name, 'mention_id': mention,
                        'predicted_cluster': assignments[mention],
                        'gold_cluster': cluster_reference['gold'][mention]})
            predframe=test.copy(); predframe['model']=name; predframe['score']=scores; predframe['prediction']=pred
            predframe['error']=predframe.label!=predframe.prediction; exports.append(predframe)
            safe_name=''.join(x for x in name if x.isalnum() or x=='_')[:80]
            dump(folder/f'model_{safe_name}.json',{k:v for k,v in model.items() if k!='scores'})
        if not exports: raise ValueError('Algorithm returned no models')
        predictions=pd.concat(exports,ignore_index=True)
        predictions.to_csv(folder/'predictions.csv',index=False,encoding='utf-8-sig')
        predictions[predictions.error].to_csv(folder/'errors.csv',index=False,encoding='utf-8-sig')
        if cluster_reference:
            pd.DataFrame(cluster_rows).to_csv(folder/'cluster_predictions.csv',index=False,encoding='utf-8-sig')
        if {'text_baseline','text_plus_roles'}.issubset(result['models']):
            result['delta_f1']=result['models']['text_plus_roles']['f1']-result['models']['text_baseline']['f1']
        if {'text_baseline','text_plus_time'}.issubset(result['models']):
            result['delta_time_f1']=result['models']['text_plus_time']['f1']-result['models']['text_baseline']['f1']
            a, b = test.event_date_a.ne('').to_numpy(), test.event_date_b.ne('').to_numpy()
            result['time_strata'] = {}
            for key, mask in [('both', a & b), ('one', a ^ b), ('neither', ~a & ~b)]:
                if not mask.any(): continue
                labels = test.label.to_numpy()[mask]
                scores = {}
                for name in ('text_baseline', 'text_plus_time'):
                    model = models[name]
                    pred = (np.asarray(model['scores'])[mask] >= float(model.get('threshold', 0.5))).astype(int)
                    p, r, f, _ = precision_recall_fscore_support(labels, pred, average='binary', zero_division=0)
                    scores[name] = {'precision':float(p), 'recall':float(r), 'f1':float(f)}
                result['time_strata'][key] = {'pairs':int(mask.sum()), 'positive_pairs':int(labels.sum()), 'models':scores}
        result['elapsed_seconds']=round(time.perf_counter()-started,3)
        dump(folder/'metrics.json',result)
        manifest.update(status='completed', elapsed_seconds=result['elapsed_seconds'])
        manifest['environment']={'python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','openpyxl']}}
        lines=['# Experiment record',f"Run: {manifest['run_id']}",f"Source: {manifest['source']}",
               'Custom pairwise baseline; NOT a reproduction of CohTP.',result['method'],
               '| Model | Precision | Recall | F1 | Macro F1 |','|---|---:|---:|---:|---:|']
        for n,m in result['models'].items(): lines.append(f"| {n} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['macro_f1']:.4f} |")
        if cluster_reference:
            lines += ['', '## Clustering (B³, Pilot test topic only)',
                      'Positive pair predictions → undirected graph → connected components. B³ averages per-mention precision and recall.',
                      '| Model | B³ Precision | B³ Recall | B³ F1 | Predicted clusters |', '|---|---:|---:|---:|---:|']
            for n,m in result['clustering']['models'].items():
                lines.append(f"| {n} | {m['b3_precision']:.4f} | {m['b3_recall']:.4f} | {m['b3_f1']:.4f} | {m['predicted_clusters']} |")
            lines += ['', *['- '+x for x in result['clustering']['limitations']]]
        else:
            lines += ['', 'Clustering unavailable: '+cluster_error]
        lines+=['','Warnings:']+['- '+x for x in result['warnings']+manifest['limitations']]
        (folder/'report.md').write_text('\n'.join(lines),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        manifest.update(status='failed',error=str(exc)); traceback.print_exc()
    dump(folder/'manifest.json',manifest)
    return 0 if manifest['status']=='completed' else 1

if __name__=='__main__': sys.exit(main(Path(sys.argv[1]).resolve()))
