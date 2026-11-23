import {loadIndex, buildPool, drawPair, pairAt, sampleKinds, traceKinds, membershipSHA256} from '/evidence-core.mjs';
import {checkedRows, fetchRows, source, hashes, upstream} from '/audit-source.mjs';

const $ = id => document.getElementById(id);
const node = (tag, text, cls) => {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  return e;
};
const count = n => n.toLocaleString('en-US');
const label = {same: 'เหตุการณ์เดียวกัน', different: 'คนละเหตุการณ์', unclear: 'หลักฐานไม่พอ'};
const frames = {all: 'ทุกคู่ข้ามข่าว', merged: 'คู่ที่ระบบรวม', separate: 'คู่ที่ระบบแยก', added: 'คู่ที่เพิ่งรวม'};
const traces = {tp: 'TP · รวมถูก', fp: 'FP · รวมผิด', fn: 'FN · แยกผิด', tn: 'TN · แยกถูก',
  addedRight: 'คู่เพิ่งรวมที่ตรงกับเฉลย', addedWrong: 'คู่เพิ่งรวมที่ต่างจากเฉลย'};
const storeKey = 'xamr-evidence-review-v1';
let index, pool, current, ready = false, requestId = 0;
const sourceCache = new Map(), sessionSeen = new Set();
let book = {reviews: {}, exposed: {}};
let storageFailed = false;

function syncBook() {
  try {
    const old = JSON.parse(localStorage.getItem(storeKey) || '{}');
    book = {reviews: {...old.reviews, ...book.reviews}, exposed: {...old.exposed, ...book.exposed}};
  } catch { storageFailed = true; }
}
function persist() {
  try { localStorage.setItem(storeKey, JSON.stringify(book)); storageFailed = false; }
  catch { storageFailed = true; }
}
syncBook();
const initial = new URLSearchParams(location.search);
const trace = initial.get('mode') === 'trace';
const targetKind = initial.get('kind') || 'fp';
const model = initial.get('model') === 'or' ? 'or' : 'hybrid';
const modelName = model === 'or' ? 'OR' : 'OR + TF-IDF';
const annotation = () => $('sample-ann').value;
const topicValue = () => $('sample-topic').value;
const kindValue = () => trace ? targetKind : $('sample-kind').value;
const keyOf = p => [p.a.id, p.b.id].join('|');
const reviewId = () => annotation() + ':' + keyOf(current.pair);
const sameText = v => v ? label.same : label.different;
const fmtAnn = a => a === 'ann1' ? 'Ann1' : 'Ann2';

function updateLocation() {
  const params = new URLSearchParams({ann: annotation()});
  if (topicValue()) params.set('topic', topicValue());
  if (trace) { params.set('mode', 'trace'); params.set('model', model); }
  if (kindValue() !== 'all') params.set('kind', kindValue());
  if (current) {
    params.set('rank', String(current.rank));
    params.set('v', membershipSHA256.slice(0, 12));
  }
  const address = location.pathname + '?' + params;
  history.replaceState(null, '', address);
  $('permalink').href = address;
}

function tally() {
  const reviews = Object.values(book.reviews);
  $('export').disabled = !reviews.length;
  $('log-summary').textContent = reviews.length
    ? 'บันทึกแล้ว ' + count(reviews.length) + ' รายการ · แยกตามชุดคำกำกับและวิธีเลือกคู่'
    : 'ยังไม่มีคำตัดสินในเครื่องนี้ เมื่อบันทึกคู่แรก จะเห็นว่าความเห็นของคนอ่านตรงกับระบบกี่คู่';
  const batches = new Map();
  for (const r of reviews) {
    const name = fmtAnn(r.ann) + ' · ' + frames[r.frame] + (r.selectedTopic ? ' · Topic ' + r.selectedTopic : ' · ทุกหัวข้อ')
      + (r.selection === 'link' ? ' · เปิดจากลิงก์' : ' · สุ่ม');
    if (!batches.has(name)) batches.set(name, {agree: 0, decided: 0, unclear: 0});
    const batch = batches.get(name);
    if (r.decision === 'unclear') batch.unclear++;
    else { batch.decided++; if ((r.decision === 'same') === r.results.hybrid) batch.agree++; }
  }
  const listing = node('ul');
  for (const [name, b] of batches) listing.append(node('li', name + ' — ตรงกับ OR + TF-IDF '
    + b.agree + '/' + b.decided + ' คู่ที่ตัดสินได้ · หลักฐานไม่พอ ' + b.unclear + ' คู่'));
  $('review-tally').replaceChildren(...(batches.size ? [listing] : []));
}

function configure() {
  current = null;
  requestId++;
  $('pair-panel').hidden = true;
  const ann = annotation(), topic = topicValue(), kind = kindValue();
  pool = buildPool(index[ann], {topic, kind, model: trace ? model : 'hybrid', crossOnly: !trace});
  $('frame-size').textContent = fmtAnn(ann) + ' · ' + (topic ? 'Topic ' + topic : 'ทุกหัวข้อ')
    + ' · ' + count(pool.codes.length) + ' คู่ในกลุ่มที่เลือก';
  $('draw').disabled = !pool.codes.length;
  $('draw').textContent = trace ? 'สุ่มดูหนึ่งคู่จากตัวเลขนี้' : 'สุ่มคู่ข่าว';
  $('frame-note').textContent = trace
    ? modelName + ' · ' + traces[kind] + ' · นับทุกคู่ภายในหัวข้อ รวมคู่จากข่าวชิ้นเดียวกัน'
    : (kind === 'all' ? 'ผลของ OR, OR + TF-IDF และเฉลย ECB+ จะเปิดหลังบันทึกคำตัดสิน'
      : 'คุณทราบเงื่อนไขการเลือกคู่ ส่วนเฉลย ECB+ จะเปิดหลังบันทึกคำตัดสิน');
  if (trace) $('back-to-counts').href = '/audit-analysis?ann=' + ann + '&topic=' + topic + '#pair-inspector';
}

function randomPair() {
  syncBook();
  const seen = new Set(sessionSeen);
  if (!trace) {
    Object.keys(book.exposed).forEach(k => seen.add(k));
    Object.values(book.reviews).forEach(r => seen.add(r.ids.join('|')));
  }
  const draw = drawPair(pool, seen);
  if (!draw) {
    $('draw').disabled = true;
    $('frame-size').textContent = 'เปิดครบทุกคู่ที่เลือกได้ในกลุ่มนี้แล้ว';
    return;
  }
  openPair(draw.rank, 'random', draw.remaining);
}

function markText(text) {
  const frag = document.createDocumentFragment();
  let marked = false;
  for (const part of String(text || '').split(/(<\/?mark\b[^>]*>)/gi)) {
    if (/^<mark\b/i.test(part)) marked = true;
    else if (/^<\/mark/i.test(part)) marked = false;
    else if (part) frag.append(marked ? node('mark', part) : document.createTextNode(part));
  }
  return frag;
}
function evidenceCard(row, side) {
  const card = node('article');
  card.append(node('h3', 'ข้อความ ' + side), node('div', row.mention_id, 'evidence-id'));
  const lines = String(row.marked_doc || '').split(/<p\s*\/?\s*>/i).map(s => s.trim()).filter(s => s && !/^https?\s*:/i.test(s));
  const focus = lines.findIndex(s => /<mark\b/i.test(s));
  const sentence = node('p', '', 'target-sentence');
  sentence.lang = 'en';
  sentence.append(markText(row.marked_sentence || row.text));
  card.append(sentence);
  if (lines.length) {
    const details = node('details'), body = node('div', '', 'doc-body');
    body.lang = 'en';
    if (focus >= 0) {
      const context = [lines[focus - 1], lines[focus + 1]].filter(Boolean);
      if (context.length) {
        card.append(node('small', 'บริบทรอบประโยค'));
        for (const line of context) { const p = node('p', '', 'context-line'); p.lang = 'en'; p.append(markText(line)); card.append(p); }
      }
    }
    for (const line of lines) { const p = node('p'); p.append(markText(line)); body.append(p); }
    details.append(node('summary', 'อ่านเนื้อข่าวทั้งหมดที่มีใน ECB+'), body);
    card.append(details);
  } else card.append(node('p', 'ต้นฉบับชุดนี้มีเฉพาะประโยคเป้าหมาย'));
  return card;
}

function reveal(review) {
  const p = current.pair, list = node('dl', '', 'review-results');
  const answers = [['OR', sameText(p.or)], ['OR + TF-IDF', sameText(p.hybrid)], ['เฉลย ECB+', sameText(p.gold)]];
  if (review) answers.unshift(['คำตัดสินที่บันทึก', label[review.decision]]);
  for (const [name, answer] of answers) {
    const cell = node('div'); cell.append(node('dt', name), node('dd', answer)); list.append(cell);
  }
  const panel = $('verdict');
  panel.replaceChildren(node('h3', 'ผลของคู่นี้'), list);
  if (review) panel.append(node('p', 'เหตุผลที่บันทึกไว้ · ' + review.reason));
  if (keyOf(p) === '35_10ecb.xml_35|35_4ecbplus.xml_8') {
    panel.append(node('p', 'ทั้งสองฝั่งไฮไลต์คำว่า arrested ฝั่ง A กล่าวถึง Jackson ส่วนการจับกุมที่ไฮไลต์ในฝั่ง B เป็นของ Jamal Williams เมื่อเปิดเนื้อข่าว B จะพบว่าข่าวยังเล่าย้อนถึง Vincent Jackson ด้วย ต้องดูว่าคำที่ไฮไลต์อ้างถึงใคร'));
  }
  panel.hidden = false;
  $('judgement').hidden = true;
}
function originalRows(ann) {
  if (!sourceCache.has(ann)) {
    const fetchTask = fetchRows(ann).then(rows => new Map(rows.map(r => [r.mention_id, r]))).catch(error => {
      sourceCache.delete(ann); throw error;
    });
    sourceCache.set(ann, fetchTask);
  }
  return sourceCache.get(ann);
}
async function showEvidence() {
  const token = ++requestId, ann = annotation(), p = current.pair;
  $('source-repair').hidden = true;
  $('article-state').textContent = 'กำลังเปิดข้อความต้นทางที่ตรวจรุ่นข้อมูลแล้ว…';
  ready = false;
  try {
    const rows = await originalRows(ann);
    if (token !== requestId) return;
    const a = rows.get(p.a.id), b = rows.get(p.b.id);
    if (!a?.marked_sentence || !b?.marked_sentence) throw new Error('ไม่พบข้อความเป้าหมาย');
    $('evidence').replaceChildren(evidenceCard(a, 'A'), evidenceCard(b, 'B'));
    $('article-state').textContent = p.a.doc === p.b.doc
      ? 'คู่นี้เป็นสองตำแหน่งในข่าวชิ้นเดียวกัน' : 'สองตำแหน่งจากคนละเอกสาร · ไฮไลต์คือคำที่ใช้ประเมิน';
    ready = true;
    const saved = book.reviews[reviewId()];
    if (trace || saved) {
      reveal(saved);
    } else if (book.exposed[keyOf(p)] || Object.values(book.reviews).some(r => r.ids.join('|') === keyOf(p))) {
      $('decision-state').textContent = 'เครื่องนี้เคยเปิดผลของคู่นี้แล้ว จึงดูย้อนหลังได้อย่างเดียว';
      reveal(null);
    } else $('judgement').hidden = false;
  } catch {
    if (token !== requestId) return;
    $('article-state').textContent = 'ยังอ่านหลักฐานคู่นี้ไม่ได้ กรุณาลองอีกครั้งหรือใช้ไฟล์ต้นทาง';
    $('raw-link').href = source(ann);
    $('source-repair').hidden = false;
  }
}

function openPair(rank, selection, remaining = null) {
  const pair = pairAt(pool, rank);
  if (!pair) { $('frame-size').textContent = 'ลำดับคู่ในลิงก์อยู่นอกกลุ่มนี้ กรุณาสุ่มใหม่'; return; }
  current = {rank, pair, selection, remaining};
  sessionSeen.add(keyOf(pair));
  if (trace) { syncBook(); book.exposed[keyOf(pair)] = true; persist(); }
  updateLocation();
  $('pair-panel').hidden = false;
  $('pair-location').textContent = fmtAnn(annotation()) + ' / TOPIC ' + pair.a.topic + ' / คู่ลำดับ '
    + count(rank) + ' จาก ' + count(pool.codes.length);
  $('draw').textContent = 'สุ่มคู่อื่น';
  $('decision-state').textContent = trace ? 'เลือกจากผลการทดลองที่ทราบคำตอบแล้ว ใช้ตรวจที่มาของตัวเลข' : '';
  $('evidence').replaceChildren(); $('judgement').reset(); $('judgement').hidden = true;
  $('verdict').hidden = true; $('verdict').replaceChildren(); $('manual-json').value = '';
  $('pair-title').focus({preventScroll: true});
  showEvidence();
}

$('judgement').addEventListener('submit', event => {
  event.preventDefault();
  if (!ready || !current || trace) return;
  const data = new FormData(event.currentTarget), decision = data.get('decision'), reason = $('reason').value.trim();
  if (!Object.hasOwn(label, decision) || !reason) { $('decision-state').textContent = 'กรุณาเลือกคำตัดสินและระบุเหตุผลจากข่าว'; return; }
  syncBook();
  const p = current.pair, id = reviewId();
  if (!book.reviews[id] && !book.exposed[keyOf(p)] && !Object.values(book.reviews).some(r => r.ids.join('|') === keyOf(p))) {
    book.reviews[id] = {ann: annotation(), topic: p.a.topic, selectedTopic: topicValue(), frame: kindValue(),
      selection: current.selection, crossDocumentOnly: true, poolSize: pool.codes.length, rank: current.rank,
      remainingBeforeDraw: current.remaining, ids: [p.a.id, p.b.id], documents: [p.a.doc, p.b.doc],
      decision, reason, results: {or: p.or, hybrid: p.hybrid, gold: p.gold}, sourceSHA256: hashes[annotation()], membershipSHA256,
      url: location.href, savedAt: new Date().toISOString()};
    persist();
  }
  reveal(book.reviews[id]);
  $('decision-state').textContent = storageFailed ? 'เก็บได้เฉพาะในหน้านี้ กรุณาดาวน์โหลดบันทึกก่อนปิด'
    : book.reviews[id] ? 'บันทึกคำตัดสินก่อนเปิดผลแล้ว' : 'คู่นี้เคยเปิดผลในเครื่องแล้ว';
  tally();
});
$('export').addEventListener('click', () => {
  syncBook();
  const payload = {version: 1, dataset: 'ECB+ explored dev', upstream, membershipSHA256,
    unit: 'Two mentions from different documents in the same topic. Rank is one-based in the selected frame.',
    reviews: Object.values(book.reviews)};
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}));
  const link = node('a'); link.href = url; link.download = 'xamr-pair-reviews.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$('draw').addEventListener('click', randomPair);
$('retry').addEventListener('click', showEvidence);
$('manual-json').addEventListener('change', async event => {
  const file = event.target.files[0], ann = annotation(), token = requestId;
  if (!file) return;
  try {
    if (file.size > 14e6) throw new Error();
    const rows = await checkedRows(await file.arrayBuffer(), ann);
    sourceCache.set(ann, Promise.resolve(new Map(rows.map(r => [r.mention_id, r]))));
    if (token === requestId) await showEvidence();
  } catch { if (token === requestId) $('article-state').textContent = 'ไฟล์ไม่ตรงกับชุดที่เลือก กรุณาใช้ลิงก์ไฟล์ต้นทาง'; }
  event.target.value = '';
});
for (const id of ['sample-ann', 'sample-topic', 'sample-kind']) {
  $(id).addEventListener('change', () => { if (index) { configure(); updateLocation(); } });
}

async function start() {
  tally();
  index = await loadIndex();
  if (initial.has('v') && initial.get('v') !== membershipSHA256.slice(0, 12)) {
    throw new Error('ลิงก์นี้อ้างดัชนีคนละรุ่นกับที่กำลังใช้งาน');
  }
  const ann = initial.get('ann') || 'ann1';
  if (!Object.hasOwn(index, ann)) throw new Error('ไม่พบชุดคำกำกับในลิงก์');
  $('sample-ann').value = ann;
  for (const topic of index[ann].topics) $('sample-topic').add(new Option('Topic ' + topic, topic));
  const topic = initial.get('topic') || '';
  if (topic && !index[ann].groups.has(topic)) throw new Error('ไม่พบหัวข้อในลิงก์');
  $('sample-topic').value = topic;
  if (trace) {
    if (!topic || !traceKinds.includes(targetKind)) throw new Error('ลิงก์ย้อนจากคะแนนไม่ครบ');
    $('page-title').textContent = 'ตรวจคู่ที่ถูกนับ';
    $('intro').textContent = 'เปิดอ่านข้อความตรงตำแหน่งที่ถูกนับในผลการทดลองของหัวข้อนี้';
    $('sample-filters').hidden = true; $('sampling-details').hidden = true; $('trace-controls').hidden = false;
  } else {
    const kind = initial.get('kind') || 'all';
    if (!sampleKinds.includes(kind)) throw new Error('ไม่พบกลุ่มตัวอย่างในลิงก์');
    $('sample-kind').value = kind;
  }
  configure();
  if (initial.has('rank')) openPair(Number(initial.get('rank')), 'link');
  else if (trace && pool.codes.length) randomPair();
}
start().catch(e => { $('frame-size').textContent = e.message + ' · เปิดหน้าสุ่มตรวจใหม่เพื่อเริ่มอีกครั้ง'; $('draw').disabled = true; });
