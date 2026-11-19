'use strict';
const SOURCE='https://github.com/Micosz/company-news-nlp-workbench/blob/598ea06926df664d439fc1e9f082ac30ec1f0d55/docs/';
const groups=[
{name:'Introduction',thai:'ปัญหาและขอบเขต',x:54,y:248},
{name:'Approach',thai:'วิธีที่นำมาศึกษา',x:1270,y:248},
{name:'Data & Methods',thai:'ข้อมูลและการทดลอง',x:54,y:950},
{name:'Results & Wrap',thai:'ผลที่พบและข้อสรุป',x:1270,y:950}
];
const panel=(title,body)=>'<div class="panel"><h3>'+title+'</h3>'+body+'</div>';
const p=t=>'<p>'+t+'</p>';
const call=t=>'<div class="callout">'+t+'</div>';
const flow=items=>'<div class="flow">'+items.map((t,i)=>(i?'<span class="arrow">→</span>':'')+'<div class="box">'+t+'</div>').join('')+'</div>';
const compare=rows=>'<div class="compare"><span></span><b>proposal</b><span></span><b class="accent">งานที่ทำจริง</b>'+rows.map(r=>'<span class="rowname">'+r[0]+'</span><div class="was">'+r[1]+'</div><span class="arrow">→</span><div class="now">'+r[2]+'</div>').join('')+'</div>';
function eventMotion(separate){return '<div class="eventmotion '+(separate?'separate':'together')+'" role="img" aria-label="'+(separate?'การกล่าวถึง A และ B เคลื่อนแยกเป็นสองกลุ่ม':'การกล่าวถึง A B และ C เคลื่อนรวมเป็นกลุ่มเดียว')+'"><span class="eventhalo one"></span>'+(separate?'<span class="eventhalo two"></span>':'')+'<span class="mention ma">A</span><span class="mention mb">B</span>'+(separate?'':'<span class="mention mc">C</span>')+'</div>';}
const resultRows=[['OR',79.77,71.89,77.12,68.44],['OR + Temporal',79.86,74.57,72.37,62.19],['TF-IDF',52.78,13.54,52.78,13.54],['OR + TF-IDF',79.07,68.00,77.43,65.07],['OR + NB',79.77,71.89,77.12,68.44]];
function resultChart(){return '<div class="resultlegend"><span><i></i>CoNLL F1</span><span><i></i>Pair F1</span><span>คะแนน F1 (%) บน dev</span></div><div class="resultcharts">'+[0,1].map(a=>'<section class="resultpanel"><h3>Ann'+(a+1)+'</h3><div class="resultaxis"><span>0</span><span>50</span><span>100</span></div>'+resultRows.map((r,i)=>'<div class="resultrow '+(i===0?'baseline':'')+'"><div class="resultname">'+r[0]+(i===1?' <small>tolerance 0 วัน</small>':i===2?' <small>อย่างเดียว</small>':i===4?' <small>เลือกไม่ตัดเส้น</small>':'')+'</div><div class="resultbars">'+[0,1].map(m=>'<div class="resultbar '+(m?'pair':'')+'"><span style="width:'+r[1+a*2+m]+'%"></span><b>'+r[1+a*2+m].toFixed(2)+'</b></div>').join('')+'</div></div>').join('')+'</section>').join('')+'</div>';}
const members=[['ปพนพัชร์ มีวน','6709650458'],['ชนกานต์ คงรัชตภิญโญ','6709650235']];
function titleSlide(){return '<div class="titlecopy"><h1><span>การศึกษากฎเวลาและสัญญาณข้อความ</span><span>สำหรับการจัดกลุ่มเหตุการณ์ข้ามเอกสาร</span><span class="accent">บนฐาน X-AMR</span></h1><p class="titleen">Temporal rules and text signals for cross-document event coreference with X-AMR</p><div class="memberlist">'+members.map(m=>'<div><span>'+m[0]+'</span><span>'+m[1]+'</span></div>').join('')+'</div><p class="course">โครงงานวิชา CS374</p></div><div class="paper-art" aria-hidden="true"><svg viewBox="0 0 360 440"><ellipse class="paper-ground" cx="181" cy="388" rx="142" ry="12"/><g class="paper-orbit"><circle cx="180" cy="210" r="159"/><circle cx="180" cy="51" r="7" class="orbit-dot"/><circle cx="180" cy="369" r="5" class="orbit-dot"/></g><g class="document-back"><path class="paper-sheet" d="M173 106Q173 96 184 96H271L306 134V324Q306 335 295 335H185Q173 335 173 324Z"/><path class="paper-fold" d="M271 96V134H306"/><path class="paper-line" d="M193 158H278M193 169H262M193 281H279M193 291H265M193 302H279"/><circle class="paper-eye" cx="212" cy="211" r="13"/><circle class="paper-eye" cx="263" cy="211" r="13"/><g class="paper-pupils"><circle cx="208" cy="212" r="4"/><circle cx="259" cy="212" r="4"/></g><path class="paper-smile" d="M223 242Q238 254 253 240"/></g><g class="document-front"><path class="paper-sheet" d="M47 148Q47 138 58 138H147L180 175V352Q180 364 168 364H58Q47 364 47 352Z"/><path class="paper-fold" d="M147 138V175H180"/><rect class="paper-heading" x="65" y="195" width="66" height="8" rx="4"/><path class="paper-line" d="M65 215H160M65 226H142M65 317H158M65 329H143"/><circle class="paper-eye" cx="87" cy="263" r="13"/><circle class="paper-eye" cx="137" cy="263" r="13"/><g class="paper-pupils"><circle cx="91" cy="262" r="4"/><circle cx="141" cy="262" r="4"/></g><path class="paper-smile" d="M98 291Q113 304 127 289"/></g><g class="paper-link"><path d="M127 101Q147 72 170 89"/><path d="M158 79L170 89L156 92"/><path d="M203 358Q221 382 246 361"/><path d="M234 361L246 361L244 374"/></g></svg></div>';}
const sigRows=[['Ann1','Pair F1',-3.89,-11.17,0.20,'0.56'],['Ann1','B³ F1',-1.32,-4.54,0.17,'0.50'],['Ann2','Pair F1',-3.37,-9.23,1.02,'0.59'],['Ann2','B³ F1',-0.68,-2.98,0.37,'0.69']];
function forest(){const x=v=>((v+12)/16*100).toFixed(2)+'%';const fmt=v=>(v>0?'+':v<0?'−':'')+Math.abs(v).toFixed(2);return '<div class="forest"><div class="forestaxis"><span></span><div class="foresttrack">'+[-10,-5,0].map(t=>'<span style="left:'+x(t)+'">'+(t?'−'+(-t):'0')+'</span>').join('')+'</div><span>ต่างจาก OR</span><span>p</span></div>'+sigRows.map(r=>'<div class="forestrow"><span class="forestname">'+r[0]+' <em>'+r[1]+'</em></span><div class="foresttrack"><i class="zero" style="left:'+x(0)+'"></i><i class="ci" style="left:'+x(r[3])+';width:calc('+x(r[4])+' - '+x(r[3])+')"></i><i class="point" style="left:'+x(r[2])+'"></i></div><span class="forestnum">'+fmt(r[2])+'<small>['+fmt(r[3])+', '+fmt(r[4])+']</small></span><span class="forestp">'+r[5]+'</span></div>').join('')+'</div>';}
const dateRows=[['Ann1 dev',1032,1032],['Ann2 dev',1244,1244],['Ann2 train',0,3194],['Ann2 test_common',0,787]];
const coverage=()=>'<div class="coverage">'+dateRows.map(r=>'<div class="covrow'+(r[1]?'':' none')+'"><span>'+r[0]+'</span><div class="covtrack"><i style="width:'+(r[1]/r[2]*100)+'%"></i></div><b>'+r[1].toLocaleString('en-US')+' / '+r[2].toLocaleString('en-US')+'</b></div>').join('')+'</div>';
const slides=[
{g:0,cover:true,title:"การศึกษากฎเวลาและสัญญาณข้อความสำหรับการจัดกลุ่มเหตุการณ์ข้ามเอกสารบนฐาน X-AMR",body:titleSlide(),note:'สวัสดีครับ โครงงานของเราศึกษาว่ากฎด้านเวลาและความคล้ายของข้อความช่วยจัดกลุ่มข่าวที่พูดถึงเหตุการณ์เดียวกันได้แค่ไหน โดยต่อยอดจาก X-AMR ผู้นำเสนอคือปพนพัชร์ มีวน และชนกานต์ คงรัชตภิญโญ ครับ',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:0,title:"โจทย์และวัตถุประสงค์ของโครงงาน",sub:"ศึกษาการจัดกลุ่มเหตุการณ์ข้ามเอกสารด้วย X-AMR และประเมินแนวทางเสริมด้านเวลา ข้อความ และ Naive Bayes",
body:'<div class="cols">'+panel('โจทย์การศึกษา','<div class="lede">การระบุและจัดกลุ่ม<br><span class="accent">เหตุการณ์เดียวกัน</span><br>ที่กล่าวถึงในหลายเอกสาร</div>')+panel('วัตถุประสงค์','<ol class="goals"><li>เปรียบเทียบ OR กับแนวทางเสริมด้านเวลา ข้อความ และ NB</li><li>ประเมินผลบนคำกำกับสองเวอร์ชันและวิเคราะห์ข้อผิดพลาด</li><li>ทดสอบว่าผลต่างแยกจากความบังเอิญได้หรือไม่</li><li>พัฒนาเครื่องมือทดลองและตรวจสอบผลย้อนกลับ</li></ol>')+'</div>',note:'โครงงานนี้ศึกษาการจัดกลุ่มการกล่าวถึงเหตุการณ์เดียวกันข้ามเอกสาร โดยใช้ X-AMR เป็นฐาน แล้วทดลองเพิ่มข้อมูลเวลา ความคล้ายคลึงข้อความ และ Naive Bayes ครับ การนำเสนอจะเล่าทั้งสิ่งที่พัฒนา ผลที่ได้ และข้อจำกัด โดยไม่ได้ตั้งต้นว่าทุกวิธีที่เพิ่มต้องดีกว่าเดิม',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:0,title:"ปัญหาการจัดกลุ่มเหตุการณ์ข้ามเอกสาร",sub:"การระบุเหตุการณ์เดียวกันต้องแยกความคล้ายคลึงของข้อความออกจากความเป็นเหตุการณ์เดียวกัน",
body:'<div class="cols">'+panel('ตัวอย่างสมมติ: เหตุการณ์เดียวกัน',eventMotion(false)+'<div class="caption">ข่าว A · B · C รายงานการปรับบริษัทครั้งเดียวกัน<br><strong>รวมเป็น 1 กลุ่มเหตุการณ์</strong></div>')+panel('ตัวอย่างสมมติ: คนละเหตุการณ์',eventMotion(true)+'<div class="caption">ข่าว A และ B กล่าวถึงการปรับบริษัทคนละครั้ง<br><strong>แยกเป็น 2 กลุ่มเหตุการณ์</strong></div>')+'</div>'+call('ภาพสมมติ ไม่ใช่ผลโมเดล · แต่ละจุดแทนการกล่าวถึงเหตุการณ์ในข่าว'),note:'ตัวอย่างนี้เป็นสถานการณ์สมมติสำหรับอธิบายปัญหาครับ หลายข่าวอาจรายงานการปรับบริษัทครั้งเดียวกัน จึงควรอยู่กลุ่มเดียว แต่ถ้าบริษัทเดิมถูกปรับอีกครั้ง แม้ชื่อและคำในข่าวจะคล้ายกัน ก็ควรแยกเหตุการณ์ ความยากคือทั้งการรวมผิดและการแยกผิดล้วนเกิดได้',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:0,title:"ขอบเขตการศึกษาและงานวิจัยอ้างอิง",sub:"ศึกษาการจัดกลุ่มจากคำกำกับเหตุการณ์ โดยใช้ X-AMR เป็นฐานและ CohTP เป็นแนวคิดอ้างอิงด้านเวลา",
body:flow(['คำกำกับเหตุการณ์<small>roleset · arguments · time</small>','สร้างเส้นเชื่อม<small>วิธีอ้างอิงและกฎเสริม</small>','กลุ่มเหตุการณ์<small>เทียบคำตอบอ้างอิง</small>'])+'<div class="cols">'+panel('X-AMR เป็นฐานทดลอง',p('ใช้โค้ดและ semantic annotations ที่ผู้เขียนเผยแพร่')+p('OR เป็นการรวมกราฟ ไม่ใช่ neural network'))+panel('CohTP เป็นแรงบันดาลใจ',p('ศึกษาความสอดคล้องของเวลา แต่ไม่ได้ทำซ้ำระบบ NLI / GNN ของผู้เขียนทั้งชุด'))+'</div>',note:'การทดลองเริ่มจากคำกำกับที่มีอยู่แล้ว ไม่ได้ประเมินการรับข่าวดิบแล้วสกัดเหตุการณ์จนจบครับ เราเลือก X-AMR เพราะมีโค้ดและข้อมูลให้ตรวจสอบ ส่วน CohTP ใช้เป็นแรงบันดาลใจเรื่องเวลา ไม่ใช่การอ้างว่าทำซ้ำระบบของผู้เขียนทั้งหมด',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:0,title:"สิ่งที่เปลี่ยนไปจาก proposal",body:compare([
['งานวิจัยที่ใช้เป็นฐาน','CohTP (ACL 2026)','X-AMR (LREC-COLING 2024)<small>repository ของ CohTP มีแค่ placeholder ส่วน X-AMR มีโค้ดและคำกำกับให้รันเทียบได้</small>'],
['สิ่งที่ระบบตัดสิน','จำแนกทีละคู่ข่าว','จัด mention ทั้งหมดเป็นกลุ่มเหตุการณ์'],
['ข้อมูลเวลา','วันที่จาก Event StoryLine','argT ในคำกำกับ และตรวจเวลาก่อนรวมกลุ่ม'],
['บทบาทของ TF-IDF และ NB','NB จำแนกคู่จาก cosine และข้อมูลเวลา','TF-IDF เติมเส้น และ NB เลือกตัดเส้นในกราฟ OR'],
['การวัดผล','Precision, Recall, F1 ของคู่','CoNLL F1, Pair F1, FP และ FN']
])+call('คำถามเดิมยังอยู่: เวลาและความคล้ายของข้อความช่วยแยกเหตุการณ์ที่คล้ายกันได้แค่ไหน'),note:'จาก proposal ที่ส่งไป มีสามเรื่องหลักที่เปลี่ยนครับ อย่างแรกคือฐานงาน เราตั้งใจต่อยอด CohTP แต่ตอนเริ่มทำ repository ของผู้เขียนมีแค่ placeholder จึงเปลี่ยนมาใช้ X-AMR ซึ่งมีโค้ดและคำกำกับให้รันเทียบได้ อย่างที่สองคือหน่วยที่ตัดสิน จากเดิมที่จำแนกทีละคู่ข่าว เปลี่ยนเป็นจัดกลุ่มเหตุการณ์ทั้งกลุ่ม ซึ่งตรงกับการวัดผลมาตรฐานของงานนี้ อย่างที่สามคือข้อมูลเวลาใช้จากคำกำกับของ X-AMR แทน Event StoryLine แต่คำถามหลักยังเหมือนเดิม คือเวลาและความคล้ายของข้อความช่วยแยกเหตุการณ์ได้แค่ไหน',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:1,title:"วิธีอ้างอิง OR",sub:"รวมเส้นเชื่อมจาก EID_N และ EID_lt แล้วจัดกลุ่มด้วย connected components",
body:'<div class="cols">'+panel('EID_N · โครงสร้างและบทบาท',p('สร้างรหัสจาก ARG0 + ประเภทเหตุการณ์ + ARG1')+p('ถ้า ARG1 เป็นเหตุการณ์ซ้อน จะคลี่โซ่เหตุการณ์นั้นด้วย')+p('เชื่อมคู่ที่มีรหัสร่วมกันอย่างน้อยหนึ่งรหัส'))+panel('EID_lt · สถานที่และเวลา',p('สร้างรหัสจาก topic + ARG0 + ประเภทเหตุการณ์ + สถานที่ + เวลา')+p('เชื่อมคู่ที่มีรหัสตรงกัน')+p('ใช้เวลาในรหัส ไม่ใช่กฎตรวจระยะห่างของวัน'))+'</div>'+flow(['เส้น EID_N ∪ เส้น EID_lt','กราฟเหตุการณ์','กลุ่มที่เชื่อมถึงกัน'])+call('Ann1 และ Ann2 เป็นคำกำกับสองเวอร์ชัน แต่ละเวอร์ชันใช้ทั้ง EID_N และ EID_lt แล้วรวมเส้นเชื่อมเป็น OR<br>สมมติ: “บริษัท A ซื้อบริษัท B” → ARG0 = A · ประเภท = ซื้อ · ARG1 = B<br>รหัสตรงกันจึงเกิดเส้นตามกฎ ไม่ได้ยืนยันว่าเป็นเหตุการณ์เดียวกันแน่นอน'),note:'baseline OR รวมเส้นจาก EID_N กับ EID_lt แล้วหา connected components ครับ เวลาไม่ได้เพิ่งถูกใส่ครั้งแรกในวิธีใหม่ เพราะ EID_lt ใช้เวลาอยู่แล้ว สิ่งที่เพิ่มคือการตรวจความขัดแย้งก่อนรวมกลุ่ม รอบนี้ปิด syn_map จึงยังไม่ใช่การทำซ้ำทุก setting รวมถึง VerbNet ของ paper',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:1,title:"การตรวจสอบความสอดคล้องของเวลา",sub:"ตรวจช่วงเวลาของคู่ข้ามกลุ่ม และระงับการรวมเมื่อช่วงเวลาห่างเกินค่า tolerance",
body:'<div class="cols">'+panel('กฎที่ทดลอง','<div class="big">0 <span class="day-unit">วัน</span></div>'+p('เวลาไม่ทราบหรือแปลงไม่ได้ ไม่ขวางการรวม')+p('ตรวจทุกคู่ข้ามกลุ่ม ไม่ใช่เฉพาะปลายเส้น'))+panel('ข้อจำกัดของข้อมูลเวลา',p('วันเผยแพร่ข่าวอาจไม่ใช่วันเกิดเหตุ')+p('หลักฐานวันที่ของสมาชิกหนึ่งตัว อาจขวางทั้งกลุ่ม')+p('กฎเข้มขึ้นอาจลดการรวมผิด แต่เพิ่มการแยกผิด'))+'</div>',note:'Temporal เริ่มจาก OR เดิม แล้วตรวจคู่ข้ามกลุ่มก่อนรวมครับ ในผลหลักใช้ tolerance ศูนย์วัน ถ้าไม่มีเวลาที่อ่านได้ก็ไม่ขวางการรวม จุดเสี่ยงคือวันเผยแพร่ไม่ใช่วันเกิดเหตุเสมอไป และกฎระดับกลุ่มทำให้สมาชิกเพียงตัวเดียวส่งผลต่อการรวมของสมาชิกอื่นได้ด้วย',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:1,title:"การจัดกลุ่มและการเสริมกราฟด้วย TF-IDF",sub:"เปรียบเทียบการจัดกลุ่มด้วย TF-IDF เพียงอย่างเดียวกับการเพิ่มเส้นเชื่อมในกราฟ OR",
body:'<div class="cols">'+panel('TF-IDF standalone',p('word 1–2 grams → cosine similarity')+p('พิจารณาคู่ข้ามเอกสารภายใน topic')+'<div class="big">≥ 0.50</div>')+panel('OR + TF-IDF',p('เติมเส้นระหว่างกลุ่มแบบ unique mutual-best หนึ่งรอบ')+p('roleset ต้องตรงและไม่ว่าง')+p('ARG0 หรือ ARG1 อย่างน้อยหนึ่งบทบาทต้องตรงและไม่ว่าง'))+'</div>'+call('เกณฑ์ 0.50 เลือกด้วย train CV แล้วตรึงก่อนประเมิน dev'),note:'เราแยก TF-IDF อย่างเดียวกับแบบเสริม OR ครับ แบบเสริมไม่ได้เชื่อมทุกคู่ที่คล้ายกัน แต่เลือกกลุ่มที่เป็นคู่ที่ดีที่สุดซึ่งกันและกัน และต้องมีหลักฐานบทบาทตรงกันด้วย อย่างไรก็ตาม ข้อความของคนละเหตุการณ์อาจคล้ายกันมาก จึงต้องตรวจทั้งคะแนนและ false merges',source:'XAMR_TFIDF_ONLY_TH.md'},
{g:1,title:"การกรองเส้นเชื่อมด้วย Naive Bayes",sub:"จัดอันดับเส้น EID_lt-only ข้ามเอกสารในกราฟ OR เดิม โดยใช้ TF-IDF cosine เป็นฟีเจอร์",
body:flow(['กราฟ OR เดิม','เส้น EID_lt-only<small>เฉพาะคู่ข้ามเอกสารที่เข้าเงื่อนไข</small>','NB จัดอันดับ<small>cosine deciles</small>'])+'<div class="cols">'+panel('ตัวเลือกที่เปรียบเทียบ',p('ไม่ตัดเส้น · ตัด 10% · ตัด 25%')+p('CategoricalNB, alpha = 1, balanced prior'))+panel('ผลการเลือกจาก train CV','<div class="big">0%</div>'+p('ทั้ง Ann1 และ Ann2 เลือกไม่ตัดเส้น จึงเท่า OR โดยตั้งใจ'))+'</div>',note:'Naive Bayes รอบนี้เป็น guard ของกราฟ OR เดิม โดยจัดอันดับเฉพาะเส้น EID_lt-only ข้ามเอกสารที่อ่อนครับ CV เปรียบเทียบการไม่ตัดกับตัดสิบและยี่สิบห้าเปอร์เซ็นต์ สุดท้ายเลือกไม่ตัดทั้งสองเวอร์ชัน ผลเท่า OR จึงเป็น no-op ที่ถูกเลือก ไม่ใช่หลักฐานว่า NB เพิ่มคะแนน ชื่อเมนูบนเว็บอาจยาว แต่ไม่ได้หมายถึง TF-IDF เติมเส้นแล้ว NB กรองต่อ',source:'XAMR_OR_NB_HYBRID_TH.md'},
{g:2,title:"ชุดข้อมูลและคำกำกับเหตุการณ์",sub:"ใช้คำกำกับ Ann1 และ Ann2 บน ECB+ เดียวกัน โดยตรึงเวอร์ชันข้อมูลและตรวจสอบ checksum",
body:'<div class="cols">'+panel('ข้อมูลประเมิน dev','<div class="big">1,245</div>'+p('mentions ต่อเวอร์ชัน')+p('196 เอกสาร · 8 topics'))+panel('ความสัมพันธ์ระหว่าง Ann1 และ Ann2',p('คำกำกับเชิงความหมายสองเวอร์ชันบน corpus เดียวกัน')+p('เทียบวิธีบน mentions ชุดเดียวกันภายในแต่ละเวอร์ชัน')+p('ไม่ใช่สองชุด gold clustering ที่เป็นอิสระ'))+'</div>'+call('การเก็บ corpus ข่าวบริษัทเพิ่มเติมถูกหยุดไว้ และไม่รวมเป็น benchmark หลัก'),note:'Ann1 และ Ann2 ไม่ใช่สอง datasets อิสระครับ เป็น semantic inputs สองเวอร์ชันบน ECB+ เดียวกัน Dev มีหนึ่งพันสองร้อยสี่สิบห้า mentions ต่อเวอร์ชัน การประเมินวิธีต่าง ๆ ใช้ gold เดิม ไม่แก้คำตอบให้เข้ากับวิธี ส่วน corpus ข่าวบริษัทที่เคยสำรวจไม่ได้รวมเป็น benchmark หลัก',source:'WEBSITE_RELEASE_2026-11-16.md'},
{g:2,title:"การออกแบบการทดลองและการเลือกค่าพารามิเตอร์",sub:"เลือกค่าของ TF-IDF และ NB ด้วย 5-fold CV แบ่งตาม topic บน train แล้วตรึงก่อนประเมิน dev",
body:flow(['TRAIN<small>topic-grouped CV</small>','FREEZE<small>model · threshold · policy</small>','DEV<small>เปรียบเทียบผล</small>'])+'<div class="cols">'+panel('การควบคุมการทดลอง',p('ใช้ OR เป็น control ทุกการเปรียบเทียบ')+p('online inference ไม่ fit โมเดลใหม่จากชุดประเมิน'))+panel('ข้อจำกัดที่ต้องเปิดเผย',p('dev ผ่านการสำรวจหลายรอบแล้ว')+p('test_common เคยเปิดดูผล และเป็นเพียง subset ไม่ใช่ untouched final test'))+'</div>',note:'TF-IDF และ NB เลือกค่าจาก train ด้วยห้า folds แบ่งตาม topic และ fit เฉพาะข้อมูลของแต่ละ fold ครับ จากนั้นตรึงค่าก่อนประเมิน dev แต่ต้องบอกตรง ๆ ว่า dev ผ่านการสำรวจมาหลายรอบ และ test_common เคยเปิดดูแล้ว จึงยังไม่ใช่ผลจากชุดทดสอบสุดท้ายที่ไม่เคยเห็น ห้า folds ไม่ใช่ห้า random seeds',source:'WEBSITE_RELEASE_2026-11-16.md'},
{g:2,title:"เกณฑ์การประเมินผล",sub:"ประเมินคุณภาพกลุ่มด้วย CoNLL F1 และประเมินคู่เหตุการณ์ด้วย Pair F1, FP และ FN",
body:'<div class="cols three">'+panel('CoNLL F1',p('ค่าเฉลี่ย MUC, B³ และ CEAF_e')+p('มองคุณภาพการจัดกลุ่ม'))+panel('Pair F1',p('สมดุล precision / recall ของคู่ที่อยู่เหตุการณ์เดียวกัน')+p('ช่วยมองผลกระทบระดับคู่'))+panel('FP / FN',p('FP: คนละเหตุการณ์แต่รวมกัน')+p('FN: เหตุเดียวกันแต่แยกกัน'))+'</div>'+call('เส้นเชื่อม 1 เส้น อาจทำให้สมาชิกทั้งสองกลุ่มเปลี่ยนผลหลายคู่'),note:'เราใช้ CoNLL F1 เพื่อดูคุณภาพกลุ่ม และ Pair F1 รวมถึง FP FN เพื่อดูข้อผิดพลาดรายคู่ครับ เวลาสองกลุ่มถูกเชื่อมด้วยเส้นเดียว ผลอาจเปลี่ยนหลายคู่พร้อมกัน ดังนั้นจำนวนเส้นที่เติมจึงไม่เท่ากับจำนวนคู่ที่แก้ถูกหรือทำให้ผิด',source:'WEBSITE_RELEASE_2026-11-16.md'},
{g:3,title:"ผลการทดลองเปรียบเทียบ",sub:"เปรียบเทียบ CoNLL F1 / Pair F1 (%) บน dev ที่ผ่านการสำรวจแล้ว ไม่ใช่ held-out final test",
body:resultChart()+call('OR + TF-IDF เพิ่ม CoNLL F1 ของ Ann2 เล็กน้อย แต่ลด Pair F1 ทั้งสองเวอร์ชัน'),note:'กราฟนี้แสดงสองตัวชี้วัดคู่กันบนแกนศูนย์ถึงหนึ่งร้อยครับ Temporal เพิ่มคะแนนบน Ann1 แต่ลดลงมากบน Ann2 ส่วน OR บวก TF-IDF ทำให้ CoNLL ของ Ann2 เพิ่มเล็กน้อย แต่ Pair F1 ลดทั้งสองเวอร์ชัน NB guard ที่เลือกเท่า OR เพราะไม่ตัดเส้น เราจึงยังไม่อ้างว่าแนวทางเสริมเหนือกว่า baseline อย่างสม่ำเสมอ หน้าถัดไปจะดูว่าผลต่างระดับนี้แยกออกจากความบังเอิญได้หรือไม่',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:3,title:"ผลต่างนี้แยกออกจากความบังเอิญได้ไหม",body:'<div class="cols sig">'+panel('OR + TF-IDF เทียบกับ OR',forest()+'<p class="sigread">จุดคือผลต่างจริง เส้นคือช่วงความเชื่อมั่น 95% ทุกเส้นข้ามศูนย์</p>')+panel('เทียบกับ TF-IDF อย่างเดียว','<div class="big">p = 0.0078</div>'+p('Pair F1 ต่ำกว่า OR 58 และ 55 จุด ช่วง 95% ไม่ข้ามศูนย์ทั้งสองชุด')+p('แสดงว่าการทดสอบจับความต่างที่มีจริงได้'))+'</div>'+call('ใช้ topic เป็นหน่วย: สุ่มซ้ำ 1,000 รอบ และสลับผลสองระบบครบ 256 แบบ'),note:'หน้านี้เป็นส่วนที่เราเพิ่มครับ ผลต่างของ OR บวก TF-IDF ราวสามถึงสี่จุด ดูเหมือนแย่ลง แต่ dev มีแค่แปด topic เราจึงทดสอบโดยใช้ topic เป็นหน่วย ทั้ง bootstrap หนึ่งพันรอบ และ permutation ที่สลับผลครบสองร้อยห้าสิบหกแบบ ผลคือช่วงความเชื่อมั่นทุกเส้นข้ามศูนย์ และค่า p อยู่ราวศูนย์จุดห้าถึงศูนย์จุดเจ็ด จึงยังสรุปไม่ได้ว่าแย่ลงจริง ส่วน TF-IDF อย่างเดียวได้ p เท่ากับศูนย์จุดศูนย์ศูนย์เจ็ดแปด ซึ่งต่ำสุดเท่าที่แปด topic ให้ได้ แสดงว่าการทดสอบจับความต่างได้เมื่อความต่างมีอยู่จริง',source:'XAMR_SIGNIFICANCE_TH.md'},
{g:3,title:"การวิเคราะห์ข้อผิดพลาด",sub:"วิเคราะห์การรวมผิดและการแยกผิดจากกฎเวลาและการเพิ่มเส้นเชื่อมด้วย TF-IDF",
body:'<div class="cols">'+panel('ข้อผิดพลาดจากข้อมูลเวลา','<div class="big">+674</div>'+p('คู่แยกผิดของ Ann2 เมื่อใช้ Temporal เทียบ OR')+p('ตัวอย่าง Jamal Williams: วันในหัวข่าวต่างกัน แต่เนื้อหากล่าวถึงเช้าวันอาทิตย์'))+panel('ข้อผิดพลาดจากความคล้ายของข้อความ',p('OR + TF-IDF กู้คู่ที่เคยแยกผิดได้ 7 / 164 คู่')+p('แต่รวมผิดเพิ่ม 621 / 880 คู่ (Ann1 / Ann2)')+'<div class="mergeviz" role="img" aria-label="กลุ่ม 22 mention รวมกับกลุ่ม 19 mention ได้คู่ใหม่ 418 คู่"><span class="blob">22</span><span class="op">×</span><span class="blob warm">19</span><span class="op">=</span><b>418 คู่</b></div>'+p('<span class="accent">612 / 719</span> คู่มาจาก topic 35')+p('ซึ่งมีการรวมกลุ่มเพียง 3 ครั้ง'))+'</div>'+call('ทั้งสองแบบมาจากหลักฐานคลุมเครือ: วันเผยแพร่ไม่ใช่วันเกิดเหตุ และข่าวต่างเหตุการณ์ใช้คำคล้ายกัน'),note:'ตัวอย่างวันที่ช่วยให้เห็นว่าวันเผยแพร่อาจต่างจากวันเกิดเหตุ แต่ไม่ได้พิสูจน์ว่าสาเหตุนี้อธิบายทั้งหกร้อยเจ็ดสิบสี่คู่ครับ ส่วน TF-IDF พอเราแยกดูราย topic พบว่าคู่ผิดเกือบทั้งหมดมาจาก topic 35 topic เดียว ซึ่งเป็นข่าวจับนักกีฬา ใน topic นี้มีการรวมกลุ่มแค่สามครั้ง แต่การรวมกลุ่มยี่สิบสองกับสิบเก้า mention ครั้งเดียวสร้างคู่ใหม่ได้สี่ร้อยสิบแปดคู่ ถ้าสองกลุ่มเป็นคนละเหตุการณ์ คู่ทั้งหมดนั้นก็ผิดทันที ความคล้ายของข้อความจึงยังต้องมีหลักฐานระบุตัวเหตุการณ์ที่ละเอียดขึ้น',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:3,title:"parser อ่านวันที่ได้ครบทุกชุดหรือไม่",body:'<div class="cols dates">'+panel('วันที่ที่ parser อ่านได้',coverage()+'<p class="sigread">Ann2 ใน train และ test_common เขียนวันที่แบบ 12/18/2008 ทั้งหมด</p>')+panel('เป็นเดือน/วัน หรือ วัน/เดือน','<div class="order"><div><b>795</b><span>ครั้งที่ตรงกับ Ann1 เมื่ออ่านเป็นเดือน/วัน</span></div><div class="no"><b>0</b><span>ครั้งที่ตรงกับ Ann1 เมื่ออ่านเป็นวัน/เดือน</span></div></div>'+p('นับจาก Ann2 train ค่าที่มีเลขเกิน 12 ทั้ง 1,431 ค่า ก็เป็นเดือน/วันทั้งหมด'))+'</div>'+call('ผลบน dev ไม่ได้รับผลกระทบ แต่ถ้าประเมินบน test_common ของ Ann2 กฎเวลาจะไม่ทำงานเลย'),note:'เรื่องสุดท้ายที่เราตรวจคือวันที่ครับ กฎเวลาจะตัดสินได้ก็ต่อเมื่ออ่านวันที่ของทั้งสอง mention ออก เราจึงนับว่า parser อ่านวันที่ได้กี่ค่าในแต่ละชุด ใน dev อ่านได้ครบทั้งสองเวอร์ชัน ผลที่นำเสนอจึงใช้ได้ แต่ Ann2 ใน train และ test_common เขียนวันที่แบบทับ เช่น สิบสองทับสิบแปดทับสองพันแปด ซึ่ง parser ตั้งใจไม่อ่านเพราะอาจเป็นได้ทั้งวันก่อนหรือเดือนก่อน เราจึงหาหลักฐาน เมื่อเทียบกับวันที่ที่ Ann1 กำกับให้ mention เดียวกัน การอ่านแบบเดือนนำหน้าตรงเจ็ดร้อยเก้าสิบห้าครั้ง ส่วนแบบวันนำหน้าตรงศูนย์ครั้ง จึงสรุปได้ว่า Ann2 ใช้เดือนนำหน้า ถ้าจะแก้ parser ควรผูกกับชุดข้อมูลนี้และล็อกกติกาบน dev ก่อน',source:'XAMR_DATE_AUDIT_TH.md'},
{g:3,title:"สรุปผล ข้อจำกัด และแนวทางพัฒนาต่อ",sub:"สรุปผลเทียบ OR ข้อจำกัดของการประเมิน และข้อเสนอสำหรับการศึกษาต่อยอด",
body:'<div class="cols">'+panel('ผลการดำเนินงาน',p('เปรียบเทียบกฎเวลา ความคล้ายข้อความ และ NB บนฐาน OR เดียวกัน')+p('ผลต่างของ OR + TF-IDF ยังแยกจากความบังเอิญไม่ได้ (p 0.50–0.69)')+p('คู่รวมผิดส่วนใหญ่มาจาก topic 35 topic เดียว')+p('มีเครื่องมือทำซ้ำผล วิเคราะห์รายหัวข้อ และตรวจวันที่'))+panel('ข้อจำกัดและงานต่อยอด',p('dev มีเพียง 8 topics และผ่านการสำรวจมาหลายรอบ')+p('ยังไม่มี held-out evaluation และยังไม่ประเมินการสกัดเหตุการณ์จากข่าวดิบ')+p('ให้ parser อ่านวันที่ของ Ann2 โดยล็อกกติกาบน dev ก่อนประเมิน test_common'))+'</div>'+call('ผลยังไม่แสดงว่าแนวทางเสริมให้คะแนนสูงกว่า OR อย่างสม่ำเสมอ'),note:'สิ่งที่ได้ไม่ใช่แค่คะแนนครับ เราพบว่าหลักฐานเวลาและข้อความที่ยังคลุมเครืออาจสร้างข้อผิดพลาดเพิ่ม และได้เครื่องมือช่วยตรวจผลอย่างเป็นระบบ การทดสอบนัยสำคัญบอกว่าผลต่างของ OR บวก TF-IDF ยังสรุปไม่ได้ด้วยข้อมูลแปด topic และข้อผิดพลาดส่วนใหญ่มาจาก topic เดียว ข้อจำกัดหลักคือ dev มีขนาดเล็กและถูกสำรวจมาแล้ว งานต่อยอดที่เสนอคือให้ parser อ่านวันที่ของ Ann2 ได้ โดยล็อกกติกาบน dev ก่อนประเมินชุดใหม่ ส่วนนี้ยังเป็นข้อเสนอ ไม่ใช่งานที่ทำเสร็จแล้ว',source:'NLP_PROJECT_HANDOFF_TH.md'},
{g:3,title:"เอกสารอ้างอิงและหลักฐานของโครงงาน",sub:"รวบรวมงานวิจัยต้นทาง เอกสารการพัฒนาระบบ และหลักฐานผลการทดลองที่ตรวจสอบย้อนกลับได้",
body:'<div class="refs"><a class="ref" href="https://aclanthology.org/2024.lrec-main.920/" target="_blank" rel="noopener">X-AMR · งานวิจัยและวิธีอ้างอิง<small>ACL Anthology · LREC-COLING 2024</small></a><a class="ref" href="https://aclanthology.org/2026.acl-long.1345/" target="_blank" rel="noopener">CohTP · แนวคิดเรื่องความสอดคล้องของเวลา<small>ใช้เป็นแรงบันดาลใจ ไม่ใช่การทำซ้ำครบระบบ</small></a><a class="ref" href="'+SOURCE+'NLP_PROJECT_HANDOFF_TH.md" target="_blank" rel="noopener">บันทึกการตัดสินใจและผลทดลองของโครงงาน<small>ตรึงเอกสารที่ commit 598ea069</small></a><a class="ref" href="https://github.com/Micosz/company-news-nlp-workbench/blob/6ba0d56/docs/XAMR_SIGNIFICANCE_TH.md" target="_blank" rel="noopener">การวิเคราะห์รายหัวข้อ ทดสอบนัยสำคัญ และตรวจวันที่<small>XAMR_TOPIC_ANALYSIS_TH, XAMR_SIGNIFICANCE_TH และ XAMR_DATE_AUDIT_TH ใน docs</small></a><a class="ref" href="'+SOURCE+'WEBSITE_RELEASE_2026-11-16.md" target="_blank" rel="noopener">Release, metric values และ protocol สำหรับ replay<small>เชื่อมไปยังรายละเอียด TF-IDF และ NB ใน repository</small></a></div>',note:'แหล่งอ้างอิงแยกเป็นงาน X-AMR และ CohTP ต้นทาง กับเอกสาร implementation ของโครงงานครับ ตัวเลขในสไลด์อ้างผลที่บันทึกไว้ ไม่ได้รัน benchmark ใหม่เพื่อสร้างสไลด์ และข้อจำกัดของแต่ละการทดลองยังคงเดิม',source:'WEBSITE_RELEASE_2026-11-16.md'}
];
groups.forEach((g,i)=>{g.start=slides.findIndex(s=>s.g===i);});
const world = document.getElementById('world');
const viewport = document.getElementById('viewport');
const stations = [...world.querySelectorAll('.station')];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const portrait = matchMedia('(max-width:740px) and (orientation:portrait)');
const byId = id => document.getElementById(id);
const icon = name => '<svg class="icon" aria-hidden="true"><use href="#i-'+name+'"/></svg>';
const chapterIcons = ['intro','method','data','results'];
let current = -1, last = 0, transitionTimer, rendered = false;
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain = s => s.replace(/<br\s*\/?\s*>/gi,' ').replace(/<[^>]+>/g,'');
const fmt = n => String(n).padStart(2,'0');
const range = i => fmt(groups[i].start+1)+' – '+fmt(groups[i+1]?.start ?? slides.length);
function art(i) {
 const lines = [
  '<path d="M7 25h55v38H39L28 75V63H7z"/><path d="M59 39h27v32H73l-8 7v-7H53"/><path d="M17 36h32M17 45h23"/>',
  '<circle cx="19" cy="59" r="7"/><circle cx="49" cy="28" r="9"/><circle cx="76" cy="61" r="10"/><path d="m24 53 18-19m13 1 15 18M27 60l37 1"/>',
  '<path d="m7 35 40-16 40 16-40 16zM10 49l37 16 37-16M10 63l37 16 37-16"/>',
  '<path d="M10 23v52h76M22 64V47h10v17m10 0V34h10v30m10 0V20h10v44"/>'
 ];
 return '<svg viewBox="0 0 94 94" class="chapter-art" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'+lines[i]+'</g></svg>';
}
function cover(g,i) {
 return '<button class="cover" data-open="'+g.start+'" aria-label="'+esc(g.name+' '+g.thai)+'"><span class="number">'+fmt(i+1)+'</span>'+art(i)+'<div class="cover-copy"><h2>'+esc(g.name)+'</h2><p>'+esc(g.thai)+'</p></div><span class="range">'+range(i)+'</span><span class="enter">'+icon('right')+'</span></button>';
}
byId('chapters').innerHTML=['หน้าปก',...groups.map(g=>g.thai)].map((name,i)=>'<button data-chapter="'+(i-1)+'" aria-label="'+esc(name)+'" title="'+esc(name)+'">'+icon(i?chapterIcons[i-1]:'home')+'</button>').join('');
byId('chapters').addEventListener('click',e=>{const b=e.target.closest('button');if(b)go(Number(b.dataset.chapter)<0?0:groups[Number(b.dataset.chapter)].start);});
stations.forEach((el,i)=>{el.style.left=groups[i].x+'px';el.style.top=groups[i].y+'px';});
function render() {
 document.body.classList.toggle('focused',current>=0);
 document.body.classList.toggle('on-title',current===0);
 for(const [i,el] of stations.entries()){
  const active=current>=0 && slides[current].g===i;
  el.classList.toggle('active',active); el.inert=current>=0&&!active;
  const view=active?'slide-'+current:'cover';
  if(el.dataset.view===view)continue;
  el.dataset.view=view;
  if(!active){el.innerHTML=cover(groups[i],i);continue;}
  const s=slides[current];
  el.innerHTML=s.cover?'<article data-page="1" class="slide titleslide">'+s.body+'</article>':'<article data-page="'+(current+1)+'" class="slide"><h1>'+s.title+'</h1><div class="slidebody">'+s.body+'</div><div class="pagenum">'+fmt(current+1)+'</div></article>';
 }
 const label=current<0?'ภาพรวม':fmt(current+1)+' / '+slides.length;
 byId('position').textContent=label;
 byId('progressFill').style.width=current<0?'0%':((current+1)/slides.length*100)+'%';
 const nextLabel=current<0?'เริ่มนำเสนอ':current===slides.length-1?'กลับภาพรวม':'สไลด์ถัดไป';
 byId('next').setAttribute('aria-label',nextLabel);byId('next').title=nextLabel+' (→)';
 byId('next').innerHTML=icon(current===slides.length-1?'grid':'right');
 byId('noteTitle').textContent=current<0?'ภาพรวมเส้นทาง':plain(slides[current].title);
 byId('noteText').textContent=current<0?'เริ่มจาก Introduction แล้วเดินตามเส้นทางผ่าน Approach, Data & Methods และ Results & Wrap ใช้ลูกศรขวาเพื่อเล่าตามลำดับ หรือเลือกหมวดที่ต้องการ':slides[current].note;
 byId('live').textContent=current<0?'ภาพรวม สี่หมวด':(current+1)+' จาก '+slides.length+' '+plain(slides[current].title);
 byId('chapters').querySelectorAll('button').forEach(b=>{const i=Number(b.dataset.chapter);if(current>=0&&(current===0?i===-1:i===slides[current].g))b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 byId('tocItems').querySelectorAll('[data-index]').forEach(b=>{if(Number(b.dataset.index)===current)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
}
function camera(target=current){
 if(portrait.matches){world.style.removeProperty('transform');return;}
 const w=viewport.clientWidth,h=viewport.clientHeight;
 const overview=target<0;
 const width=overview?2504:1180,height=overview?1660:660;
 const scale=Math.min((w-(overview?28:8))/width,(h-4)/height);
 const g=overview?{x:0,y:0}:groups[slides[target].g];
 world.style.transform='translate('+( (w-width*scale)/2-g.x*scale )+'px,'+( (h-height*scale)/2-g.y*scale )+'px) scale('+scale+')';
}
function go(n,updateHistory=true){
 const old=current;current=Math.max(-1,Math.min(slides.length-1,n));
 if(current>=0)last=current;
 if(updateHistory&&old!==current){history.pushState(null,'',current<0?'#overview':'#slide-'+(current+1));}
 clearTimeout(transitionTimer);
 const moving=rendered && old!==current && !reduced.matches && !portrait.matches && (old<0||current<0||slides[old].g!==slides[current].g);
 world.classList.toggle('moving',moving);
 if(old!==current && (viewport.contains(document.activeElement)||byId('tocItems').contains(document.activeElement)))viewport.focus({preventScroll:true});
 render();camera();viewport.scrollTop=0;
 if(moving)transitionTimer=setTimeout(()=>world.classList.remove('moving'),425);
 rendered=true;
}
const fromHash=()=>{const m=location.hash.match(/^#slide-(\d+)$/);return m?Math.max(0,Math.min(slides.length-1,Number(m[1])-1)):location.hash==='#overview'?-1:0;};
function next(){go(current<0?0:current===slides.length-1?-1:current+1);}
function prev(){go(current<0?last:current===0?-1:current-1);}
function setNotes(open){byId('notes').hidden=!open;byId('notesButton').setAttribute('aria-expanded',String(open));}
function fullscreen(){if(document.fullscreenElement)document.exitFullscreen?.();else document.documentElement.requestFullscreen?.().catch(()=>{});}
function setTheme(dark){document.documentElement.classList.toggle('dark',dark);byId('theme').setAttribute('aria-pressed',String(dark));byId('theme').title=dark?'กลับโหมดสว่าง':'เปิดโหมดมืด';byId('theme').innerHTML=icon(dark?'sun':'moon');document.querySelector('meta[name="theme-color"]').content=dark?'#141414':'#ffffff';}
setTheme(false);
byId('theme').onclick=()=>setTheme(!document.documentElement.classList.contains('dark'));
byId('next').onclick=next;byId('prev').onclick=prev;byId('map').onclick=()=>go(-1);byId('full').onclick=fullscreen;
byId('notesButton').onclick=()=>setNotes(byId('notes').hidden);byId('closeNotes').onclick=()=>{setNotes(false);byId('notesButton').focus();};
byId('contents').onclick=()=>byId('toc').showModal();
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>byId(b.dataset.close).close());
byId('tocItems').innerHTML=groups.map((g,i)=>'<section><h3>'+fmt(i+1)+' / '+esc(g.name)+'</h3>'+slides.map((s,j)=>s.g===i?'<button data-index="'+j+'"><small>'+fmt(j+1)+'</small><span>'+esc(plain(s.title))+'</span></button>':'').join('')+'</section>').join('');
byId('tocItems').onclick=e=>{const b=e.target.closest('[data-index]');if(b){byId('toc').close();go(Number(b.dataset.index));}};
world.addEventListener('click',e=>{const b=e.target.closest('[data-open]');if(b)go(Number(b.dataset.open));});
window.addEventListener('keydown',e=>{
 if(e.ctrlKey||e.metaKey||e.altKey||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||document.querySelector('dialog[open]'))return;
 if(/BUTTON|A/.test(e.target.tagName)&&(e.key===' '||e.key==='Enter'))return;
 const key=({KeyN:'n',KeyF:'f',KeyO:'o'}[e.code]||e.key.toLowerCase());
 if(['arrowright','pagedown',' '].includes(key)){e.preventDefault();next();}
 else if(['arrowleft','pageup'].includes(key)){e.preventDefault();prev();}
 else if(key==='escape'||key==='o'){setNotes(false);go(-1);}
 else if(key==='home'){e.preventDefault();go(0);}
 else if(key==='end'){e.preventDefault();go(slides.length-1);}
 else if(key==='n')setNotes(byId('notes').hidden);else if(key==='f')fullscreen();else if(key==='?')byId('help').showModal();
});
let touchStart;
viewport.addEventListener('touchstart',e=>{touchStart=e.touches.length===1?[e.touches[0].clientX,e.touches[0].clientY]:null;},{passive:true});
viewport.addEventListener('touchcancel',()=>{touchStart=null;});
viewport.addEventListener('touchend',e=>{if(!touchStart)return;const dx=e.changedTouches[0].clientX-touchStart[0],dy=e.changedTouches[0].clientY-touchStart[1];touchStart=null;if(Math.abs(dx)>70&&Math.abs(dx)>Math.abs(dy)*1.5)dx<0?next():prev();},{passive:true});
window.addEventListener('resize',()=>camera());
window.addEventListener('hashchange',()=>go(fromHash(),false));
reduced.addEventListener('change',()=>{clearTimeout(transitionTimer);world.classList.remove('moving');camera();});
go(fromHash(),false);
