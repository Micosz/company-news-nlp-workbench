const test = require('node:test');
const assert = require('node:assert/strict');
const {compare, amount, date} = require('./static/facts.js');
const a = {buyer:'Company X',target:'Company Y',date:'2026-01-01',stage:'announced',currency:'USD',amount:'1.5',scale:'billion'};
const compareVerified = (a, b) => compare(a, b, {sameDealVerified:true});
test('normalizes numeric units without floating point drift', () => {
  assert.equal(amount('1.5','billion'), amount('1500','million'));
  assert.equal(amount('0.000001','unit'), 1n);
  for (const s of ['','-1','NaN','1e9','0.0000001','1,000']) assert.equal(amount(s,'unit'),null);
});
test('requires known identity, time, stage, currency and value', () => {
  for (const patch of [{buyer:''},{target:''},{date:''},{stage:''},{currency:''},{amount:''},{date:'2026-02-30'}]) {
    assert.equal(compareVerified(a,{...a,...patch}).kind, 'unknown');
  }
  assert.equal(date('2026-02-30'),null);
  assert.equal(compareVerified(a,{...a,target:'Other'}).kind,'unknown');
  assert.equal(compareVerified(a,{...a,target:'unknown'}).kind,'unknown');
  assert.equal(compareVerified(a,{...a,currency:'THB'}).kind,'unknown');
  assert.equal(compare(a,a).kind,'unknown');
});
test('compares two manually supplied claims conservatively', () => {
  assert.equal(compareVerified(a,{...a,amount:'1500',scale:'million'}).kind,'agreement');
  assert.equal(compareVerified(a,{...a,amount:'2'}).kind,'possible_conflict');
  assert.equal(compareVerified(a,{...a,date:'2026-02-01',amount:'2'}).kind,'update');
  assert.equal(compareVerified(a,{...a,stage:'completed',amount:'2'}).kind,'update');
});
