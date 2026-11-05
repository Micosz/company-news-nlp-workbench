/* Online results are private to this browser; export ZIP for durable evidence. */
const cloudDB=new Promise((resolve,reject)=>{const r=indexedDB.open('xamr-results-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('runs',{keyPath:'id'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
async function cloudStore(method,value){const db=await cloudDB;return new Promise((resolve,reject)=>{const tx=db.transaction('runs',method==='put'?'readwrite':'readonly'),s=tx.objectStore('runs'),r=method==='put'?s.put(value):method==='get'?s.get(value):s.getAll();tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
let cloudCurrent=null,cloudURL=null;
async function cloudAPI(url,options){
 if(url==='/api/history')return (await cloudStore('all')).map(x=>x.report).sort((a,b)=>b.id.localeCompare(a.id));
 if(url.startsWith('/api/run/')){cloudCurrent=await cloudStore('get',url.split('/').pop());if(!cloudCurrent)throw Error('ไม่พบผลในเบราว์เซอร์นี้');return cloudCurrent.report;}
 return null;
}
function cloudExport(){if(!cloudCurrent)return;try{if(cloudURL)URL.revokeObjectURL(cloudURL);const bytes=Uint8Array.from(atob(cloudCurrent.archive),c=>c.charCodeAt(0));cloudURL=URL.createObjectURL(new Blob([bytes],{type:'application/zip'}));const a=document.getElementById('export');a.href=cloudURL;a.download=cloudCurrent.id+'.zip';}catch(e){document.getElementById('status').textContent='สร้าง ZIP ไม่สำเร็จ: '+e.message;}}
async function cloudSave(result){cloudCurrent={id:result.report.id,report:result.report,archive:result.archive_base64};try{await cloudStore('put',cloudCurrent);return true;}catch(e){return false;}}
