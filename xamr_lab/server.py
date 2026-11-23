import argparse,json,re,threading,traceback,uuid
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import parse_qs,urlparse
from demo import CUSTOM_BODY_LIMIT,run_custom_demo,run_demo
from engine import BASE,FILES,load_dataset,coverage,experiment,bundle
JOBS={};LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def page(self,filename):
  html=(BASE/'static'/filename).read_text(encoding='utf-8')
  pair_port=getattr(self.server,'pair_port',None)
  link=f'<a href="http://127.0.0.1:{pair_port}/">เว็บเก่า · Pair Workbench</a>' if pair_port else ''
  return self.send(html.replace('<!-- LOCAL_PAIR_LINK -->',link),kind='text/html; charset=utf-8')

 def send(self,data,status=200,kind='application/json; charset=utf-8',attachment=None):
  if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode()
  elif isinstance(data,str):data=data.encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  if attachment:self.send_header('Content-Disposition',f'attachment; filename="{attachment}"')
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  path=urlparse(self.path).path
  try:
   if path=='/':return self.page('index.html')
   if path=='/audit':return self.page('audit.html')
   if path=='/audit-analysis':return self.page('audit-analysis.html')
   if path=='/audit-review':return self.page('audit-review.html')
   if path in ('/audit-data.json','/cluster-memberships.json'):return self.send((BASE/'static'/path[1:]).read_bytes())
   if path=='/paper':return self.page('paper.html')
   if path in ('/research.js','/research.css','/orbit-motion.js','/audit.js','/audit.css','/audit-analysis.js','/audit-analysis.css','/evidence.css','/evidence-core.mjs','/evidence-inspector.mjs','/audit-source.mjs','/audit-review.mjs'):return self.send((BASE/'static'/path[1:]).read_text(),kind='text/css' if path.endswith('.css') else 'application/javascript')
   if path=='/api/workbench/catalog':
    from research_runner import catalog
    return self.send(catalog())
   if path=='/api/runtime':return self.send({'cloud':False,'key_required':False})
   if path=='/demo':return self.page('demo.html')
   if path=='/legacy':return self.page('legacy.html')
   if path=='/api/demo':
    params=parse_qs(urlparse(self.path).query)
    return self.send(run_demo(params.get('case',['separate'])[0],int(params.get('tolerance_days',['0'])[0])))
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
   path=urlparse(self.path).path
   if path not in ('/api/run','/api/demo/custom','/api/workbench/run'):return self.send({'error':'Not found'},404)
   origin=self.headers.get('Origin')
   if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.send({'error':'Origin rejected'},403)
   if not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON required')
   length=int(self.headers.get('Content-Length','0'))
   if path=='/api/workbench/run':
    if not 0<length<=4096:return self.send({'error':'Request exceeds 4 KB.'},413)
    from research_runner import run_online
    return self.send(run_online(json.loads(self.rfile.read(length))))
   if path=='/api/demo/custom':
    if not 0<length<=CUSTOM_BODY_LIMIT:
     return self.send({'error':'ข้อมูลข่าวเกินขนาดที่รองรับหรือไม่มีข้อมูล'},413)
    return self.send(run_custom_demo(json.loads(self.rfile.read(length))))
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
 parser=argparse.ArgumentParser()
 parser.add_argument('--port',type=int,default=8767)
 parser.add_argument('--pair-port',type=int,help='Loopback port of Pair Workbench started by the launcher')
 a=parser.parse_args()
 if a.pair_port is not None and not 1<=a.pair_port<=65535:parser.error('invalid Pair Workbench port')
 server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
 server.pair_port=a.pair_port
 print(f'X-AMR Research Lab: http://127.0.0.1:{a.port}',flush=True)
 server.serve_forever()
