const test = require('node:test');
const assert = require('node:assert/strict');
const {metricChart, confusionChart, metrics} = require('./static/charts.js');
const records = require('./docs/INITIAL_RESULTS.json').records;

test('saved pilot metrics keep exact bar widths and matching displayed percentages', () => {
  for (const record of records) {
    for (const metric of Object.keys(metrics)) {
      const svg = metricChart(record.metrics.models, metric, record.run_id);
      assert.ok(svg.includes(record.run_id));
      for (const [name, model] of Object.entries(record.metrics.models)) {
        const bar = svg.match(new RegExp(`<rect data-model="${name}"[^>]+width="([^"]+)"`));
        assert.equal(Number(bar[1]), model[metric] * 400);
        assert.ok(svg.includes((model[metric] * 100).toFixed(2) + '%'));
      }
      assert.ok(svg.includes('>0%</text>') && svg.includes('>100%</text>'));
      assert.ok(!svg.includes('data-model="text_plus_roles"'));
    }
  }
});

test('zero and perfect scores stay distinct from missing or invalid scores', () => {
  const svg = metricChart({zero: {f1: 0}, perfect: {f1: 1}, missing: {}, invalid: {f1: 2}}, 'f1');
  assert.match(svg, /data-model="zero"[^>]+width="0"/);
  assert.match(svg, /data-model="perfect"[^>]+width="400"/);
  assert.ok(!svg.includes('data-model="missing"') && !svg.includes('data-model="invalid"'));
  assert.ok(svg.includes('ไม่มีข้อมูล'));
});

test('roles and custom models are displayed only when present', () => {
  const models = {text_baseline: {f1: 0.8}, text_plus_roles: {f1: 0.7}, custom: {f1: 0.6}};
  const before = JSON.stringify(models);
  const svg = metricChart(models, 'f1');
  assert.match(svg, /data-model="text_plus_roles"[^>]+width="280"/);
  assert.match(svg, /data-model="custom"[^>]+width="240"/);
  assert.equal(JSON.stringify(models), before);
});

test('confusion matrix uses actual rows, predicted columns, and original counts', () => {
  const model = records[0].metrics.models.text_baseline;
  const svg = confusionChart(model, 'Text baseline');
  for (const [key, x, y, count] of [['tn',156,112,21], ['fp',306,112,63], ['fn',156,246,15], ['tp',306,246,72]]) {
    const cell = svg.match(new RegExp(`<g data-cell="${key}">(.*?)</g>`))[1];
    assert.ok(cell.includes(`x="${x}" y="${y}"`));
    assert.ok(cell.includes(`>${count}</text>`));
  }
  assert.ok(svg.includes('รวม 171 คู่'));
  assert.ok(confusionChart({confusion: {tn: 0, fp: 0, fn: 0, tp: 0}}, 'Empty').includes('รวม 0 คู่'));
  assert.ok(confusionChart({}, 'Missing').includes('ไม่มีข้อมูล confusion matrix'));
});

test('SVG text and attributes escape user-defined model names', () => {
  const name = '<script>alert("x")</script>';
  for (const svg of [metricChart({[name]: {f1: 0.5}}, 'f1', name), confusionChart(records[0].metrics.models.text_baseline, name, name)]) {
    assert.ok(!svg.includes('<script>'));
    assert.ok(svg.includes('&lt;script&gt;'));
    assert.ok(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"'));
  }
});

test('overview preserves scores, fixed scale, and missing-vs-zero distinction', () => {
  const {benchmarkChart} = require('./static/charts.js');
  const models={text_baseline:{f1:0},text_plus_time:{f1:0.1851},missing:{},perfect:{f1:1}};
  const chart=benchmarkChart(models,'f1','saved-run');
  assert.match(chart,/data-model="text_baseline"[^>]+width="0"/);
  const width=Number(chart.match(/data-model="text_plus_time"[^>]+width="([^"]+)"/)[1]);
  assert.ok(Math.abs(width-183.249)<1e-9);
  assert.match(chart,/data-model="perfect"[^>]+width="990"/);
  assert.ok(!chart.includes('data-model="missing"'));
  assert.ok(chart.includes('ไม่มีข้อมูล')&&chart.includes('18.51%')&&chart.includes('100%'));
  assert.ok(chart.includes('saved-run'));
});

test('overview separates only known references and keeps custom experiments', () => {
  const {modelGroups} = require('./static/charts.js');
  const models={majority_reference:{f1:0},cosine_reference:{f1:.1},time_only:{f1:.2},text_baseline:{f1:.3},custom:{f1:.4}};
  const before=JSON.stringify(models),{primary,references}=modelGroups(models);
  assert.deepEqual(Object.keys(primary),['text_baseline','custom']);
  assert.deepEqual(Object.keys(references),['majority_reference','cosine_reference','time_only']);
  assert.equal(JSON.stringify(models),before);
});

test('overview insight is derived from the selected run, not mockup scores', () => {
  const {resultInsight,benchmarkChart}=require('./static/charts.js');
  assert.match(resultInsight({text_plus_time:{f1:.2},text_plus_availability:{f1:.1}}),/สูงกว่า.*10.00/);
  assert.match(resultInsight({text_plus_time:{f1:.1},text_plus_availability:{f1:.2}}),/ต่ำกว่า.*10.00/);
  assert.match(resultInsight({text_plus_time:{f1:.1851},text_plus_availability:{f1:.1851}}),/ยังสรุป.*ไม่ได้/);
  assert.ok(!resultInsight({text_plus_time:{}}).includes('เท่ากับ'));
  assert.ok(!benchmarkChart({'<script>':{f1:.1}},'f1','<img>').includes('<script>'));
});

test('mobile overview keeps the full score range and readable stacked rows', () => {
  const {benchmarkChart}=require('./static/charts.js');
  const svg=benchmarkChart({text_baseline:{f1:0},text_plus_time:{f1:.5},custom:{f1:1}},'f1','mobile-run',true);
  assert.match(svg,/viewBox="0 0 360/);
  assert.match(svg,/data-model="text_baseline"[^>]+width="0"/);
  assert.match(svg,/data-model="text_plus_time"[^>]+width="160"/);
  assert.match(svg,/data-model="custom"[^>]+width="320"/);
  assert.ok(svg.includes('100%')&&svg.includes('mobile-run'));
});
