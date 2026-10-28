const $=s=>document.querySelector(s), token=$('meta[name="workbench-token"]').content;
let dataset=null, defaults='', fields=[], optional=[], running=false, displayedRun=null;
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Workbench-Token':token},body:JSON.stringify(body)}:{});const j=await r.json();if(!r.ok)throw Error(j.error||r.statusText);return j;}
function status(message,error=false){$('#status').className='alert'+(error?' error':'');$('#status').textContent=message;}
function clearData(message){dataset=null;$('#run').disabled=true;$('#data-info').className='empty';$('#data-info').textContent=message;$('#mapping-wrap').hidden=true;}
function showData(d){dataset=d;$('#data-info').className='empty loaded';const t=d.time_coverage;$('#data-info').innerHTML=`<div><strong>${d.rows.toLocaleString()}</strong>คู่ข้อความ</div><div>${escapeHTML(d.source)}<br><small>${escapeHTML(Object.entries(d.splits).map(([k,v])=>`${k}: ${v}`).join(' · '))}</small>${t?`<br><small>วันครบทั้งคู่ ${t.both.toLocaleString()} · มีวันฝั่งเดียว ${t.one.toLocaleString()} · ไม่มีวันทั้งคู่ ${t.neither.toLocaleString()}</small>`:''}</div>`;$('#mapping-wrap').hidden=false;
$('#mapping').innerHTML=[...fields,...optional].map(k=>`<label>${escapeHTML(k)} ${fields.includes(k)?'*':'(เสริม)'}<select data-field="${k}"><option value="">— ไม่เลือก —</option>${d.columns.map(c=>`<option value="${escapeHTML(c)}" ${c===k?'selected':''}>${escapeHTML(c)}</option>`).join('')}</select></label>`).join('');
$('#preview').innerHTML=`<table><thead><tr>${d.columns.map(c=>`<th>${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${d.preview.map(r=>`<tr>${d.columns.map(c=>`<td class="text">${escapeHTML(String(r[c]).slice(0,180))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;$('#run').disabled=running;status('โหลดข้อมูลแล้ว ตรวจคอลัมน์และกดรันได้ค่ะ');}
$('#builtin').onchange=()=>{clearData('เลือกชุดใหม่แล้ว กด “โหลดข้อมูล” ก่อนรันค่ะ');};
$('#load').onclick=async()=>{try{$('#load').disabled=true;const mode=$('#builtin').value;showData(await api('/api/builtin',{mode}));const ai=mode.endsWith('_ai'),timed=['story_time','story_mixed'].includes(mode),aiNote='AI-assisted roles from full article; human review pending; exploratory';$('#roles').value=ai?'predicted':'none';$('#time-source').value=timed?'oracle':'none';if(timed){status('โหลดชุดเวลาแล้ว · วันที่ที่มีเป็นป้ายกำกับ (oracle) · วันที่ขาดเป็น unknown ไม่ใช่วันที่โมเดลดึงเอง');}else if(ai){if(!$('#note').value.trim())$('#note').value=aiNote;status('โหลดบทบาทจาก AI แล้ว · ยังรอคนตรวจ · บทบาทใช้บริบทข่าวเต็มที่ข้อความทดลองแบบสั้นอาจไม่มี');}if(!ai&&$('#note').value===aiNote)$('#note').value='';}catch(e){clearData('โหลดข้อมูลไม่สำเร็จ กรุณาเลือกและโหลดอีกครั้ง');status(e.message,true);}finally{$('#load').disabled=false;}};
$('#file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>50*1024*1024)throw Error('ไฟล์ใหญ่เกิน 50 MB');status('กำลังอ่านไฟล์…');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f);});showData(await api('/api/upload',{name:f.name,data}));}catch(e){clearData('นำเข้าข้อมูลไม่สำเร็จ กรุณาเลือกไฟล์อีกครั้ง');status(e.message,true);}};
$('#load-annotation').onclick=async()=>{const f=$('#annotation-file').files[0];if(!f){status('เลือกแบบฟอร์มบทบาทก่อนค่ะ',true);return;}try{if(f.size>50*1024*1024)throw Error('ไฟล์ใหญ่เกิน 50 MB');$('#load-annotation').disabled=true;status('กำลังตรวจหลักฐานและเตรียมคู่ข้อความ…');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f);});const prepared=await api('/api/annotations',{name:f.name,data,fold:$('#annotation-fold').value});showData(prepared);$('#roles').value='none';status('โหลดบทบาทแล้ว โปรดเลือกที่มาของบทบาทตามจริงก่อนรัน และตรวจ coverage ค่ะ');}catch(e){clearData('โหลดบทบาทไม่สำเร็จ กรุณาตรวจไฟล์และลองอีกครั้ง');status(e.message,true);}finally{$('#load-annotation').disabled=false;}};
$('#reset').onclick=()=>{$('#code').value=defaults;};
$('#import-code').onclick=()=>$('#code-file').click();$('#code-file').onchange=async e=>{if(e.target.files[0])$('#code').value=await e.target.files[0].text();};
$('#save-code').onclick=()=>{const url=URL.createObjectURL(new Blob([$('#code').value],{type:'text/x-python'}));const a=document.createElement('a');a.href=url;a.download='pair_experiment.py';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('#code').addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();const t=e.target,s=t.selectionStart;t.setRangeText('    ',s,t.selectionEnd,'end');}});
const names=WorkbenchCharts.names;
function chartPanel(r){
  return `<div class="charts-heading"><h3>ดูภาพรวมจากกราฟ</h3><p>ค่าจากผลรอบนี้ · กราฟแท่งใช้สเกลเดียวกัน 0–100% · ตารางตัวเลขอยู่ด้านล่าง</p></div>
  <div class="charts-grid"><div class="card chart-card"><label for="chart-metric">เลือกคะแนนที่จะเปรียบเทียบ</label><div class="chart-controls"><select id="chart-metric">${Object.entries(WorkbenchCharts.metrics).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select><button class="secondary" id="save-metric-chart">↓ บันทึก SVG</button></div><div id="metric-chart" class="chart-image" aria-live="polite"></div><p class="chart-note">F1, Precision และ Recall วัด class 1 (เหตุการณ์เดียวกัน) · Macro F1 เฉลี่ยทั้งสอง class</p></div>
  <div class="card chart-card"><label for="chart-model">ดูจำนวนคู่ที่ทายถูก / ผิด (Confusion matrix)</label><div class="chart-controls"><select id="chart-model">${Object.keys(r.models).map(key=>`<option value="${escapeHTML(key)}" ${key==='text_baseline'?'selected':''}>${escapeHTML(names[key]||key)}</option>`).join('')}</select><button class="secondary" id="save-confusion-chart">↓ บันทึก SVG</button></div><div id="confusion-chart" class="chart-image" aria-live="polite"></div><p class="chart-note">FP = รวมคนละเหตุการณ์เข้าด้วยกัน · FN = แยกเหตุการณ์เดียวกันออกจากกัน<br>สีแสดงถูก/ผิดเท่านั้น ความเข้มไม่ได้แทนจำนวน</p></div></div>
  <p class="chart-note">เทียบ Text baseline กับ Text + roles หรือ Text + event date ในรอบเดียวกัน ส่วน Majority / Cosine / Time only ใช้เป็นค่าอ้างอิง</p>
  ${!r.models.text_plus_roles?'<div class="alert">รอบนี้ยังไม่มีผล Text + finance roles จึงยังเทียบส่วนเพิ่มไม่ได้ กราฟแสดงเฉพาะโมเดลที่รันจริง ไม่แทนผลที่ขาดด้วยศูนย์</div>':''}`;
}
function clusteringPanel(c){
  if(!c)return '';
  if(c.status!=='available')return `<div class="alert">ยังไม่มีผลจัดกลุ่ม B³: ${escapeHTML(c.reason||'ข้อมูลไม่ครบ')}</div>`;
  const rows=Object.entries(c.models||{}).map(([name,v])=>`<tr><td>${escapeHTML(names[name]||name)}</td><td>${(100*v.b3_precision).toFixed(2)}%</td><td>${(100*v.b3_recall).toFixed(2)}%</td><td>${(100*v.b3_f1).toFixed(2)}%</td><td>${v.predicted_clusters}</td></tr>`).join('');
  return `<div class="cluster-panel card"><h3>ผลจัดกลุ่มเหตุการณ์ · B³</h3><p>นำคู่ที่ทำนายว่าเหมือนกันมาเชื่อมเป็นกลุ่ม แล้วเทียบกับเฉลย: test topic ${escapeHTML(c.test_topic)} · ${c.test_mentions} mentions · เฉลย ${c.gold_clusters} กลุ่ม</p><div class="table-wrap"><table><thead><tr><th>โมเดล</th><th>B³ Precision</th><th>B³ Recall</th><th>B³ F1</th><th>กลุ่มที่ทำนาย</th></tr></thead><tbody>${rows}</tbody></table></div><p class="chart-note">คำนวณเฉพาะ Pilot ที่มีคู่ test ครบทุกคู่ การเชื่อมเป็นทอด ๆ อาจรวมกลุ่มเกินจริง · B³ เพียงค่าเดียวไม่ใช่ CoNLL F1 และยังเทียบกับ CohTP โดยตรงไม่ได้</p><div class="alert">Pilot มีเพียง 4 เหตุการณ์และหนึ่งเหตุการณ์หลักต่อดีล ชื่อบริษัทอาจกลายเป็นทางลัดในการทำนาย คะแนนรอบนี้ยังสรุปผลทั่วไปไม่ได้</div></div>`;
}
function bindCharts(data){
  const models=data.metrics.models, runId=data.manifest.run_id;
  const renderMetric=()=>{$('#metric-chart').innerHTML=WorkbenchCharts.metricChart(models,$('#chart-metric').value,runId);};
  const renderConfusion=()=>{const key=$('#chart-model').value;$('#confusion-chart').innerHTML=WorkbenchCharts.confusionChart(models[key],names[key]||key,runId);};
  function download(selector,suffix){
    const svg=$(selector).querySelector('svg');if(!svg)return;
    const url=URL.createObjectURL(new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n'+svg.outerHTML],{type:'image/svg+xml;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`${runId}_${suffix.replace(/[^a-zA-Z0-9_-]/g,'_')}.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  $('#chart-metric').onchange=renderMetric;$('#chart-model').onchange=renderConfusion;
  $('#save-metric-chart').onclick=()=>download('#metric-chart',$('#chart-metric').value);
  $('#save-confusion-chart').onclick=()=>download('#confusion-chart','confusion_'+$('#chart-model').value);
  renderMetric();renderConfusion();
}
function results(data){const m=data.manifest;displayedRun=m.run_id;$('#result-body').className='';let html=`<div class="result-top"><small>${escapeHTML(m.run_id)} · ${escapeHTML(m.source)}</small><a href="/api/download?id=${encodeURIComponent(m.run_id)}">↓ ดาวน์โหลดบันทึกทั้งหมด (.zip)</a></div>`;
const roleSources={none:'ไม่มีบทบาท',manual:'คนทำป้ายกำกับ (oracle)',predicted:'บทบาทจากโมเดลที่นำเข้า'};
const timeSources={none:'ไม่ใช้ข้อมูลเวลา',oracle:'ป้ายเวลาจากชุดข้อมูล (oracle)',predicted:'วันที่จากโมเดลทำนาย'};
if(m.config){html+=`<p class="chart-note">ที่มาบทบาท: ${escapeHTML(roleSources[m.config.role_source]||m.config.role_source||'ไม่ระบุ')} · ที่มาเวลา: ${escapeHTML(timeSources[m.config.time_source]||m.config.time_source||'ไม่ระบุ')} · หมายเหตุ: ${escapeHTML(m.config.note||'ไม่มี')}</p>`;}
if(data.metrics){const r=data.metrics;html+=`<p class="chart-note">วิธีที่บันทึกในรอบนี้: ${escapeHTML(r.method||'ไม่ระบุ')}</p>`;html+=chartPanel(r);html+=`<h3 class="numbers-heading">ตัวเลขของแต่ละโมเดล</h3><div class="metric-grid">${Object.entries(r.models).map(([n,v])=>`<div class="metric-card"><h3>${escapeHTML(names[n]||n)}</h3><small>${v.features.length} features · threshold ${v.threshold}</small><div class="big-score">${(100*v.f1).toFixed(2)}<span> % F1</span></div><div class="mini-metrics"><span>Precision<br><b>${(100*v.precision).toFixed(2)}%</b></span><span>Recall<br><b>${(100*v.recall).toFixed(2)}%</b></span><span>Macro F1<br><b>${(100*v.macro_f1).toFixed(2)}%</b></span></div><div class="confusion">TP ${v.confusion.tp} · FP ${v.confusion.fp}<br>FN ${v.confusion.fn} · TN ${v.confusion.tn}</div></div>`).join('')}</div><p><small>Test ${r.test_pairs} คู่ · ใช้เวลา ${r.elapsed_seconds} วินาที · Cosine เป็น reference; เปรียบเทียบส่วนเพิ่มระหว่าง Text baseline กับ Text + roles ของรอบเดียวกัน</small></p>`;
for(const [name,model] of Object.entries(r.models)){const c=model.confusion;if(c && r.test_pairs>0 && c.tp+c.fp===0)html+=`<div class="alert">${escapeHTML(names[name]||name)} ทำนายทุกคู่เป็นคนละเหตุการณ์ (class 0) จึงไม่พบคู่ที่เป็น class 1 ในผลทำนาย</div>`;else if(c && r.test_pairs>0 && c.tn+c.fn===0)html+=`<div class="alert">${escapeHTML(names[name]||name)} ทำนายทุกคู่เป็นเหตุการณ์เดียวกัน (class 1)</div>`;}
if(r.role_coverage && r.role_coverage.train_complete_pairs!==undefined)html+=`<p class="chart-note">คู่ที่มีบทบาทครบ: train ${r.role_coverage.train_complete_pairs} · test ${r.role_coverage.test_complete_pairs} (คู่อื่นยังเก็บเป็น unknown)</p>`;
if(r.time_coverage && r.time_coverage.train_complete_pairs!==undefined)html+=`<p class="chart-note">คู่ที่มีวันเหตุการณ์ครบ: train ${r.time_coverage.train_complete_pairs} · test ${r.time_coverage.test_complete_pairs} · วันเดียวกันไม่ได้ยืนยันว่าเป็นเหตุการณ์เดียวกัน</p>`;
html+=clusteringPanel(r.clustering);
if(r.delta_f1!==undefined)html+=`<div class="alert">Δ F1 (Text + roles − Text baseline) = ${(100*r.delta_f1).toFixed(2)} จุดเปอร์เซ็นต์ · ผลของรอบนี้เท่านั้น ยังไม่ใช่ข้อสรุปเชิงสถิติ</div>`;
if(r.delta_time_f1!==undefined)html+=`<div class="alert">Δ F1 (Text + time − Text baseline) = ${(100*r.delta_time_f1).toFixed(2)} จุดเปอร์เซ็นต์ · ผลของรอบนี้เท่านั้น ยังไม่ใช่ข้อสรุปเชิงสถิติ</div>`;
if(r.time_strata){const labels={both:'มีวันทั้งสองฝั่ง',one:'มีวันฝั่งเดียว',neither:'ไม่มีวันทั้งสองฝั่ง'};html+=`<h3>ผล test แยกตามข้อมูลวันที่มี</h3><p class="chart-note">เปรียบเทียบสองโมเดลบนคู่เดียวกันในแต่ละกลุ่ม · กลุ่มมีขนาดและสัดส่วน label ต่างกัน</p><div class="table-wrap"><table><thead><tr><th>ข้อมูลเวลา</th><th>จำนวนคู่</th><th>คู่เหตุการณ์เดียวกัน</th><th>Text F1</th><th>Text + time F1</th></tr></thead><tbody>${Object.entries(r.time_strata).map(([k,v])=>`<tr><td>${escapeHTML(labels[k]||k)}</td><td>${v.pairs}</td><td>${v.positive_pairs}</td><td>${(100*v.models.text_baseline.f1).toFixed(2)}%</td><td>${(100*v.models.text_plus_time.f1).toFixed(2)}%</td></tr>`).join('')}</tbody></table></div>`;}
html+=r.warnings.map(w=>`<div class="alert">${escapeHTML(w)}</div>`).join('');
if(!r.models.text_plus_roles)html+='<div class="alert">ยังไม่มีผลของส่วนเพิ่มบทบาท: เติม buyer_a / target_a / buyer_b / target_b ทั้ง train และ test แล้วเลือกที่มาของบทบาทก่อนค่ะ</div>';
html+=`<details><summary>ดูคู่ที่ทำนายผิด (แสดง 20 แถวแรก · ทั้งหมดอยู่ใน ZIP)</summary><div class="table-wrap"><table><thead><tr><th>โมเดล</th><th>ข้อความ A</th><th>ข้อความ B</th><th>จริง → ทำนาย</th><th>คะแนน</th></tr></thead><tbody>${(data.errors||[]).map(e=>`<tr><td>${escapeHTML(e.model)}</td><td class="text">${escapeHTML(e.text_a)}</td><td class="text">${escapeHTML(e.text_b)}</td><td>${e.label} → ${e.prediction}</td><td>${Number(e.score).toFixed(3)}</td></tr>`).join('')}</tbody></table></div></details>`;}
if(m.error)html+=`<div class="alert error">${escapeHTML(m.error)}</div>`;
html+=`<details><summary>Python log / รายละเอียดข้อผิดพลาด</summary><pre>${escapeHTML(data.log||'ยังไม่มี log')}</pre></details>`;$('#result-body').innerHTML=html;if(data.metrics)bindCharts(data);}
async function watch(id){try{const data=await api('/api/status?id='+id);if(data.manifest.status==='running'){status('กำลังประมวลผล… บันทึก '+id);setTimeout(()=>watch(id),1200);return;}running=false;$('#run').disabled=!dataset;status(data.manifest.status==='completed'?'รันสำเร็จและบันทึกผลแล้วค่ะ':'รันไม่สำเร็จ — เก็บโค้ดและ error log แล้ว',data.manifest.status!=='completed');results(data);await history();$('#results').scrollIntoView({behavior:'smooth'});}catch(e){running=false;$('#run').disabled=!dataset;status('อ่านสถานะไม่ได้: '+e.message+' ลองดูในสมุดบันทึกอีกครั้ง',true);}}
$('#run').onclick=async()=>{try{const mapping={};document.querySelectorAll('[data-field]').forEach(s=>mapping[s.dataset.field]=s.value);if(fields.some(k=>!mapping[k]))throw Error('เลือกคอลัมน์ที่มี * ให้ครบก่อนค่ะ');if(dataset?.source?.endsWith('_ai')&&$('#roles').value==='manual')throw Error('ชุดบทบาท AI ยังไม่ได้ผ่านการตรวจโดยคน โปรดเลือกโมเดลทำนาย');running=true;$('#run').disabled=true;status('กำลังตรวจข้อมูลและเตรียมการทดลอง…');const r=await api('/api/run',{dataset_id:dataset.dataset_id,mapping,code:$('#code').value,config:{seed:Number($('#seed').value),role_source:$('#roles').value,time_source:$('#time-source').value,note:$('#note').value}});watch(r.run_id);}catch(e){running=false;$('#run').disabled=!dataset;status(e.message,true);}};
async function deleteHistory(mode, id){
  const message=mode==='all'?'ลบประวัติการทดลองทั้งหมด รวมรายการเก่าที่ไม่แสดงหรือไม่?\nไฟล์ผลลัพธ์ ข้อมูล และโค้ดที่บันทึกในแต่ละรอบจะถูกลบและกู้คืนจากเว็บไม่ได้':`ลบการทดลอง ${id} หรือไม่?\nไฟล์ผลลัพธ์ ข้อมูล และโค้ดที่บันทึกในรอบนี้จะถูกลบและกู้คืนจากเว็บไม่ได้`;
  if(!window.confirm(message))return;
  try{const result=await api('/api/delete-runs',{mode,run_id:id});if(displayedRun&&result.deleted.includes(displayedRun)){displayedRun=null;$('#result-body').className='empty';$('#result-body').textContent='ผลการทดลองนี้ถูกลบแล้ว';}$('#history-message').textContent=`ลบแล้ว ${result.count} รายการ`;await history();}
  catch(e){$('#history-message').textContent='ลบไม่สำเร็จ: '+e.message;await history();}
}
async function history(){const rows=await api('/api/history');$('#history-list').innerHTML=rows.length?rows.map(r=>`<div class="history-item"><div><b>${escapeHTML(r.note||r.run_id)}</b><small>${escapeHTML(r.source)} · ${escapeHTML(r.status)} · ${escapeHTML(r.run_id)}</small></div><div class="history-actions"><button type="button" class="secondary" data-run="${escapeHTML(r.run_id)}">เปิดผล</button><button type="button" class="secondary danger" data-delete-run="${escapeHTML(r.run_id)}" ${r.status==='running'?'disabled':''}>ลบ</button></div></div>`).join(''):'<div class="empty">การทดลองของเธอจะถูกเก็บไว้ที่นี่</div>';document.querySelectorAll('[data-run]').forEach(b=>b.onclick=async()=>{try{const r=await api('/api/status?id='+encodeURIComponent(b.dataset.run));results(r);$('#results').scrollIntoView({behavior:'smooth'});}catch(e){status(e.message,true);}});document.querySelectorAll('[data-delete-run]').forEach(b=>b.onclick=()=>deleteHistory('one',b.dataset.deleteRun));$('#delete-all-runs').disabled=!rows.length;}
$('#delete-all-runs').onclick=()=>deleteHistory('all');
(async()=>{try{const d=await api('/api/init');defaults=d.code;fields=d.required;optional=d.optional;$('#code').value=defaults;await history();}catch(e){status(e.message,true);}})();

// Manual comparison demo: no document fetching, AI inference, or fact verification.
function claim(side){
  return Object.fromEntries(['buyer','target','company','date','time','period','stage','certainty','amount','scale','currency','url','evidence'].map(k=>[k,$(`#${side}-${k}`).value]));
}
function safeSource(url){
  try { const u=new URL(url); return ['http:','https:'].includes(u.protocol)?u.href:null; } catch { return null; }
}
let claimRendered=false;
$('#event-type').onchange=()=>{
  const dividend=$('#event-type').value==='dividend';
  document.querySelectorAll('.dividend-only').forEach(e=>{e.hidden=!dividend;});
  document.querySelectorAll('.ma-only').forEach(e=>{e.hidden=dividend;});
};
function clearClaimResult(){if(claimRendered){const box=$('#claim-result');box.className='empty';box.textContent='ข้อมูลเปลี่ยนแล้ว กดเปรียบเทียบอีกครั้งค่ะ';claimRendered=false;}}
$('#claims').addEventListener('input',clearClaimResult);
$('#claims').addEventListener('change',clearClaimResult);
$('#compare-claims').onclick=()=>{
  const a=claim('a'),b=claim('b'),eventType=$('#event-type').value;
  const result=WorkbenchFacts.compare(a,b,{sameDealVerified:$('#same-deal').checked,sameFactVerified:$('#same-fact').checked,tolerancePercent:$('#claim-tolerance').value,eventType});
  const box=$('#claim-result');box.className='claim-result '+result.kind;box.replaceChildren();
  claimRendered=true;
  const title=document.createElement('strong');title.textContent=result.message;box.appendChild(title);
  const hint=document.createElement('p');hint.textContent='ผลมาจากข้อมูลที่กรอกและกฎเบื้องต้น กรุณาตรวจชนิดมูลค่า เงื่อนไข และแหล่งข่าว ไม่ใช่ผลจาก NLI หรือการตรวจสอบข้อเท็จจริง';box.appendChild(hint);
  const list=document.createElement('ol');list.className='claim-timeline';
  const entries=[{name:'ข่าว A',data:a},{name:'ข่าว B',data:b}];
  const stages={negotiating:'เจรจา',announced:'ประกาศ',signed:'ลงนาม',pending:'กำลังพิจารณา / รอดำเนินการ',approved:'อนุมัติ',completed:'เสร็จสิ้น',cancelled:'ยกเลิก'};
  const certainty={forecast:'คาดว่า / กำลังพิจารณา',confirmed:'อนุมัติ / ยืนยันแล้ว'};
  const scales={unit:'หน่วย',million:'ล้าน',billion:'พันล้าน'};
  if(WorkbenchFacts.date(a.date)&&WorkbenchFacts.date(b.date)){
    if(a.date!==b.date)entries.sort((x,y)=>x.data.date.localeCompare(y.data.date));
    else if(a.time&&b.time&&a.time!==b.time)entries.sort((x,y)=>x.data.time.localeCompare(y.data.time));
  }
  for(const item of entries){
    const li=document.createElement('li');
    const head=document.createElement('b');head.textContent=`${item.name} · ${item.data.date||'ไม่ระบุวัน'} ${item.data.time||''} · ${stages[item.data.stage]||'ไม่ทราบสถานะ'} · ${certainty[item.data.certainty]||'ไม่ทราบความแน่นอน'}`;li.appendChild(head);
    const value=document.createElement('div');value.textContent=`มูลค่าที่กรอก: ${item.data.amount||'ไม่ระบุ'} ${scales[item.data.scale]||''} ${item.data.currency||''}${eventType==='dividend'?' ต่อหุ้น':''} · งวด/วันที่มีผล: ${item.data.period||'ไม่ระบุ'}`;li.appendChild(value);
    if(item.data.evidence.trim()){const ev=document.createElement('blockquote');ev.textContent=item.data.evidence;li.appendChild(ev);}
    const link=safeSource(item.data.url);if(link){const el=document.createElement('a');el.href=link;el.target='_blank';el.rel='noopener noreferrer';el.textContent='เปิดแหล่งข่าวที่ระบุ';li.appendChild(el);}
    list.appendChild(li);
  }
  box.appendChild(list);
};
function fillClaimExample(mode){
  const dividend=mode!=='stage';
  const a={buyer:'Company X',target:'Company Y',company:'Company X',date:'2026-01-01',time:'09:00',period:'FY2026',stage:'negotiating',certainty:'',amount:'',scale:'unit',currency:'',url:'',evidence:'ตัวอย่างสมมติ: เริ่มเจรจา'};
  const b={...a,time:'17:30',stage:'signed',evidence:'ตัวอย่างสมมติ: ลงนาม'};
  if(dividend){
    Object.assign(a,{stage:mode==='dividend'?'pending':'approved',certainty:mode==='dividend'?'forecast':'confirmed',amount:mode==='dividend'?'2':'1.80',currency:'THB',evidence:'ตัวอย่างสมมติ: ปันผลต่อหุ้นจากข่าว A'});
    Object.assign(b,{date:'2026-01-02',stage:'approved',certainty:'confirmed',amount:mode==='dividend'?'1.80':'1.50',currency:'THB',evidence:'ตัวอย่างสมมติ: ปันผลต่อหุ้นจากข่าว B'});
  }
  $('#event-type').value=dividend?'dividend':'acquisition';$('#event-type').onchange();
  $('#claim-tolerance').value='0.5';$('#same-deal').checked=true;$('#same-fact').checked=dividend;
  for(const [side,record] of [['a',a],['b',b]])for(const [key,value] of Object.entries(record))$(`#${side}-${key}`).value=value;
  clearClaimResult();$('#compare-claims').click();
}
$('#example-stage').onclick=()=>fillClaimExample('stage');
$('#example-dividend').onclick=()=>fillClaimExample('dividend');
$('#example-conflict').onclick=()=>fillClaimExample('conflict');
