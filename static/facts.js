/* Conservative prototype: compare user-entered claims, never extract or verify news. */
(function (root) {
  'use strict';
  const text = v => String(v ?? '').normalize('NFKC').trim().replace(/\s+/gu, ' ').toLowerCase();
  const known = v => !!text(v) && !['unknown','n/a','na','null','none','nan','-','ไม่ทราบ','ไม่ระบุ'].includes(text(v));
  const date = value => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value ?? ''))) return null;
    const d = new Date(value + 'T00:00:00Z');
    return !Number.isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === value ? value : null;
  };
  const time = value => {
    const s = String(value ?? '').trim();
    return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(s) ? s : null;
  };
  // Accept valid thousands separators and retain integer micro-units for precision.
  const amount = (value, scale) => {
    const s = String(value ?? '').normalize('NFKC').trim();
    if (!/^(?:\d{1,3}(?:,\d{3})+|\d{1,20})(?:\.\d{1,6})?$/.test(s)) return null;
    const scales = {unit: 1n, million: 1000000n, billion: 1000000000n};
    if (!Object.hasOwn(scales, scale)) return null;
    const multiplier = scales[scale];
    const [integer, fractional = ''] = s.replace(/,/g, '').split('.');
    if (integer.length > 20) return null;
    return (BigInt(integer) * 1000000n + BigInt(fractional.padEnd(6, '0'))) * multiplier;
  };
  const unknown = message => ({kind:'unknown', message});
  const chronology = (a, b) => {
    const da = date(a.date), db = date(b.date);
    if (!da || !db) return null;
    if (da !== db) return da < db ? [a,b] : [b,a];
    const ta = time(a.time), tb = time(b.time);
    if (!ta || !tb || ta === tb) return null;
    return ta < tb ? [a,b] : [b,a];
  };
  function compare(a, b, options = {}) {
    if (!options.sameDealVerified) return unknown('โปรดยืนยันก่อนว่าข่าวทั้งสองกล่าวถึงดีลหรือเรื่องเดียวกัน');
    const eventType = options.eventType || 'acquisition';
    if (!['acquisition','dividend'].includes(eventType)) return unknown('ยังไม่รองรับประเภทเหตุการณ์นี้');
    const entities = eventType === 'dividend' ? ['company'] : ['buyer','target'];
    if (entities.some(k => !known(a[k]) || !known(b[k]))) return unknown(eventType === 'dividend' ? 'ข้อมูลไม่พอ: โปรดระบุบริษัททั้งสองข่าว' : 'ข้อมูลไม่พอ: โปรดระบุผู้ซื้อและเป้าหมายทั้งสองข่าว');
    if (entities.some(k => text(a[k]) !== text(b[k]))) return unknown('ชื่อบริษัทไม่ตรงกัน โปรดตรวจว่าเป็นเรื่องเดียวกันและตรวจชื่อย่อก่อน');
    const sa = known(a.stage) ? text(a.stage) : '', sb = known(b.stage) ? text(b.stage) : '';
    const ca = known(a.certainty) ? text(a.certainty) : '', cb = known(b.certainty) ? text(b.certainty) : '';
    const certaintyValues = ['', 'forecast', 'confirmed'];
    if (!certaintyValues.includes(ca) || !certaintyValues.includes(cb)) return unknown('ไม่รู้จักระดับความแน่นอน โปรดตรวจข้อมูล');
    for (const record of [a,b]) {
      if ((record.date && !date(record.date)) || (record.time && !time(record.time))) return unknown('รูปแบบวันที่หรือเวลารายงานไม่ถูกต้อง');
    }
    // Status progress is independent of amount and currency. Date/time establish order;
    // reported changes remain hypotheses, not verified developments.
    if (eventType === 'acquisition') {
      const stages = ['negotiating','announced','signed','pending','approved','completed','cancelled'];
      if ((sa || sb) && (!stages.includes(sa) || !stages.includes(sb))) return unknown('ข้อมูลสถานะดีลไม่ครบหรือไม่ถูกต้อง โปรดตรวจทั้งสองข่าว');
      if (sa !== sb) {
        const order = chronology(a,b);
        if (!order) return unknown('สถานะต่างกัน แต่ข้อมูลวันหรือเวลาไม่พอที่จะเรียงลำดับข่าว');
        if (text(order[1].certainty) === 'forecast') return unknown('ข่าวภายหลังเป็นการคาดการณ์ จึงยังยืนยันความคืบหน้าของสถานะไม่ได้');
        const transitions = {
          negotiating: ['announced','signed','pending','approved','completed','cancelled'],
          announced: ['signed','pending','approved','completed','cancelled'],
          signed: ['pending','approved','completed','cancelled'],
          pending: ['approved','completed','cancelled'],
          approved: ['completed','cancelled'],
          completed: [], cancelled: []
        };
        if (!transitions[text(order[0].stage)].includes(text(order[1].stage))) return unknown('ลำดับสถานะยังไม่สอดคล้องกับความคืบหน้าแบบปกติ โปรดตรวจหลักฐาน');
        return {kind:'update', message:'สถานะต่างกันตามลำดับรายงาน อาจเป็นความคืบหน้า โปรดตรวจลำดับและหลักฐาน'};
      }
    }
    // For numeric comparisons or changes in certainty, the user explicitly confirms
    // that the reported metric refers to the same subject, unit, and effective period.
    if (!options.sameFactVerified) return unknown('โปรดยืนยันว่าตัวเลขหรือข้ออ้างเป็นชนิดและงวดเดียวกันก่อนเปรียบเทียบ');
    if (known(a.period) && known(b.period) && text(a.period) !== text(b.period)) return unknown('งวดหรือช่วงเวลาที่ข้อมูลมีผลต่างกัน จึงยังเปรียบเทียบเป็นข้ออ้างเดียวกันไม่ได้');
    if (ca !== cb) {
      if (!ca || !cb) return unknown('ข้อมูลความแน่นอนไม่ครบ จึงเปรียบเทียบข้ออ้างไม่ได้');
      const order = chronology(a,b);
      if (!order) return unknown('ความแน่นอนต่างกัน แต่ข้อมูลวันหรือเวลาไม่พอที่จะเรียงลำดับข่าว');
      if (text(order[0].certainty) === 'forecast' && text(order[1].certainty) === 'confirmed') {
        return {kind:'update', message:'จากการคาดการณ์สู่ข้อมูลที่ยืนยันแล้ว อาจเป็นการอัปเดต โปรดตรวจวัน งวด และหลักฐาน'};
      }
      return unknown('ความแน่นอนต่างกันและลำดับยังไม่รองรับการสรุปเป็นอัปเดต โปรดตรวจหลักฐาน');
    }
    if (eventType === 'dividend' && (!ca || !cb)) return unknown('ข้อมูลความแน่นอนของข่าวปันผลไม่ครบ กรุณาระบุคาดการณ์หรือยืนยันแล้ว');
    if (!/^[A-Z]{3}$/.test(String(a.currency || '').trim().toUpperCase()) || !/^[A-Z]{3}$/.test(String(b.currency || '').trim().toUpperCase())) return unknown('ข้อมูลไม่พอ: โปรดระบุสกุลเงินเป็นรหัส 3 ตัวอักษร');
    if (text(a.currency) !== text(b.currency)) return unknown('สกุลเงินต่างกัน ยังไม่แปลงสกุลเงินและเปรียบเทียบมูลค่าโดยตรงไม่ได้');
    const va = amount(a.amount, a.scale), vb = amount(b.amount, b.scale);
    if (va === null || vb === null) return unknown('ข้อมูลมูลค่าไม่ครบหรือรูปแบบตัวเลขไม่ถูกต้อง');
    const toleranceText = options.tolerancePercent === undefined || options.tolerancePercent === '' ? '0' : String(options.tolerancePercent).trim();
    const tolerance = amount(toleranceText,'unit');
    if (tolerance === null || tolerance > 100000000n) return unknown('ค่าคลาดเคลื่อนต้องเป็นตัวเลขระหว่าง 0 ถึง 100 เปอร์เซ็นต์');
    const diff = va > vb ? va-vb : vb-va, larger = va > vb ? va : vb;
    if (diff === 0n) return {kind:'agreement', message:'มูลค่าที่กรอกตรงกันภายใต้ข้ออ้างและงวดที่ยืนยัน โปรดตรวจหลักฐานต้นฉบับ'};
    // Relative tolerance uses the larger magnitude as denominator, stated in UI.
    if (diff * 100000000n <= larger * tolerance) return {kind:'agreement', message:`มูลค่าไม่เท่ากันเป๊ะ แต่ต่างกันไม่เกินค่าคลาดเคลื่อน ${toleranceText}% ของค่าที่มากกว่า โปรดตรวจวิธีปัดเศษและหลักฐาน`};
    if (ca === 'forecast' && cb === 'forecast') return unknown('ตัวเลขคาดการณ์ต่างกัน แต่ยังสรุปว่าข้อมูลที่ยืนยันแล้วขัดแย้งกันไม่ได้ โปรดตรวจช่วงเวลาและหลักฐาน');
    return {kind:'possible_conflict', message:'มูลค่าที่กรอกอาจขัดแย้งกัน แม้วันรายงานต่างกัน โปรดตรวจประเภทมูลค่า งวด เงื่อนไข และต้นฉบับ'};
  }
  const api = {compare, amount, date, time};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WorkbenchFacts = api;
})(globalThis);
