## Deployment

This app is now in `xamr_lab/` on `main`. See [root deployment instructions](../README.md). Online mode runs the same engine, limits inputs to 2,000 mentions, and stores returned evidence in browser IndexedDB. Local mode keeps filesystem history.

# X-AMR Research Lab

เว็บทดลองใน `xamr_lab/` บน `main` พอร์ต 8767 เว็บเดิมอยู่ใน `pair_workbench/` ไม่ใช่ CohTP reproduction

## เปิดเว็บ

macOS: ดับเบิลคลิก `Start_XAMR.command` จาก root ของ repository ครั้งแรกต้องมีอินเทอร์เน็ตเพื่อติดตั้ง dependencies และดาวน์โหลด annotation จาก commit ที่ตรึงไว้ พร้อมตรวจ SHA-256 ทุกไฟล์ ใช้ Python 3.9–3.12

Windows / Linux หรือรันเอง:

```sh
python3 -m venv .venv-xamr
.venv-xamr/bin/python -m pip install -r xamr_lab/requirements.txt
.venv-xamr/bin/python xamr_lab/setup_data.py
.venv-xamr/bin/python xamr_lab/server.py --port 8767
```

Windows ใช้ `py -3.11 -m venv .venv-xamr` และ `.venv-xamr\Scripts\python.exe` แทนคำสั่ง Python ของ venv เปิด http://127.0.0.1:8767 ไม่ใช้ file://

## Workflow

1. เลือก `ann1-dev` เพื่อสำรวจ หรือใช้ JSON/CSV ที่มี schema ครบ
2. ตั้ง tolerance จาก train/dev เท่านั้น เริ่ม 0 วัน ไม่ปรับเพื่อไล่คะแนนบน test
3. รันทั้ง 5 วิธี: EID_N, EID_lt, AND, OR, OR_temporal
4. ดู CoNLL, MUC, B3, CEAF_e, pair P/R/F1, confusion counts, errors, date coverage
5. ดาวน์โหลด ZIP เพื่อจัดทำรายงาน ตัวเลขเปอร์เซ็นต์ใน CSV/LaTeX แต่ JSON เก็บ fractions
6. เมื่อวิธีนิ่งแล้วจึงเลือก test_common + Held-out และยืนยัน protocol ทุกครั้งที่เปิดดู test ถูกเก็บใน history การกดยืนยันไม่ทำให้ test ที่เคยใช้ปรับวิธีกลายเป็น untouched test

## Research question

การเพิ่มการตรวจความเข้ากันของช่วงเวลาในระดับกลุ่มช่วยลด false-positive merges ของ X-AMR แบบ OR ได้หรือไม่ และเสีย recall เท่าไร?

Base: annotations -> original EIDs -> original OR edges -> connected components.
Proposed: annotations -> same EIDs -> same OR edges -> greedy merging with cluster temporal constraints.

ก่อนรวมกลุ่ม A/B ตรวจทุกคู่ข้ามกลุ่มที่ parse ช่วงเวลาได้ หากช่วงแยกกันเกิน tolerance จะระงับการรวม ไม่ใช้ gold label ในการตัดสิน Gold ใช้สำหรับ evaluation เท่านั้น ไม่เพิ่ม/แก้ annotation เพื่อให้ผลดีขึ้น

- ลำดับ edge ตาม mention_id คงที่ ผล deterministic ไม่ใช้ random seed แต่ไม่อ้างว่า order-invariant ต่อการเปลี่ยน ID
- Unknown ไม่ใช่ conflict
- รองรับ YYYY, YYYY-MM, ISO date, English day/month names, month/year, explicit English ranges; slash dates และ relative dates ไม่เดา
- เวลาเป็น event time จาก annotation ไม่ใช่ publication time
- Partial precision (ปี/เดือน) แปลงเป็นช่วง ทั้งช่วงต้องไม่ทับกันจึง conflict
- เป็น hard temporal heuristic; ongoing events หรือ annotations ผิดอาจทำให้ recall ลด
- ต้องเทียบ AND ด้วย ไม่อ้างว่า OR vs temporal อย่างเดียวเพียงพอ
- runtime วัด clustering แยกจาก preprocessing/evaluation ไม่ใช่ประสิทธิภาพ production
- constrained merge อาจต้องตรวจหลายคู่ ไม่คงคำอ้าง linear complexity ของ paper

## ข้อมูล

จาก https://github.com/ahmeshaf/gpt_coref ที่ commit ใน NOTICE.md
- Human ann1/ann2: train 3,194, dev 1,245, dev_small 120, test_common 847 mentions ต่อ annotator
- GPT-4 G1/G2: archived dev_small outputs 120 mentions ไม่เรียก API ใหม่
- Ann1/Ann2 ใช้ mentions เดียวกัน ไม่ใช่ independent datasets
- test_common เป็น annotated subset ไม่ใช่ official ECB+ test ทั้งหมด ต้องรายงาน coverage
- Human roles/time ใช้ข้อมูล annotation ที่พร้อมอยู่แล้ว ไม่ใช่ automatic extraction; การประเมินชั้น clustering เท่านั้น
- CSV/JSON custom ต้องมี mention_id, topic, doc_id, sentence_id, lemma, roleset_id, arg0, arg1, argL, argT, gold_cluster
- ช่อง arguments/roleset อาจว่างเพื่อรักษาข้อมูลต้นฉบับ ID/topic/gold ต้องไม่ว่าง ต้องไม่มี mention_id ซ้ำ
- ไม่โหลดไฟล์ Excel โดยตรง ให้ export CSV/JSON; raw news ยังต้องสร้าง annotations ก่อน

## สิ่งที่นำไปใช้เขียน paper ได้

- Methods: เปรียบเทียบเฉพาะขั้น clustering, no VerbNet; interval parser และ deterministic edge order
- Setup: provenance hash, subset/split, annotation source, coverage, selected tolerance, environment
- Results: metrics.csv และ table.tex จากรันจริง ใช้ full precision คำนวณ CoNLL
- Upstream reproduction: `paper_rounded_CoNLL` เลียนแบบการปัด intermediate scores ของผู้เขียน เพื่อเทียบตาราง ไม่ใช้แทน raw-score mean
- Error analysis: error_examples.csv (สูงสุด 500 คู่), blocked_merges.csv พร้อม witness; exact aggregate confusion ไม่ถูกจำกัด
- Reproducibility: input.json, source snapshots, source SHA-256, upstream/checkout commit, config, pip freeze, gold/predicted keyfiles

ยังไม่พร้อมอ้างผลวิจัยขั้นสุดท้ายเพียงเพราะเว็บพร้อม: ต้องล็อก protocol, ประเมิน held-out ที่ไม่ใช้ปรับวิธี, วิเคราะห์ error, แยก human/predicted, และประเมินความไม่แน่นอนของผลหากจะอ้าง statistical significance เว็บไม่สร้างค่า p-value หรือ CI ปลอม ไม่มีการทดลองซ้ำ random seeds สำหรับขั้น deterministic

## Tests

```sh
.venv-xamr/bin/python -m unittest discover -s xamr_lab -p 'test_*.py' -v
```

Evidence of the initial development runs is in `verification.json` (aggregate results only, not test results). Full local run bundles are ignored in Git. Local source snapshots, not checkout commit alone, identify the actual executed code when the worktree was dirty.

## Command-line / replay

```sh
.venv-xamr/bin/python xamr_lab/cli.py --dataset ann1-dev --tolerance-days 0
.venv-xamr/bin/python xamr_lab/cli.py --replay /absolute/path/to/unpacked-run
```

Replay ใช้ input/config เดิมกับโค้ด checkout ปัจจุบัน หากต้องการโค้ดเดียวกับรอบเดิม ให้ตรวจ source SHA-256 เทียบ snapshot ใน ZIP ก่อน ตัวเลขเวลารันและ ID รอบย่อมต่างกัน
