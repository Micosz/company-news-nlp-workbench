# ชุดข่าวและเวลาสำหรับทดลองเพิ่มเติม

## ข้อมูลที่เตรียมและข้อจำกัด

| แหล่ง | สิ่งที่ตรวจพบ | การใช้งาน |
|---|---|---|
| [ECB+](https://github.com/cltl/ecbPlus), [Cybulska & Vossen (2014)](https://aclanthology.org/L14-1646/) | ชุดเต็มที่โครงการเตรียมไว้มี 982 ข่าว, 6,821 selected event mentions และ 104,840 คู่จาก 43 หัวข้อ ป้าย same-event มาจาก annotation ต้นฉบับ | ชุดหลักสำหรับ cross-document coreference; คู่ลบในไฟล์ถูกสุ่มตามสัดส่วนของโครงการ ไม่สะท้อนสัดส่วนข่าวจริง |
| [Event StoryLine v1.0](https://github.com/tommasoc80/EventStoryLine), [Caselli & Vossen (2017)](https://aclanthology.org/W17-2711/) | 258 ข่าวมี annotation เพิ่มบนส่วนหนึ่งของ ECB+; v1.0 ระบุ TLINK จาก time expression ไป event | จับคู่กับ ECB+ ที่เป็นข่าวเดียวกัน ใช้เฉพาะ date แบบ YYYY-MM-DD ที่ source ระบุว่าเวลาครอบคลุม event (`CONTAINS`); ไม่ใช่ dataset ข่าวอิสระอีกชุด |
| [CDEC-WN v1.0](https://github.com/adithya7/cdec-wikinews), [Pratapa et al. (2021)](https://aclanthology.org/2021.conll-1.39/) | release ที่ตรวจมี 176 ข่าว Wikinews และ 4,282 **คู่เชื่อมที่เป็นบวก**: full 2,914 และ partial 1,368; train 3,140 / test 1,142 คู่ | เตรียมไฟล์ตรวจสอบแยก ยังไม่รวม train/test แบบ binary; release ที่ตรวจไม่ได้แจกคู่ลบในไฟล์นี้ การไม่มีลิงก์ไม่ใช่เฉลยว่าเป็นคนละเหตุการณ์ และ partial มีนิยามต่างจาก ECB+ |
| [TKGQA](https://osf.io/xqwa4/), [Ong et al. (2023)](https://doi.org/10.3390/data8030061) | 5,721 snippets ที่เตรียมไว้จาก 5,390 article IDs; มีวันที่เผยแพร่และข้อมูลสถานะ/บทบาทตามต้นทาง | สำรวจข่าวการเงินและ timeline แยก; วันเผยแพร่ไม่ใช่วันเกิดเหตุการณ์ และ 637 คู่ candidate ยังไม่มี gold coreference |
| [MAVEN-ERE](https://github.com/THU-KEG/MAVEN-ERE), [Wang et al. (2022)](https://aclanthology.org/2022.emnlp-main.60/) | Wikipedia พร้อม event relations/temporal labels ภายในเอกสาร; gold test ของผู้จัดทำถูกซ่อน | แหล่งศึกษาเทคนิคเวลา ยังไม่ได้ดาวน์โหลดหรือรวม; ไม่ใช่คู่ข่าว cross-document |

ไม่สุ่มเอา datasets ที่นิยาม label ต่างกันมาปนโดยถือว่าเทียบเท่ากัน ไม่ใส่ buyer/target ให้ข่าวทั่วไป และไม่ใช้วันเผยแพร่แทนเวลาเหตุการณ์โดยไม่มีหลักฐาน

## ชุด ECB+ × Event StoryLine: สร้างจาก annotation จริง

สคริปต์ `scripts/build_story_time.py` ตรวจ SHA-256 ของ ECB+.zip และ Event StoryLine ที่ pin commit ไว้ อ่าน 258 เอกสาร ตรวจว่า token map ของสองชุดตรงกันทุกเอกสาร แล้วเชื่อมด้วย document ID และ **unique event token span** เพราะรหัส mention ระหว่างสองชุดอาจไม่ตรงกัน สคริปต์ตรวจเฉลย coreference กับ XML ต้นฉบับ ไม่สร้าง label จากวันเวลา

คัด `TIME_DATE` ที่เป็นวันปฏิทินจริงแบบ `YYYY-MM-DD`, TLINK จากเวลาไปเหตุการณ์เป็น `CONTAINS`, modality `ACT` หรือไม่ได้ระบุ; **modality ที่ไม่ได้ระบุไม่ถือว่าเป็นความจริงที่ยืนยันแล้ว** ไม่ใช้ mention ที่จับคู่ได้หลายแบบหรือมีวันที่ขัดกัน เลือกคู่จาก ECB+ ที่ทั้งสองฝั่งผ่านเงื่อนไข

ผลที่สร้างจาก source และ split ของโครงการในเครื่องนี้:

- 793 mentions ที่มีวันจาก annotation, 181 เอกสาร; 4,732 คู่จาก 21 หัวข้อ
- 21 หัวข้อนี้ไม่รวมสองหัวข้อซื้อกิจการ AMD/HP ของ Pilot เดิม (43 และ 44) จึงยังไม่ใช่หลักฐานว่าการเพิ่มเวลาใช้ได้ดีกับข่าว M&A
- Train 2,850 คู่ / 16 หัวข้อ; dev 880 คู่ / 3 หัวข้อ; test 1,002 คู่ / **2 หัวข้อ**; label 1 = 2,583 และ label 0 = 2,149
- ใน 4,732 คู่ มี **1,540 คู่ที่วันตรงกันแต่เป็นคนละ event** และ **399 คู่ที่วันต่างกันแต่มี label event เดียวกัน** ตาม annotation ต้นทาง การเลือกวันเดียวกันจึงไม่ใช่กฎตัดสิน coreference
- `event_date_a`/`event_date_b` เป็น **oracle dates** จาก annotation ไม่ใช่ผลจากระบบดึงเวลาของเรา; บาง TLINK ใช้วันสร้างเอกสารเมื่อผู้จัดทำ annotate ว่าเวลานั้นครอบคลุม event แต่เราไม่ได้เหมารวมว่าทุกวันเผยแพร่คือวันเกิดเหตุการณ์
- ชุดนี้เลือกเฉพาะคู่ที่มีวันที่ครบ ไม่ครอบคลุมช่วงเวลา/วันที่ไม่ชัด และ time annotation อาจอาศัยข้อความนอก snippet เช่น DCT; ใช้เพื่อดูศักยภาพของ feature ไม่ใช่การประเมิน extraction end-to-end
- split เป็น custom topic split ของโครงการ ไม่ใช่ split ตาม CohTP; test มีแค่สองหัวข้อและมีการดูผล/สำรวจ ECB+ มาก่อน จึงไม่ใช่ held-out สุดท้ายที่ไม่เคยเห็น หรือหลักฐานว่าสรุปผลทั่วไปได้

### ผลตรวจรันได้ในเครื่อง (สำรวจ ไม่ใช่ผลสุดท้าย)

รอบ `20261028T115953Z_a58ea6` ใช้ชุด 4,732 คู่, Text baseline, Time only และ Text + event date โดยใช้ Categorical Naive Bayes/threshold เดียวกัน ได้ pairwise F1 **69.62% ทั้งสามแบบ** และทำนาย test ทั้งหมดเป็น class 1 (TP 535, FP 467, FN 0, TN 0; Macro F1 34.81%) เหมือน majority reference ในรอบนี้ จึง **ยังไม่พบ improvement** และห้ามปรับค่าจาก test นี้แล้วอ้างว่าเป็นการทดสอบใหม่ จำนวนคู่ไม่ใช่จำนวนเหตุการณ์อิสระ

ในเว็บนำเข้า `ecb_story_pairs.csv`, ตรวจ mapping ของ `event_date_a`/`event_date_b`, เลือกที่มาเวลา **ป้ายกำกับจากชุดข้อมูล (oracle)** แล้วรัน ค่า `event_day_relation` แยก unknown / วันเดียวกัน / วันต่างกัน เป็น feature แบบ soft ไม่ตัดสิน identity ด้วยกฎวันตรงกัน ค่า Text baseline, Time only และ Text + event date ถูกฝึกบนข้อมูล train เดียวกัน

## สร้างไฟล์ในเครื่องใหม่

เริ่มจากติดตั้งตาม README แล้วเตรียม ECB+ full ตาม [DATA_SOURCES_TH.md](DATA_SOURCES_TH.md) ซึ่งตรวจ SHA-256 ของต้นฉบับ รวมทั้งดาวน์โหลด Event StoryLine และ CDEC-WN จาก release ที่ตรึงค่า:

```sh
.venv/bin/python scripts/download_sources.py
.venv/bin/python scripts/prepare_datasets.py --source-root local_data/raw --output-root local_data/prepared
.venv/bin/python scripts/download_research_sources.py
.venv/bin/python scripts/build_story_time.py \
  --story-zip local_data/external_sources/eventstoryline-46edefee.zip \
  --ecb-zip local_data/raw/ecbplus/ECB+.zip \
  --full-root local_data/prepared --output-dir local_data/ecb_story_time
.venv/bin/python scripts/inspect_cdec_wn.py \
  --archive local_data/external_sources/cdec-wn-dataset-v1.tar.gz \
  --output-dir local_data/cdec_wn
```

PowerShell ใช้ `.venv\Scripts\python.exe` และเปลี่ยนการขึ้นบรรทัดตาม shell; สคริปต์ไม่เขียนทับไฟล์ผลลัพธ์เดิม หาก output มีอยู่ให้เลือกโฟลเดอร์ใหม่ ในเครื่องผู้พัฒนามี `local_data/ecb_story_time_v1/ecb_story_pairs.csv` และ `local_data/cdec_wn_v1/` แล้ว ไฟล์ข่าวและ archive เก็บเฉพาะ local_data ที่ไม่ติดตามใน Git; ผู้ร่วมงานต้องสร้างเองจาก source ไม่ได้อยู่ใน GitHub

สคริปต์ตรวจ source hash, span, labels และ train/test document/topic overlap แต่ไม่ยืนยันความถูกต้องของคำอธิบาย event/date ของผู้ทำ annotation; ต้องตรวจข้อจำกัดและสิทธิการเผยแพร่ข่าวจากต้นทางก่อนใช้หรือเผยแพร่ต่อ
