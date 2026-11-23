/* Pair units are two distinct event mentions in one ECB+ topic. */
export function indexAnnotation(rows) {
  const groups = new Map();
  const byId = new Map();
  for (const [id, gold, or, hybrid] of rows) {
    const match = /^(\d+)_(.+\.xml)_\d+$/.exec(id);
    if (!match || byId.has(id) || [gold, or, hybrid].some(x => x == null || x === '')) {
      throw new Error('ข้อมูลกลุ่มเหตุการณ์ไม่ครบ');
    }
    const topic = match[1];
    const mention = {id, topic, doc: topic + '_' + match[2], gold, or, hybrid};
    if (!groups.has(topic)) groups.set(topic, []);
    groups.get(topic).push(mention);
    byId.set(id, mention);
  }
  const topics = [...groups.keys()].sort((a, b) => Number(a) - Number(b));
  const mentions = [];
  for (const topic of topics) {
    const group = groups.get(topic);
    group.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    for (const row of group) {
      row.index = mentions.length;
      mentions.push(row);
    }
  }
  return {groups, topics, mentions, byId};
}

let request;
export let membershipSHA256;
export function loadIndex() {
  if (!request) request = fetch('/cluster-memberships.json').then(async response => {
    if (!response.ok) throw new Error('เปิดดัชนีคู่ข่าวไม่ได้');
    const bytes = await response.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    membershipSHA256 = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
    const data = JSON.parse(new TextDecoder().decode(bytes));
    if (data.schemaVersion !== 1 || data.columns.join('|') !== 'mentionId|goldCluster|orCluster|hybridCluster') {
      throw new Error('ดัชนีคนละรุ่นกับหน้าเว็บ');
    }
    return {ann1: indexAnnotation(data.annotations.ann1), ann2: indexAnnotation(data.annotations.ann2)};
  }).catch(error => { request = undefined; throw error; });
  return request;
}

function visitPairs(index, topic, crossOnly, visit) {
  const topics = topic ? [topic] : index.topics;
  for (const key of topics) {
    const group = index.groups.get(key);
    if (!group) throw new Error('ไม่พบหัวข้อนี้');
    for (let i = 0; i < group.length; i++) {
      const a = group[i];
      for (let j = i + 1; j < group.length; j++) {
        const b = group[j];
        if (!crossOnly || a.doc !== b.doc) visit(a, b);
      }
    }
  }
}

export function category(merged, gold) {
  return merged ? (gold ? 'tp' : 'fp') : (gold ? 'fn' : 'tn');
}

export function pairF1({tp, fp, fn}) {
  const denominator = 2 * tp + fp + fn;
  return denominator ? 200 * tp / denominator : 100;
}

export function summarize(index, topic, crossOnly = false) {
  const counts = () => ({tp: 0, fp: 0, fn: 0, tn: 0});
  const result = {or: counts(), hybrid: counts(), addedRight: 0, addedWrong: 0, total: 0, cross: 0};
  visitPairs(index, topic, crossOnly, (a, b) => {
    const gold = a.gold === b.gold, before = a.or === b.or, after = a.hybrid === b.hybrid;
    result.total++;
    if (a.doc !== b.doc) result.cross++;
    result.or[category(before, gold)]++;
    result.hybrid[category(after, gold)]++;
    if (after && !before) result[gold ? 'addedRight' : 'addedWrong']++;
  });
  return result;
}

export const sampleKinds = ['all', 'merged', 'separate', 'added'];
export const traceKinds = ['tp', 'fp', 'fn', 'tn', 'addedRight', 'addedWrong'];

export function buildPool(index, {topic = '', kind = 'all', model = 'hybrid', crossOnly = true}) {
  if (![...sampleKinds, ...traceKinds].includes(kind) || !['or', 'hybrid'].includes(model)) {
    throw new Error('ไม่รู้จักกลุ่มตัวอย่าง');
  }
  const codes = [], n = index.mentions.length;
  visitPairs(index, topic, crossOnly, (a, b) => {
    const merged = a[model] === b[model], gold = a.gold === b.gold;
    const added = a.hybrid === b.hybrid && a.or !== b.or;
    const keep = kind === 'all' || (kind === 'merged' && merged) || (kind === 'separate' && !merged)
      || (kind === 'added' && added) || (kind === 'addedRight' && added && gold)
      || (kind === 'addedWrong' && added && !gold) || kind === category(merged, gold);
    if (keep) codes.push(a.index * n + b.index);
  });
  return {index, codes};
}

export function pairAt(pool, rank) {
  if (!Number.isInteger(rank) || rank < 1 || rank > pool.codes.length) return null;
  const n = pool.index.mentions.length, code = pool.codes[rank - 1];
  const a = pool.index.mentions[Math.floor(code / n)], b = pool.index.mentions[code % n];
  return {a, b, gold: a.gold === b.gold, or: a.or === b.or, hybrid: a.hybrid === b.hybrid};
}

export function randomBelow(size, fill = words => crypto.getRandomValues(words)) {
  if (!Number.isInteger(size) || size < 1 || size > 2 ** 32) throw new RangeError('invalid pool size');
  const limit = 2 ** 32 - (2 ** 32 % size);
  const words = new Uint32Array(1);
  do { fill(words); } while (words[0] >= limit);
  return words[0] % size;
}

/* Sample uniformly without replacement. rank always refers to the original frame. */
export function drawPair(pool, seen, random = randomBelow) {
  const n = pool.index.mentions.length, excluded = new Set();
  for (const key of seen) {
    const [left, right] = key.split('|');
    const a = pool.index.byId.get(left), b = pool.index.byId.get(right);
    if (a && b) excluded.add(Math.min(a.index, b.index) * n + Math.max(a.index, b.index));
  }
  const available = [];
  pool.codes.forEach((code, i) => { if (!excluded.has(code)) available.push(i + 1); });
  if (!available.length) return null;
  return {rank: available[random(available.length)], remaining: available.length};
}
