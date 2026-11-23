"""Stateless online runner; same research engine as the local workbench."""
import base64, hashlib, hmac, json, os, tempfile, urllib.request
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from demo import CUSTOM_BODY_LIMIT, run_custom_demo, run_demo
from engine import experiment, bundle, REQUIRED
from setup_data import BASE, FILES, COMMIT
app = FastAPI(docs_url=None, redoc_url=None)
MAX_MENTIONS = 2000
CATALOG = json.loads((BASE/'dataset_catalog.json').read_text())

@app.get('/')
def home():
    return HTMLResponse((BASE/'static/index.html').read_text())

@app.get('/audit', response_class=HTMLResponse)
def audit_page():
    return (BASE / 'static/audit.html').read_text(encoding='utf-8')

@app.get('/audit-analysis', response_class=HTMLResponse)
def audit_analysis_page():
    return (BASE / 'static/audit-analysis.html').read_text(encoding='utf-8')

@app.get('/audit-review', response_class=HTMLResponse)
def audit_review_page():
    return (BASE / 'static/audit-review.html').read_text(encoding='utf-8')

@app.get('/cluster-memberships.json')
def audit_memberships():
    from fastapi.responses import Response
    return Response((BASE / 'static/cluster-memberships.json').read_bytes(), media_type='application/json')

@app.get('/audit-data.json')
def audit_dataset():
    from fastapi.responses import Response
    return Response((BASE / 'static/audit-data.json').read_bytes(), media_type='application/json')

@app.get('/demo', response_class=HTMLResponse)
def demo_page():
    return (BASE / 'static/demo.html').read_text(encoding='utf-8')

@app.get('/legacy', response_class=HTMLResponse)
def legacy_page():
    return (BASE / 'static/legacy.html').read_text(encoding='utf-8')

@app.get('/api/demo')
def demo_result(case: str = 'separate', tolerance_days: int = 0):
    try:
        return run_demo(case, tolerance_days)
    except ValueError as error:
        return JSONResponse({'error': str(error)}, status_code=400)

@app.post('/api/demo/custom')
async def demo_custom_result(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > CUSTOM_BODY_LIMIT:
            return JSONResponse({'error': 'ข้อมูลข่าวเกินขนาดที่รองรับ'}, status_code=413)
        raw.extend(chunk)
    try:
        return await run_in_threadpool(run_custom_demo, json.loads(raw))
    except ValueError as error:
        return JSONResponse({'error': str(error)}, status_code=400)

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


@app.get('/paper', response_class=HTMLResponse)
def paper_page():
    html = (BASE / 'static/paper.html').read_text()
    return html.replace('<script>', '<script>window.CLOUD_MODE=true;</script><script src="/cloud.js"></script><script>', 1)

@app.get('/evidence.css')
@app.get('/evidence-core.mjs')
@app.get('/evidence-inspector.mjs')
@app.get('/audit-source.mjs')
@app.get('/audit-review.mjs')
@app.get('/audit.css')
@app.get('/audit.js')
@app.get('/audit-analysis.js')
@app.get('/audit-analysis.css')
@app.get('/orbit-motion.js')
@app.get('/research.js')
@app.get('/research.css')
def research_asset(request: Request):
    from fastapi.responses import Response
    name = request.url.path.rsplit('/', 1)[-1]
    return Response((BASE / 'static' / name).read_text(), media_type='text/css' if name.endswith('.css') else 'application/javascript')

@app.get('/api/workbench/catalog')
def research_catalog():
    from research_runner import catalog
    return catalog()

@app.post('/api/workbench/run')
async def research_run(request: Request):
    key = os.getenv('XAMR_ACCESS_KEY', '')
    if key and not hmac.compare_digest(request.headers.get('X-Access-Key', ''), key):
        return JSONResponse({'error': 'Access key is incorrect.'}, status_code=401)
    from urllib.parse import urlparse
    origin = request.headers.get('origin')
    if origin and urlparse(origin).netloc != request.headers.get('host'):
        return JSONResponse({'error': 'Origin rejected'}, status_code=403)
    if not request.headers.get('content-type', '').startswith('application/json'):
        return JSONResponse({'error': 'JSON required'}, status_code=415)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 4096:
            return JSONResponse({'error': 'Request exceeds 4 KB.'}, status_code=413)
        raw.extend(chunk)
    try:
        from research_runner import run_online, RunBusyError
        return await run_in_threadpool(run_online, json.loads(raw))
    except RunBusyError as error:
        return JSONResponse({'error': str(error)}, status_code=409)
    except (ValueError, TypeError, KeyError) as error:
        return JSONResponse({'error': str(error)}, status_code=400)
    except Exception:
        import logging
        logging.exception('Research run failed')
        return JSONResponse({'error': 'Run failed. Retry or use the local runner.'}, status_code=500)
