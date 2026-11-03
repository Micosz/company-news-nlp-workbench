"""X-AMR baselines plus deterministic, cluster-level temporal constraints."""
import calendar,copy,csv,hashlib,io,itertools,json,platform,re,subprocess,sys,time,uuid,zipfile
from datetime import date,datetime,timezone
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from coval.eval.evaluator import evaluate_documents,muc,b_cubed,ceafe
from coval.conll.reader import get_coref_infos
from vendor.coreference import generate_eids,get_sparse_matrix,c_clustering,generate_key_file
from setup_data import BASE,FILES,COMMIT
METHODS=['EID_N','EID_lt','AND','OR','OR_temporal']
REQUIRED=['mention_id','topic','doc_id','sentence_id','lemma','roleset_id','arg0','arg1','argL','argT','gold_cluster']

def interval(value):
 """Conservative English calendar intervals. Unknown/ambiguous text -> None."""
 s=value.strip()
 if not s:return None
 if re.fullmatch(r'\d{4}',s):
  y=int(s)
  return (date(y,1,1),date(y,12,31)) if 1<=y<=9999 else None
 if re.fullmatch(r'\d{4}-\d{2}',s):
  try:
   y,m=map(int,s.split('-'));return date(y,m,1),date(y,m,calendar.monthrange(y,m)[1])
  except ValueError:return None
 for fmt in ['%Y-%m-%d','%d %B %Y','%d %b %Y','%B %d, %Y','%B %d %Y']:
  try:d=datetime.strptime(s,fmt).date();return d,d
  except ValueError:pass
 for fmt in ['%B %Y','%b %Y']:
  try:
   d=datetime.strptime(s,fmt).date();return d,date(d.year,d.month,calendar.monthrange(d.year,d.month)[1])
  except ValueError:pass
 # Slash dates are ambiguous and also upstream multi-value delimiters: leave unknown.
 for sep in [' to ',' – ',' — ',' - ']:
  if sep in s:
   a,b=s.split(sep,1);x,y=interval(a),interval(b)
   if x and y and x[0]<=y[1]:return x[0],y[1]
 m=re.fullmatch(r'(\d{1,2} [A-Za-z]+ \d{4})-(\d{1,2} [A-Za-z]+ \d{4})',s)
 if m:
  x,y=interval(m[1]),interval(m[2])
  if x and y and x[0]<=y[1]:return x[0],y[1]
 return None

def conflict(a,b,tolerance):
 if a is None or b is None:return False
 return (a[0]-b[1]).days>tolerance or (b[0]-a[1]).days>tolerance

def validate(tasks):
 if not isinstance(tasks,list) or not 2<=len(tasks)<=10000:raise ValueError('ต้องมีข้อมูล 2–10,000 mentions ใน JSON array')
 seen=set()
 for t in tasks:
  if not isinstance(t,dict):raise ValueError('แต่ละแถวต้องเป็น object')
  for k in REQUIRED:
   if k not in t or not isinstance(t[k],(str,int)):raise ValueError('คอลัมน์ไม่ครบหรือชนิดผิด: '+k)
   t[k]=str(t[k])
  for k in ['mention_id','doc_id','topic','gold_cluster']:
   if not t[k].strip():raise ValueError('ห้ามว่าง: '+k)
  if t['mention_id'] in seen:raise ValueError('mention_id ซ้ำ: '+t['mention_id'])
  seen.add(t['mention_id'])
 return tasks

def coverage(tasks):
 dates=[interval(t['argT']) for t in tasks]
 return {'mentions':len(tasks),'documents':len({t['doc_id'] for t in tasks}),'topics':len({t['topic'] for t in tasks}),'gold_clusters':len({t['gold_cluster'] for t in tasks}),'date_parsed':sum(d is not None for d in dates),'date_missing':sum(not t['argT'].strip() for t in tasks),'date_unparsed':sum(bool(t['argT'].strip()) and d is None for t,d in zip(tasks,dates)),'role_missing':sum(not t['arg0'].strip() or not t['arg1'].strip() for t in tasks)}

def load_dataset(name):
 if name not in FILES:raise ValueError('Unknown dataset')
 p=BASE/'data'/f'{name}.json'
 if not p.exists():raise ValueError('ยังไม่มีข้อมูล กรุณารัน setup_data.py')
 b=p.read_bytes();expected=json.loads((BASE/'dataset_checksums.json').read_text())[name]
 if hashlib.sha256(b).hexdigest()!=expected:raise ValueError('ข้อมูลเปลี่ยนจาก upstream: checksum ไม่ตรง')
 return validate(json.loads(b)),expected

def constrained(adj,ids,dates,tolerance):
 """Process original OR edges by lexical mention-id order; block incompatible merges."""
 parent=list(range(len(ids)));members={i:[i] for i in range(len(ids))};blocked=[]
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 rows,cols=adj.nonzero();edges=sorted(((i,j) for i,j in zip(rows.tolist(),cols.tolist()) if i<j),key=lambda ij:(min(ids[ij[0]],ids[ij[1]]),max(ids[ij[0]],ids[ij[1]])))
 for i,j in edges:
  a,b=root(i),root(j)
  if a==b:continue
  witness=next(((u,v) for u in members[a] for v in members[b] if conflict(dates[u],dates[v],tolerance)),None)
  if witness:
   blocked.append({'edge_a':ids[i],'edge_b':ids[j],'witness_a':ids[witness[0]],'witness_b':ids[witness[1]]});continue
  if min(ids[u] for u in members[b])<min(ids[u] for u in members[a]):a,b=b,a
  parent[b]=a;members[a]+=members.pop(b)
 return [(m,root(i)) for i,m in enumerate(ids)],blocked

def pair_counts(gold,pred):
 # O(n) contingency counts instead of materializing n^2 pairs.
 comb=lambda x:x*(x-1)//2
 joint=Counter(zip(gold,pred));tp=sum(comb(v) for v in joint.values());pp=sum(comb(v) for v in Counter(pred).values());gp=sum(comb(v) for v in Counter(gold).values())
 fp,fn=pp-tp,gp-tp;tn=comb(len(gold))-tp-fp-fn
 p=tp/pp if pp else 0;r=tp/gp if gp else 0
 return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'pair_precision':p,'pair_recall':r,'pair_f1':2*p*r/(p+r) if p+r else 0}

def scores(tasks,pred,out,method):
 gold=[(t['mention_id'],t['gold_cluster']) for t in tasks]
 g=out/'gold.key';s=out/f'{method}.key'
 generate_key_file(gold,'evt',str(out),str(g));generate_key_file(pred,'evt',str(out),str(s))
 doc=get_coref_infos(str(g),str(s),False,False,True)
 vals={k:dict(zip(['recall','precision','f1'],map(float,evaluate_documents(doc,fn)))) for k,fn in [('muc',muc),('b3',b_cubed),('ceafe',ceafe)]}
 conll=sum(v['f1'] for v in vals.values())/3
 # Reproduce author's display rounding separately from full-precision score.
 paper=float(np.round(sum(float(np.round(np.round(v['f1'],3)*100,1)) for v in vals.values())/3,1))
 vals.update({'conll_f1':conll,'paper_rounded_conll':paper,'clusters':len({c for _,c in pred})})
 vals.update(pair_counts([c for _,c in gold],[c for _,c in pred]));return vals

def csv_text(rows):
 f=io.StringIO();w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['empty']);w.writeheader();w.writerows(rows);return f.getvalue()

def experiment(config,tasks=None):
 name=config.get('dataset','ann1-dev');tolerance=int(config.get('tolerance_days',0))
 if not 0<=tolerance<=365:raise ValueError('tolerance ต้องอยู่ระหว่าง 0–365 วัน')
 custom=tasks is not None
 if custom:
  tasks=validate(copy.deepcopy(tasks));sha=hashlib.sha256(json.dumps(tasks,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 else:tasks,sha=load_dataset(name)
 phase=config.get('phase','development')
 if phase not in ['development','heldout']:raise ValueError('Unknown phase')
 if 'test_common' in name and phase!='heldout':raise ValueError('test_common ต้องรันในโหมด held-out')
 if phase=='heldout' and not config.get('frozen_protocol'):raise ValueError('ยืนยันว่าเลือกกฎจาก train/dev ก่อนแล้ว')
 if phase=='heldout' and not custom and 'test_common' not in name:raise ValueError('ชุดนี้ไม่ใช่ held-out test')
 if custom and (not config.get('source','').strip() or not config.get('annotation_source','').strip()):raise ValueError('ระบุแหล่งข้อมูลและผู้สร้าง annotation')
 run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
 out=BASE/'runs'/run_id;out.mkdir(parents=True)
 try:
  (out/'input.json').write_text(json.dumps(tasks,ensure_ascii=False))
  config={**config,'tolerance_days':tolerance,'dataset':name,'phase':phase,'custom_upload':custom}
  (out/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
  source_files=[BASE/p for p in ['engine.py','setup_data.py','cli.py','requirements.txt','dataset_checksums.json','vendor/coreference.py','vendor/utils.py','vendor/__init__.py','vendor/LICENSE']]
  source_hash={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
  for p in source_files:
   dest=out/'source'/p.relative_to(BASE);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
  original=copy.deepcopy(tasks);prepared=copy.deepcopy(tasks);t0=time.perf_counter();generate_eids(prepared,{})
  ids=[t['mention_id'] for t in tasks];m2i={m:i for i,m in enumerate(ids)}
  n=get_sparse_matrix(m2i,[(t['mention_id'],t['EIDs']) for t in prepared]);lt=get_sparse_matrix(m2i,[(t['mention_id'],t['EID_lt']) for t in prepared]);both=n.multiply(lt);either=n+lt
  preprocessing=time.perf_counter()-t0
  dates=[interval(t['argT']) for t in original];result={};predictions={};blocked=[]
  for method,adj in [('EID_N',n),('EID_lt',lt),('AND',both),('OR',either),('OR_temporal',either)]:
   t0=time.perf_counter()
   if method=='OR_temporal':pred,blocked=constrained(adj,ids,dates,tolerance)
   else:pred=c_clustering(adj,ids)
   elapsed=time.perf_counter()-t0;pred=[(m,int(c)) for m,c in pred];predictions[method]=dict(pred)
   result[method]=scores(tasks,pred,out,method);result[method]['clustering_seconds']=elapsed
  rows=[]
  for m,v in result.items():rows.append({'method':m,'MUC_F1':v['muc']['f1']*100,'B3_F1':v['b3']['f1']*100,'CEAF_e_F1':v['ceafe']['f1']*100,'CoNLL_F1':v['conll_f1']*100,'paper_rounded_CoNLL':v['paper_rounded_conll'],'pair_precision':v['pair_precision']*100,'pair_recall':v['pair_recall']*100,'pair_F1':v['pair_f1']*100,'TP':v['tp'],'FP':v['fp'],'FN':v['fn'],'TN':v['tn'],'clusters':v['clusters'],'clustering_seconds':v['clustering_seconds']})
  (out/'metrics.csv').write_text(csv_text(rows));(out/'blocked_merges.csv').write_text(csv_text(blocked))
  prediction_rows=[{**{k:t[k] for k in REQUIRED},**{m:predictions[m][t['mention_id']] for m in METHODS}} for t in tasks]
  (out/'predictions.csv').write_text(csv_text(prediction_rows))
  error_rows=[];total=0
  # Examples capped; exact counts above use all pairs.
  for i,t in enumerate(tasks):
   for u in tasks[:i]:
    a,b=t['mention_id'],u['mention_id'];g=t['gold_cluster']==u['gold_cluster'];old=predictions['OR'][a]==predictions['OR'][b];new=predictions['OR_temporal'][a]==predictions['OR_temporal'][b]
    if new!=g or old!=new:
     total+=1
     if len(error_rows)<500:error_rows.append({'a':a,'b':b,'gold_same':g,'OR_same':old,'temporal_same':new,'date_a':t['argT'],'date_b':u['argT'],'text_a':t.get('text',t.get('marked_sentence','')),'text_b':u.get('text',u.get('marked_sentence',''))})
  (out/'error_examples.csv').write_text(csv_text(error_rows))
  latex='\\begin{tabular}{lrrrr}\nMethod & MUC & B$^3$ & CEAF$_e$ & CoNLL \\\\\n\\hline\n'
  for r in rows:latex+='{} & {:.2f} & {:.2f} & {:.2f} & {:.2f} \\\\\n'.format(r['method'].replace('_','\\_'),r['MUC_F1'],r['B3_F1'],r['CEAF_e_F1'],r['CoNLL_F1'])
  (out/'table.tex').write_text(latex+'\\end{tabular}\n')
  env=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True,stderr=subprocess.DEVNULL);(out/'environment.txt').write_text(env)
  try:revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BASE,text=True,stderr=subprocess.DEVNULL).strip()
  except subprocess.CalledProcessError:revision='uncommitted'
  report={'id':run_id,'created':datetime.now(timezone.utc).isoformat(),'dataset':name,'phase':phase,'config':config,'coverage':coverage(tasks),'metrics':result,'blocked_merges':len(blocked),'blocked_examples':blocked[:30],'errors':error_rows[:30],'error_example_total':total,'error_examples_exported':len(error_rows),'provenance':{'dataset_sha256':sha,'upstream_commit':COMMIT,'source_sha256':source_hash,'checkout_commit':revision,'python':sys.version,'platform':platform.platform()},'preprocessing_seconds':preprocessing,'warnings':['Human annotation results are not end-to-end news extraction results.' if not name.startswith('gpt4') and not custom else 'Annotation provenance must be reported.','Temporal intervals reflect supplied annotations; publication date is not event date.','Deterministic edge-order heuristic; no significance or generalization claim.','Test common is a partial annotated subset, not full ECB+ test.' if 'test_common' in name else 'Development results must not be reported as untouched test results.']}
  (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  (out/'README.txt').write_text('Metrics are percentages in metrics.csv and fractions in report.json. CoNLL = mean(MUC F1, B3 F1, CEAF_e F1). Raw scores used, not rounded intermediates. paper_rounded_CoNLL reproduces upstream rounding. All five methods share identical mentions and annotation source. No VerbNet. Temporal constraints apply to whole clusters, unknown does not veto merges. Edges processed by mention-id order. Timing is clustering only, no benchmark claim. Error examples capped at 500; confusion counts exact. Human/GPT archived annotations are not live automatic extraction. Report source, subset, split and coverage; no automatic claim of improvement or significance.\n'+json.dumps(config,ensure_ascii=False,indent=2))
  return report
 except Exception:
  (out/'FAILED.txt').write_text('Incomplete run; not valid for reporting.');raise

def bundle(run_id):
 if not re.fullmatch(r'\d{8}T\d{6}-[a-f0-9]{8}',run_id):raise ValueError('Invalid run id')
 folder=BASE/'runs'/run_id
 if not (folder/'report.json').exists():raise ValueError('Unknown run')
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(folder)))
 return b.getvalue()
