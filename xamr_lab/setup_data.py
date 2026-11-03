"""Download only the published annotations at a pinned upstream commit."""
import hashlib,json,urllib.request
from pathlib import Path
COMMIT='5639eb84f9cd32c360ff2ee715eb937ed2cc3c8e'
BASE=Path(__file__).resolve().parent
FILES={f'{a}-{s}':f'{a}/{s}_xamr.json' for a in ['ann1','ann2'] for s in ['train','dev','dev_small']}
FILES.update({f'{a}-test_common':f'{a}/test_common_xamr.json' for a in ['ann1','ann2']})
FILES.update({f'gpt4-{s}':f'gpt-4/dev_small_{s}.json' for s in ['g1','g2']})
def setup():
 expected=json.loads((BASE/'dataset_checksums.json').read_text())
 (BASE/'data').mkdir(exist_ok=True)
 for name,rel in FILES.items():
  dest=BASE/'data'/f'{name}.json'
  if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==expected[name]:continue
  url=f'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/{COMMIT}/project/annotations/ecb/{rel}'
  print('Downloading',name,flush=True)
  data=urllib.request.urlopen(url,timeout=90).read()
  if hashlib.sha256(data).hexdigest()!=expected[name]:raise ValueError('Checksum mismatch: '+name)
  json.loads(data);temp=dest.with_suffix('.tmp');temp.write_bytes(data);temp.replace(dest)
 print('All annotation files verified.')
if __name__=='__main__':setup()
