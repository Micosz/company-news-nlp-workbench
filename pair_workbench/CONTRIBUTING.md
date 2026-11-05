# ทำงานร่วมกันในทีม

เริ่มด้วย README แล้วรัน Pilot A ด้วยโค้ดเดิมให้ได้ก่อน บันทึกว่าติดขั้นตอนไหนโดยใช้ issue ไม่ต้องใส่ข้อมูลส่วนตัวหรือ token

## การส่งโค้ด

1. ดึง `main` ล่าสุดตอน working tree สะอาด แล้วสร้าง branch ของงาน เช่น `feat/role-annotation` หรือ `fix/excel-import`
2. ทำงานที่มีขอบเขตชัดเจน อธิบายว่าปรับ input, feature หรือ protocol ตรงไหน
3. รัน `.venv/bin/python -m unittest test_workbench -v` หากเปลี่ยน JavaScript ให้รัน `node --check static/app.js` ด้วย
4. เปิด Pull Request พร้อมสิ่งที่เปลี่ยน เหตุผล วิธีตรวจ และข้อจำกัด อย่าใส่ผลที่ยังไม่ได้รันจริง
5. ให้เพื่อน review ก่อนรวมโค้ด เพื่อให้ทุกคนทราบว่าผลรอบใหม่ใช้วิธีไหน

## การแก้อัลกอริทึม

- `run(train, test, config)` รับ train ที่มี label และ test ที่ไม่มี label
- การแยก labels นี้เป็นข้อตกลงการทดลอง ไม่ใช่ตัวกั้นสิทธิ์อ่านไฟล์
- Fit vocabulary, IDF, scaler และ classifier ด้วย train เท่านั้น
- ค่า threshold/hyperparameters ต้องระบุล่วงหน้าหรือเลือกด้วย train/dev ห้ามเลือกจากคะแนน test
- คงข้อมูล split classifier และการตั้งค่าเดิมเมื่อเปรียบเทียบ feature ablation
- อย่าใช้ `pair_id`, `doc_id`, `group_id`, gold event cluster หรือ labels มาเป็น input feature
- ถ้าแก้ workflow ให้ปรับ METHODS_TH.md และคำอธิบายบนเว็บด้วย

## ข้อมูลและผลการทดลอง

- บทบาทบริษัทต้องมีที่มา/หลักฐาน ตรวจชื่อบริษัทสม่ำเสมอ และเก็บ unknown เป็นช่องว่าง
- ไม่กำหนด same-event label จาก role agreement ที่เรากำลังทดสอบ
- ห้ามแก้ test labels เพื่อให้โมเดลดูดี หากพบ annotation ผิด ให้บันทึกเหตุผลและ version ข้อมูล
- `runs/` กับ `.venv/` ถูก ignore; อย่า force-add ข้อมูลส่วนตัว ไฟล์ upload, credentials หรือผลดิบขนาดใหญ่
- ผลที่จะใส่รายงานควรมี run ID, config, code/data SHA-256, source ของ roles และไฟล์ทำนายที่เก็บนอก Git อย่างตรวจสอบได้
- ตัวอย่างสังเคราะห์ใน unit tests ใช้ทดสอบซอฟต์แวร์ ไม่ใช่ผลทดลองวิจัย

## เพิ่มสมาชิกทีม

Repo เป็น public ทุกคนอ่านและ clone ได้ ส่วนผู้ที่จะ push เข้า repo โดยตรงต้องได้รับสิทธิ์ collaborator จากเจ้าของผ่าน Settings → Collaborators และตอบรับคำเชิญก่อน หรือส่งงานผ่าน fork และ Pull Request
