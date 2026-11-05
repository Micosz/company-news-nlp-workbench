"""Stateless online runner; same research engine as the local workbench."""
import base64, hashlib, hmac, json, os, tempfile, urllib.request
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from engine import experiment, bundle, REQUIRED
from setup_data import BASE, FILES, COMMIT
app = FastAPI(docs_url=None, redoc_url=None)
MAX_MENTIONS = 2000
CATALOG = json.loads((BASE/'dataset_catalog.json').read_text())

@app.get('/')
def home():
    html=(BASE/'static/index.html').read_text()
    return HTMLResponse(html.replace('<script>', '<script>window.CLOUD_MODE=true;</script><script src="/cloud.js"></script><script>',1))

@app.get('/cloud.js')
def cloud_js():
    from fastapi.responses import Response
    return Response((BASE/'static/cloud.js').read_text(),media_type='application/javascript')

@app.get('/api/datasets')
def datasets():
    return [{**d,'ready':d['mentions']<=MAX_MENTIONS,'error':'ชุดนี้เกินขนาดออนไลน์ 2,000 mentions — ใช้โหมด local'} for d in CATALOG]

@app.get('/template.json')
def template():return [{k:'' for k in REQUIRED}]

@app.get('/api/runtime')
def runtime():return {'cloud':True,'key_required':bool(os.getenv('XAMR_ACCESS_KEY')),'max_mentions':MAX_MENTIONS}

def run_online(body):
    config=body.get('config',{}); tasks=body.get('tasks')
    if not isinstance(config,dict):raise ValueError('config ต้องเป็น object')
    name=config.get('dataset','ann1-dev')
    with tempfile.TemporaryDirectory(prefix='xamr-') as temp:
        root=Path(temp);data=root/'data';data.mkdir()
        if tasks is None:
            meta=next((d for d in CATALOG if d['name']==name),None)
            if not meta:raise ValueError('Unknown dataset')
            if meta['mentions']>MAX_MENTIONS:raise ValueError('ชุดนี้เกินขนาดออนไลน์ ใช้โหมด local')
            url=f'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/{COMMIT}/project/annotations/ecb/{FILES[name]}'
            with urllib.request.urlopen(url,timeout=60) as r:raw=r.read(30_000_001)
            if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Dataset checksum mismatch')
            (data/f'{name}.json').write_bytes(raw)
        elif not isinstance(tasks,list) or len(tasks)>MAX_MENTIONS:
            raise ValueError('ออนไลน์รองรับไม่เกิน 2,000 mentions')
        report=experiment(config,tasks,output_root=root/'runs',data_root=data)
        archive=base64.b64encode(bundle(report['id'],root/'runs')).decode()
        result={'status':'done','report':report,'archive_base64':archive}
        if len(json.dumps(result,ensure_ascii=False).encode())>4_000_000:
            raise ValueError('ผลลัพธ์เกินขนาดตอบกลับออนไลน์ กรุณารันชุดนี้ในโหมด local')
        return result

@app.post('/api/run')
async def run(request:Request):
    key=os.getenv('XAMR_ACCESS_KEY','')
    if key and not hmac.compare_digest(request.headers.get('X-Access-Key',''),key):
        return JSONResponse({'error':'รหัสเข้าใช้งานไม่ถูกต้อง'},status_code=401)
    origin=request.headers.get('origin')
    from urllib.parse import urlparse
    if origin and urlparse(origin).netloc!=request.headers.get('host'):
        return JSONResponse({'error':'Origin rejected'},status_code=403)
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>3_000_000:return JSONResponse({'error':'ขนาดคำขอเกิน 3 MB'},status_code=413)
    try:
        body=json.loads(raw)
        if not isinstance(body,dict):raise ValueError('JSON object required')
        return await run_in_threadpool(run_online,body)
    except (ValueError,TypeError,KeyError) as e:
        return JSONResponse({'error':str(e)},status_code=400)
    except Exception:
        import logging
        logging.exception('Online experiment failed')
        return JSONResponse({'error':'รันไม่สำเร็จ ตรวจ server log หรือใช้โหมด local'},status_code=500)
