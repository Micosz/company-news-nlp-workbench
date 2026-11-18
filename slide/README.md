# X-AMR Final Presentation

สไลด์ HTML 15 หน้า พร้อมภาพรวม 4 หมวดและบทพูดภาษาไทย ใช้ธีมถนนแสงสีฟ้าบนพื้นเข้ม

**เปิดสไลด์ออนไลน์: [X-AMR Final Presentation](https://xamr-nlp-slides.vercel.app/)**

## เปิดในเครื่อง

จาก root ของ repository:

```sh
python3 -m http.server 8768 --bind 127.0.0.1
```

เปิด http://127.0.0.1:8768/slide/ หรือเปิด `slide/index.html` โดยตรง ไม่มี build หรือ dependency ใหม่ ใช้พอร์ต 8768 เพื่อไม่ชน X-AMR Workbench ที่ปกติใช้ 8767

## การควบคุม

| ปุ่ม | การทำงาน |
|---|---|
| → / Page Down / Space | หน้าถัดไป; จากหน้าสุดท้ายกลับภาพรวม |
| ← / Page Up | หน้าก่อนหน้า |
| Esc / O | กลับภาพรวมและปิดบทพูด (เมื่อไม่มี dialog เปิดอยู่) |
| Home / End | หน้าแรก / หน้าสุดท้าย |
| N | เปิดหรือปิดบทพูด |
| F | เข้า/ออกเต็มจอ หากเบราว์เซอร์รองรับ |
| ? | เปิดวิธีใช้ |

คลิกการ์ดหมวดหรือปุ่มสารบัญด้านล่างเพื่อข้ามหน้า บนอุปกรณ์สัมผัสปัดซ้าย/ขวาเพื่อเปลี่ยนหน้าได้ ลิงก์ตรงใช้ `#slide-1` ถึง `#slide-15` เช่น [หน้าผลทดลอง](https://xamr-nlp-slides.vercel.app/#slide-11) และ `#overview` สำหรับภาพรวม

รองรับ reduced motion ตามระบบ โดยปิดการซูมและแสดงจุดเหตุการณ์ในตำแหน่งสุดท้าย การเคลื่อนกล้องปกติเป็นเส้นทางตรงประมาณ 580 ms ไม่ซูมออกแล้วกลับเข้าเมื่อข้ามหมวด

## เนื้อหาและการแก้ไข

- `deck.js`: หมวด หัวข้อ เนื้อหา บทพูด และลิงก์หลักฐานอยู่ใน array `slides`; กราฟหน้า 11 ใช้ `resultRows` ไม่ใช่ผลที่คำนวณใหม่ในเบราว์เซอร์
- `style.css`: รูปแบบ ฟอนต์ ขนาดข้อความ และ animation
- `index.html`: โครงหน้าจอ ปุ่มควบคุม สารบัญ และภาพถนน SVG
- ไม่แสดงประโยคใต้หัวข้อ (`p.sub`) แล้ว แม้ฟิลด์ `sub` เดิมยังอยู่ในข้อมูล
- หน้า 2 ใช้จุดเคลื่อนรวม/แยกกลุ่ม เป็น **ภาพจำลองแนวคิด ไม่ใช่ผลโมเดล**
- หน้า 4 อธิบาย EID_N, EID_lt และ OR พร้อมตัวอย่างสมมติ; EID_N รองรับเหตุการณ์ซ้อน ส่วน EID_lt ใช้ topic, ARG0, ประเภทเหตุการณ์, สถานที่ และเวลา ไม่ใช่กฎระยะห่างของวัน
- หน้า 11 แสดง CoNLL F1 และ Pair F1 ของทั้ง Ann1/Ann2 ครบ 5 วิธีด้วยแกน 0–100 เดียวกัน; หน้า 15 เก็บเอกสารอ้างอิงไว้เป็นหน้าสำรอง
- ยังไม่ใช่ collaborative editor หรือระบบบันทึกพร้อมกัน การร่วมแก้ทำผ่านไฟล์และ Git

## หลักฐานและขอบเขตผล

เนื้อหาอ้าง [เอกสารโครงงานที่ commit 598ea069](https://github.com/Micosz/company-news-nlp-workbench/blob/598ea06926df664d439fc1e9f082ac30ec1f0d55/docs/NLP_PROJECT_HANDOFF_TH.md), [release 16 พ.ย.](../docs/WEBSITE_RELEASE_2026-11-16.md) และ [ผลอ้างอิง](../xamr_lab/research_reference.json) การปรับสไลด์ไม่ได้รัน benchmark ใหม่ หรือแก้ชุดข้อมูล โมเดล และโค้ด workbench

- Ann1/Ann2 เป็นสอง semantic input versions บน ECB+ เดียวกัน ไม่ใช่ชุดข้อมูลอิสระ
- กราฟเป็นผล development ที่ผ่านการสำรวจแล้ว ไม่ใช่ held-out final test; `test_common` เคยเปิดดูแล้ว
- OR + TF-IDF มี CoNLL เพิ่มเล็กน้อยเฉพาะ Ann2 แต่ Pair F1 ลดทั้งสองเวอร์ชัน จึงไม่อ้างว่าดีขึ้นโดยรวม
- NB guard ที่เลือกไม่ตัดเส้น (no-op) จึงได้ผลเท่า OR ไม่ใช่หลักฐานว่า NB เพิ่มคะแนน
- เว็บรับข้อมูลที่มี annotation แล้ว ไม่ใช่ raw-news extractor และยังไม่ได้พิสูจน์ statistical significance

ชื่อสมาชิกไม่ถูกเดาขึ้นมา หากต้องใส่ให้เติมก่อนนำเสนอ จำนวน 15 หน้าเป็นโครงเสนอ ไม่ใช่ rubric อาจารย์

## Deployment

สไลด์เผยแพร่แยกบน Vercel project **`xamr-nlp-slides`**, Root Directory **`slide`**, Production Branch **`main`** เป็น static HTML/CSS/JS และเชื่อม Git auto-deploy แล้ว ไม่ต้องแก้ route ของแอปวิจัย

เว็บวิจัย [xamrlab-nlp.vercel.app](https://xamrlab-nlp.vercel.app/) เป็นอีก project ที่ใช้ Root Directory `xamr_lab` จึงไม่ควรใช้ `/slide` บนโดเมนเว็บวิจัย การ push main อาจกระตุ้น build ของทั้งสอง project ตามการตั้งค่า Vercel

ก่อนเผยแพร่ ตรวจ `node --check slide/deck.js`, `git diff --check`, เปิดดูทุกหน้า ทดสอบปุ่ม/ลิงก์ ตรวจตัวเลขและขอบเขตผล แล้วตรวจสถานะ deployment และเว็บจริงหลัง push

## ภาพอ้างอิงและฟอนต์

ใช้แนวคิดภาพรวมสี่สถานีเชื่อมด้วยถนนแสงสีฟ้าและการซูมตามหัวข้อ ตามคำขอผู้ใช้ สร้าง HTML/CSS/SVG ใหม่ ไม่คัดลอก assets ของ Prezi

ใช้ฟอนต์ **Sarabun** Regular (400) และ SemiBold (600) ที่แนบใน `assets/` ไม่ใช่ TH Sarabun PSK แจกจ่ายภายใต้ SIL Open Font License 1.1 ดู [Sarabun-OFL.txt](assets/Sarabun-OFL.txt) และ [ต้นทาง Google Fonts](https://github.com/google/fonts/tree/main/ofl/sarabun) ไฟล์ Noto Sans Thai เดิมยังเก็บไว้แต่ไม่ได้เรียกใช้
