"""Single-user loopback workbench. User Python runs with current user's permissions."""
import argparse, base64, io, json, os, secrets, signal, subprocess, sys, threading, uuid, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import pandas as pd
from engine import ROOT, REQUIRED, ROLES, builtin, read_table, summary, prepare_run, dump
from scripts.annotate_roles import blank_annotation, apply_annotations
TOKEN=secrets.token_urlsafe(32)
TABLES={}
LOCK=threading.Lock()
ACTIVE=None


def table_store(frame, source, original=None):
    key=uuid.uuid4().hex
    TABLES[key]={'frame':frame,'source':source,'original':original}
    if len(TABLES)>8: TABLES.pop(next(iter(TABLES)))
    return {'dataset_id':key, 'source':source, **summary(frame)}


def execute(folder):
    global ACTIVE
    with (folder/'stdout.log').open('w') as log:
        try:
            env=os.environ.copy(); env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
            proc=subprocess.Popen([sys.executable,str(ROOT/'worker.py'),str(folder)],cwd=folder,
                                   stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            try: proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL); proc.wait()
                raise RuntimeError('หยุดการทดลองหลังเกิน 10 นาที')
            m=json.loads((folder/'manifest.json').read_text())
            if m['status']=='running': raise RuntimeError(f'Python process exited {proc.returncode} without a result')
        except Exception as e:
            m=json.loads((folder/'manifest.json').read_text()); m.update(status='failed',error=str(e)); dump(folder/'manifest.json',m)
        finally:
            with LOCK: ACTIVE=None


def excel(frame):
    from openpyxl import Workbook
    book=Workbook(); sheet=book.active; sheet.title='pairs'
    sheet.append(list(frame.columns))
    for row in frame.itertuples(index=False,name=None):
        sheet.append(list(row))
        for c in sheet[sheet.max_row]:
            if isinstance(c.value,str): c.data_type='s'  # Treat imported text as literal, not an Excel formula.
    sheet.freeze_panes='A2'; sheet.auto_filter.ref=sheet.dimensions
    for c in sheet[1]: sheet.column_dimensions[c.column_letter].width=24
    stream=io.BytesIO(); book.save(stream); return stream.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,data,status=200,ctype='application/json; charset=utf-8',filename=None):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        if isinstance(data,str): data=data.encode()
        self.send_response(status); self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; connect-src 'self'")
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(data)
    def allowed(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.allowed(): return self.send({'error':'Invalid host'},403)
        path=urlparse(self.path).path; query=parse_qs(urlparse(self.path).query)
        try:
            if path=='/': return self.send((ROOT/'static/index.html').read_text().replace('__TOKEN__',TOKEN),ctype='text/html; charset=utf-8')
            if path in ('/app.js','/charts.js','/facts.js','/style.css'):
                return self.send((ROOT/'static'/path[1:]).read_bytes(),ctype='text/javascript' if path.endswith('js') else 'text/css')
            if path=='/api/init':
                return self.send({'code':(ROOT/'algorithms/pair_experiment.py').read_text(),
                                  'required':REQUIRED,'optional':ROLES,'root':str(ROOT)})
            if path=='/api/template':
                return self.send(excel(builtin('small_A')),ctype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='pilot_fold_A_roles_blank.xlsx')
            if path=='/api/annotation-template':
                return self.send(excel(blank_annotation()),ctype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='pilot_role_annotations_blank.xlsx')
            if path=='/api/history':
                rows=[]
                for f in sorted((ROOT/'runs').glob('*/manifest.json'),reverse=True)[:50]:
                    try:
                        m=json.loads(f.read_text()); scores=f.parent/'metrics.json'
                        rows.append({'run_id':m['run_id'],'status':m['status'],'source':m['source'],
                                     'note':m['config'].get('note',''), 'metrics':json.loads(scores.read_text()).get('models',{}) if scores.exists() else {}})
                    except (OSError,ValueError): pass
                return self.send(rows)
            if path in ('/api/status','/api/download'):
                ident=query.get('id',[''])[0]
                if not ident or any(c not in '0123456789TZ_abcdef' for c in ident): raise ValueError('Invalid run ID')
                folder=ROOT/'runs'/ident
                m=json.loads((folder/'manifest.json').read_text())
                if path=='/api/download':
                    if m['status']=='running': raise ValueError('รอให้รันเสร็จก่อนดาวน์โหลด')
                    stream=io.BytesIO()
                    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
                        for f in folder.iterdir():
                            if f.is_file(): z.write(f,f.name)
                    return self.send(stream.getvalue(),ctype='application/zip',filename=ident+'.zip')
                result={'manifest':m}
                if (folder/'metrics.json').exists(): result['metrics']=json.loads((folder/'metrics.json').read_text())
                if (folder/'errors.csv').exists(): result['errors']=pd.read_csv(folder/'errors.csv',keep_default_na=False).head(20).to_dict('records')
                if (folder/'stdout.log').exists(): result['log']=(folder/'stdout.log').read_text(errors='replace')[-15000:]
                return self.send(result)
            self.send({'error':'Not found'},404)
        except Exception as e: self.send({'error':str(e)},400)
    def do_POST(self):
        global ACTIVE
        if not self.allowed() or self.headers.get('X-Workbench-Token')!=TOKEN: return self.send({'error':'Invalid session'},403)
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.send({'error':'Invalid origin'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>70*1024*1024: raise ValueError('ขนาดข้อมูลต้องไม่เกิน 50 MB ก่อนเข้ารหัส')
            payload=json.loads(self.rfile.read(length))
            path=urlparse(self.path).path
            if path=='/api/builtin': return self.send(table_store(builtin(payload['mode']),payload['mode']))
            if path=='/api/upload':
                raw=base64.b64decode(payload['data'],validate=True)
                if len(raw)>50*1024*1024: raise ValueError('ไฟล์ใหญ่เกิน 50 MB')
                frame=read_table(raw,payload['name'])
                if len(frame)>150000: raise ValueError('ต้นแบบรองรับไม่เกิน 150,000 คู่ต่อไฟล์')
                return self.send(table_store(frame,Path(payload['name']).name,raw))
            if path=='/api/annotations':
                raw=base64.b64decode(payload['data'],validate=True)
                if len(raw)>50*1024*1024: raise ValueError('ไฟล์ใหญ่เกิน 50 MB')
                fold=payload.get('fold')
                if fold not in ('A','B'): raise ValueError('เลือก Pilot A หรือ B')
                annotated=apply_annotations(read_table(raw,payload['name']),'small_'+fold)
                return self.send(table_store(annotated,'pilot_'+fold+'_roles:'+Path(payload['name']).name,raw))
            if path=='/api/run':
                entry=TABLES.get(payload['dataset_id'])
                if not entry: raise ValueError('กรุณาโหลดข้อมูลอีกครั้ง')
                mapping=payload['mapping']; frame=pd.DataFrame()
                for target in REQUIRED+ROLES:
                    source=mapping.get(target)
                    if source: frame[target]=entry['frame'][source]
                # Keep mention identities for original event-level data, never use as features.
                for k in ('mention_a','mention_b'):
                    if k in entry['frame']: frame[k]=entry['frame'][k]
                config=payload['config']
                config['seed']=int(config.get('seed',374))
                if not 0<=config['seed']<2**32: raise ValueError('seed ต้องอยู่ระหว่าง 0 ถึง 4294967295')
                if config.get('role_source') not in ('none','manual','predicted'): raise ValueError('Invalid role source')
                if entry['source'].endswith('_ai') and config['role_source']=='manual': raise ValueError('ชุดบทบาท AI ยังไม่ได้ผ่านการตรวจโดยคน โปรดเลือกโมเดลทำนาย')
                if not payload['code'].strip(): raise ValueError('กรุณาใส่โค้ด')
                with LOCK:
                    if ACTIVE: raise ValueError('มีการทดลองกำลังรันอยู่ กรุณารอ')
                    folder=prepare_run(frame,payload['code'],config,entry['source'])
                    if entry['original'] is not None:
                        (folder/'uploaded_source.bin').write_bytes(entry['original'])
                    ACTIVE=folder.name
                threading.Thread(target=execute,args=(folder,),daemon=True).start()
                return self.send({'run_id':folder.name})
            self.send({'error':'Not found'},404)
        except Exception as e: self.send({'error':str(e)},400)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765); parser.add_argument('--open-browser',action='store_true'); args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'NLP Research Workbench: http://127.0.0.1:{args.port}',flush=True)
    print('Local trusted code only. Ctrl+C to stop.',flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
