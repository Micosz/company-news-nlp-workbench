"""Run or replay without a browser. Replay uses the current checkout's algorithm."""
import argparse,json
from pathlib import Path
from engine import experiment
p=argparse.ArgumentParser();p.add_argument('--dataset',default='ann1-dev');p.add_argument('--tolerance-days',type=int,default=0);p.add_argument('--replay',type=Path);a=p.parse_args()
if a.replay:
 config=json.loads((a.replay/'config.json').read_text());tasks=json.loads((a.replay/'input.json').read_text())
 config['source']='Replay from '+str(a.replay)
 config['annotation_source']=config.get('annotation_source') or ('upstream '+config['dataset'])
 config['replay_of']=a.replay.name
 r=experiment(config,tasks)
else:r=experiment({'dataset':a.dataset,'tolerance_days':a.tolerance_days,'phase':'development'})
print(r['id'])
for k,v in r['metrics'].items():print(k,round(v['conll_f1']*100,4))
