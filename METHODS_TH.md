# วิธีการทดลองที่ใช้ใน workbench

งานนี้เป็น **baseline ที่เขียนเองจากโจทย์ event coreference** ไม่ใช่ implementation หรือผลเปรียบเทียบโดยตรงกับ CohTP คำถามคือ เมื่อคงข้อมูล split และตัวจำแนกเดิม การเพิ่ม buyer/target role compatibility ช่วยจำแนกคู่ข้อความเหตุการณ์เดียวกันหรือไม่?

## ข้อมูลและการเตรียม

หน่วยข้อมูลคือคู่ event contexts จากคนละข่าว `label=1` คือ gold same-event และ `0` คือ different-event ใช้ gold event contexts เป็น input จึงยังไม่ประเมินการตรวจหาเหตุการณ์เอง ระบบตรวจเอกสาร กลุ่ม และข้อความตรงกันข้าม split; Pilot A/B แบ่งตาม topic และสลับ train/test แต่ไม่ใช่ชุด test อิสระสองชุด

ข้อความผ่าน HTML unescape → Unicode NFC → รวม whitespace → trim แล้วใช้ TF-IDF word 1–2 grams สร้าง vocabulary/IDF จาก unique TRAIN contexts เท่านั้น (L2-normalized, max_features=30000) คำนวณ cosine ของแต่ละคู่

## ตัวจำแนกและฟีเจอร์

แบ่ง cosine เป็นหมวดด้วยขอบ tertile ที่คำนวณจาก TRAIN เท่านั้น แล้วใช้ขอบเดิมกับ test ไม่ใช้ test ในการ fit bins; ถ้าขอบซ้ำอาจมีหมวดน้อยกว่าสาม และระบบจะเตือน ขอบแบ่งบันทึกไว้ใน `vectorizer.json` และพารามิเตอร์โมเดล

- **Text baseline:** หมวด cosine → CategoricalNB
- **Text + roles:** หมวด cosine เดิม + buyer_relation + target_relation + role_reversed → CategoricalNB
- Relation codes: 0 unknown, 1 match, 2 mismatch; reversed: 0 unknown, 1 no, 2 yes. ค่าว่างหรือ marker ที่ระบุว่าไม่ทราบไม่ถือเป็น mismatch; role disagreement ไม่ใช่ข้อสรุปว่าข่าวขัดแย้ง
- ทั้งสองตัวใช้ CategoricalNB `alpha=1`, `min_categories=3`, class prior จาก train และ threshold 0.5 เช่นเดียวกัน โดยเปลี่ยนเฉพาะฟีเจอร์บทบาท อัลกอริทึมตั้งต้น deterministic; seed บันทึกไว้สำหรับโค้ด custom
- Majority และ cosine ≥ 0.5 เป็น reference แยกต่างหาก ห้ามใช้ reference เทียบกับ Text + roles เพื่ออ้างผลเฉพาะของ role features เพราะตัวจำแนกต่างกัน

การกรอกบทบาทด้วยคนเป็น **manual/oracle role experiment** ต้องทำจาก evidence โดยอิสระจาก gold labels ตาม [คู่มือ annotation](docs/ROLE_ANNOTATION_TH.md) ที่มาของบทบาททำนายต้องบันทึกให้ชัด; โครงการยังไม่มีตัวสกัดอัตโนมัติ

## การวัดผล

วัด pairwise Precision, Recall และ F1 สำหรับ label 1, Macro F1 เฉลี่ย class 0/1, Accuracy และ TP/FP/FN/TN เมื่อมีทั้งสองโมเดล ΔF1 = F1(Text + roles) − F1(Text baseline); บนหน้าเปอร์เซ็นต์แสดงเป็นจุดเปอร์เซ็นต์

Pilot ที่มี test pairs ครบทุกคู่และ IDs/text/labels ตรงกับ reference จะนำ predicted-positive edges มารวมด้วย connected components แล้ววัด **B³ Precision / Recall / F1 ระดับ mention** เทียบ gold event clusters หลังโมเดลทำนายแล้วและไม่ส่ง gold ให้โมเดล เก็บ `clustering_reference.json` และ `cluster_predictions.csv` พร้อม hash reference การเชื่อมเป็นทอด ๆ อาจรวมผิดกลุ่ม B³ เพียงค่าเดียวไม่ใช่ CoNLL F1; จะเปรียบเทียบกับ paper ต้องมีข้อมูล mention set split และ protocol ตรงกัน

Full ECB+ มีคู่ลบที่สุ่มโดยใช้ gold การใช้แค่คู่ที่มีอยู่สร้างกราฟอาจนำข้อมูลเฉลยไปรั่วและไม่ครอบคลุมคู่ที่ขาด จึง **ไม่คำนวณ B³ บน Full** ในรุ่นนี้ ข้อมูล upload ที่ไม่ตรงกับ complete Pilot reference จะข้ามพร้อมเหตุผล

## ข้อจำกัดและหลักฐาน

Pilot มีเพียง 42 mentions, 4 focal events และ 2 topics; 424 คู่ไม่ใช่ตัวอย่างอิสระ 424 เหตุการณ์ ใน subset นี้เลือกหนึ่ง acquisition event ต่อดีล จึงมีความเสี่ยงที่การตรงกันของบริษัทเป้าหมายเป็น shortcut สำหรับ gold ไม่ใช่หลักฐานว่าแยกเหตุการณ์หลายระยะของดีลเดียวกันได้ ต้องมีตัวอย่าง same-buyer/same-target แต่ต่าง event และ gold อิสระเพื่อทดสอบเพิ่มเติม

Pilot เป็น subset ของ Full และเคยตรวจผลทดสอบแล้ว; หากปรับจากผล test ต้องใช้ held-out ใหม่สำหรับข้อสรุปสุดท้าย Full เป็น mixed-domain ไม่ใช่ชุดทดสอบ M&A ใหม่ Gold labels ไม่ควรสร้างจากข้อมูล roles เอง

ผล Logistic Regression ใน `docs/INITIAL_RESULTS.json` เป็นผลรุ่นก่อน ใช้เป็นประวัติเท่านั้น ไม่ติดป้ายเป็น Naive Bayes หรือผล improvement บทบาทจริงยังต้องทำ annotation และตรวจ coverage ก่อนรายงานผล

ส่วนเปรียบเทียบข่าวในหน้า 05 ใช้ข้อมูลที่ผู้ใช้กรอกและกฎเบื้องต้น ไม่ใช่การสกัดอัตโนมัติ ไม่ใช้ NLI ไม่ยืนยันข่าวจริงและไม่ถือเป็นผลวิจัยจนมีข้อมูลอ้างอิงและการประเมิน
