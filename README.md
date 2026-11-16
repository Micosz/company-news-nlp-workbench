# Company News NLP — two research workbenches

หน้าหลักใหม่เป็น **X-AMR Research Workbench** สำหรับ OR, TF-IDF, OR + TF-IDF และ OR + TF-IDF + Naive Bayes ที่รันจริงจาก preset ที่เลือกด้วย train CV พร้อมดาวน์โหลด ZIP/CSV/JSON และ replay ได้ ดู [วิธีใช้งานและข้อจำกัด](docs/WEBSITE_RELEASE_2026-11-16.md)

หน้า temporal เดิมอยู่ที่ `/paper` โดยเก็บ HTML เดิม ส่วน `/legacy` และ Pair Workbench เดิมยังคงเดิม

X-AMR Research Lab เมนู **เดโม** เปิดตัวอย่างข่าวจริงจาก ECB+ และฟอร์มกรอกข้อมูลเหตุการณ์ เมนู **ผลทดลองเดิม** เปิดหน้าอ้างอิงของ Pair Workbench เมื่อเปิดทั้งสองเว็บในเครื่อง เมนู **เว็บเก่า · Pair Workbench** จะพาไปยังเวอร์ชันที่รันการทดลองได้

| โฟลเดอร์ | หน้าที่ | การใช้งาน |
|---|---|---|
| [`pair_workbench/`](pair_workbench/) | เว็บเดิม: TF-IDF / Naive Bayes, role/date features, NLI graph | ดูผลที่ `/legacy` หรือเปิดฉบับเต็มในเครื่องเพื่อรัน Python |
| [`xamr_lab/`](xamr_lab/) | X-AMR เดิม 4 วิธี เทียบ OR + temporal clustering | รันบนเครื่องหรือออนไลน์ผ่าน Vercel |

## เว็บออนไลน์และงานวิจัยอ้างอิง

**เปิดเว็บวิจัยใหม่: [X-AMR Research Lab](https://xamrlab-nlp.vercel.app/)**

| งานวิจัย | Paper | GitHub ของผู้เขียน | ใช้ในโครงงานนี้ |
|---|---|---|---|
| CohTP — Incorporating Temporal Coherence to Cross-Document Event Coreference Resolution (2026) | [ACL Anthology](https://aclanthology.org/2026.acl-long.1345/) · [PDF](https://aclanthology.org/2026.acl-long.1345.pdf) | [chenxinyu-nlp/CohTP](https://github.com/chenxinyu-nlp/CohTP) | งานอ้างอิงของแนวทางเดิม ไม่ใช่ implementation ที่เว็บเดิมรัน |
| X-AMR — Linear Cross-document Event Coreference Resolution with X-AMR (2024) | [ACL Anthology](https://aclanthology.org/2024.lrec-main.920/) · [PDF](https://aclanthology.org/2024.lrec-main.920.pdf) | [ahmeshaf/gpt_coref](https://github.com/ahmeshaf/gpt_coref) | ฐานการทดลองเว็บใหม่ ใช้โค้ดและ annotation ของผู้เขียนจาก commit ที่ตรึงไว้ |

ตรวจเมื่อ 5 พฤศจิกายน 2026: repository CohTP ยังมีเพียงไฟล์ `Comming soon` จึงยังไม่ใช่โค้ดพร้อมรัน ส่วน X-AMR มีโค้ดที่ใช้ในการทดลองนี้ ดูรายละเอียดใน [NOTICE](xamr_lab/NOTICE.md)

## เปิดในเครื่อง

ตั้งค่า Python แยกตามแต่ละเว็บ เพราะเวอร์ชันของ dependencies ต่างกัน

```sh
python3.12 -m venv .venv-xamr
.venv-xamr/bin/python -m pip install -r xamr_lab/requirements.txt
.venv-xamr/bin/python xamr_lab/setup_data.py
python3.12 -m venv pair_workbench/.venv
pair_workbench/.venv/bin/python -m pip install -r pair_workbench/requirements.txt
.venv-xamr/bin/python launch_workbenches.py
```

ตัวเปิดจะพาไปหน้า X-AMR ที่ `http://127.0.0.1:8767/` เมื่อทั้งสองบริการพร้อม เมนู **เว็บเก่า · Pair Workbench** เปิดเว็บเดิมที่พอร์ต 8765 และ **กลับ X-AMR** พากลับหน้าหลัก กด Ctrl+C ใน Terminal เพื่อหยุดทั้งสองบริการ

ถ้ามี environment อยู่แล้ว ให้ระบุ Python ด้วย `--xamr-python` หรือ `--pair-python` เปลี่ยนพอร์ตได้ด้วย `--xamr-port` และ `--pair-port` บน Windows ให้แทน `bin/python` ด้วย `Scripts/python.exe` และใช้ `py -3.12` สร้าง environment

เปิดแยกเฉพาะเว็บที่ต้องการได้ด้วย

- เว็บเดิม: เปิด `pair_workbench/Start_Workbench.command` (port 8765)
- X-AMR: เปิด `Start_XAMR.command` แล้วไปที่ `http://127.0.0.1:8767/`
- เส้นทางบน X-AMR ได้แก่ `/` สำหรับ workbench ใหม่, `/paper` สำหรับ temporal lab เดิม, `/demo` สำหรับเดโม และ `/legacy` สำหรับผลทดลองเดิม

## Deploy X-AMR บน Vercel — รันการทดลองจริง

1. Import GitHub repository นี้ หรือเปิด Project Settings ของโปรเจกต์เดิม
2. Production Branch: `main`
3. Root Directory: **`xamr_lab`** (ไม่ใช่ root ของ repo)
4. Framework: FastAPI หากไม่ตรวจพบอัตโนมัติ ใช้ Python 3.12 ตาม `.python-version`
5. ไม่ตั้ง Output Directory เป็น static และไม่ต้องกำหนด frontend build command
6. เลือกเปิด Fluid Compute; `vercel.json` กำหนด maxDuration 300 วินาที
7. หากต้องการจำกัดคนรัน ตั้ง environment variable `XAMR_ACCESS_KEY` แล้วกรอกรหัสบนหน้าเว็บ
8. เมื่อพร้อม deploy ให้ลองเปิด `/` → `/paper` → `/demo` → `/legacy` แล้วกดกลับหน้าหลัก ลอง Compare บน Ann1/Ann2 dev และตรวจ source hashes จาก `/api/workbench/catalog`

เอกสารทางการ: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Function limits](https://vercel.com/docs/functions/limitations)

### การทำงานออนไลน์และข้อจำกัด

- `/` ใช้ fixed research runner สำหรับ 4 วิธี และเทียบ OR ทุกครั้ง ส่วน `/paper` รัน temporal engine เดิมทั้ง 5 วิธี ไม่มี mock scores
- ดาวน์โหลดเฉพาะชุดที่เลือกจาก commit ของผู้เขียน ตรวจ SHA-256 ก่อนรัน โมเดล JSON ฝึกจาก train และแนบผล CV ที่ตรึงไว้ ไม่ต้องเตรียม dataset ในเครื่องผู้ชม
- รับข้อมูลที่มี annotation แล้ว ไม่ได้เรียก LLM อ่านข่าวดิบ
- จำกัด 2,000 mentions / คำขอหน้าใหม่ 4 KB (หน้า temporal เดิม 3 MB) / ผลตอบกลับ 4 MB ชุด train ใช้สำหรับเตรียมโมเดลแยกจากหน้า inference
- ผลและ ZIP ถูกส่งกลับทันที ประวัติอยู่ใน IndexedDB ของเบราว์เซอร์ ไม่ใช่ฐานข้อมูลร่วม ไม่มีการเก็บไฟล์ถาวรบน Vercel
- ล้าง browser storage หรือเปลี่ยนเครื่องจะไม่เห็นประวัติเดิม ดาวน์โหลด ZIP เพื่อใช้ในรายงานทุกครั้ง
- ปิดหน้าเว็บ/เครือข่ายหลุดก่อนคำขอจบอาจไม่ได้รับผล ไม่มี queue/resume หรือ background worker
- งานที่เกิน timeout หรือขนาดผลตอบกลับให้รัน local; ความเร็วในเครื่องไม่ใช่หลักฐานว่า Vercel จะเสร็จทัน
- เว็บเดิมยังเป็น local-only การย้ายไว้ใน main ไม่ได้ทำให้ช่องรัน Python อิสระเหมาะกับ public server โดยอัตโนมัติ

## งานวิจัยและข้อมูล

อ่าน [X-AMR methods / reproduction](xamr_lab/README.md) และ [source notice](xamr_lab/NOTICE.md)
อ่าน [เว็บเดิมและ dataset](pair_workbench/README_TH.md)

ผล development ไม่ใช่ held-out test และวิธีที่เพิ่มยังไม่รับประกันว่าคะแนนดีขึ้น
