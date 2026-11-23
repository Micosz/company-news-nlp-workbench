import {checkedRows, fetchRows, source} from '/audit-source.mjs';
(() => {
 const $=id=>document.getElementById(id);
 const el=(tag,txt='',cls='')=>{const n=document.createElement(tag);n.textContent=txt;if(cls)n.className=cls;return n;};
 const sourceRequests={}, datasets={};
 const suggested=['35_10ecb.xml','35_4ecbplus.xml','12_10ecb.xml'];
 const removeMarkup=s=>String(s??'').replace(/<\/?mark\b[^>]*>/gi,'').trim();
 const paragraphs=raw=>String(raw??'').split(/<p\s*\/?\s*>/i).map(v=>v.trim()).filter(Boolean);
 const urlLine=s=>/^https?\s*:/i.test(s);
 const compact=s=>String(s??'').normalize('NFC').toLowerCase().trim();
 const normalize=s=>compact(s).replace(/[’‘']/g,'').replace(/\s+/g,' ');
 const alias=[[/จับกุม|ถูกจับ|เมาแล้วขับ/g,'arrest'],[/แจ็กสัน|แจ็คสัน/g,'jackson'],[/จามาล|วิลเลียมส์/g,'williams'],[/โจรสลัด/g,'pirat']];
 const terms=s=>{let out=normalize(s);for(const [re,value] of alias)out=out.replace(re,value);return out.split(/\s+/).filter(Boolean);};
 let annotations=null, listLimit=12, viewAll=false, activeArticle=null, lastTrigger=null, lastHash=null;
 let selected='';
 function catalogFor(rows) {
  const byDoc=new Map(), byId=new Map();
  for(const row of rows){
   byId.set(row.mention_id,row);
   if(!byDoc.has(row.doc_id))byDoc.set(row.doc_id,{id:row.doc_id,topic:String(row.topic),rows:[],title:'',text:[],search:''});
   const doc=byDoc.get(row.doc_id);doc.rows.push(row);
   if(!doc.text.length && row.marked_doc)doc.text=paragraphs(row.marked_doc).filter(x=>!urlLine(x));
  }
  for(const doc of byDoc.values()){
   const a=doc.rows[0];
   const first=removeMarkup(doc.text[0]||a.text).replace(/\s+([.,:;!?])/g,'$1');
   doc.title=first.length>120?'':first;doc.description=removeMarkup(doc.text[doc.title?1:0]||a.text);
   doc.search=normalize([doc.id,...doc.text.map(removeMarkup),...doc.rows.flatMap(r=>[r.lemma,r.arg0,r.arg1,r.argL,r.argT,r.text])].join(' '));
  }
  return {byDoc,byId,articles:[...byDoc.values()].sort((a,b)=>Number(a.topic)-Number(b.topic)||a.id.localeCompare(b.id,undefined,{numeric:true}))};
 }
 async function useRows(bytes,ann){const d=catalogFor(await checkedRows(bytes,ann));datasets[ann]=d;return d;}
 async function ensure(ann) {
  if(datasets[ann])return datasets[ann];
  if(!sourceRequests[ann])sourceRequests[ann]=(async()=>{
   const d=catalogFor(await fetchRows(ann));datasets[ann]=d;return d;
  })().finally(()=>{delete sourceRequests[ann];});
  return sourceRequests[ann];
 }
 const annMatch=(value,ann)=>String(value).toLowerCase().replace(/-/g,'').startsWith(ann.toLowerCase());
 const sameLabel=value=>value?'เหตุการณ์เดียวกัน':'คนละเหตุการณ์';
 function card(a,rank) {
  const item=el('article','','news-card'),info=el('div','','card-copy');
  const button=el('button',a.title||'เปิดอ่านเอกสาร '+a.id,'card-title');button.type='button';button.dataset.doc=a.id;
  item.append(el('span','TOPIC '+a.topic+' / '+String(rank+1).padStart(2,'0'),'eyebrow'),info);
  info.append(button,el('p',a.description.length>133?a.description.slice(0,130)+'…':a.description),el('small',a.id+' · '+a.rows.length+' การกล่าวถึง'));
  item.append(el('span','↗','card-arrow'));return item;
 }
 function render() {
  const ann=$('ann').value, d=datasets[ann], q=terms($('query').value), topic=$('topic').value;
  if(!d)return;
  const results=d.articles.filter(a=>(!topic||a.topic===topic)&&q.every(word=>a.search.includes(word)));
  const recommendations=!viewAll&&!topic&&!q.length;
  let display=results;
  if(recommendations){
   const top=suggested.map(id=>d.byDoc.get(id)).filter(Boolean);
   const representatives=[...new Map(results.slice().reverse().map(a=>[a.topic,a])).values()].reverse();
   display=[...new Map([...top,...representatives].map(a=>[a.id,a])).values()].slice(0,6);
  }
  $('listing-title').textContent=recommendations?'ข่าวแนะนำ':q.length?'ผลการค้นหา':'ข่าวทั้งหมด';
  $('browse-all').hidden=!recommendations;
  $('more-news').hidden=recommendations||display.length<=listLimit;
  $('news-status').textContent='ECB+ '+ann+' dev · '+d.articles.length+' เอกสารในชุด'+(recommendations?'':' · พบ '+results.length+' เอกสาร')+'.';
  $('news-grid').replaceChildren(...display.slice(0,listLimit).map(card));
  if(!display.length)$('news-grid').append(el('p','ไม่พบข่าว ลองใช้คำสั้นลงหรือเลือกทุกหัวข้อ'));
 }
 async function selectDataset(topic='') {
  const ann=$('ann').value;$('source-recovery').hidden=true;$('manual-source').href=source(ann);
  if(!datasets[ann]){
   $('news-status').textContent='กำลังอ่านดัชนีข่าวต้นทาง '+ann+'…';
   $('news-grid').replaceChildren();$('more-news').hidden=true;
  }
  try {
   const d=await ensure(ann);
   if(ann!==$('ann').value)return;
   const valid=[...new Set(d.articles.map(x=>x.topic))];
   $('topic').replaceChildren(new Option('ทุกหัวข้อ',''),...valid.map(x=>new Option('Topic '+x,x)));
   $('topic').value=valid.includes(topic)?topic:'';
   render();
   if(!activeArticle && /^#doc=/.test(location.hash)){
    const id=decodeURIComponent(location.hash.slice(5));
    if(d.byDoc.has(id))openArticle(id,null);
   }
  } catch {
   if(ann!==$('ann').value)return;
   $('news-status').textContent='เปิดดัชนีข่าวต้นทางไม่ได้จากเครือข่ายนี้';
   $('source-recovery').hidden=false;
  }
 }
 function makeEvidence(doc,mention) {
  const article=el('section','','article-pane');article.append(el('div','TOPIC '+doc.topic+' / '+doc.id,'eyebrow'));
  article.append(el('h3',doc.title||'เนื้อหาข่าวจาก ECB+'));
  if(mention) {
   const note=el('div','','annotation');
   note.append(el('strong','การกล่าวถึงที่ใช้เทียบ'),el('p',removeMarkup(mention.text)),el('small',mention.mention_id+(mention.argT?' · วันที่ตามคำกำกับ: '+mention.argT:'')));
   article.append(note);
  }
  const text=el('div','','article-text');
  const lines=mention?.marked_doc ? paragraphs(mention.marked_doc).filter(x=>!urlLine(x)) : doc.text;
  for(const line of lines){
   const p=el('p');
   for(const [i,s] of line.split(/<\/?mark\b[^>]*>/gi).entries())p.append(mention&&i%2?el('mark',s):document.createTextNode(s));
   text.append(p);
  }
  if(!doc.text.length)text.append(el('p','ชุดคำกำกับไม่มีเนื้อหาข่าวฉบับยาวสำหรับเอกสารนี้'));
  article.append(text);
  if(doc.text[0])article.append(el('p','ข้อความภาษาอังกฤษมาจากฉบับที่อยู่ในชุด ECB+ อาจไม่ครบเหมือนหน้าเว็บสำนักข่าว','annotation'));
  return article;
 }
 const storageKey='xamr-news-audit-v1';
 const readReviews=()=>{try{return JSON.parse(localStorage.getItem(storageKey)||'{}')||{};}catch{return {};}};
 function saveReviews(items){try{localStorage.setItem(storageKey,JSON.stringify(items));return true;}catch{return false;}}
 function nearby(doc,ann) {
  return (annotations?.pairs||[]).filter(p=>annMatch(p.ann,ann)&&p.mentions.some(m=>m.doc===doc.id));
 }
 function exportReviews() {
  const reviews=readReviews();
  const blob=new Blob([JSON.stringify({scope:'ECB+ dev; reviewer decisions saved in this browser',reviews},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='xamr-news-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function configureComparison(mount,doc,d,ann,pairs){
  mount.append(el('h3','เทียบการจัดกลุ่ม'));
  const randomLink=el('a','สุ่มจากทุกคู่ข้ามข่าวในหัวข้อนี้ →');randomLink.href='/audit-review?'+new URLSearchParams({ann:ann.toLowerCase(),topic:doc.topic});
  mount.append(el('p','คู่ในรายการนี้คัดไว้เป็นตัวอย่าง'),randomLink);
  if(!pairs.length){mount.append(el('p',annotations?'เอกสารนี้ยังไม่มีคู่ในชุดตรวจที่เตรียมไว้ แต่ยังอ่านและค้นข่าวได้':'ยังโหลดชุดเปรียบเทียบไม่สำเร็จ'),el('p','เลือกข่าวแนะนำ เช่น Vincent Jackson หรือ Jamal Williams เพื่อดูตัวอย่าง'));return;}
  const choose=el('select');choose.setAttribute('aria-label','เลือกข่าวอีกชิ้นเพื่อเปรียบเทียบ');choose.append(new Option('เลือกข่าวที่ต้องการเทียบ',''));
  for(const pair of pairs){const other=pair.mentions.find(m=>m.doc!==doc.id);if(!other)continue;const article=d.byDoc.get(other.doc);choose.append(new Option(article?.title||other.doc,String(pair.id)));}
  const controls=el('div','','filter-row');controls.append(choose);
  const outcome=el('div');mount.append(el('p','เลือกคู่แล้วอ่านทั้งสองฝั่ง ก่อนเปิดดูเฉลย ECB+ และผลของโมเดล'),controls,outcome);
  function display(){
   selected=choose.value;outcome.replaceChildren();if(!selected)return;
   const pair=pairs.find(p=>String(p.id)===selected);if(!pair)return;
   const here=pair.mentions.find(x=>x.doc===doc.id),other=pair.mentions.find(x=>x.doc!==doc.id);
   const a=d.byDoc.get(here?.doc),b=d.byDoc.get(other?.doc);
   if(!a||!b){outcome.append(el('p','ยังไม่พบเอกสารสองชิ้นในต้นฉบับ'));return;}
   const evidence=el('div','','article-shell');evidence.append(makeEvidence(a,d.byId.get(here.id)),makeEvidence(b,d.byId.get(other.id)));
   const actions=el('div','','review-actions'),label=el('label','ความเห็นของคนอ่าน '),review=el('select');
   review.setAttribute('aria-label','ความเห็นของคนอ่าน');review.append(new Option('ยังไม่ตัดสิน',''),new Option('เหตุการณ์เดียวกัน','same'),new Option('คนละเหตุการณ์','different'),new Option('หลักฐานไม่พอ','unclear'));label.append(review);
   const items=readReviews();review.value=items[selected]?.decision||'';
   const memo=el('textarea');memo.maxLength=500;memo.setAttribute('aria-label','เหตุผลสั้น ๆ');memo.placeholder='เหตุผลสั้น ๆ เช่น คนละผู้ถูกจับ';memo.value=items[selected]?.reason||'';
   const save=el('button','บันทึกในเครื่อง'), reveal=el('button','เปิดผลระบบ'), exp=el('button','ส่งออกบันทึก'), status=el('p','','status');status.setAttribute('aria-live','polite');
   for(const x of [save,reveal,exp])x.type='button';
   save.addEventListener('click',()=>{if(!review.value){status.textContent='เลือกความเห็นก่อนนะ';return;}const r=readReviews();r[selected]={ann,topic:doc.topic,docs:[a.id,b.id],decision:review.value,reason:memo.value.trim()};status.textContent=saveReviews(r)?'บันทึกในเบราว์เซอร์นี้แล้ว':'บันทึกไม่ได้ เบราว์เซอร์อาจปิดการจัดเก็บ';});
   const models=el('dl','','model-results');models.hidden=true;
   for(const [k,v] of [['เฉลย ECB+',pair.goldSame],['OR',pair.orSame],['OR + TF-IDF',pair.hybridSame]]){models.append(el('dt',k),el('dd',typeof v==='boolean'?sameLabel(v):'ไม่มีผล'));}
   reveal.addEventListener('click',()=>{models.hidden=!models.hidden;reveal.textContent=models.hidden?'เปิดผลระบบ':'ซ่อนผลระบบ';});
   exp.addEventListener('click',exportReviews);
   actions.append(label,memo,save,reveal,exp);outcome.append(evidence,actions,status,models);
  }
  choose.addEventListener('change',display);
 }
 function openArticle(id,trigger) {
  const ann=$('ann').value,d=datasets[ann],doc=d?.byDoc.get(id);if(!doc)return;
  activeArticle=id;lastTrigger=trigger;lastHash=location.hash;
  const body=$('article-body'),head=el('h2',doc.title||'อ่านเอกสาร '+doc.id);head.id='article-title';
  const evidence=el('div','','article-shell'), compare=el('section');compare.id='compare-panel';
  evidence.append(makeEvidence(doc));body.replaceChildren(head,evidence,compare);
  configureComparison(compare,doc,d,ann,nearby(doc,ann));
  if(!$('article').open)$('article').showModal();
  $('close-article').focus();
 }
 $('news-grid').addEventListener('click',e=>{const b=e.target.closest?.('[data-doc]');if(b)openArticle(b.dataset.doc,b);});
 $('close-article').addEventListener('click',()=>$('article').close());
 $('article').addEventListener('close',()=>{activeArticle=null;selected='';lastTrigger?.focus();lastHash=null;});
 $('search-form').addEventListener('submit',e=>{e.preventDefault();listLimit=12;viewAll=!!$('query').value.trim();render();});
 $('query').addEventListener('input',()=>{listLimit=12;viewAll=!!$('query').value.trim();render();});
 $('topic').addEventListener('change',()=>{listLimit=12;render();});
 $('ann').addEventListener('change',()=>{listLimit=12;selectDataset($('topic').value);});
 $('clear-filters').addEventListener('click',()=>{$('query').value='';$('topic').value='';listLimit=12;viewAll=false;render();});
 $('browse-all').addEventListener('click',e=>{e.preventDefault();viewAll=true;render();$('listing-title').scrollIntoView({block:'start'});});
 $('more-news').addEventListener('click',()=>{listLimit+=12;render();});
 $('retry-source').addEventListener('click',()=>selectDataset());
 $('source-file').addEventListener('change',async e=>{
  const file=e.target.files[0],ann=$('ann').value;if(!file)return;
  try{if(file.size>14e6)throw Error('oversize');await useRows(await file.arrayBuffer(),ann);if($('ann').value===ann)await selectDataset();}
  catch{$('news-status').textContent='ไฟล์ไม่ตรงกับเวอร์ชัน '+ann+' dev กรุณาใช้ไฟล์ที่ลิงก์ต้นทาง';}
  finally{e.target.value='';}
 });
 fetch('/audit-data.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(value=>{annotations=value;if(activeArticle){const current=activeArticle;openArticle(current,lastTrigger);}}).catch(()=>null);
 const params=new URLSearchParams(location.search);
 if(params.get('ann')==='Ann2')$('ann').value='Ann2';
 if(params.has('topic')){viewAll=true;selectDataset(params.get('topic'));}
 else selectDataset();
})();
