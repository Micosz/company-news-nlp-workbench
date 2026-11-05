const $=s=>document.querySelector(s), token=$('meta[name="workbench-token"]').content;
let dataset=null, defaults='', fields=[], optional=[], running=false, displayedRun=null;
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Workbench-Token':token},body:JSON.stringify(body)}:{});const j=await r.json();if(!r.ok)throw Error(j.error||r.statusText);return j;}
function status(message,error=false){$('#status').className='alert'+(error?' error':'');$('#status').textContent=message;}
function dataStatus(message,error=false){$('#data-status').className='alert'+(error?' error':'');$('#data-status').textContent=message;}
function clearData(message){dataset=null;$('#run').disabled=true;$('#data-info').className='empty';$('#data-info').textContent=message;$('#mapping-wrap').hidden=true;}
function showData(d){dataset=d;$('#data-info').className='empty loaded';const t=d.time_coverage;$('#data-info').innerHTML=`<div><strong>${d.rows.toLocaleString()}</strong>คู่ข้อความ</div><div>${escapeHTML(d.source)}<br><small>${escapeHTML(Object.entries(d.splits).map(([k,v])=>`${k}: ${v}`).join(' · '))}</small>${t?`<br><small>วันครบทั้งคู่ ${t.both.toLocaleString()} · มีวันฝั่งเดียว ${t.one.toLocaleString()} · ไม่มีวันทั้งคู่ ${t.neither.toLocaleString()}</small>`:''}${d.test_date_relation?`<br><small>Test วันเดียวกัน ${d.test_date_relation.same.toLocaleString()} · ต่างวัน ${d.test_date_relation.different.toLocaleString()}</small>${d.test_date_relation.same+d.test_date_relation.different>0 && (!d.test_date_relation.same||!d.test_date_relation.different)?'<br><small>⚠️ Test ขาดความหลากหลายของวัน: ยังเทียบกรณีวันตรงกับต่างวันไม่ได้</small>':''}`:''}</div>`;$('#mapping-wrap').hidden=false;
$('#mapping').innerHTML=[...fields,...optional].map(k=>`<label>${escapeHTML(k)} ${fields.includes(k)?'*':'(เสริม)'}<select data-field="${k}"><option value="">— ไม่เลือก —</option>${d.columns.map(c=>`<option value="${escapeHTML(c)}" ${c===k?'selected':''}>${escapeHTML(c)}</option>`).join('')}</select></label>`).join('');
$('#preview').innerHTML=`<table><thead><tr>${d.columns.map(c=>`<th>${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${d.preview.map(r=>`<tr>${d.columns.map(c=>`<td class="text">${escapeHTML(String(r[c]).slice(0,180))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;$('#run').disabled=running;dataStatus('โหลดข้อมูลแล้ว พร้อมตรวจสอบคอลัมน์และเริ่มทดลอง');}
$('#builtin').onchange=()=>{clearData('กด “โหลดข้อมูล” เพื่อใช้ชุดที่เลือก');};
$('#load').onclick=async()=>{try{$('#load').disabled=true;const mode=$('#builtin').value;showData(await api('/api/builtin',{mode}));const joint=mode.endsWith('_joint'),ai=mode.endsWith('_ai')||joint,timed=['story_time','story_resplit','story_mixed'].includes(mode),aiNote='AI-assisted roles from full article; human review pending; exploratory';$('#roles').value=ai?'predicted':'none';$('#time-source').value=joint?'announcement_proxy':timed?'oracle':'none';if(joint){dataStatus('Demo: sparse announcement dates are proxies from full articles, not gold event dates; AI roles need review.');}else if(timed){dataStatus('โหลดชุดเวลาแล้ว · วันที่ที่มีเป็นป้ายกำกับ (oracle) · วันที่ขาดเป็น unknown ไม่ใช่วันที่โมเดลดึงเอง');}else if(ai){if(!$('#note').value.trim())$('#note').value=aiNote;dataStatus('โหลดบทบาทจาก AI แล้ว · ยังรอคนตรวจ · บทบาทใช้บริบทข่าวเต็มที่ข้อความทดลองแบบสั้นอาจไม่มี');}if(!ai&&$('#note').value===aiNote)$('#note').value='';}catch(e){clearData('โหลดข้อมูลไม่สำเร็จ กรุณาเลือกและโหลดอีกครั้ง');dataStatus(e.message,true);}finally{$('#load').disabled=false;}};
$('#file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>50*1024*1024)throw Error('ไฟล์ใหญ่เกิน 50 MB');dataStatus('กำลังอ่านไฟล์…');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f);});showData(await api('/api/upload',{name:f.name,data}));}catch(e){clearData('นำเข้าข้อมูลไม่สำเร็จ กรุณาเลือกไฟล์อีกครั้ง');dataStatus(e.message,true);}};
$('#load-annotation').onclick=async()=>{const f=$('#annotation-file').files[0];if(!f){dataStatus('กรุณาเลือกแบบฟอร์มบทบาท',true);return;}try{if(f.size>50*1024*1024)throw Error('ไฟล์ใหญ่เกิน 50 MB');$('#load-annotation').disabled=true;dataStatus('กำลังตรวจหลักฐานและเตรียมคู่ข้อความ…');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f);});const prepared=await api('/api/annotations',{name:f.name,data,fold:$('#annotation-fold').value});showData(prepared);$('#roles').value='none';const warnings=prepared.annotation_warnings||[];dataStatus(warnings.length?`เตือน ${warnings.length} รายการ: ชื่อบริษัทไม่ปรากฏในข้อความหลักฐาน โปรดตรวจชื่อย่อหรือ alias: `+warnings.map(w=>`${w.mention_id} (${w.role}: ${w.name})`).join('; '):'โหลดบทบาทแล้ว โปรดเลือกที่มาของบทบาทตามจริงก่อนรัน และตรวจ coverage ค่ะ',warnings.length>0);}catch(e){clearData('โหลดบทบาทไม่สำเร็จ กรุณาตรวจไฟล์และลองอีกครั้ง');dataStatus(e.message,true);}finally{$('#load-annotation').disabled=false;}};
const originalFlow=$('.flow').innerHTML;
$('#reset').onclick=selectExperiment;
$('#import-code').onclick=()=>$('#code-file').click();$('#code-file').onchange=async e=>{if(e.target.files[0])$('#code').value=await e.target.files[0].text();};
$('#save-code').onclick=()=>{const url=URL.createObjectURL(new Blob([$('#code').value],{type:'text/x-python'}));const a=document.createElement('a');a.href=url;a.download='pair_experiment.py';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('#code').addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();const t=e.target,s=t.selectionStart;t.setRangeText('    ',s,t.selectionEnd,'end');}});
const names=WorkbenchCharts.names;
function clusteringPanel(c){
  if(!c)return '';
  if(c.status!=='available')return `<div class="alert">ยังไม่มีผลจัดกลุ่ม B³: ${escapeHTML(c.reason||'ข้อมูลไม่ครบ')}</div>`;
  const rows=Object.entries(c.models||{}).map(([name,v])=>`<tr><td>${escapeHTML(names[name]||name)}</td><td>${(100*v.b3_precision).toFixed(2)}%</td><td>${(100*v.b3_recall).toFixed(2)}%</td><td>${(100*v.b3_f1).toFixed(2)}%</td><td>${v.predicted_clusters}</td></tr>`).join('');
  return `<div class="cluster-panel card"><h3>ผลจัดกลุ่มเหตุการณ์ · B³</h3><p>นำคู่ที่ทำนายว่าเหมือนกันมาเชื่อมเป็นกลุ่ม แล้วเทียบกับเฉลย: test topic ${escapeHTML(c.test_topic)} · ${c.test_mentions} mentions · เฉลย ${c.gold_clusters} กลุ่ม</p><div class="table-wrap"><table><thead><tr><th>โมเดล</th><th>B³ Precision</th><th>B³ Recall</th><th>B³ F1</th><th>กลุ่มที่ทำนาย</th></tr></thead><tbody>${rows}</tbody></table></div><p class="chart-note">คำนวณเฉพาะ Pilot ที่มีคู่ test ครบทุกคู่ การเชื่อมเป็นทอด ๆ อาจรวมกลุ่มเกินจริง · B³ เพียงค่าเดียวไม่ใช่ CoNLL F1 และยังเทียบกับ CohTP โดยตรงไม่ได้</p><div class="alert">Pilot มีเพียง 4 เหตุการณ์และหนึ่งเหตุการณ์หลักต่อดีล ชื่อบริษัทอาจกลายเป็นทางลัดในการทำนาย คะแนนรอบนี้ยังสรุปผลทั่วไปไม่ได้</div></div>`;
}
let selectedMetric='f1', savedRuns=[], openingRun=0, redrawCharts=null;
const sourceName=s=>({story_mixed:'Full Mixed',story_time:'Full + Timeline',story_resplit:'Timeline · exploratory split',full:'Full ECB+',small_A:'Pilot A',small_B:'Pilot B',small_A_joint:'Pilot A - roles + announcement proxy',small_B_joint:'Pilot B - roles + announcement proxy',small_A_ai:'Pilot A + AI roles',small_B_ai:'Pilot B + AI roles'})[s]||s||'ไม่ระบุชุดข้อมูล';
function showView(id){
  const target=['data','algorithm','results','history','claims'].includes(id)?id:'results';
  document.querySelectorAll('main > section').forEach(s=>s.hidden=s.id!==target);
  document.querySelectorAll('.app-header nav a').forEach(a=>{if(a.hash==='#'+target)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(location.hash!=='#'+target)location.hash=target;
}
window.addEventListener('hashchange',()=>{if(location.hash!=='#main-content')showView(location.hash.slice(1));});
showView(location.hash.slice(1));
function detail(title,content,extra=''){return `<details class="result-detail" ${extra}><summary>${title}</summary><div class="detail-content">${content}</div></details>`;}
function scoreTable(models){
  return `<div class="table-wrap score-table"><table><thead><tr><th scope="col">โมเดล</th>${Object.entries(WorkbenchCharts.metrics).filter(([k])=>k!=='f1').map(([k,label])=>`<th scope="col" data-score="${k}">${label} (%)</th>`).join('')}<th scope="col" data-score="f1">F1 (%)</th></tr></thead><tbody>${Object.entries(models).map(([key,v])=>`<tr><td>${escapeHTML(names[key]||key)}</td>${['precision','recall','macro_f1','f1'].map(k=>`<td data-score="${k}">${WorkbenchCharts.percentage(v[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function chartPanel(r){
  const groups=WorkbenchCharts.modelGroups(r.models);
  return `<div class="card benchmark-card"><div class="benchmark-heading"><div><h3 id="metric-title">${WorkbenchCharts.metrics[selectedMetric]} · เปรียบเทียบโมเดล</h3><p>สเกล 0–100% · ค่าสูงกว่าแสดงว่าดีกว่า</p></div><div class="benchmark-tools">${Object.keys(groups.references).length?'<label><input id="include-references" type="checkbox">รวมโมเดลอ้างอิง</label>':''}<button class="secondary" id="save-metric-chart">บันทึก SVG</button></div></div><div id="metric-chart" class="benchmark-scroll" aria-live="polite"></div><div class="insight">${escapeHTML(WorkbenchCharts.resultInsight(r.models))}</div></div>`;
}
function bindCharts(data){
  const models=data.metrics.models, runId=data.manifest.run_id;
  redrawCharts=()=>{
    const groups=WorkbenchCharts.modelGroups(models), all=$('#include-references')?.checked;
    const shown=all||!Object.keys(groups.primary).length?models:groups.primary;
    $('#metric-chart').innerHTML=WorkbenchCharts.benchmarkChart(shown,selectedMetric,runId,window.matchMedia('(max-width:600px)').matches);
    $('#metric-title').textContent=WorkbenchCharts.metrics[selectedMetric]+' · เปรียบเทียบโมเดล';
    document.querySelectorAll('[data-score]').forEach(e=>e.classList.toggle('is-selected',e.dataset.score===selectedMetric));
  };
  const renderConfusion=()=>{const key=$('#chart-model').value;$('#confusion-chart').innerHTML=WorkbenchCharts.confusionChart(models[key],names[key]||key,runId);};
  function download(selector,suffix){
    const svg=$(selector).querySelector('svg');if(!svg)return;
    const url=URL.createObjectURL(new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n'+svg.outerHTML],{type:'image/svg+xml;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`${runId}_${suffix.replace(/[^a-zA-Z0-9_-]/g,'_')}.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  if($('#include-references'))$('#include-references').onchange=redrawCharts;
  $('#chart-model').onchange=renderConfusion;
  $('#save-metric-chart').onclick=()=>download('#metric-chart',selectedMetric);
  $('#save-confusion-chart').onclick=()=>download('#confusion-chart','confusion_'+$('#chart-model').value);
  redrawCharts();renderConfusion();
}
document.querySelectorAll('[data-metric]').forEach(b=>b.onclick=()=>{
  selectedMetric=b.dataset.metric;
  document.querySelectorAll('[data-metric]').forEach(t=>t.setAttribute('aria-pressed',String(t===b)));
  if(redrawCharts)redrawCharts();
});
function updateRunPicker(){
  const picker=$('#run-picker');picker.innerHTML=savedRuns.length?savedRuns.map(r=>`<option value="${escapeHTML(r.run_id)}">${escapeHTML(sourceName(r.source))} · ${escapeHTML(r.run_id)}${r.status!=='completed'?' · '+escapeHTML(r.status):''}</option>`).join(''):'<option value="">ยังไม่มีรอบทดลอง</option>';
  picker.disabled=!savedRuns.length;
  picker.value=displayedRun||'';
}
async function openRun(id){
  if(!id)return;
  const request=++openingRun;$('#result-body').classList.add('load-state');$('#app-message').textContent='กำลังเปิดผลการทดลอง…';
  try{const r=await api('/api/status?id='+encodeURIComponent(id));if(request!==openingRun)return;results(r);$('#app-message').textContent='';}
  catch(e){if(request!==openingRun)return;$('#app-message').textContent='เปิดผลไม่สำเร็จ: '+e.message;updateRunPicker();}
  finally{if(request===openingRun)$('#result-body').classList.remove('load-state');}
}
window.matchMedia('(max-width:600px)').addEventListener('change',()=>{if(redrawCharts)redrawCharts();});
$('#run-picker').onchange=()=>openRun($('#run-picker').value);
function results(data){
  const m=data.manifest,r=data.metrics;displayedRun=m.run_id;redrawCharts=null;$('#result-body').className='';
  if(!savedRuns.some(run=>run.run_id===m.run_id))savedRuns.unshift(m);updateRunPicker();
  const exportLink=$('#export-run');exportLink.hidden=false;exportLink.href='/api/download?id='+encodeURIComponent(m.run_id);
  const roleSources={none:'ไม่มีบทบาท',manual:'คนทำป้ายกำกับ (oracle)',predicted:'บทบาทจากโมเดลที่นำเข้า'};
  const timeSources={announcement_proxy:'Announcement date proxy (not gold event date)',none:'ไม่ใช้ข้อมูลเวลา',oracle:'เวลาแบบ oracle',predicted:'เวลาจากโมเดลทำนาย'};
  let html=m.config?.time_source==='announcement_proxy' ? '<div class="alert">ชุดสาธิตเท่านั้น: วันประกาศเป็นข้อมูลแทนเวลา ไม่ใช่วันเกิดเหตุการณ์ที่ยืนยันแล้ว · คู่ที่มีบทบาทและวันครบมีน้อยมาก · คะแนน 100% อาจเกิดจากทางลัดของข้อมูล และใช้สรุป improvement ไม่ได้</div>' : '';
  if(r){
    const groups=WorkbenchCharts.modelGroups(r.models);
    html+=chartPanel(r)+'<div class="card score-surface">'+scoreTable(Object.keys(groups.primary).length?groups.primary:r.models);
    if(Object.keys(groups.references).length)html+=detail('โมเดลอ้างอิง',scoreTable(groups.references));
    const warnings=[...(r.warnings||[])];
    if(m.annotation_warnings?.length)warnings.push(`ชื่อบทบาทไม่ปรากฏในหลักฐาน ${m.annotation_warnings.length} รายการ: `+m.annotation_warnings.map(w=>`${w.mention_id} (${w.role}: ${w.name})`).join('; '));
    for(const [feature,coverage] of [['role',r.role_coverage],['time',r.time_coverage]]){
      if(m.config?.[feature+'_source'] && m.config[feature+'_source']!=='none' && coverage?.train_complete_pairs!==undefined && coverage?.test_complete_pairs!==undefined && (!coverage.train_complete_pairs||!coverage.test_complete_pairs))warnings.push(`รอบเก่า: เลือกที่มา${feature==='role'?'บทบาท':'เวลา'}ไว้ แต่ข้อมูลครบไม่พอใน train หรือ test จึงยังไม่ใช่ผลทดลองของส่วนเพิ่มนี้`);
    }
    for(const [name,model] of Object.entries(r.models)){
      const c=model.confusion;
      if(c&&r.test_pairs>0&&c.tp+c.fp===0)warnings.push(`${names[name]||name} ทำนายทุกคู่เป็นคนละเหตุการณ์ (class 0)`);
      else if(c&&r.test_pairs>0&&c.tn+c.fn===0)warnings.push(`${names[name]||name} ทำนายทุกคู่เป็นเหตุการณ์เดียวกัน (class 1)`);
    }
    let methods='<p>การทดลองนี้เป็น baseline ของโครงงาน ไม่ใช่การรัน CohTP เต็มระบบ และไม่ได้วัดคุณภาพการดึงเหตุการณ์อัตโนมัติ</p>';
    methods+=`<dl class="method-meta"><dt>วิธีที่บันทึก</dt><dd>${escapeHTML(r.method||'ไม่ระบุ')}</dd><dt>บทบาทผู้ซื้อ–เป้าหมาย</dt><dd>${escapeHTML(roleSources[m.config?.role_source]||'ไม่ระบุ')}</dd><dt>วันเหตุการณ์</dt><dd>${escapeHTML(timeSources[m.config?.time_source]||'ไม่ระบุ')}</dd><dt>Threshold</dt><dd>${m.config?.threshold_mode==='dev_f1'?'เลือกจาก dev F1':'คงที่ 0.5'}</dd><dt>Seed</dt><dd>${escapeHTML(m.config?.seed??'ไม่ระบุ')}</dd><dt>หมายเหตุ</dt><dd>${escapeHTML(m.config?.note||'ไม่มี')}</dd></dl>`;
    methods+='<p>F1, Precision และ Recall วัด class 1 (เหตุการณ์เดียวกัน) · Macro F1 เฉลี่ยทั้งสอง class · ใช้ผลของรอบเดียวกันเพื่อเปรียบเทียบฟีเจอร์</p>';
    if(r.role_coverage?.train_complete_pairs!==undefined)methods+=`<p>คู่ที่มีบทบาทครบ: train ${r.role_coverage.train_complete_pairs} · test ${r.role_coverage.test_complete_pairs} · ช่องว่างยังเป็น unknown</p>`;
    if(r.time_coverage?.train_complete_pairs!==undefined)methods+=`<p>คู่ที่มีวันครบ: train ${r.time_coverage.train_complete_pairs} · test ${r.time_coverage.test_complete_pairs} · วันเดียวกันไม่ได้ยืนยันว่าเป็นเหตุการณ์เดียวกัน</p>`;
    if(r.joint_coverage?.train_complete_pairs!==undefined)methods+=`<p>คู่ที่มีบทบาทและวันครบพร้อมกัน: train ${r.joint_coverage.train_complete_pairs} · test ${r.joint_coverage.test_complete_pairs} · ข้อมูลไม่ครบยังเป็น unknown</p>`;
    if(!r.models.text_plus_roles)methods+='<p>รอบนี้ไม่มีผล Text + finance roles · ต้องมีบทบาท buyer/target และเลือกที่มาก่อนรัน กราฟไม่แทนผลที่ขาดด้วยศูนย์</p>';
    methods+=warnings.map(w=>`<div class="alert">${escapeHTML(w)}</div>`).join('');
    methods+=`<div class="table-wrap"><table><thead><tr><th>โมเดล</th><th>Features</th><th>Threshold</th></tr></thead><tbody>${Object.entries(r.models).map(([name,v])=>`<tr><td>${escapeHTML(names[name]||name)}</td><td>${escapeHTML((v.features||[]).join(', '))}</td><td>${escapeHTML(v.threshold??'ไม่ระบุ')}</td></tr>`).join('')}</tbody></table></div>`;
    if(r.delta_f1!==undefined)methods+=`<p>Δ F1 (roles − text) = ${(100*r.delta_f1).toFixed(2)} จุดเปอร์เซ็นต์</p>`;
    if(r.delta_time_f1!==undefined)methods+=`<p>Δ F1 (time − text) = ${(100*r.delta_time_f1).toFixed(2)} จุดเปอร์เซ็นต์</p>`;
    methods+='<p>ผลเฉพาะรอบนี้ ยังไม่ใช่ข้อสรุปเชิงสถิติ</p>';
    html+=detail(`วิธีทดลองและข้อจำกัด${warnings.length?`<span class="tag">${warnings.length} ข้อสังเกต</span>`:''}`,methods);
    html+=detail('ดูคู่ข่าวที่ทายผิด',`<p>แสดง 20 แถวแรก · ดาวน์โหลดครบได้ใน ZIP</p><div class="table-wrap result-errors"><table><thead><tr><th>โมเดล</th><th>ข้อความ A</th><th>ข้อความ B</th><th>จริง → ทำนาย</th><th>คะแนน</th></tr></thead><tbody>${(data.errors||[]).map(e=>`<tr><td>${escapeHTML(names[e.model]||e.model)}</td><td class="text">${escapeHTML(e.text_a)}</td><td class="text">${escapeHTML(e.text_b)}</td><td>${escapeHTML(e.label)} → ${escapeHTML(e.prediction)}</td><td>${Number(e.score).toFixed(3)}</td></tr>`).join('')}</tbody></table></div>${!(data.errors||[]).length?'<p>ไม่มีแถวข้อผิดพลาดที่บันทึกไว้ในผลนี้</p>':''}`);
    html+=detail('จำนวนคู่ที่ทายถูก / ผิด',`<div class="confusion-layout"><div class="chart-controls"><select id="chart-model" aria-label="โมเดลสำหรับ confusion matrix">${Object.keys(r.models).map(key=>`<option value="${escapeHTML(key)}" ${key==='text_baseline'?'selected':''}>${escapeHTML(names[key]||key)}</option>`).join('')}</select><button class="secondary" id="save-confusion-chart">บันทึก SVG</button></div><div id="confusion-chart" class="chart-image"></div><p class="chart-note">FP = รวมคนละเหตุการณ์ · FN = แยกเหตุการณ์เดียวกัน · สีแสดงถูก/ผิด ไม่ใช่ความเข้มตามจำนวน</p></div>`);
    if(r.clustering)html+=detail('ผลจัดกลุ่มเหตุการณ์ · B³',clusteringPanel(r.clustering));
    if(r.time_strata){const labels={both:'มีวันทั้งสองฝั่ง',one:'มีวันฝั่งเดียว',neither:'ไม่มีวันทั้งสองฝั่ง'};html+=detail('ผลแยกตามความครบของวันที่',`<p>เทียบโมเดลบนคู่เดียวกันในแต่ละกลุ่ม · ขนาดและสัดส่วน label ต่างกัน</p><div class="table-wrap"><table><thead><tr><th>ข้อมูลเวลา</th><th>จำนวนคู่</th><th>คู่เหตุการณ์เดียวกัน</th><th>Text F1</th><th>Text + time F1</th></tr></thead><tbody>${Object.entries(r.time_strata).map(([k,v])=>`<tr><td>${escapeHTML(labels[k]||k)}</td><td>${v.pairs}</td><td>${v.positive_pairs}</td><td>${WorkbenchCharts.percentage(v.models?.text_baseline?.f1)}</td><td>${WorkbenchCharts.percentage(v.models?.text_plus_time?.f1)}</td></tr>`).join('')}</tbody></table></div>`);}
    html+='</div>';
    html+=`<p class="result-meta">Test ${Number(r.test_pairs).toLocaleString()} คู่ · ${escapeHTML(r.elapsed_seconds)} วินาที · ${escapeHTML(m.run_id)}</p>`;
  }else html+=`<div class="empty">${m.status==='running'?'รอบนี้กำลังทำงาน เปิดผลอีกครั้งเมื่อเสร็จ':'รอบนี้ยังไม่มีคะแนนที่บันทึกไว้'}</div>`;
  if(m.error)html+=`<div class="alert error">${escapeHTML(m.error)}</div>`;
  html+=detail('Python log',`<pre>${escapeHTML(data.log||'ยังไม่มี log')}</pre>`);
  $('#result-body').innerHTML=html;if(r)bindCharts(data);renderEventGraph(m.run_id);
}

async function watch(id){try{const data=await api('/api/status?id='+id);if(data.manifest.status==='running'){status('กำลังประมวลผล… บันทึก '+id);setTimeout(()=>watch(id),1200);return;}running=false;$('#run').disabled=!dataset;status(data.manifest.status==='completed'?'บันทึกผลการทดลองแล้ว':'รันไม่สำเร็จ — เก็บโค้ดและ error log แล้ว',data.manifest.status!=='completed');results(data);await history();showView('results');}catch(e){running=false;$('#run').disabled=!dataset;status('อ่านสถานะไม่ได้: '+e.message+' ลองดูในสมุดบันทึกอีกครั้ง',true);}}
$('#run').onclick=async()=>{try{const mapping={};document.querySelectorAll('[data-field]').forEach(s=>mapping[s.dataset.field]=s.value);if(fields.some(k=>!mapping[k]))throw Error('เลือกคอลัมน์ที่มี * ให้ครบก่อนค่ะ');if((dataset?.source?.endsWith('_ai')||dataset?.source?.endsWith('_joint'))&&$('#roles').value==='manual')throw Error('ชุดบทบาท AI ยังไม่ได้ผ่านการตรวจโดยคน โปรดเลือกโมเดลทำนาย');running=true;$('#run').disabled=true;status('กำลังตรวจข้อมูลและเตรียมการทดลอง…');const r=await api('/api/run',{dataset_id:dataset.dataset_id,mapping,code:$('#code').value,config:{seed:Number($('#seed').value),experiment_mode:$('#experiment-mode').value,role_source:['graph','text','time'].includes($('#experiment-mode').value)?'none':$('#roles').value,time_source:['graph','text','roles'].includes($('#experiment-mode').value)?'none':$('#time-source').value,threshold_mode:$('#threshold-mode').value,joint_enabled:$('#joint-enabled').checked,note:$('#note').value}});watch(r.run_id);}catch(e){running=false;$('#run').disabled=!dataset;status(e.message,true);}};
async function deleteHistory(mode, id){
  const message=mode==='all'?'ลบประวัติการทดลองทั้งหมด รวมรายการเก่าที่ไม่แสดงหรือไม่?\nไฟล์ผลลัพธ์ ข้อมูล และโค้ดที่บันทึกในแต่ละรอบจะถูกลบและกู้คืนจากเว็บไม่ได้':`ลบการทดลอง ${id} หรือไม่?\nไฟล์ผลลัพธ์ ข้อมูล และโค้ดที่บันทึกในรอบนี้จะถูกลบและกู้คืนจากเว็บไม่ได้`;
  if(!window.confirm(message))return;
  try{const result=await api('/api/delete-runs',{mode,run_id:id});if(displayedRun&&result.deleted.includes(displayedRun)){openingRun++;displayedRun=null;redrawCharts=null;$('#export-run').hidden=true;$('#result-body').className='empty';$('#result-body').textContent='ผลการทดลองนี้ถูกลบแล้ว';}$('#history-message').textContent=`ลบแล้ว ${result.count} รายการ`;await history();}
  catch(e){$('#history-message').textContent='ลบไม่สำเร็จ: '+e.message;await history();}
}
async function history(){const rows=await api('/api/history');savedRuns=rows;updateRunPicker();$('#history-list').innerHTML=rows.length?rows.map(r=>`<div class="history-item"><div><b>${escapeHTML(r.note||r.run_id)}</b><small>${escapeHTML(r.source)} · ${escapeHTML(r.status)} · ${escapeHTML(r.run_id)}</small></div><div class="history-actions"><button type="button" class="secondary" data-run="${escapeHTML(r.run_id)}">เปิดผล</button><button type="button" class="secondary danger" data-delete-run="${escapeHTML(r.run_id)}" ${r.status==='running'?'disabled':''}>ลบ</button></div></div>`).join(''):'<div class="empty">ยังไม่มีประวัติการทดลอง</div>';document.querySelectorAll('[data-run]').forEach(b=>b.onclick=async()=>{try{showView('results');await openRun(b.dataset.run);}catch(e){status(e.message,true);}});document.querySelectorAll('[data-delete-run]').forEach(b=>b.onclick=()=>deleteHistory('one',b.dataset.deleteRun));$('#delete-all-runs').disabled=!rows.length;}
$('#delete-all-runs').onclick=()=>deleteHistory('all');
(async()=>{try{const d=await api('/api/init');defaults=d.code;fields=d.required;optional=d.optional;$('#code').value=defaults;await history();const latest=savedRuns.find(r=>r.status==='completed');if(latest&&!displayedRun)await openRun(latest.run_id);}catch(e){$('#app-message').textContent='เปิดระบบไม่สำเร็จ: '+e.message;}})();

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
function clearClaimResult(){if(claimRendered){const box=$('#claim-result');box.className='empty';box.textContent='ข้อมูลเปลี่ยนแปลง กรุณาเปรียบเทียบอีกครั้ง';claimRendered=false;}}
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

let modeVersion=0;
async function selectExperiment(){
 const mode=$('#experiment-mode').value, version=++modeVersion;
 $('#run').disabled=true;
 try{
 const code=mode==='graph'?(await api('/api/nli-code')).code:defaults;
 if(version!==modeVersion)return;
 $('#code').value=code;
 const graph=mode==='graph';
 $('#threshold-mode').disabled=graph;if(graph)$('#threshold-mode').value='fixed';
 $('#roles').closest('label').hidden=graph||mode==='text'||mode==='time';
 $('#time-source').closest('label').hidden=graph||mode==='text'||mode==='roles';
 $('.flow').innerHTML=originalFlow;
 if(graph)$('.flow').textContent='NLI + TF-IDF → No-message / GNN → Held-out test';
 $('#experiment-help').textContent=graph?'Pilot A/B · เปรียบเทียบ NLI ที่ไม่ส่งข้อมูลผ่านกราฟกับ NLI + GNN':'เปรียบเทียบกับ Text baseline · ต้องมีข้อมูลและระบุที่มาของฟีเจอร์ที่เลือก';
 $('#run').disabled=!dataset||running;
 }catch(e){status(e.message,true);}
}
$('#experiment-mode').onchange=selectExperiment;

async function renderEventGraph(runId){
 let data;try{data=await api('/api/graph?id='+encodeURIComponent(runId));}catch{return;}
 if(displayedRun!==runId)return;
 const wrap=document.createElement('div');wrap.className='card event-network';
 wrap.innerHTML='<h3>NLI + GNN · Event graph</h3><p>Drag a node to move its connections. Drag the background to pan. Scroll to zoom.</p><div class="network-controls"><button type="button" class="secondary">Reset view</button><label>Link display <select><option value="3">Top 3 connections per node</option><option value="all">All predicted positive connections</option></select></label><label>Repulsion <input type="range" min="500" max="5000" value="2200"></label></div><p class="network-summary"></p>';
 const canvas=document.createElement('canvas');canvas.width=1100;canvas.height=650;canvas.setAttribute('aria-label','Interactive event graph. Drag nodes, pan background, zoom using the mouse wheel.');canvas.tabIndex=0;wrap.append(canvas);
 const info=document.createElement('p');info.className='network-detail';info.textContent='Select a node or edge to inspect its evidence. Layout and link filtering do not change model scores.';wrap.append(info);$('#result-body').append(wrap);
 const ctx=canvas.getContext('2d'),n=data.nodes.length;
 const points=data.nodes.map((v,i)=>({...v,x:550+Math.cos(i*2.399)*Math.sqrt(i+1)*30,y:325+Math.sin(i*2.399)*Math.sqrt(i+1)*30,vx:0,vy:0}));
 let edges=[],zoom=1,tx=0,ty=0,drag=null,pan=null,hover=null,alpha=1,raf=0,repel=2200;
 const controls=wrap.querySelector('.network-controls'),filter=controls.querySelector('select');
 function selectEdges(){const candidates=data.edges.filter(e=>e.score>=.5);const keep=new Set();if(filter.value==='all')candidates.forEach(e=>keep.add(e));else for(const p of points)candidates.filter(e=>e.a===p.id||e.b===p.id).sort((a,b)=>b.score-a.score).slice(0,3).forEach(e=>keep.add(e));edges=[...keep];wrap.querySelector('.network-summary').textContent=`${n} text nodes · ${edges.length} displayed links / ${candidates.length} predicted positive pairs · display filter only`;wake();}
 function screen(e){const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)*1100/r.width,y:(e.clientY-r.top)*650/r.height};}
 function world(p){return{x:(p.x-550-tx)/zoom+550,y:(p.y-325-ty)/zoom+325};}
 function near(p){return points.find(v=>Math.hypot(v.x-p.x,v.y-p.y)<13/zoom);}
 function draw(){ctx.clearRect(0,0,1100,650);ctx.save();ctx.translate(550+tx,325+ty);ctx.scale(zoom,zoom);ctx.translate(-550,-325);
 const neighbors=new Set(hover?[hover.id]:[]);if(hover)for(const e of edges){if(e.a===hover.id)neighbors.add(e.b);if(e.b===hover.id)neighbors.add(e.a);}
 for(const e of edges){const a=points[e.a],b=points[e.b],active=hover&&(e.a===hover.id||e.b===hover.id);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=active?'#8874ce':hover?'#e9e8ed':'#d1d0d6';ctx.lineWidth=(active?1.7:.8)/zoom;ctx.stroke();}
 for(const p of points){const active=hover===p,dim=hover&&!neighbors.has(p.id);ctx.fillStyle=active?'#9074de':dim?'#d8d8dc':'#68666f';ctx.beginPath();ctx.arc(p.x,p.y,active?8:6,0,Math.PI*2);ctx.fill();ctx.fillStyle=dim?'#d0cfd4':'#45434b';ctx.font=`${13/Math.sqrt(zoom)}px sans-serif`;ctx.fillText(`News ${p.id+1}`,p.x+11,p.y+4);}
 ctx.restore();}
 function tick(){raf=0;if(!wrap.isConnected)return;if(alpha>.002||drag){for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){const a=points[i],b=points[j];let dx=a.x-b.x,dy=a.y-b.y,d2=Math.max(100,dx*dx+dy*dy),d=Math.sqrt(d2),f=repel*alpha/d2;a.vx+=dx/d*f;b.vx-=dx/d*f;a.vy+=dy/d*f;b.vy-=dy/d*f;}
 for(const e of edges){const a=points[e.a],b=points[e.b],dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-140)*.009*alpha;a.vx+=dx/d*f;b.vx-=dx/d*f;a.vy+=dy/d*f;b.vy-=dy/d*f;}
 for(const p of points){if(p===drag){p.vx=p.vy=0;continue;}p.vx=(p.vx+(550-p.x)*.0015*alpha)*.83;p.vy=(p.vy+(325-p.y)*.0015*alpha)*.83;p.x+=Math.max(-12,Math.min(12,p.vx));p.y+=Math.max(-12,Math.min(12,p.vy));}alpha*=.985;if(drag)alpha=Math.max(.3,alpha);draw();raf=requestAnimationFrame(tick);}else draw();}
 function wake(){alpha=.8;if(!raf)raf=requestAnimationFrame(tick);}
 canvas.onpointerdown=e=>{const s=screen(e),p=world(s);drag=near(p)||null;hover=drag;if(drag){info.textContent=`News ${drag.id+1}: ${drag.text}`;wake();}else pan={x:s.x,y:s.y,tx,ty,moved:false};canvas.setPointerCapture(e.pointerId);};
 canvas.onpointermove=e=>{const s=screen(e),p=world(s);if(drag){drag.x=p.x;drag.y=p.y;wake();}else if(pan){tx=pan.tx+s.x-pan.x;ty=pan.ty+s.y-pan.y;pan.moved ||= Math.hypot(s.x-pan.x,s.y-pan.y)>4;draw();}else{hover=near(p)||null;canvas.style.cursor=hover?'grab':'default';draw();}};
 canvas.onpointerup=e=>{if(pan&&!pan.moved){const p=world(screen(e));let nearest=null,dist=7/zoom;for(const edge of edges){const a=points[edge.a],b=points[edge.b],dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1))),d=Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);if(d<dist){nearest=edge;dist=d;}}if(nearest)info.textContent=`News ${nearest.a+1} ↔ ${nearest.b+1}: GNN ${nearest.score.toFixed(3)} · NLI contradiction / entailment / neutral ${nearest.nli.map(v=>v.toFixed(3)).join(' / ')}`;}drag=null;pan=null;wake();};
 canvas.onpointercancel=()=>{drag=null;pan=null;wake();};canvas.onpointerleave=()=>{if(!drag&&!pan){hover=null;draw();}};
 canvas.onwheel=e=>{e.preventDefault();const p=screen(e),old=zoom;zoom=Math.max(.3,Math.min(4,zoom*Math.exp(-e.deltaY*.001)));tx=p.x-550-(p.x-550-tx)*zoom/old;ty=p.y-325-(p.y-325-ty)*zoom/old;draw();};
 canvas.onkeydown=e=>{if(['+','=','-','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();if(e.key==='+'||e.key==='=')zoom=Math.min(4,zoom*1.1);if(e.key==='-')zoom=Math.max(.3,zoom/1.1);if(e.key==='ArrowLeft')tx-=30;if(e.key==='ArrowRight')tx+=30;if(e.key==='ArrowUp')ty-=30;if(e.key==='ArrowDown')ty+=30;draw();}};
 controls.querySelector('button').onclick=()=>{zoom=1;tx=ty=0;wake();};filter.onchange=selectEdges;controls.querySelector('input').oninput=e=>{repel=+e.target.value;wake();};selectEdges();
}
