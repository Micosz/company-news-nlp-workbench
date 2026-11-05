const test = require('node:test');
const assert = require('node:assert/strict');
const {compare, amount, date, time} = require('./static/facts.js');
const a = {buyer:'Company X',target:'Company Y',date:'2026-01-01',stage:'announced',currency:'USD',amount:'5.0',scale:'billion',certainty:'confirmed'};
const verified = {sameDealVerified:true,sameFactVerified:true};
const compareVerified = (left, right, options={}) => compare(left,right,{...verified,...options});

test('correct thousands separators and unit normalization preserve exact values', () => {
  assert.equal(amount('5,000','unit'), amount('5000','unit'));
  assert.equal(amount('1,234.56','million'), amount('1234.56','million'));
  assert.equal(amount('0.000001','unit'), 1n);
  for (const s of ['', '-1', 'NaN', '1e9', '0.0000001', '5,00', '12,34', '1.234,56', '1,2,3', '1234,567']) assert.equal(amount(s,'unit'),null, s);
  assert.equal(amount('100','constructor'),null);
  assert.equal(compareVerified({...a,amount:'5,000',scale:'unit'}, {...a,amount:'5000',scale:'unit'}).kind,'agreement');
});

test('percentage tolerance applies exactly relative to larger value', () => {
  const b={...a,amount:'4.98'};
  assert.equal(compareVerified(a,b).kind,'possible_conflict');
  const result=compareVerified(a,b,{tolerancePercent:'0.5'});
  assert.equal(result.kind,'agreement');
  assert.match(result.message,/ไม่เท่ากันเป๊ะ/);
  assert.equal(compareVerified(a,b,{tolerancePercent:'0.4'}).kind,'agreement');
  assert.equal(compareVerified(a,b,{tolerancePercent:'0.399999'}).kind,'possible_conflict');
  for(const tolerancePercent of ['-1','100.000001','NaN','abc','0.0000001']) assert.equal(compareVerified(a,b,{tolerancePercent}).kind,'unknown');
  assert.equal(compareVerified({...a,amount:'0'}, {...a,amount:'0'}, {tolerancePercent:'0'}).kind,'agreement');
  assert.equal(compareVerified({...a,amount:'0'}, {...a,amount:'1'}, {tolerancePercent:'100'}).kind,'agreement');
  assert.equal(compareVerified({...a,stage:'',amount:'5,000',scale:'unit'}, {...a,stage:'',amount:'5000',scale:'unit'}).kind,'agreement');
  assert.equal(compareVerified({...a,stage:'',amount:'5.0'}, {...a,stage:'',amount:'4.98'}, {tolerancePercent:'0.5'}).kind,'agreement');
});

test('requires verified subject, deal, same fact and comparable currencies', () => {
  assert.equal(compare(a,a).kind,'unknown');
  assert.equal(compare(a,a,{sameDealVerified:true}).kind,'unknown');
  for (const patch of [{buyer:''},{target:''},{buyer:'unknown'},{target:'Other'},{stage:''},{currency:''},{amount:''}]) assert.equal(compareVerified(a,{...a,...patch}).kind,'unknown');
  const fx=compareVerified(a,{...a,currency:'THB'});
  assert.equal(fx.kind,'unknown');
  assert.match(fx.message,/ไม่แปลงสกุลเงิน/);
  assert.equal(compareVerified({...a,period:'FY2025'}, {...a,period:'FY2026'}).kind,'unknown');
});

test('reporting date alone never proves an update', () => {
  const b={...a,date:'2026-02-01',amount:'4.5'};
  assert.equal(compareVerified(a,b).kind,'possible_conflict');
  assert.equal(compare(a,b,{sameDealVerified:true}).kind,'unknown');
  assert.equal(compareVerified(a,{...b,amount:'5'}).kind,'agreement');
  assert.equal(compareVerified({...a,period:'FY2025'}, {...b,period:'FY2026'}).kind,'unknown');
});

test('stage progression needs ordered reporting times, not amount', () => {
  const before={...a,stage:'negotiating',date:'2026-01-01',time:'09:00',amount:'',currency:''};
  const after={...a,stage:'signed',date:'2026-01-01',time:'17:30',amount:'',currency:''};
  assert.equal(compare(before,after,{sameDealVerified:true}).kind,'update');
  assert.equal(compare(after,before,{sameDealVerified:true}).kind,'update');
  assert.equal(compare(before,{...after,time:''},{sameDealVerified:true}).kind,'unknown');
  assert.equal(compare(before,{...after,time:'09:00'},{sameDealVerified:true}).kind,'unknown');
  const announced={...a,stage:'announced',date:'2026-01-01',amount:'',currency:''};
  const completed={...a,stage:'completed',date:'2026-01-02',amount:'',currency:''};
  assert.equal(compare(announced,completed,{sameDealVerified:true}).kind,'update');
  assert.equal(compare({...completed,date:'2026-01-01'}, {...announced,date:'2026-01-02'}, {sameDealVerified:true}).kind,'unknown');
  assert.equal(compare(announced,{...completed,certainty:'forecast'},{sameDealVerified:true}).kind,'unknown');
  assert.equal(date('2026-02-30'),null);
  assert.equal(time('25:00'),null);
  assert.equal(time('17:30'),'17:30');
  assert.equal(compare(announced,{...completed,date:'bad'},{sameDealVerified:true}).kind,'unknown');
});

test('dividend uses company identity, same period, and certainty separately from status', () => {
  const forecast={company:'Company Z',period:'FY2026',date:'2026-03-01',certainty:'forecast',amount:'2',scale:'unit',currency:'THB'};
  const approved={...forecast,date:'2026-03-02',certainty:'confirmed',amount:'1.80'};
  const opts={eventType:'dividend',...verified};
  assert.equal(compare(forecast,approved,opts).kind,'update');
  assert.equal(compare(forecast,{...approved,period:'FY2027'},opts).kind,'unknown');
  assert.equal(compare({...forecast,certainty:'confirmed'},approved,opts).kind,'possible_conflict');
  assert.equal(compare(forecast,{...forecast,amount:'1.50'},opts).kind,'unknown');
  assert.equal(compare({...forecast,certainty:''},approved,opts).kind,'unknown');
  assert.equal(compare(forecast,{...approved,date:'2026-03-01'},opts).kind,'unknown');
  assert.equal(compare(forecast,{...approved,company:'Company W'},opts).kind,'unknown');
  assert.equal(compare({...forecast,certainty:'confirmed'}, {...approved,amount:'2',currency:'USD'},opts).kind,'unknown');
  assert.equal(compare(forecast,approved,{eventType:'dividend',sameDealVerified:true}).kind,'unknown');
});
