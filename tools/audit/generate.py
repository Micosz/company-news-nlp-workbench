#!/usr/bin/env python3
"""Generate a small, no-news-text audit dataset with original frozen inference."""
import argparse, hashlib, json, sys, urllib.request, subprocess, tempfile
from pathlib import Path
from collections import defaultdict

def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,default=Path(__file__).parent/'audit-data.json');p.add_argument('--cache',type=Path,default=Path(tempfile.gettempdir())/'xamr-audit-source-cache');a=p.parse_args()
 base=a.repo.resolve()/'xamr_lab';sys.path[:0]=[str(Path(__file__).parent/'.deps'),str(base)]
 import numpy as np
 import sklearn
 from sklearn.feature_extraction.text import TfidfVectorizer
 import tfidf_only as tf
 from analysis import compare_topics,topic_pair_counts
 from engine import validate
 from setup_data import COMMIT
 checks=json.loads((base/'dataset_checksums.json').read_text()); model_checks=json.loads((base/'models/checksums.json').read_text())
 provenance={'upstreamCommit':COMMIT,'repoCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.repo,text=True).strip(),'datasets':{},'models':{},'sourceHashes':{},'sklearnVersion':sklearn.__version__,'metric':'Pair F1, percentage 0–100; not CoNLL F1','notes':['Development split previously explored; illustrative stratified samples, not random or representative.','No article text included. Load original pinned annotation locally to read sentences/documents; redistribution rights are not granted here.','ARG dates and roles are supplied annotation values, not independently verified facts.','Pair labels use complete graph connected components, not only direct edges.']}
 for f in ['tfidf_only.py','tfidf_nb.py','or_nb_hybrid.py','engine.py','analysis.py','argument_audit.py','vendor/coreference.py','vendor/utils.py']:provenance['sourceHashes'][f]=sha((base/f).read_bytes())
 result={'schemaVersion':1,'provenance':provenance,'sampling':{'perTopicPerAnnotation':4,'strategy':'First deterministic example of each available category in priority order, then fill by pair ID; one known bridge forced per annotation. Cross-document pairs only.','priority':['new_fp','recovered_fn','unchanged_tp','unchanged_fp','unchanged_fn','unchanged_tn']},'pairs':[],'topics':[]}
 articles={};memberships={}
 a.cache.mkdir(parents=True,exist_ok=True)
 for ann in ['ann1','ann2']:
  name=f'{ann}-dev';url=f'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/{COMMIT}/project/annotations/ecb/{ann}/dev_xamr.json';source=f'https://github.com/ahmeshaf/gpt_coref/blob/{COMMIT}/project/annotations/ecb/{ann}/dev_xamr.json'
  local=a.cache/(name+'.json');raw=local.read_bytes() if local.exists() else urllib.request.urlopen(url,timeout=60).read()
  assert sha(raw)==checks[name], 'dataset checksum mismatch'
  local.write_bytes(raw);rows=validate(json.loads(raw));provenance['datasets'][name]={'sha256':sha(raw),'url':source,'mentions':len(rows)}
  raw_model=(base/'models'/f'{ann}.json').read_bytes();assert sha(raw_model)==model_checks[f'{ann}.json'];frozen=json.loads(raw_model);assert frozen['train_sha256']==checks[ann+'-train'];provenance['models'][ann]={'sha256':sha(raw_model),'selection':frozen['text_selection'],'path':f'xamr_lab/models/{ann}.json'}
  v=TfidfVectorizer(lowercase=True,ngram_range=(1,2),min_df=1,max_features=30000,norm='l2',vocabulary=frozen['tfidf']['vocabulary']);v.idf_=np.asarray(frozen['tfidf']['idf'])
  for r in rows:
   doc=r['doc_id'];article=articles.setdefault(doc,{'id':doc,'topic':r['topic'],'annotations':{}})
   entry=article['annotations'].setdefault(ann,{'mentionId':r['mention_id'],'lemma':r['lemma'],'arg0':r['arg0'],'arg1':r['arg1'],'date':r['argT'],'mentionCount':0,'sourceKey':name})
   entry['mentionCount']+=1
  ids,candidates,sims,edges,cross,weak=tf.prepare(rows,v);changed,added,cut=tf.edits(rows,ids,edges,weak,candidates,sims,frozen['text_selection']['policy']);before=dict(tf.predict(ids,edges));after=dict(tf.predict(ids,changed))
  predicted=[{'mention_id':r['mention_id'],'topic':r['topic'],'gold_cluster':r['gold_cluster'],'OR':before[r['mention_id']],'OR_TFIDF':after[r['mention_id']]} for r in rows]
  memberships[ann]=[[r['mention_id'],str(r['gold_cluster']),str(r['OR']),str(r['OR_TFIDF'])] for r in predicted]
  for t in compare_topics(predicted,'OR_TFIDF'):result['topics'].append({'ann':ann,'topic':t['topic'],'orF1':t['pair_F1_OR'],'hybridF1':t['pair_F1_OR_TFIDF'],'orFP':t['FP_OR'],'hybridFP':t['FP_OR_TFIDF'],'orFN':t['FN_OR'],'hybridFN':t['FN_OR_TFIDF'],'count':t['mentions']})
  buckets=defaultdict(lambda:defaultdict(list));known=None;added_set={tuple(sorted(map(int,e))) for e in added}
  for (i,j),sim in zip(candidates,sims):
   l,r=rows[i],rows[j];x,y=ids[i],ids[j];g=(l['topic'],l['gold_cluster'])==(r['topic'],r['gold_cluster']);b=before[x]==before[y];h=after[x]==after[y]
   kind=('recovered_fn' if g else 'new_fp') if not b and h else ('new_fn' if g else 'removed_fp') if b and not h else 'unchanged_'+('tp' if g and h else 'fn' if g else 'fp' if h else 'tn')
   pair={'id':ann+':'+x+'|'+y,'ann':ann,'topic':l['topic'],'mentions':[{ 'id':z['mention_id'],'doc':z['doc_id'],'date':z['argT'],'lemma':z['lemma'],'arg0':z['arg0'],'arg1':z['arg1'],'roleset':z['roleset_id'],'sourceUrl':source} for z in [l,r]],'orSame':b,'hybridSame':h,'goldSame':g,'kind':kind,'cosine':round(float(sim),6),'directAddedEdge':tuple(sorted((int(i),int(j)))) in added_set}
   buckets[l['topic']][kind].append(pair)
   if {x,y}=={'35_10ecb.xml_35','35_4ecbplus.xml_8'}:known=pair
  selected={}
  for topic in sorted(buckets,key=int):
   pool=buckets[topic];chosen=[]
   for kind in result['sampling']['priority']:
    if pool[kind] and len(chosen)<4:chosen.append(min(pool[kind],key=lambda q:q['id']))
   used={q['id'] for q in chosen}
   extra=sorted([q for v in pool.values() for q in v if q['id'] not in used],key=lambda q:q['id'])
   chosen+=extra[:4-len(chosen)]
   for q in chosen:selected[q['id']]=q
  assert known and known['directAddedEdge'] and known['kind']=='new_fp';selected[known['id']]=known;result['pairs']+=list(selected.values())
  totals={m:{k:sum(t[k] for t in topic_pair_counts(predicted,m).values()) for k in ['tp','fp','fn']} for m in ['OR','OR_TFIDF']}
  expected={'ann1':(926,2062,1547,2055,8),'ann2':(982,2312,1862,2148,16)}[ann]
  actual=(totals['OR']['fp'],totals['OR']['fn'],totals['OR_TFIDF']['fp'],totals['OR_TFIDF']['fn'],len(added));assert actual==expected,(actual,expected)
  provenance['datasets'][name]['verification']={'totals':totals,'addedEdges':len(added),'matchesPublishedTotals':True}
 result['pairs'].sort(key=lambda q:q['id']);assert len(result['pairs'])>=32
 a.output.with_name('cluster-memberships.json').write_text(json.dumps({'schemaVersion':1,'columns':['mentionId','goldCluster','orCluster','hybridCluster'],'note':'Cluster labels scoped to annotation + topic; gold is evaluation only, never inference input.','annotations':memberships},separators=(',',':')))
 catalog={'schemaVersion':1,'note':'Metadata-only catalogue. Labels are annotation fields, not original headlines. Representative mention is first in original dataset order. Read raw news only through local/imported original data.','sources':provenance['datasets'],'articles':sorted(articles.values(),key=lambda r:r['id'])}
 a.output.with_name('article-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 a.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8');print(f'{len(result["pairs"])} pairs, {len(result["topics"])} topics, {a.output.stat().st_size} bytes -> {a.output}')
if __name__=='__main__':main()
