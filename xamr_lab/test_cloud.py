import base64,io,json,os,tempfile,unittest,zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app
from engine import BASE,experiment

class CloudTests(unittest.TestCase):
 def setUp(self):self.client=TestClient(app)
 def test_home_catalog_and_limit(self):
  self.assertIn('window.CLOUD_MODE=true',self.client.get('/').text)
  self.assertTrue(any(not d['ready'] for d in self.client.get('/api/datasets').json()))
  r=self.client.post('/api/run',json={'tasks':[{}]*2001});self.assertEqual(r.status_code,400)
 def test_key_origin_and_invalid_json(self):
  with patch.dict(os.environ,{'XAMR_ACCESS_KEY':'test-only'}):
   self.assertEqual(self.client.post('/api/run',json={}).status_code,401)
  self.assertEqual(self.client.post('/api/run',json={},headers={'Origin':'https://other.example'}).status_code,403)
  self.assertEqual(self.client.post('/api/run',content='{').status_code,400)
 def test_real_engine_archive_and_parity(self):
  name='ann1-dev_small';raw=(BASE/'data'/f'{name}.json').read_bytes()
  config={'dataset':name,'phase':'development','tolerance_days':0}
  before=set((BASE/'runs').glob('*'))
  with patch('app.urllib.request.urlopen',return_value=io.BytesIO(raw)):
   r=self.client.post('/api/run',json={'config':config})
  self.assertEqual(r.status_code,200,r.text[:1000]);body=r.json()
  self.assertEqual(before,set((BASE/'runs').glob('*')))
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(body['archive_base64']))) as z:
   self.assertIn('table.tex',z.namelist());self.assertIn('input.json',z.namelist())
   self.assertEqual(json.loads(z.read('report.json')),body['report'])
  with tempfile.TemporaryDirectory() as tmp:
   local=experiment(config,output_root=tmp)
  for m in local['metrics']:
   for k in ['conll_f1','tp','fp','fn','tn']:
    self.assertEqual(local['metrics'][m][k],body['report']['metrics'][m][k])
 def test_checksum_rejected(self):
  with patch('app.urllib.request.urlopen',return_value=io.BytesIO(b'[]')):
   r=self.client.post('/api/run',json={'config':{'dataset':'ann1-dev_small'}})
  self.assertEqual(r.status_code,400)
if __name__=='__main__':unittest.main()
