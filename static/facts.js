/* Conservative prototype: compare user-entered claims, never extract or verify news. */
(function (root) {
  'use strict';
  const text = v => String(v ?? '').normalize('NFKC').trim().replace(/\s+/gu, ' ').toLowerCase();
  const known = v => !!text(v) && !['unknown','n/a','na','null','none','nan','-','ไม่ทราบ','ไม่ระบุ'].includes(text(v));
  const date = value => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const d = new Date(value + 'T00:00:00Z');
    return !Number.isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === value ? value : null;
  };
  // Integer micro-units avoid rounding error when comparing amount scales.
  const amount = (value, scale) => {
    const s = String(value ?? '').trim();
    if (!/^\d{1,20}(?:\.\d{1,6})?$/.test(s)) return null;
    const multiplier = {unit: 1n, million: 1000000n, billion: 1000000000n}[scale];
    if (!multiplier) return null;
    const [integer, fractional = ''] = s.split('.');
    return (BigInt(integer) * 1000000n + BigInt(fractional.padEnd(6, '0'))) * multiplier;
  };
  function compare(a, b, options = {}) {
    if (!options.sameDealVerified) return {kind: 'unknown', message: 'โปรดยืนยันก่อนว่าข่าวทั้งสองเกี่ยวกับดีลเดียวกัน'};
    const entities = ['buyer', 'target'];
    if (entities.some(k => !known(a[k]) || !known(b[k]))) return {kind: 'unknown', message: 'ข้อมูลไม่พอ: โปรดระบุผู้ซื้อและเป้าหมายทั้งสองข่าว'};
    if (entities.some(k => text(a[k]) !== text(b[k]))) return {kind: 'unknown', message: 'ชื่อผู้ซื้อหรือเป้าหมายไม่ตรงกัน โปรดตรวจว่าเป็นดีลเดียวกันและตรวจชื่อย่อก่อน'};
    const da = date(a.date), db = date(b.date), sa = text(a.stage), sb = text(b.stage);
    if (!da || !db || !sa || !sb) return {kind: 'unknown', message: 'ข้อมูลไม่พอ: ต้องมีวันที่และสถานะดีลของทั้งสองข่าว'};
    if (!/^[A-Z]{3}$/.test(String(a.currency || '').trim().toUpperCase()) || !/^[A-Z]{3}$/.test(String(b.currency || '').trim().toUpperCase())) return {kind: 'unknown', message: 'ข้อมูลไม่พอ: โปรดระบุสกุลเงินเป็นรหัส 3 ตัวอักษร'};
    if (text(a.currency) !== text(b.currency)) return {kind: 'unknown', message: 'สกุลเงินต่างกัน ยังเปรียบเทียบมูลค่าโดยตรงไม่ได้'};
    const va = amount(a.amount, a.scale), vb = amount(b.amount, b.scale);
    if (va === null || vb === null) return {kind: 'unknown', message: 'ข้อมูลมูลค่าไม่ครบหรือรูปแบบตัวเลขไม่ถูกต้อง'};
    if (da !== db || sa !== sb) return {kind: 'update', message: 'วันหรือสถานะดีลต่างกัน อาจเป็นความคืบหน้า โปรดตรวจลำดับและหลักฐาน'};
    if (va === vb) return {kind: 'agreement', message: 'ข้อมูลมูลค่าที่กรอกสอดคล้องกันในวันและสถานะเดียวกัน'};
    return {kind: 'possible_conflict', message: 'มูลค่าที่กรอกอาจขัดแย้งกัน โปรดตรวจประเภทมูลค่า หน่วย เงื่อนไข และต้นฉบับ'};
  }
  const api = {compare, amount, date};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WorkbenchFacts = api;
})(globalThis);
