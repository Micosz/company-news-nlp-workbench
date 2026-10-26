# เริ่มทำงานต่อจากตรงไหน

เป้าหมายรอบนี้คือ **พิสูจน์ว่า experiment ที่ควบคุมตัวแปรรันได้ และทดสอบผลของ buyer/target compatibility** ส่วนเว็บติดตามบริษัทสำหรับใช้งานจริงเป็นแนวทางต่อยอดภายหลัง

## สิ่งที่ทำแล้ว

- เว็บภาษาไทยบน localhost: import Excel/CSV, mapping คอลัมน์, แก้ Python, รันเบื้องหลัง, ดูผลและดาวน์โหลด ZIP
- Pilot A/B จาก ECB+ พร้อม gold labels และ grouped split
- โค้ด TF-IDF/cosine + Logistic Regression และโค้ดส่วนเพิ่ม role features
- ตัวตรวจเอกสาร/กลุ่ม/ข้อความซ้ำข้าม split
- บันทึกโค้ด ข้อมูล seed dependencies และผลแยกต่อ run
- Unit tests 9 กรณี และการตรวจ Excel import → run → ZIP บนเครื่องพัฒนา
- รัน baseline จริงทั้ง A/B และตรวจว่า full package รันได้บนเครื่องพัฒนา

## ยังไม่ได้ทำ

- ป้ายกำกับ buyer/target บนข้อมูลจริง (ช่องในไฟล์ว่างอยู่)
- ผลเปรียบเทียบ Text vs Text + roles บน roles จริง
- Automatic role extraction หรือ company alias/entity linking
- การประเมิน clustering หรือการทำ CohTP เต็มระบบ
- ข้อมูล M&A ที่มี gold อิสระจำนวนมากพอสำหรับข้อสรุปทั่วไป
- ผลทดสอบ Windows ครบทั้ง workflow

## ลำดับงานที่แนะนำ

1. **ตรวจว่า setup ตรงกัน:** ทุกคนรัน Pilot A ด้วย seed=374 แล้วตรวจ metrics เทียบกับ docs/INITIAL_RESULTS.json ใช้ตัวเลขเต็มใน JSON ไม่ปรับค่าเพื่อให้ตรงโดยเดา
2. **ตกลงนิยาม annotation:** buyer/target ของ focal event คือใคร ใช้รูปชื่อบริษัทแบบใด unknown/หลายบทบาททำอย่างไร และเก็บ evidence ตรงไหน
3. **ทำ roles ให้ครบ pilot:** อ่านข้อมูลอิสระจาก labels เก็บผู้ทำ/ผู้ตรวจและหลักฐาน หากบทบาทไม่ชัดให้คงว่างและบันทึกเหตุผล
4. **รัน ablation:** เลือก manual roles รันทั้ง Text baseline และ Text + roles ในรอบเดียวกัน คงค่าที่ตกลงไว้ ดู coverage และผลที่ผิด
5. **อธิบายผล:** ถ้าดีขึ้นหรือลดลงให้ดูว่า FP/FN เปลี่ยนตรงไหน ห้ามใช้ F1 ที่ดีขึ้นอย่างเดียวอ้างว่าใช้ได้ทั่วไป
6. **เลือกงานรอบถัดไปจากหลักฐาน:** หาก pilot ชี้ว่าวิธีน่าลองต่อ ค่อยเพิ่มกลุ่มดีล/held-out data หรือขยาย model ให้ตรงข้อจำกัดที่พบ

ไม่จำเป็นต้องทำ features สินค้าให้ครบเพื่อสรุปผลวิชานี้ การทดลองที่ดีอาจได้ผล “ไม่ช่วย” โดยยังอธิบายหลักการและเหตุผลได้

## ตัวแปรที่ต้องตรึงในการเปรียบเทียบ

- ชุดข่าว/event contexts และ gold same-event labels
- Grouped split และการเลือกคู่ลบ
- Text preprocessing, TF-IDF vocabulary/IDF และ cosine
- Classifier, regularization, class_weight, seed และ threshold
- เปลี่ยนเฉพาะการเติม finance role compatibility features

## จุดที่ต้องระวังในการตีความ

- 424 คู่มาจาก 4 เหตุการณ์และ 2 topics ไม่ใช่ตัวอย่างอิสระ 424 เหตุการณ์
- Manual roles วัดความช่วยได้ของข้อมูลที่ให้แล้ว (oracle); ไม่วัดคุณภาพตัวดึงบทบาท
- Same buyer + same target ยังไม่เพียงพอจะบอกว่า same event เสมอไป
- Pilot A/B เป็นข้อมูลชุดเดียวกันสลับทิศ ไม่ใช่ test สองชุดอิสระ
- Positive F1 ของ baseline ปัจจุบันยังต่ำกว่า majority reference จึงต้องดูทั้ง Macro F1 และ confusion counts
- Full เป็น mixed-domain execution check หลังเห็น pilot แล้ว ไม่ใช่ผล held-out M&A ใหม่

## แนวทางแบ่งงาน (ข้อเสนอ ยังไม่ได้กำหนดคน)

| งาน | สิ่งที่ส่งต่อให้เพื่อนตรวจได้ |
|---|---|
| Data/annotation | คู่มือ annotation, roles พร้อม evidence, version และผลตรวจซ้ำ |
| Modeling | โค้ดฟีเจอร์, config, run ID, ตารางเปรียบเทียบและ error analysis |
| App/reproducibility | ขั้นตอนติดตั้ง, validation, export และการเก็บหลักฐาน |
| Report/presentation | Their Workflow / Proposed Workflow ที่อธิบายตรงกับโค้ดและผลจริง |
