'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent = value => (100 * value).toFixed(4);
const labels = {OR:'Original OR',TFIDF:'TF-IDF only',OR_TFIDF:'OR + TF-IDF',OR_TFIDF_NB:'OR + TF-IDF + NB'};
let catalog, current, busy = false;
const orbitMotion = createOrbitMotion($('orbitScene'));
function showOrbit(active) {
  $('empty').classList.toggle('in-flight', active);
  $('orbitCaption').hidden = !active;
  $('empty').hidden = !active && Boolean(current);
  $('output').hidden = active || !current;
}
const downloadURLs = [];
let database;
function openDB() {
  if (!database) database = new Promise((resolve, reject) => {
    const request = indexedDB.open('xamr-research-evidence-v1', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('runs', {keyPath:'id'});
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  return database;
}
async function storage(action, value) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('runs', action === 'put' ? 'readwrite' : 'readonly');
    const store = tx.objectStore('runs');
    const request = action === 'put' ? store.put(value) : action === 'get' ? store.get(value) : store.getAll();
    tx.oncomplete = () => resolve(request.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}
async function api(path, options) {
  const response = await fetch(path, options);
  let value;
  try { value = await response.json(); } catch { throw Error('Server returned an unreadable response. Please retry.'); }
  if (!response.ok) throw Error(value.error || `Request failed (${response.status}).`);
  return value;
}
function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
  $('status').classList.toggle('running', busy);
}
function stale() {
  if (current) $('stale').hidden = current.report.dataset === $('dataset').value && current.report.algorithm === $('algorithm').value;
}
function update() {
  const entry = catalog.datasets.find(d => d.name === $('dataset').value);
  const subset = entry.split === 'dev_small' ? 'Small development subset' : entry.split === 'dev' ? 'Full development split' : 'Previously viewed partial test subset';
  $('datasetDescription').textContent = `${entry.annotation.toUpperCase()} · ${subset}. ${entry.split === 'test_common' ? 'Not an untouched held-out evaluation.' : 'Development data has been explored.'}`;
  $('datasetStats').innerHTML = [[entry.mentions,'MENTIONS'],[entry.documents,'DOCUMENTS'],[entry.topics,'TOPICS']].map(([value,label]) => `<div><b>${esc(value ?? '—')}</b><span>${label}</span></div>`).join('');
  $('testAckWrap').hidden = !entry.previously_viewed;
  $('methodDescription').textContent = $('algorithm').value === 'compare' ? 'Run all four methods on identical inputs. OR is the reference for every comparison. The NB guard is disclosed as a train-selected no-op.' : catalog.methods[$('algorithm').value].description;
  stale();
}
function download(id, blob, filename) {
  const url = URL.createObjectURL(blob);
  downloadURLs.push(url);
  $(id).href = url;
  $(id).download = filename;
}
function csv(report) {
  const rows = [['method','MUC_F1','B3_F1','CEAF_e_F1','CoNLL_F1','Pair_P','Pair_R','Pair_F1','FP','FN','clusters']];
  for (const [method, m] of Object.entries(report.metrics)) rows.push([method,...[m.muc.f1,m.b3.f1,m.ceafe.f1,m.conll_f1,m.pair_precision,m.pair_recall,m.pair_f1].map(v => 100*v),m.fp,m.fn,m.clusters]);
  return rows.map(row => row.join(',')).join('\r\n') + '\r\n';
}
function render(item) {
  current = item;
  const r = item.report;
  $('empty').hidden = true;
  $('output').hidden = false;
  $('runBadge').textContent = 'COMPUTED / ' + r.dataset.toUpperCase();
  $('resultCaption').textContent = `${r.dataset} · ${r.phase} · ${new Date(r.created).toLocaleString()} · ${r.id}`;
  $('resultStats').innerHTML = [[r.coverage.mentions,'mentions evaluated'],[r.coverage.candidate_pairs.toLocaleString(),'cross-document candidates'],[r.duration_seconds.toFixed(2)+'s','compute + scoring']].map(([v,l]) => `<div><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join('');
  $('chart').innerHTML = Object.entries(r.metrics).map(([method,m]) => `<div class="chart-row"><span class="chart-label">${labels[method]}${method === 'OR_TFIDF_NB' && r.selection.nb_no_op ? '<small>CV selected unchanged OR</small>' : ''}</span><div class="track"><div class="bar ${method==='OR_TFIDF'?'accent':''}" style="width:${Math.max(0,Math.min(100,m.conll_f1*100))}%"></div></div><b>${percent(m.conll_f1)}</b></div>`).join('');
  const baseline = r.metrics.OR;
  const deltas = Object.entries(r.metrics).filter(([m]) => m !== 'OR').map(([method,m]) => {
    const conll = (m.conll_f1-baseline.conll_f1)*100, pair = (m.pair_f1-baseline.pair_f1)*100;
    return `${labels[method]}: Δ CoNLL ${conll>=0?'+':''}${conll.toFixed(4)}, Δ Pair F1 ${pair>=0?'+':''}${pair.toFixed(4)} points versus OR.`;
  });
  $('interpretation').textContent = deltas.length ? deltas.join(' ') + ' Read both metrics together; these results do not establish consistent superiority.' : 'Original OR reference, evaluated with topic-scoped gold. Choose a comparison to inspect metric and error tradeoffs.';
  $('noop').hidden = !r.metrics.OR_TFIDF_NB || !r.selection.nb_no_op;
  $('metrics').innerHTML = Object.entries(r.metrics).map(([method,m]) => `<tr class="${method==='OR_TFIDF'?'highlight':''}"><td>${labels[method]}</td>${[m.muc.f1,m.b3.f1,m.ceafe.f1,m.conll_f1,m.pair_precision,m.pair_recall,m.pair_f1].map(v=>`<td>${percent(v)}</td>`).join('')}<td>${m.fp}</td><td>${m.fn}</td><td>${m.clusters}</td></tr>`).join('');
  $('changes').innerHTML = Object.entries(r.pair_changes).map(([method, counts]) => `<div class="change-row"><strong>${labels[method]}</strong><span>${r.edge_changes.filter(e=>e.method===method && e.operation==='add').length} added / ${r.edge_changes.filter(e=>e.method===method && e.operation==='cut').length} cut links<br>${counts.recovered_fn} recovered FN · ${counts.new_fp} new FP<br>${counts.removed_fp} removed FP · ${counts.new_fn} new FN</span></div>`).join('') || '<p class="caption">Only the original OR reference was requested.</p>';
  $('examples').innerHTML = r.examples.slice(0,10).map(e => `<article class="example"><strong>${labels[e.method]} · ${e.predicted_same?'Merged different events (FP)':'Split the same event (FN)'}</strong><p><b>${esc(e.a)}</b><br>${esc(e.text_a)}</p><p><b>${esc(e.b)}</b><br>${esc(e.text_b)}</p></article>`).join('') || '<p class="caption">No errors in the exported sample.</p>';
  $('provenance').textContent = JSON.stringify({selection:r.selection,provenance:r.provenance,warnings:r.warnings,coverage:r.coverage,edge_counts:r.edge_counts},null,2);
  for (const url of downloadURLs.splice(0)) URL.revokeObjectURL(url);
  const bytes = Uint8Array.from(atob(item.archive_base64), c=>c.charCodeAt(0));
  download('exportZip',new Blob([bytes],{type:'application/zip'}),r.id+'.zip');
  download('exportCsv',new Blob([csv(r)],{type:'text/csv;charset=utf-8'}),r.id+'-metrics.csv');
  download('exportJson',new Blob([JSON.stringify(r,null,2)],{type:'application/json'}),r.id+'-report.json');
  stale();
}
async function history() {
  try {
    const items = (await storage('all')).sort((a,b)=>b.id.localeCompare(a.id)).slice(0,12);
    $('historyRows').innerHTML = items.map(item => `<button class="history-entry" data-id="${esc(item.id)}"><span>${esc(item.report.dataset)} · ${esc(item.report.algorithm==='compare'?'All four methods':labels[item.report.algorithm])}<small>${esc(new Date(item.report.created).toLocaleString())} · OR ${percent(item.report.metrics.OR.conll_f1)}</small></span><span>Open ↗</span></button>`).join('') || '<p class="caption">No saved runs yet. Every completed run is kept here, including decreases.</p>';
    $('historyRows').querySelectorAll('[data-id]').forEach(button => button.onclick = async () => {
      if (busy) return;
      try { const entry = await storage('get',button.dataset.id); if (!entry) throw Error('Saved run is unavailable.'); render(entry); status('Opened saved evidence.'); $('results').scrollIntoView({behavior:'smooth'}); }
      catch(error) { status(error.message,true); }
    });
  } catch { $('historyRows').textContent = 'Browser storage is unavailable. Download evidence before closing this page.'; }
}
$('dataset').onchange = () => { $('testAck').checked=false; update(); };
$('algorithm').onchange = update;
$('refresh').onclick = history;
$('run').onclick = async () => {
  if (busy) return;
  const body = {dataset:$('dataset').value,algorithm:$('algorithm').value,acknowledge_test:$('testAck').checked};
  if (body.dataset.includes('test_common') && !body.acknowledge_test) { status('Acknowledge the previously viewed test subset before running.',true); $('testAck').focus(); return; }
  busy=true;
  showOrbit(true);
  orbitMotion.start();
  $('run').disabled=true; $('dataset').disabled=true; $('algorithm').disabled=true; $('results').setAttribute('aria-busy','true');
  $('run').firstElementChild.textContent='Running…';
  status('Verifying the dataset, computing links and scoring clusters…');
  try {
    const value = await api('/api/workbench/run',{method:'POST',headers:{'Content-Type':'application/json','X-Access-Key':$('accessKey').value},body:JSON.stringify(body)});
    const item = {id:value.report.id,report:value.report,archive_base64:value.archive_base64};
    status('Computation complete. Preparing the evidence view…');
    await orbitMotion.complete();
    render(item);
    let saved = true;
    try { await storage('put',item); } catch { saved=false; }
    await history();
    status(saved ? 'Complete. Evidence saved in this browser; download ZIP for your presentation or paper.' : 'Complete. Storage unavailable—download evidence before closing the page.', !saved);
    $('results').scrollIntoView({behavior:'smooth'});
  } catch(error) { status(error.message+' Your previous evidence is still available.',true); }
  finally { orbitMotion.reset(); showOrbit(false); busy=false; $('run').disabled=false; $('dataset').disabled=false; $('algorithm').disabled=false; $('results').setAttribute('aria-busy','false'); $('run').firstElementChild.textContent='Run experiment'; $('status').classList.remove('running'); }
};
(async () => {
  try {
    [catalog] = await Promise.all([api('/api/workbench/catalog'),api('/api/runtime').then(runtime => {
      $('keyLabel').hidden = !runtime.key_required;
      $('accessKey').hidden = !runtime.key_required;
    })]);
    $('dataset').innerHTML = catalog.datasets.map(d => `<option value="${esc(d.name)}">${d.annotation.toUpperCase()} / ${d.split==='dev'?'Full dev':d.split==='dev_small'?'Small dev':'test_common · previously viewed'} · ${d.mentions} mentions</option>`).join('');
    $('dataset').disabled=false; $('run').disabled=false;
    update(); status('Ready. Select a method and run the experiment.');
    await history();
  } catch(error) { status('Unable to load the workbench: '+error.message+' Reload to retry.',true); }
})();
