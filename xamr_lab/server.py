import argparse,json,re,threading,traceback,uuid
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
from engine import BASE,FILES,load_dataset,coverage,experiment,bundle
JOBS={};LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def send(self,data,status=200,kind='application/json; charset=utf-8',attachment=None):
  if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode()
  elif isinstance(data,str):data=data.encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  if attachment:self.send_header('Content-Disposition',f'attachment; filename="{attachment}"')
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  path=urlparse(self.path).path
  try:
   if path=='/':return self.send((BASE/'static/index.html').read_bytes(),kind='text/html; charset=utf-8')
   if path=='/api/datasets':
    rows=[]
    for name in FILES:
     try:d,h=load_dataset(name);rows.append({'name':name,'ready':True,'sha256':h,**coverage(d)})
     except Exception as e:rows.append({'name':name,'ready':False,'error':str(e)})
    return self.send(rows)
   if path.startswith('/api/job/'):
    return self.send(JOBS.get(path.split('/')[-1],{'status':'missing'}))
   if path=='/api/history':
    rows=[]
    for p in sorted((BASE/'runs').glob('*/report.json'),reverse=True):
     r=json.loads(p.read_text());rows.append({k:r[k] for k in ['id','created','dataset','phase','coverage','metrics']})
    return self.send(rows)
   if path.startswith('/api/run/'):
    key=path.split('/')[-1]
    if not re.fullmatch(r'\d{8}T\d{6}-[a-f0-9]{8}',key):raise ValueError('Invalid run')
    return self.send(json.loads((BASE/'runs'/key/'report.json').read_text()))
   if path.startswith('/export/'):
    key=path.split('/')[-1];return self.send(bundle(key),kind='application/zip',attachment=key+'.zip')
   if path=='/template.json':
    example=[{k:'' for k in ['mention_id','topic','doc_id','sentence_id','lemma','roleset_id','arg0','arg1','argL','argT','gold_cluster']}]
    return self.send(example,attachment='xamr-template.json')
   return self.send({'error':'Not found'},404)
  except Exception as e:self.send({'error':str(e)},400)
 def do_POST(self):
  try:
   if urlparse(self.path).path!='/api/run':return self.send({'error':'Not found'},404)
   origin=self.headers.get('Origin')
   if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.send({'error':'Origin rejected'},403)
   if not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON required')
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=40_000_000:raise ValueError('Request too large or empty')
   body=json.loads(self.rfile.read(length))
   if not LOCK.acquire(blocking=False):return self.send({'error':'มีการทดลองกำลังทำงานอยู่'},409)
   key=uuid.uuid4().hex;JOBS[key]={'status':'running'}
   def work():
    try:JOBS[key]={'status':'done','report':experiment(body.get('config',{}),body.get('tasks'))}
    except Exception as e:JOBS[key]={'status':'error','error':str(e)};traceback.print_exc()
    finally:LOCK.release()
   threading.Thread(target=work,daemon=True).start();self.send({'job':key},202)
  except Exception as e:self.send({'error':str(e)},400)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8767);a=parser.parse_args()
 print(f'X-AMR Research Lab: http://127.0.0.1:{a.port}',flush=True)
 ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
