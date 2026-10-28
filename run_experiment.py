"""CLI companion; every run saves the same evidence bundle as the web app."""
import argparse, subprocess, sys
from pathlib import Path
from engine import ROOT, builtin, prepare_run, read_table
p=argparse.ArgumentParser()
p.add_argument('--dataset',choices=['small_A','small_B','small_A_ai','small_B_ai','full'],default='small_A')
p.add_argument('--input',type=Path)
p.add_argument('--algorithm',type=Path,default=ROOT/'algorithms/pair_experiment.py')
p.add_argument('--seed',type=int,default=374)
p.add_argument('--role-source',choices=['none','manual','predicted'],default='none')
p.add_argument('--note',default='CLI reproducibility run')
a=p.parse_args()
f=read_table(a.input.read_bytes(),a.input.name) if a.input else builtin(a.dataset)
folder=prepare_run(f,a.algorithm.read_text(),{'seed':a.seed,'role_source':a.role_source,'note':a.note},str(a.input) if a.input else a.dataset)
print('Saved run:',folder,flush=True)
with (folder/'stdout.log').open('w') as log:
    result=subprocess.run([sys.executable,str(ROOT/'worker.py'),str(folder)],stdout=log,stderr=subprocess.STDOUT)
print((folder/'stdout.log').read_text())
sys.exit(result.returncode)
