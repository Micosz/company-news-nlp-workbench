export const upstream = '5639eb84f9cd32c360ff2ee715eb937ed2cc3c8e';
export const hashes = {
  ann1: 'a39c855868a0faac3ea223b2e7d4a864b2bf557d7bba3d7cbb759908d5345575',
  ann2: '3fe1164306c4f9600427571b450a5fc4e427789b651e8a6cdcddfeaf0d0c4d32'
};
export const source = ann => 'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/' + upstream
  + '/project/annotations/ecb/' + ann.toLowerCase() + '/dev_xamr.json';

export async function checkedRows(bytes, ann) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const sum = [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  if (sum !== hashes[ann.toLowerCase()]) throw new Error('ไฟล์ไม่ตรงกับชุดคำกำกับที่เลือก');
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function fetchRows(ann) {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), 20000);
  try {
    const res = await fetch(source(ann), {credentials: 'omit', signal: timeout.signal});
    if (!res.ok) throw new Error('โหลดข่าวต้นทางไม่ได้');
    return checkedRows(await res.arrayBuffer(), ann);
  } finally {
    clearTimeout(timer);
  }
}
