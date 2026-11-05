# Company News NLP — two research workbenches

แยกสองเว็บใน branch `main` โดยไม่ผสมวิธีทดลองเข้าด้วยกัน

| โฟลเดอร์ | หน้าที่ | การใช้งาน |
|---|---|---|
| [`pair_workbench/`](pair_workbench/) | เว็บเดิม: TF-IDF / Naive Bayes, role/date features, NLI graph | รันบนเครื่อง มีช่องแก้ Python จึงยังไม่เปิดรันสาธารณะบน Vercel |
| [`xamr_lab/`](xamr_lab/) | X-AMR เดิม 4 วิธี เทียบ OR + temporal clustering | รันบนเครื่องหรือออนไลน์ผ่าน Vercel |

## เปิดในเครื่อง

- เว็บเดิม: เปิด `pair_workbench/Start_Workbench.command` (port 8765)
- X-AMR: เปิด `Start_XAMR.command` (port 8767)
- ย้ายไฟล์โค้ดเดิมเท่านั้น ผลทดลอง/virtualenv ที่เคยสร้างไว้ไม่ได้ย้ายหรือรวมอัตโนมัติ

## Deploy X-AMR บน Vercel — รันการทดลองจริง

1. Import GitHub repository นี้ หรือเปิด Project Settings ของโปรเจกต์เดิม
2. Production Branch: `main`
3. Root Directory: **`xamr_lab`** (ไม่ใช่ root ของ repo)
4. Framework: FastAPI หากไม่ตรวจพบอัตโนมัติ ใช้ Python 3.12 ตาม `.python-version`
5. ไม่ตั้ง Output Directory เป็น static และไม่ต้องกำหนด frontend build command
6. เลือกเปิด Fluid Compute; `vercel.json` กำหนด maxDuration 300 วินาที
7. หากต้องการจำกัดคนรัน ตั้ง environment variable `XAMR_ACCESS_KEY` แล้วกรอกรหัสบนหน้าเว็บ
8. Deploy แล้วทดสอบ `ann1-dev_small` ก่อน `ann1-dev`

เอกสารทางการ: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Function limits](https://vercel.com/docs/functions/limitations)

### การทำงานออนไลน์และข้อจำกัด

- `app.py` ใช้ engine เดียวกับ local และรันทั้ง 5 วิธีจริงภายในคำขอเดียว ไม่มี mock scores
- ดาวน์โหลดเฉพาะชุดที่เลือกจาก commit ของผู้เขียน ตรวจ SHA-256 ก่อนรัน ไม่ต้องเตรียม dataset ในเครื่องผู้ชม
- รับข้อมูลที่มี annotation แล้ว ไม่ได้เรียก LLM อ่านข่าวดิบ
- จำกัด 2,000 mentions / คำขอ 3 MB / ผลตอบกลับ 4 MB ชุด train ที่เกินขนาดยังใช้ local ได้
- ผลและ ZIP ถูกส่งกลับทันที ประวัติอยู่ใน IndexedDB ของเบราว์เซอร์ ไม่ใช่ฐานข้อมูลร่วม ไม่มีการเก็บไฟล์ถาวรบน Vercel
- ล้าง browser storage หรือเปลี่ยนเครื่องจะไม่เห็นประวัติเดิม ดาวน์โหลด ZIP เพื่อใช้ในรายงานทุกครั้ง
- ปิดหน้าเว็บ/เครือข่ายหลุดก่อนคำขอจบอาจไม่ได้รับผล ไม่มี queue/resume หรือ background worker
- งานที่เกิน timeout หรือขนาดผลตอบกลับให้รัน local; ความเร็วในเครื่องไม่ใช่หลักฐานว่า Vercel จะเสร็จทัน
- เว็บเดิมยังเป็น local-only การย้ายไว้ใน main ไม่ได้ทำให้ช่องรัน Python อิสระเหมาะกับ public server โดยอัตโนมัติ

## งานวิจัยและข้อมูล

อ่าน [X-AMR methods / reproduction](xamr_lab/README.md) และ [source notice](xamr_lab/NOTICE.md)
อ่าน [เว็บเดิมและ dataset](pair_workbench/README_TH.md)

ผล development ไม่ใช่ held-out test และวิธีที่เพิ่มยังไม่รับประกันว่าคะแนนดีขึ้น
