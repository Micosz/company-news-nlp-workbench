import {loadIndex, summarize, pairF1, buildPool, pairAt} from '/evidence-core.mjs';

const $ = id => document.getElementById(id);
const n = (tag, text, cls) => {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  return e;
};
const number = x => x.toLocaleString('en-US');
const f1 = x => x.toFixed(2) + '%';
const metricNames = {tp: 'TP รวมถูก', fp: 'FP รวมผิด', fn: 'FN แยกผิด'};
const params = new URLSearchParams(location.search);
let index, published;

function traceLink(text, ann, topic, model, kind, tally, rank) {
  if (!tally) return n('span', text);
  const query = new URLSearchParams({mode: 'trace', ann, topic, model, kind});
  if (rank != null) query.set('rank', rank);
  const a = n('a', text); a.href = '/audit-review?' + query;
  return a;
}
function scoreCard(title, counts, ann, topic, model) {
  const box = n('div', '', 'score-card'), links = n('div', '', 'metric-links');
  for (const [key, name] of Object.entries(metricNames)) {
    links.append(traceLink(name + ' ' + number(counts[key]), ann, topic, model, key, counts[key]));
  }
  const score = pairF1(counts);
  const denominator = 2 * counts.tp + counts.fp + counts.fn;
  const formula = denominator ? '2 × ' + number(counts.tp) + ' / (' + number(denominator) + ') = ' + f1(score)
    : 'ไม่มีคู่ที่เฉลยหรือระบบจัดกลุ่มร่วมกัน เกณฑ์ของโครงการให้ 100%';
  const headline = n('div', '', 'model-score');
  headline.append(n('h4', title), n('span', 'Pair F1'), n('strong', f1(score)));
  const gauge = n('div', '', 'f1-gauge'), level = n('span');
  gauge.setAttribute('aria-hidden', 'true');
  level.className = model;
  level.style.width = score + '%';
  gauge.append(level);
  box.append(headline, gauge, links, n('p', formula, 'f1-formula'));
  return box;
}

function manualExercise(ann, topic) {
  const section = $('count-check');
  const examples = [];
  for (const category of ['fp', 'tp', 'fn', 'tn']) {
    const pool = buildPool(index[ann], {topic, kind: category, crossOnly: false});
    const ranks = category === 'tp' || category === 'fp' ? [1, 2] : [1];
    for (const rank of ranks) {
      const pair = pairAt(pool, rank);
      if (pair) examples.push({pair, rank, category});
    }
  }
  examples.sort((a, b) => a.pair.a.index - b.pair.a.index || a.pair.b.index - b.pair.b.index);
  const table = n('table'), cap = n('caption', 'ตัวอย่างสำหรับฝึกนับ ' + examples.length + ' คู่ · คัดให้เห็นผลหลายแบบ');
  const head = table.createTHead().insertRow(); table.prepend(cap);
  for (const label of ['คู่', 'OR + TF-IDF', 'เฉลย ECB+']) { const th = n('th', label); th.scope = 'col'; head.append(th); }
  const body = table.createTBody();
  for (const [i, row] of examples.entries()) {
    const tr = body.insertRow(), cell = tr.insertCell();
    cell.append(traceLink('อ่านคู่ ' + (i + 1), ann, topic, 'hybrid', row.category, 1, row.rank));
    for (const state of [row.pair.hybrid, row.pair.gold]) tr.insertCell().textContent = state ? 'รวม' : 'แยก';
  }
  const fields = n('form', '', 'evidence-controls');
  for (const key of ['tp', 'fp', 'fn']) {
    const field = n('label', key.toUpperCase()), input = n('input');
    input.type = 'number'; input.name = key; input.required = true; input.min = '0'; input.max = String(examples.length);
    field.append(input); fields.append(field);
  }
  const submit = n('button', 'ตรวจที่นับ'); submit.type = 'submit'; fields.append(submit);
  const output = n('p', '', 'counts-note'); output.setAttribute('role', 'status');
  fields.addEventListener('submit', e => {
    e.preventDefault();
    const input = new FormData(fields);
    const counts = Object.fromEntries(['tp', 'fp', 'fn'].map(k => [k, examples.filter(x => x.category === k).length]));
    const correct = Object.entries(counts).every(([k, v]) => Number(input.get(k)) === v);
    output.textContent = (correct ? 'ตรงกัน' : 'ลองเทียบแต่ละแถวอีกครั้ง') + ' · จาก ' + examples.length
      + ' คู่ ตัวนับได้ TP ' + counts.tp + ', FP ' + counts.fp + ', FN ' + counts.fn + ' · Pair F1 ' + f1(pairF1(counts));
  });
  section.replaceChildren(table, fields, output);
}
function render() {
  const ann = $('inspect-ann').value, topic = $('inspect-topic').value;
  const data = summarize(index[ann], topic), group = index[ann].groups.get(topic);
  const row = published.find(r => r.ann === ann && String(r.topic) === topic);
  const match = row?.count === group.length && ['or', 'hybrid'].every(m =>
    row[m + 'FP'] === data[m].fp && row[m + 'FN'] === data[m].fn && Math.abs(row[m + 'F1'] - pairF1(data[m])) < 0.00501);
  const status = $('count-source');
  if (!match) {
    $('inspect-content').hidden = true; status.textContent = 'ตัวนับกับตารางต้นทางไม่ตรงกัน จึงงดแสดงคะแนนหัวข้อนี้'; return;
  }
  $('inspect-content').hidden = false;
  status.textContent = group.length + ' ตำแหน่งในข่าว ' + new Set(group.map(r => r.doc)).size + ' ชิ้น · '
    + number(data.total) + ' คู่ในหัวข้อ · เป็นคู่ข้ามข่าว ' + number(data.cross) + ' คู่';
  $('score-comparison').replaceChildren(scoreCard('OR', data.or, ann, topic, 'or'), scoreCard('OR + TF-IDF', data.hybrid, ann, topic, 'hybrid'));
  const total = data.addedRight + data.addedWrong;
  $('change-caption').textContent = 'หลังเติม TF-IDF มีคู่ที่เพิ่งถูกจัดกลุ่มร่วมกัน ' + number(total) + ' คู่';
  const bar = $('new-pair-bar');
  bar.replaceChildren();
  const legend = $('bar-legend');
  legend.replaceChildren();
  for (const [kind, text, cls] of [['addedRight', 'ตรงกับเฉลย', 'key-good'], ['addedWrong', 'ต่างจากเฉลย', 'key-bad']]) {
    const amount = data[kind], caption = text + ' ' + number(amount) + ' คู่';
    const item = n('span');
    item.append(n('i', '', 'color-key ' + cls), traceLink(caption, ann, topic, 'hybrid', kind, amount));
    legend.append(item);
    if (amount) {
      const segment = traceLink('', ann, topic, 'hybrid', kind, amount);
      segment.className = cls; segment.title = caption; segment.setAttribute('aria-label', caption);
      segment.style.width = (100 * amount / total) + '%';
      bar.append(segment);
    }
  }
  const example = $('topic-example');
  example.replaceChildren();
  if (topic === '35') {
    const pool = buildPool(index[ann], {topic, kind: 'addedWrong', crossOnly: false});
    const a = pool.index.byId.get('35_10ecb.xml_35'), b = pool.index.byId.get('35_4ecbplus.xml_8');
    const code = a.index * pool.index.mentions.length + b.index;
    const rank = pool.codes.indexOf(code) + 1;
    if (rank) example.append(traceLink('อ่านตัวอย่างข่าวการจับกุม Jackson และ Jamal Williams →',
      ann, topic, 'hybrid', 'addedWrong', pool.codes.length, rank));
  }
  $('blind-topic').href = '/audit-review?' + new URLSearchParams({ann, topic});
  $('manual-check').open = false;
  manualExercise(ann, topic);
}

async function init() {
  const [idx, data] = await Promise.all([loadIndex(), fetch('/audit-data.json').then(r => {
    if (!r.ok) throw new Error(); return r.json();
  })]);
  index = idx; published = data.topics;
  const ann = params.get('ann') === 'ann2' ? 'ann2' : 'ann1';
  $('inspect-ann').value = ann;
  for (const topic of index[ann].topics) $('inspect-topic').add(new Option('Topic ' + topic, topic));
  $('inspect-topic').value = index[ann].groups.has(params.get('topic')) ? params.get('topic') : '35';
  render();
  for (const id of ['inspect-ann', 'inspect-topic']) $(id).addEventListener('change', () => {
    const url = new URL(location.href); url.searchParams.set('ann', $('inspect-ann').value);
    url.searchParams.set('topic', $('inspect-topic').value); url.hash = 'pair-inspector';
    history.replaceState(null, '', url); render();
  });
}
init().catch(() => { $('inspect-content').hidden = true; $('count-source').textContent = 'เปิดข้อมูลคะแนนไม่ได้ กรุณาโหลดหน้าอีกครั้ง'; });
