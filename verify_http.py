"""Local integration check: Excel import, saved run, ZIP integrity, CSRF rejection."""
import base64, io, json, re, time, urllib.request, urllib.error, zipfile
from pathlib import Path
BASE='http://127.0.0.1:8765'
page=urllib.request.urlopen(BASE).read().decode()
token=re.search(r'name="workbench-token" content="([^"]+)"',page).group(1)
def request(path,body=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode() if body else None,
        headers={'Content-Type':'application/json','X-Workbench-Token':token})
    return urllib.request.urlopen(req).read()
init=json.loads(request('/api/init'))
raw=request('/api/template')
loaded=json.loads(request('/api/upload',{'name':'pilot_fold_A_roles_blank.xlsx','data':base64.b64encode(raw).decode()}))
assert loaded['rows']==424
body={'dataset_id':loaded['dataset_id'],'mapping':{k:k for k in init['required']+init['optional']},'code':init['code'],
      'config':{'seed':374,'role_source':'none','note':'Excel import / real-data pilot A / final algorithm'}}
run=json.loads(request('/api/run',body))['run_id']
for _ in range(90):
    status=json.loads(request('/api/status?id='+run))
    if status['manifest']['status']!='running':break
    time.sleep(1)
assert status['manifest']['status']=='completed',status
assert 'majority_reference' in status['metrics']['models']
assert 'text_plus_roles' not in status['metrics']['models']
archive=request('/api/download?id='+run)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    assert z.testzip() is None
    for f in ['algorithm.py','dataset.csv','metrics.json','errors.csv','manifest.json','uploaded_source.bin']:assert f in z.namelist()
try:
    req=urllib.request.Request(BASE+'/api/run',data=b'{}',headers={'Content-Type':'application/json'})
    urllib.request.urlopen(req)
    raise AssertionError('Missing token accepted')
except urllib.error.HTTPError as e: assert e.code==403
result={'excel_rows':424,'completed_run':run,'zip_crc':'passed','missing_token':'403 rejected','metrics':status['metrics']}
Path('http_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
