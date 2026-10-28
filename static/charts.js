/* Render saved metrics only; no model training or score recomputation here. */
(function (root) {
  'use strict';
  const names = {
    majority_reference: 'Majority reference',
    cosine_reference: 'Cosine reference',
    text_baseline: 'Text baseline',
    text_plus_roles: 'Text + finance roles',
    time_only: 'Time only reference',
    text_plus_time: 'Text + event date'
  };
  const metrics = {f1: 'F1', precision: 'Precision', recall: 'Recall', macro_f1: 'Macro F1'};
  const colors = {majority_reference: '#798781', cosine_reference: '#a17a30', text_baseline: '#176b58', text_plus_roles: '#5265b3', time_only: '#a16454', text_plus_time: '#73599c'};
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
  const percentage = value => valid(value) ? `${(value * 100).toFixed(2)}%` : 'ไม่มีข้อมูล';
  const short = (value, length = 35) => value.length > length ? value.slice(0, length - 1) + '…' : value;
  function svg(height, title, description, content) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 ${height}" role="img" aria-label="${escape(title)}" font-family="Thonburi, Noto Sans Thai, Arial, sans-serif"><title>${escape(title)}</title><desc>${escape(description)}</desc><rect width="480" height="${height}" fill="white"/>${content}</svg>`;
  }
  function metricChart(models, metric, runId = '') {
    if (!Object.hasOwn(metrics, metric)) throw new Error('Unknown metric');
    const entries = Object.entries(models || {}), height = 114 + entries.length * 72;
    const description = entries.map(([key, model]) => `${names[key] || key}: ${percentage(model[metric])}`).join('; ');
    let content = `<text x="24" y="25" font-size="20" font-weight="700" fill="#182c2c">${metrics[metric]} · เปรียบเทียบโมเดล</text><text x="24" y="47" font-size="11" fill="#667875">${escape(runId)}</text>`;
    for (const tick of [0, 25, 50, 75, 100]) {
      const x = 32 + tick * 4;
      content += `<line x1="${x}" x2="${x}" y1="78" y2="${height - 28}" stroke="#e5eae6"/><text x="${x}" y="70" text-anchor="middle" font-size="12" fill="#667875">${tick}%</text>`;
    }
    entries.forEach(([key, model], index) => {
      const y = 98 + index * 72, value = model[metric], color = colors[key] || '#5265b3';
      content += `<g><title>${escape(names[key] || key)}: ${percentage(value)}</title><text x="32" y="${y}" font-size="15" fill="#182c2c">${escape(short(names[key] || key))}</text><text x="450" y="${y}" text-anchor="end" font-size="15" font-weight="700" fill="#182c2c">${percentage(value)}</text><rect x="32" y="${y + 12}" width="400" height="20" rx="4" fill="#eef2ee"/>`;
      if (valid(value)) content += `<rect data-model="${escape(key)}" x="32" y="${y + 12}" width="${value * 400}" height="20" rx="4" fill="${color}"/>`;
      content += '</g>';
    });
    if (!entries.length) content += '<text x="24" y="96" font-size="16" fill="#667875">ยังไม่มีผลโมเดล</text>';
    return svg(height, `${metrics[metric]} comparison`, description, content);
  }
  function confusionChart(model, modelName, runId = '') {
    const c = model?.confusion;
    if (!c || !['tn', 'fp', 'fn', 'tp'].every(key => Number.isInteger(c[key]) && c[key] >= 0)) {
      return svg(120, 'Confusion matrix unavailable', 'ไม่มีจำนวนคู่สำหรับแสดงกราฟ', '<text x="24" y="60" font-size="17" fill="#667875">ไม่มีข้อมูล confusion matrix</text>');
    }
    const cells = [
      {key: 'tn', x: 156, y: 112, label: 'แยกถูก', correct: true},
      {key: 'fp', x: 306, y: 112, label: 'รวมผิด', correct: false},
      {key: 'fn', x: 156, y: 246, label: 'แยกผิด', correct: false},
      {key: 'tp', x: 306, y: 246, label: 'รวมถูก', correct: true}
    ];
    let content = `<text x="24" y="25" font-size="19" font-weight="700" fill="#182c2c">${escape(short(modelName, 38))}</text><text x="24" y="47" font-size="11" fill="#667875">${escape(runId)}</text>`;
    for (const [x, label, detail] of [[226, 'ทำนาย: 0', 'คนละเหตุการณ์'], [376, 'ทำนาย: 1', 'เหตุการณ์เดียวกัน']]) {
      content += `<text x="${x}" y="79" text-anchor="middle" font-size="14" fill="#182c2c">${label}<tspan x="${x}" dy="19" font-size="12">${detail}</tspan></text>`;
    }
    for (const [y, label, detail] of [[167, 'จริง: 0', 'คนละเหตุการณ์'], [301, 'จริง: 1', 'เหตุการณ์เดียวกัน']]) {
      content += `<text x="140" y="${y}" text-anchor="end" font-size="14" fill="#182c2c">${label}<tspan x="140" dy="20" font-size="12">${detail}</tspan></text>`;
    }
    cells.forEach(({key, x, y, label, correct}) => {
      content += `<g data-cell="${key}"><title>${key.toUpperCase()}: ${c[key]} คู่ — ${label}</title><rect x="${x}" y="${y}" width="140" height="124" rx="9" fill="${correct ? '#e5f1e9' : '#f9e9df'}"/><text x="${x + 70}" y="${y + 26}" text-anchor="middle" font-size="13" fill="#52615a">${key.toUpperCase()} · ${label}</text><text x="${x + 70}" y="${y + 73}" text-anchor="middle" font-size="34" font-weight="700" fill="#182c2c">${c[key]}</text><text x="${x + 70}" y="${y + 99}" text-anchor="middle" font-size="12" fill="#52615a">คู่ข้อความ</text></g>`;
    });
    const total = c.tn + c.fp + c.fn + c.tp;
    content += `<text x="24" y="399" font-size="13" fill="#667875">รวม ${total.toLocaleString('en-US')} คู่ · สีเขียว = ถูก · สีส้ม = ผิด</text>`;
    return svg(418, 'Confusion matrix: ' + modelName, `Rows: true labels. Columns: predicted labels. TN ${c.tn}, FP ${c.fp}, FN ${c.fn}, TP ${c.tp}. Total ${total}.`, content);
  }
  const api = {names, metrics, metricChart, confusionChart};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WorkbenchCharts = api;
})(globalThis);
