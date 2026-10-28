# ที่มาข้อมูลและการเตรียมชุดเต็ม

ดูผลตรวจแหล่งเพิ่มเติม Event StoryLine, CDEC-WN และชุดทดลองเวลา ECB+ ที่เชื่อม annotation จริงได้ใน [TEMPORAL_DATA_TH.md](TEMPORAL_DATA_TH.md)

## Pilot ที่อยู่ใน Git

`data/pilot/` มี pairs, selected event mentions และ assignments สำหรับ Pilot A/B พร้อม notices ของ ECB+ ต้นฉบับ `data/pilot_fold_A_roles_blank.xlsx` คือคู่ข้อความพร้อมช่อง roles ว่าง ไม่ใช่ชุด annotation ของผู้ซื้อ/เป้าหมายที่ทำเสร็จแล้ว

- 42 ข่าว / 42 focal mentions / 4 focal acquisition events / 424 คู่
- Same-event labels มาจาก original ECB+ event IDs
- 220 positive / 204 negative รวมทั้งสอง topics
- Pilot A: train topic 43 (AMD), test topic 44 (HP); Pilot B กลับด้าน
- จำกัดคู่ให้อยู่ภายใน topic เดียวกันเพื่อลด easy negatives ข้ามบริษัท

ข้อมูลนี้ช่วยตรวจ pipeline และตั้งแผนทดลอง ยังไม่พอสำหรับอ้างผลทั่วไปของ M&A news

## ECB+

แหล่งต้นฉบับ: https://github.com/cltl/ecbPlus

Citation: Agata Cybulska and Piek Vossen. 2014. *Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution.* LREC 2014.

ใช้ XML ใน ECB+.zip และ official selected-sentence filter เพื่อเลือก gold event mentions ก่อนสร้างคู่ โค้ดเตรียมข้อมูลอยู่ที่ `scripts/prepare_datasets.py` ส่วน licenses ต้นฉบับอยู่ใน `data/pilot/licenses/ecbplus/` ข้อความข่าวมีสิทธิ์ของสำนักข่าวแยกจาก annotation

## TKGQA (เสริมสำหรับการสำรวจ ไม่ได้รวมเป็น gold coreference)

- Dataset: https://osf.io/xqwa4/
- Paper: https://doi.org/10.3390/data8030061
- Sentence/role CSV: https://osf.io/download/y65b9/
- Article URL mapping: https://osf.io/download/swrn9/

Citation: Ong, Sun, Serban and Guo (2023). *TKGQA Dataset: Using Question Answering to Guide and Validate the Evolution of Temporal Knowledge Graph.*

ไฟล์ที่เตรียมไว้มี 5,721 snippets จาก 5,390 article IDs ข้อมูล roles/stages มีทั้งการทำป้ายกำกับและการทำนายของโมเดล ไม่ใช่ gold event coreference ที่อิสระ ห้ามใช้ company-pair ที่ตรงกันสร้าง gold แล้วนำ roles เดิมมาวัด improvement วนซ้ำ

## เตรียมชุดเต็มบนเครื่องใหม่

Pilot ไม่ต้องดาวน์โหลดเพิ่ม ชุดเต็มเป็น optional เพราะมีข้อมูลหลายโดเมนและไฟล์ใหญ่กว่า การดาวน์โหลดครั้งนี้ใช้ public sources และตรวจ SHA-256 ที่ตรึงไว้ ถ้าแหล่งข้อมูลเปลี่ยน script จะหยุดให้ตรวจ แทนที่จะใช้ข้อมูลใหม่เงียบ ๆ

ใช้ Python environment เดียวกับแอป จาก root ของ repo:

```sh
.venv/bin/python scripts/download_sources.py
.venv/bin/python scripts/prepare_datasets.py --source-root local_data/raw --output-root local_data/prepared
```

จากนั้นเปิดแอปพร้อมบอกตำแหน่ง dataset:

```sh
NLP_DATASET_ROOT="$PWD/local_data/prepared" .venv/bin/python server.py --open-browser
```

หรือรัน CLI:

```sh
NLP_DATASET_ROOT="$PWD/local_data/prepared" .venv/bin/python run_experiment.py --dataset full
```

PowerShell หลังเตรียมข้อมูล:

```powershell
$env:NLP_DATASET_ROOT = "$PWD/local_data/prepared"
.venv\Scripts\python.exe server.py --open-browser
```

`NLP_DATASET_ROOT` ต้องชี้โฟลเดอร์ที่ข้างในมี `full/ecbplus/` ไม่ใช่ชี้ CSV โดยตรง หากมี full package ที่เตรียมไว้แล้ว ให้ใช้โฟลเดอร์แม่ของ `full/` ได้เลย ระบบยังรองรับตำแหน่งเดิม `../nlp_datasets_2026-10-26/full/ecbplus` บนเครื่องพัฒนา

## ชุดเต็มที่คาดว่าจะได้จาก source version นี้

- ECB+: 982 ข่าว, 43 topics, 6,821 selected event mentions
- คู่ 104,840 คู่: positive 26,210 + sampled negative 78,630
- Custom train/dev/test: 70,280 / 15,972 / 18,588 คู่
- TKGQA: records และ 637 candidate pairs ที่ยังต้อง review; labels ของ coreference ว่าง
- SHA-256 และ summary ของ source/output อยู่ใน package ที่ builder สร้าง

Split และ sampling นี้เป็นการเตรียมข้อมูลของโครงการ ไม่ใช่ benchmark split ของ paper มีเพียง 4 focal finance events ใน pilot; การเพิ่ม mixed-domain full ไม่ได้ทำให้มี gold M&A ใหม่จำนวนมาก

**Pilot topics อยู่ใน full test** หากใช้ pilot เลือก features หรือดู errors แล้ว ให้ถือ full run เป็นการตรวจรันได้ ห้ามนำเสนอว่าเป็น finance test ที่ยังไม่เคยเห็น

ไฟล์ดิบและไฟล์เตรียมใหม่อยู่ใต้ `local_data/` ซึ่งถูก ignore ใน Git ก่อนแบ่งปันข้อมูลหรือผลชุดใหม่ให้ตรวจ provenance/สิทธิ์ของแหล่งข้อมูลและเก็บเลข version เสมอ
