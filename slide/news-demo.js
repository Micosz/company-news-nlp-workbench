'use strict';
const newsDemoSlide = (() => {
 const dataUrl = 'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/5639eb84f9cd32c360ff2ee715eb937ed2cc3c8e/project/annotations/ecb/ann1/dev_xamr.json';
 const reportUrl = 'https://github.com/Micosz/company-news-nlp-workbench/blob/b6a0683a586e6ffc9c98a19287a3138743cabb62/docs/XAMR_TFIDF_ONLY_TH.md#L44';
 const stories = [
  {name:'Vincent Jackson', date:'6 ม.ค. 2009', id:'35_10ecb.xml_35', summary:'ข่าวรายงานว่าตำรวจทางหลวงแคลิฟอร์เนียจับกุมปีกตัวรับของ San Diego Chargers หลังไม่ผ่านการทดสอบความพร้อมในการขับขี่'},
  {name:'Jamal Williams', date:'1 ก.พ. 2009', id:'35_4ecbplus.xml_8', summary:'ข่าวรายงานว่าผู้เล่นแนวรับของ Chargers ถูกจับกุมในข้อสงสัยเดียวกัน และกล่าวย้อนถึงคดีของ Jackson เมื่อเดือนก่อน'}
 ];
 const answers = [
  '<strong>OR แยกถูก · OR + TF-IDF รวมผิด</strong><span>เฉลยใน ECB+ ให้สองการจับกุมอยู่คนละกลุ่ม แต่ OR + TF-IDF เติมเส้นระหว่างข่าวคู่นี้</span>',
  '<strong>คำคล้ายกัน แต่คนละคนและคนละวัน</strong><span>ทั้งคู่มีบทบาทผู้จับเป็นตำรวจทางหลวงแคลิฟอร์เนีย และใช้ถ้อยคำคล้ายกัน แต่ผู้ถูกจับต่างกัน</span>',
  '<strong>22 × 19 = 418 คู่ใหม่</strong><span>เมื่อเพิ่มเส้นเดียว กลุ่มเดิมที่มี 22 และ 19 การกล่าวถึงถูกรวมเข้าด้วยกัน ทุกคู่ข้ามสองกลุ่มจึงถูกนับว่าเป็นเหตุการณ์เดียวกัน</span>'
 ];
 const body = `<section class="news-demo" aria-label="เดโมข่าว ECB+">
  <div class="nd-caption">ECB+ · Ann1 dev · Topic 35 · ผลทดลองที่บันทึกไว้</div>
  <div class="nd-questions" role="group" aria-label="เลือกคำถาม">
   <button type="button" data-news-question="0" aria-pressed="true">ระบบแยกข่าวถูกไหม?</button>
   <button type="button" data-news-question="1" aria-pressed="false">หลักฐานบอกอะไร?</button>
   <button type="button" data-news-question="2" aria-pressed="false">เส้นเดียวกระทบกี่คู่?</button>
  </div>
  <div class="nd-answer" aria-live="polite">${answers[0]}</div>
  <div class="nd-evidence" aria-label="หลักฐานข่าวสองชิ้น">
   ${stories.map((s,i)=>`<section class="nd-story">
    <span class="nd-label">ข่าว ${i+1} · วันที่ตามคำกำกับ Ann1: ${s.date}</span>
    <h2>${s.name}</h2>
    <p><mark>ถูกจับกุม</mark> ในข้อสงสัยว่าเมาแล้วขับ</p>
    <p>${s.summary}</p>
    <code>${s.id}</code>
    <details class="nd-original" data-news-original="${i}" hidden><summary>อ่านข้อความข่าวภาษาอังกฤษ</summary><div class="nd-original-text" tabindex="0" aria-label="ข้อความข่าวจากไฟล์ที่เลือก"></div></details>
   </section>`).join('')}
  </div>
  <div class="nd-foot">
   <a href="${reportUrl}" target="_blank" rel="noopener">หลักฐานผลทดลอง ↗</a>
   <details class="nd-import"><summary>อ่านต้นฉบับจากชุดข้อมูล</summary><div class="nd-import-panel">
    <p>ดาวน์โหลดไฟล์ Ann1 dev แล้วเลือกไฟล์เพื่ออ่านข้อความจริง เปิดต่อหน้าเท่านั้น ไม่อัปโหลดไฟล์</p>
    <a href="${dataUrl}" target="_blank" rel="noopener">เปิดไฟล์ต้นทาง ↗</a>
    <label>เลือก Ann1 dev JSON<input type="file" aria-describedby="nd-import-status" accept=".json,application/json" data-news-file></label>
    <span id="nd-import-status" aria-live="polite"></span>
   </div></details>
   <span>ข้อความภาษาไทยเป็นสรุปจากชุดข้อมูล ไม่ใช่ผลสรุปที่โมเดลสร้าง</span>
  </div>
 </section>`;
 function choose(e) {
  const button=e.target.closest?.('[data-news-question]');
  if (!button) return;
  const demo=button.closest('.news-demo');
  demo.querySelectorAll('[data-news-question]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  demo.querySelector('.nd-answer').innerHTML=answers[Number(button.dataset.newsQuestion)];
 }
 const strip = str => str.replace(/<\/?mark\b[^>]*>/gi,'');
 function renderOriginal(target, text) {
  const parts=text.split(/<p\s*\/>/i).map(p=>p.trim()).filter(Boolean);
  target.replaceChildren(...parts.filter(p=>!/^https?\s*:/i.test(p)).map(part=>{
   const p=document.createElement('p');
   for(const [i,span] of part.split(/<\/?mark\b[^>]*>/gi).entries()){
    if(i%2){const mark=document.createElement('mark');mark.textContent=span;p.append(mark);}
    else p.append(document.createTextNode(span));
   }
   return p;
  }));
 }
 const importVersion=new WeakMap();
 async function importNews(e) {
  const input=e.target.closest?.('[data-news-file]');
  if (!input || !input.files[0]) return;
  const demo=input.closest('.news-demo'), file=input.files[0];
  const status=demo.querySelector('#nd-import-status');
  const request=(importVersion.get(demo)||0)+1;
  importVersion.set(demo,request);
  status.textContent='กำลังตรวจไฟล์…';
  try {
   if(file.size>8e6) throw Error('oversize');
   const content=await file.arrayBuffer();
   if (!globalThis.crypto?.subtle) throw Error('secure context unavailable');
   const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',content)),b=>b.toString(16).padStart(2,'0')).join('');
   if(digest!=='a39c855868a0faac3ea223b2e7d4a864b2bf557d7bba3d7cbb759908d5345575') throw Error('different dataset');
   if(importVersion.get(demo)!==request || !demo.isConnected) return;
   const rows=JSON.parse(new TextDecoder().decode(content));
   const docs=stories.map(s=>rows.find(row=>row.mention_id===s.id)?.marked_doc);
   if(docs.some(d=>typeof d!=='string'||!strip(d).trim())) throw Error('missing evidence');
   demo.querySelectorAll('[data-news-original]').forEach((details,i)=>{
    renderOriginal(details.querySelector('.nd-original-text'),docs[i]);details.hidden=false;details.open=true;
   });
   status.textContent='เปิดต้นฉบับทั้งสองข่าวแล้ว';
   demo.querySelector('.nd-import').open=false;
   demo.querySelector('.nd-original summary').focus({preventScroll:true});
  } catch {
   if(importVersion.get(demo)===request) status.textContent='ไฟล์ไม่ตรงกับ Ann1 dev ต้นทาง กรุณาใช้ลิงก์ด้านบน';
  } finally {
   if(importVersion.get(demo)===request) input.value='';
  }
 }
 document.addEventListener('click',choose);
 document.addEventListener('change',importNews);
 // Scroll keys stay local when an evidence passage has keyboard focus.
 document.addEventListener('keydown',e=>{
  if(e.target.closest?.('.nd-original-text') && [' ','PageDown','PageUp','Home','End'].includes(e.key)) e.stopPropagation();
 });
 return {
  g:3, title:'ลองแกะข่าว: เหตุการณ์เดียวกันไหม?', body,
  note:'เลือกคำถามแรกเพื่อเทียบ OR กับ OR + TF-IDF จากผลจริงบน Ann1 dev ครับ สองข่าวนี้เป็นการจับกุมคนละคน แม้ถ้อยคำและผู้จับเหมือนกัน แล้วลองเปิดคำถามที่สามเพื่อดูผลของเส้นเดียวต่อคู่ข้ามกลุ่ม ตัวเลข 418 เป็นจำนวนคู่ที่เกิดเพิ่มจากการรวมกลุ่มคู่นี้'
 };
})();
