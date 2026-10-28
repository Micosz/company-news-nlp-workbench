# เริ่มทำงานต่อจากตรงไหน

เป้าหมายคือทดสอบว่าข้อมูลบทบาทผู้ซื้อ/เป้าหมายช่วย pairwise event coreference ได้หรือไม่ เว็บนี้ไม่ได้รัน CohTP เต็มระบบ

## ทำแล้ว

- หน้าเว็บ local สำหรับเลือกข้อมูล นำเข้า Excel/CSV แก้ Python รัน วัดผล ดูกราฟ เปิดผลเก่า และดาวน์โหลด ZIP
- Categorical Naive Bayes: text baseline vs text + role categories, ขอบ cosine จาก train เท่านั้น; majority/cosine เป็น reference
- เครื่องมือสร้างแบบฟอร์ม 42 mentions และแปลง annotation ที่มีหลักฐานเป็นคู่ Pilot A/B ผ่านเว็บหรือ CLI
- Connected components และ B³ สำหรับ test topic ของ Pilot ที่ตรวจว่ามีคู่ครบทุกคู่; Full และข้อมูลอื่นจะข้ามอย่างปลอดภัย
- หน้าต้นแบบเปรียบเทียบข่าวจากค่าที่ผู้ใช้กรอกเอง เป็นกฎอย่างง่าย ยังไม่สกัดข่าวและไม่ใช้ NLI

## ต้องทำต่อ

1. อ่าน [คู่มือ annotation](ROLE_ANNOTATION_TH.md) ดาวน์โหลดแบบฟอร์มจากหน้า 01 อ่าน context และกรอกบทบาทพร้อมหลักฐาน/ผู้กรอก โดยไม่ใช้ labels เป็นทางลัด
2. ทดลองกรอกบางแถวและตรวจว่ามีข้อมูลพอ ก่อนลงทุนทำทั้งชุด ค่าว่างยังเป็น unknown
3. นำแบบฟอร์มเข้าเว็บ เลือก Pilot A หรือ B, ตรวจ mapping/coverage และรัน manual roles จากนั้นตรวจ ΔF1, pairwise confusion และ B³
4. บันทึกว่าบทบาทเป็น oracle พร้อมที่มาข้อมูล ผู้ตรวจ ความไม่ชัด และข้อจำกัดของข้อมูล ให้คนอีกคนตรวจเมื่อทำได้
5. Pilot มีหนึ่ง event ต่อดีล: target อาจเป็น shortcut ต้องหา test events เดียวกันหลายขั้นและ gold อิสระก่อนสรุปทั่วไป; ชุด Full mixed-domain และคู่ลบสุ่ม ไม่ใช่ M&A held-out ใหม่
6. ประเมินกับอาจารย์ว่าการเปรียบเทียบ baseline ของเราเพียงพอหรือจำเป็นต้อง reproduce CohTP; B³ ที่ได้ยังไม่ใช่ CoNLL F1 และเทียบข้าม protocol ไม่ได้

โค้ด/ข้อมูล/metrics ของแต่ละ run ถูกบันทึกแยกกัน; ผล Logistic Regression รุ่นเก่ายังคงเป็นประวัติของรุ่นนั้น ไม่ใช่ผล Naive Bayes
