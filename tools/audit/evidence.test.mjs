import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildPool, category, drawPair, indexAnnotation, pairAt, pairF1, randomBelow, summarize} from '../../xamr_lab/static/evidence-core.mjs';

const load = file => JSON.parse(readFileSync(new URL('../../xamr_lab/static/' + file, import.meta.url)));
const frozen = load('audit-data.json'), memberships = load('cluster-memberships.json');
const indices = Object.fromEntries(Object.entries(memberships.annotations).map(([ann, rows]) => [ann, indexAnnotation(rows)]));

test('all 16 frozen topic comparisons reproduce independently from mention memberships', () => {
  assert.equal(frozen.topics.length, 16);
  for (const r of frozen.topics) {
    const index = indices[r.ann], actual = summarize(index, r.topic);
    assert.equal(actual.total, r.count * (r.count - 1) / 2);
    for (const model of ['or', 'hybrid']) {
      const c = actual[model];
      assert.equal(c.tp + c.fp + c.fn + c.tn, actual.total);
      assert.equal(c.fp, r[model + 'FP']); assert.equal(c.fn, r[model + 'FN']);
      assert.equal(Number(pairF1(c).toFixed(2)), r[model + 'F1']);
      for (const kind of ['tp', 'fp', 'fn', 'tn']) {
        const pool = buildPool(index, {topic: r.topic, model, kind, crossOnly: false});
        assert.equal(pool.codes.length, c[kind]);
        if (pool.codes.length) {
          const last = pairAt(pool, pool.codes.length);
          assert.equal(category(last[model], last.gold), kind);
        }
      }
    }
  }
});

test('reported pairs and eligible cross-news pairs use the intended denominators', () => {
  const all = summarize(indices.ann1, ''), subset = summarize(indices.ann1, '', true);
  assert.equal(all.total, 100784); assert.equal(subset.total, 96099);
  assert.equal(buildPool(indices.ann1, {}).codes.length, subset.total);
  for (const [ann, allAdded, crossAdded] of [['ann1', [0, 612], [0, 609]], ['ann2', [73, 719], [67, 718]]]) {
    for (const [crossOnly, expected] of [[false, allAdded], [true, crossAdded]]) {
      const sizes = ['addedRight', 'addedWrong'].map(kind => buildPool(indices[ann], {topic:'35', kind, crossOnly}).codes.length);
      assert.deepEqual(sizes, expected);
    }
  }
});

test('the original selected samples map to the same predictions and gold as their full-population pairs', () => {
  for (const p of frozen.pairs) {
    const rows = p.mentions.map(m => indices[p.ann].byId.get(m.id));
    assert.ok(rows.every((r, i) => r.doc === p.mentions[i].doc && r.topic === p.topic));
    assert.notEqual(rows[0].doc, rows[1].doc);
    for (const key of ['or', 'hybrid', 'gold']) assert.equal(rows[0][key] === rows[1][key], p[key + 'Same']);
  }
});

test('stable rank for shared samples, distinct mentions, no repeats, empty frames and rejection sampling', () => {
  const index = indexAnnotation([['1_2.xml_1','b','2','3'],['1_1.xml_1','a','1','3'],['1_1.xml_2','a','1','3']]);
  const pool = buildPool(index, {});
  const seen = new Set();
  for (const [remaining, rank] of [[2,2],[1,1]]) {
    assert.deepEqual(drawPair(pool, seen, size => size - 1), {rank, remaining});
    const {a,b} = pairAt(pool, rank); assert.notEqual(a.doc, b.doc);
    seen.add([a.id, b.id].join('|'));
  }
  assert.equal(drawPair(pool, seen), null);
  assert.equal(pairAt(pool, 0), null); assert.equal(pairAt(pool, 3), null);
  const words = [2 ** 32 - 1, 5];
  assert.equal(randomBelow(3, arr => { arr[0] = words.shift(); }), 2);
  assert.equal(pairF1({tp:0,fp:0,fn:0}),100);
});
