# X-AMR Final Presentation

สไลด์ HTML 15 หน้า พร้อมภาพรวม 4 หมวดและบทพูดภาษาไทย

## เปิดในเครื่อง

จาก root ของ repository: `python3 -m http.server 8767 --bind 127.0.0.1`

เปิด http://127.0.0.1:8767/slide/ หรือเปิด `slide/index.html` โดยตรง ไม่มี build หรือ dependency ใหม่ ฟอนต์ Sarabun แนบไว้พร้อม OFL (ไฟล์ Noto Sans Thai เดิมเก็บไว้แต่ไม่ได้เรียกใช้)

- ลูกศร / Space: เดินเรื่อง; Esc หรือ O: ภาพรวม; N: บทพูด; F: เต็มจอ
- เลือกสถานีหรือสารบัญเพื่อข้ามหมวด; URL `#slide-11` เปิดหน้าผลทดลอง
- รองรับ reduced motion ตามระบบ ไม่ใส่ animation หากเปิดใช้งาน
- เนื้อหาและบทพูดเป็นแหล่งเดียวใน `deck.js` (array `slides`) ไม่ต้องแก้สำเนาข้อมูลใน HTML
- ยังไม่ใช่ collaborative editor หรือระบบบันทึกพร้อมกัน

## หลักฐานและขอบเขต

เนื้อหาอ้างเอกสารโครงงานที่ GitHub commit `598ea069`, release 16 พ.ย. และผลเดิมใน `research_reference.json` ไม่ได้รัน benchmark ใหม่ ไม่แก้ชุดข้อมูล โมเดล หรือโค้ด workbench

Ann1/Ann2 เป็นสอง semantic input versions บน ECB+ เดียวกัน; dev ผ่านการสำรวจ; test_common เคยเห็นแล้ว; NB guard ที่เลือกเป็น no-op ไม่ใช่ improvement; raw-news extraction และ statistical significance ไม่ได้ถูกพิสูจน์

ชื่อสมาชิกไม่ถูกเดาขึ้นมา หากต้องใส่ให้เติมบนหน้าปกก่อนนำเสนอ จำนวน15หน้าเป็นโครงเสนอ ไม่ใช่rubricอาจารย์

## Deployment

โฟลเดอร์นี้อยู่ root ของ repo แต่ Vercel เดิมใช้ Root Directory `xamr_lab` จึงไม่ได้ทำให้ production มี route /slide โดยอัตโนมัติ การเพิ่มสไลด์เข้า GitHub ไม่ได้แก้ app routes หรือ deployment configuration. หากต้องการเผยแพร่ต้องเลือกและอนุญาตขั้นตอนนั้นแยก

## ภาพอ้างอิง

ใช้แนวคิดภาพรวมสี่สถานีเชื่อมด้วยถนนแสงสีฟ้าและการซูมตามหัวข้อ ตามคำขอผู้ใช้ งานนี้สร้าง HTML/CSS/SVG ใหม่ ไม่คัดลอก assets ของ Prezi

### Typography
Thai reading text uses locally hosted **Sarabun** Regular (400) and SemiBold (600), from Google Fonts. This is Sarabun, not TH Sarabun PSK. Distributed under SIL Open Font License 1.1; see `assets/Sarabun-OFL.txt`. Source: https://github.com/google/fonts/tree/main/ofl/sarabun . Thai wraps at normal word boundaries; no forced word-breaking or text clipping is used.
