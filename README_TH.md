# NLP Research Workbench

เว็บทดลองบนเครื่องสำหรับงาน **event coreference แบบคู่ข้อความ**: นำเข้า Excel/CSV → ตรวจ split → แก้/วาง Python → รัน → ดูผล → ดาวน์โหลดบันทึกเพื่อรายงาน

## เปิดใช้งานบนเครื่องนี้

ดับเบิลคลิก `Start_Workbench.command` แล้วเปิด http://127.0.0.1:8765 หาก macOS เปิดเป็นข้อความ ให้เปิด Terminal ในโฟลเดอร์นี้แล้วรัน:

```sh
.venv/bin/python server.py --open-browser
```

ติดตั้ง Python environment ไว้ให้บนเครื่องนี้แล้ว ใช้ CPU ไม่ต้องมี GPU/API key และไม่ส่งข่าวออกอินเทอร์เน็ต โค้ดที่วางรันบนเครื่องจริงด้วยสิทธิ์ผู้ใช้ ไม่ใช่ sandbox สำหรับโค้ดจากคนอื่น เว็บเปิดรับเฉพาะ loopback อย่าเปิดพอร์ตสาธารณะ

## เริ่มครั้งแรก

1. เลือก Pilot A แล้วกดโหลดข้อมูล (train AMD 253 คู่ / test HP 171 คู่)
2. ใช้โค้ดและ seed เริ่มต้น กดรันและบันทึกการทดลอง
3. ดู Text baseline / Majority reference / Cosine reference พร้อม Precision, Recall, F1 และ confusion counts
4. เปิดคู่ที่ทำนายผิด: FP = รวมคนละเหตุการณ์, FN = แยกเหตุการณ์เดียวกัน
5. ดาวน์โหลด ZIP หรือดูโฟลเดอร์ `runs/<run_id>/`
6. Pilot B สลับทิศ train/test เป็นการตรวจ pipeline อีกทิศ ไม่ใช่ test ใหม่อิสระ หากใช้ผลสองทิศปรับโมเดลแล้ว ต้องหาข้อมูล held-out ใหม่สำหรับข้อสรุปสุดท้าย

## โมเดลที่มี

- Majority reference: ทาย class ที่พบบ่อยใน TRAIN ทุกแถว เพื่อดูว่าการเรียนรู้ดีกว่าวิธีง่ายที่สุดหรือไม่
- Cosine reference: TF-IDF cosine ≥ 0.5 เป็น reference ไม่ได้ผ่าน Logistic Regression
- Text baseline: TF-IDF cosine 1 feature → StandardScaler → Logistic Regression
- Text + roles: cosine เดิม + 7 buyer/target compatibility features → scaler + Logistic Regression แบบเดียวกัน

**คู่เปรียบเทียบ improvement คือ Text baseline vs Text + roles เท่านั้น** โดยตรึงข้อมูล split classifier hyperparameters และ threshold เหมือนกัน ตัวแรกกับตัวที่สองเป็น reference เพิ่มเติม

ยังไม่ใช่ CohTP reproduction ไม่มี NLI graph, GNN, temporal partition หรือ clustering score ระบบนี้เป็นการทดลองขนาดเล็กเพื่อดูว่าฟีเจอร์บทบาทช่วย pairwise classification ได้ไหม

## นำเข้า Excel / CSV

ดาวน์โหลดตัวอย่างจากเว็บ หรือใช้ `data/pilot_fold_A_roles_blank.xlsx` ไฟล์ Excel อ่านเฉพาะชีตแรก ไม่มีการ execute สูตร/มาโคร

คอลัมน์จำเป็น:

| คอลัมน์ | ความหมาย |
|---|---|
| pair_id | ID คู่ไม่ซ้ำ ใช้ติดตามผล ไม่ใช้เป็น feature |
| text_a, text_b | บริบทข้อความของเหตุการณ์ A/B |
| label | 1 = เหตุการณ์เดียวกัน, 0 = ต่างเหตุการณ์ ต้องมี gold ที่เป็นอิสระจากฟีเจอร์ |
| split | train / dev / test ที่กำหนดล่วงหน้า |
| doc_a, doc_b | ID ข่าวต้นทาง ใช้ตรวจ leakage |
| group_id | กลุ่มที่ต้องอยู่ split เดียวกัน เช่น topic หรือกลุ่มดีลที่เกี่ยวเนื่อง ไม่ใช่เลขแถว |

คอลัมน์เสริม: buyer_a, target_a, buyer_b, target_b; mention_a/mention_b ใช้แยกเหตุการณ์หลาย mention ในบริบทเดียว (ต้องใช้ชื่อคอลัมน์นี้ตรง ๆ)

ถ้าชื่อคอลัมน์ต่างจากตัวอย่าง เลือก mapping ในเว็บได้ สำหรับข้อมูลใหม่ต้องวางแผน split ก่อน ระบบจะไม่สุ่มคู่ให้เพราะข่าวเดียวกันอาจรั่วข้าม train/test

**ข้อมูลไม่ครบให้เว้นว่าง ไม่ใส่ unknown/null เป็นข้อความ** ใช้ชื่อหรือ ID บริษัทที่สอดคล้องกัน แต่ไม่สร้าง mapping จาก gold event ID

## รันส่วนเพิ่มบทบาท

1. ให้คนอ่านบริบทและเติมบริษัทผู้ซื้อ/บริษัทเป้าหมายใน Excel โดยมีหลักฐานที่ตรวจสอบได้ บันทึกผู้ทำป้ายกำกับ/ข้อกำกวมไว้นอกตารางทดลองด้วย
2. ทำ gold same-event แยกจาก role annotation: ห้ามกำหนด gold ว่า “buyer/target ตรงกัน = เหตุการณ์เดียวกัน”
3. เลือกที่มาบทบาทเป็น manual หรือ predicted และบันทึกวิธี/โมเดล/เวอร์ชันในหมายเหตุ
4. ระบบจะรัน Text + roles เมื่อมีคู่ที่รู้ทั้งสองบทบาทครบอย่างน้อยหนึ่งคู่ใน train และ test; ถ้าครบเพียงบางส่วนจะเตือนและบันทึก coverage ควรทำให้ครบก่อนสรุปผล
5. Manual roles ต้องรายงานว่าเป็น **oracle-role experiment** ไม่ใช่ความสามารถของระบบสกัดบทบาทอัตโนมัติ

ฟีเจอร์ 7 ตัว: buyer_match, target_match, buyer_mismatch, target_mismatch, reversed_roles, buyer_both_known, target_both_known เป็น 0/1 ใช้เพียง casefold/space normalization ไม่มี company entity linker หรือ alias resolver

## โค้ดที่แก้เอง

```python
def run(train, test, config):
    # pandas DataFrame: train มี label; test ไม่มี label
    # ส่งคะแนน 0..1 ตามลำดับทุกแถว test
    return {"models": {"my_model": {"scores": [...], "threshold": 0.5,
                                   "features": ["my_feature"]}}}
```

ตัวรันเก็บ gold ไว้วัดผลภายนอกฟังก์ชัน ตัวแปร train/test ที่ส่งให้มีเฉพาะ text และ roles (train เพิ่ม label) ไม่ส่ง IDs, topic, gold cluster หรือ split เป็น feature แต่ไม่ได้ป้องกัน custom code อ่านไฟล์เอง: ผู้ทดลองต้องรักษา test protocol

โค้ดผิดหรือเกิน 10 นาทีจะเก็บ log และสถานะ failed โหลดโมเดลภายนอกต้องติดตั้ง dependency เองใน `.venv` และบันทึกเวอร์ชันเพิ่ม

## หลักฐานที่เก็บทุกรอบ

- `algorithm.py`, `engine.py`, `worker.py`: snapshot โค้ดอัลกอริทึม ตัวตรวจข้อมูล และตัววัดผล
- `dataset.csv`, `config.json`, `manifest.json`: ข้อมูลที่ใช้จริง split seed note SHA-256 input/code และเวอร์ชัน Python/packages
- `metrics.json`: Precision/Recall/F1/Macro F1/Accuracy/TP/FP/FN/TN และ ΔF1 เมื่อมีส่วนเพิ่ม
- `predictions.csv`, `errors.csv`: ผลทุกคู่และเฉพาะคู่ที่ผิด
- `model_*.json`, `vectorizer.json`: พารามิเตอร์ที่เรียนรู้ scaling, vocabulary และ IDF (ไม่ใช้ pickle)
- `stdout.log`, `report.md`: log และสรุปผลต่อรอบ
- `uploaded_source.bin`: ไฟล์ upload ต้นฉบับ เมื่อรันจากไฟล์ที่นำเข้า

ใช้ค่าใน manifest ของรอบนั้นเป็นหลัก ไม่เขียนทับรอบเก่า การรัน custom algorithm ต้องอัปเดตคำอธิบายวิธีเอง; ข้อความ workflow บนหน้าเว็บหมายถึงโค้ดเริ่มต้น

## รันจาก Terminal / ทำซ้ำ

```sh
.venv/bin/python run_experiment.py --dataset small_A
.venv/bin/python run_experiment.py --dataset small_B
.venv/bin/python run_experiment.py --input data/my_pairs.xlsx --role-source manual --note 'annotator/version'
.venv/bin/python run_experiment.py --dataset full
.venv/bin/python -m unittest test_workbench -v
```

รันซ้ำจากบันทึกเดิม: ใช้ไฟล์ dataset.csv และ algorithm.py ของรอบนั้นผ่าน `--input` และ `--algorithm` พร้อม seed/role-source/note ตาม config.json หรือรัน `python worker.py <สำเนาโฟลเดอร์บันทึก>` ด้วย environment เวอร์ชันเดียวกัน (ทำสำเนาก่อน เพราะ worker เขียนผลในโฟลเดอร์นั้น)

## ข้อมูลและข้อจำกัด

Pilot แนบมาในแอป: ECB+ 42 ข่าว 4 focal acquisition events / 2 topics, 424 คู่ เป็น subset ของ full; labels จาก event clusters ต้นฉบับ ไม่ได้สร้างจากบริษัท Full ต้องอยู่ข้างแอปที่ `../nlp_datasets_2026-10-26/full/ecbplus` (104,840 pairs, 982 ข่าว หลายโดเมน)

- Full split เป็น custom topic split ไม่ใช่ paper split; negative sampling 3:1 ไม่ใช่สัดส่วนข่าวจริง
- Pilot topics อยู่ใน full test ดังนั้น full run หลังตรวจ pilot เป็น execution check ห้ามนำเสนอว่าเป็นผล finance held-out ใหม่
- ใช้ gold selected event contexts ไม่ได้ตรวจหา event mentions เอง full มีหลาย mention ในบริบทเดียว โค้ดตั้งต้นใช้ context cosine ไม่ได้ encode trigger ตำแหน่ง จึงแยก mention ที่บริบทเหมือนกันไม่ได้
- ไม่ใช่ event clustering; ห้ามเทียบ pairwise F1 ตรง ๆ กับ CoNLL/MUC/B³/CEAF ของงาน coreference
- คู่จำนวนมากจากเพียง 4 events ไม่ใช่ตัวอย่างอิสระจำนวนมาก ยังไม่มี confidence interval/significance test
- Same deal ไม่เท่ากับ same event: ข่าวประกาศซื้อกับข่าวปิดดีลอาจเป็นดีลเดียวกันแต่คนละเหตุการณ์
- TF-IDF เป็นการวัดความเหมือนคำ ไม่มี pretrained semantic embeddings; ตัวจำแนกไม่ได้ดูชื่อบริษัทเป็น ID โดยตรง
- TKGQA ไม่มี gold coreference ที่อิสระ จึงไม่ได้รวมใน training อัตโนมัติ
- Backend ตรวจข่าว/group/ข้อความซ้ำข้าม split และคู่ซ้ำ แต่ตรวจความถูกต้องของ gold/กลุ่มทางความหมายแทนคนไม่ได้

## ติดตั้งบนเครื่องใหม่

ใช้ Python 3.12 และสร้าง environment ใหม่ (ไม่คัดลอก .venv ข้ามเครื่อง):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --open-browser
```

Windows ใช้ `.venv\Scripts\python` แทน `.venv/bin/python`; timeout process-group handling ของเว็บออกแบบและทดสอบบน macOS นี้เป็นหลัก

## แหล่งอ้างอิงของข้อมูลและเครื่องมือ

- ECB+ corpus: https://github.com/cltl/ecbPlus — Cybulska & Vossen (2014), Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution. เก็บ licenses ไว้ใน data/pilot/licenses; ลิขสิทธิ์เนื้อข่าวแยกจาก annotation
- TF-IDF implementation: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- Logistic Regression: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- CohTP เป็นบริบท/แรงจูงใจจากที่คุยกัน ไม่อ้างว่าไฟล์นี้ใช้ implementation ของผู้เขียน
