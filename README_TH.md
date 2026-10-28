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

## ดูผลเป็นกราฟและตัวเลข

เมื่อรันสำเร็จ หรือกด **เปิดผล** ในสมุดบันทึก หน้า 03 จะแสดงกราฟจาก `metrics.json` ของรอบนั้น (รอบเก่าระบุ Logistic Regression ตาม metadata เดิม; รอบใหม่ใช้ Naive Bayes):

- **กราฟแท่ง:** เลือก F1, Precision, Recall หรือ Macro F1 เพื่อเทียบโมเดลบนสเกลคงที่ 0–100% มีค่าตัวเลขกำกับทุกแท่ง
- **Confusion matrix:** เลือกโมเดลเพื่อดู TN/FP/FN/TP เป็นจำนวนคู่ แถวคือป้ายจริง คอลัมน์คือคำทำนาย สีเขียวหมายถึงถูก สีส้มหมายถึงผิด สีไม่ได้แสดงความมากน้อย
- **ตัวเลขเดิม:** การ์ดคะแนนยังอยู่ใต้กราฟ และยังดาวน์โหลด ZIP ผลทดลองได้ตามเดิม
- **บันทึก SVG:** ดาวน์โหลดกราฟที่กำลังเลือก พร้อม run ID ไปใช้ในรายงานได้ เป็นไฟล์ภาพเวกเตอร์แยกจาก ZIP

กราฟแต่ละหน้ามาจากรอบเดียวกัน ไม่รวมผลต่างชุดทดลอง หากรอบใดไม่ได้รัน Text + roles จะไม่สร้างแท่งคะแนนสมมติให้ การเพิ่มกราฟไม่ได้เปลี่ยนโมเดล คะแนน หรือเป็นหลักฐานว่า improvement สำเร็จ

## โมเดลที่มี

- Majority reference: ทาย class ที่พบบ่อยใน TRAIN ทุกแถว เพื่อดูว่าการเรียนรู้ดีกว่าวิธีง่ายที่สุดหรือไม่
- Cosine reference: TF-IDF cosine ≥ 0.5 เป็น reference ไม่ผ่านตัวจำแนก
- Text baseline: TF-IDF cosine แบ่งช่วงจาก tertiles ของ train → Categorical Naive Bayes
- Text + roles: หมวด cosine เดิม + buyer/target และ reversed-role categories → Categorical Naive Bayes แบบเดียวกัน

**คู่เปรียบเทียบ improvement คือ Text baseline vs Text + roles เท่านั้น** โดยตรึงข้อมูล split classifier hyperparameters และ threshold เหมือนกัน ตัวแรกกับตัวที่สองเป็น reference เพิ่มเติม

ยังไม่ใช่ CohTP reproduction ไม่มี NLI graph, GNN, temporal partition หรือ CoNLL F1 แบบเต็มระบบ (Pilot มี connected-components B³ แยกต่างหาก) ระบบนี้เป็นการทดลองขนาดเล็กเพื่อดูว่าฟีเจอร์บทบาทช่วย pairwise classification ได้ไหม

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

## ต้นแบบเปรียบเทียบข้อมูลข่าว

ส่วน 05 เป็นฟอร์มให้ทดลอง **กรอกข้อมูลด้วยตัวเอง** เพื่อเปรียบเทียบข่าวสองชิ้น เลือกได้ระหว่างการซื้อกิจการ (ผู้ซื้อและเป้าหมาย) หรือปันผล (บริษัทและมูลค่าต่อหุ้น) พร้อมสถานะ ความแน่นอน วันที่รายงาน เวลา งวดที่ข้อมูลมีผล มูลค่า สกุลเงิน หลักฐาน และลิงก์เท่าที่มี ระบบใช้กฎแสดงผลว่า *ข้อมูลตรงกัน อาจเป็นอัปเดต อาจขัดแย้ง หรือข้อมูลไม่พอ* โดยยังต้องให้คนตรวจหลักฐานต้นฉบับ

- ยืนยันก่อนว่าข่าวเป็นดีลหรือเรื่องเดียวกัน และยืนยันเพิ่มว่าข้ออ้างเป็นข้อมูลชนิดและงวดเดียวกันก่อนเทียบตัวเลข วันที่รายงานต่างกันอย่างเดียวไม่ทำให้เป็นอัปเดตหรือขัดแย้งกันโดยอัตโนมัติ
- ถ้าสถานะเปลี่ยนตามลำดับเวลาที่สมเหตุสมผล ระบบเสนอว่าอาจเป็นอัปเดตได้แม้ไม่มีมูลค่า ข่าวในวันเดียวกันต้องระบุเวลาต่างกันเพื่อเรียงลำดับ เช่น เจรจา 09:00 → ลงนาม 17:30
- รองรับเครื่องหมายจุลภาคจัดกลุ่มตัวเลข เช่น `5,000` และปรับค่าคลาดเคลื่อนเป็นเปอร์เซ็นต์ได้ ค่าเริ่มต้น **0.5% ของค่าที่มากกว่า** เป็นเพียงตัวอย่าง ไม่ใช่มาตรฐาน: เช่น 5.0 กับ 4.98 พันล้านต่างกัน 0.4% จึงอยู่ในเกณฑ์นี้ แต่ไม่ใช่ค่าที่เท่ากันพอดี ตั้งเป็น 0 หากต้องการเทียบให้เท่ากันเป๊ะ
- หากสกุลเงินต่างกัน ระบบยังไม่แปลงอัตราแลกเปลี่ยนและจะตอบว่าข้อมูลไม่พอ ค่าที่ดูเหมือนต่างกันอาจมีเหตุอื่น เช่น ช่วงเวลา เงื่อนไข หรือการปัดเศษ จึงต้องตรวจต้นฉบับ
- เลือกความแน่นอนแบบคาดการณ์หรือยืนยันแล้วได้ และมีปุ่มตัวอย่าง **ข้อมูลสมมติ** สำหรับสถานะดีลและปันผล ปุ่มเหล่านี้จะแทนข้อมูลที่กรอกไว้ในฟอร์ม

ส่วนนี้เป็น rule-based demo ไม่ใช่ NLI การสกัดข้อมูลจากข่าวอัตโนมัติ หรือการตรวจสอบข้อเท็จจริง ข้อมูลในฟอร์มยังไม่บันทึกลงสมุดทดลอง

## รันส่วนเพิ่มบทบาท

เลือก **Pilot A/B + บทบาทจาก AI** และกดโหลดในส่วน 01 เว็บจะใส่บทบาทและเลือก “โมเดลทำนาย” ให้ จากนั้นกดรันในส่วน 02 เพื่อเปรียบเทียบ Text กับ Text + roles ได้ทันที บทบาทครบทุกคู่แต่เป็น AI-assisted และยังไม่ได้ผ่านการตรวจโดยคน จึงไม่ใช่ oracle หรือคะแนนความแม่นยำของระบบสกัดบทบาท ดูรายละเอียด บริบทข่าวเต็ม ข้อจำกัด และวิธีใช้ใน [คู่มือชุดบทบาท AI](docs/PILOT_AI_ROLES_TH.md)

หากต้องการทำป้ายกำกับของทีมเอง:

1. ให้คนอ่านบริบทและเติมบริษัทผู้ซื้อ/บริษัทเป้าหมายใน Excel โดยมีหลักฐานที่ตรวจสอบได้ บันทึกผู้ทำป้ายกำกับ/ข้อกำกวมไว้นอกตารางทดลองด้วย
2. ทำ gold same-event แยกจาก role annotation: ห้ามกำหนด gold ว่า “buyer/target ตรงกัน = เหตุการณ์เดียวกัน”
3. เลือกที่มาบทบาทเป็น manual หรือ predicted และบันทึกวิธี/โมเดล/เวอร์ชันในหมายเหตุ
4. ระบบจะรัน Text + roles เมื่อมีคู่ที่รู้ทั้งสองบทบาทครบอย่างน้อยหนึ่งคู่ใน train และ test; ถ้าครบเพียงบางส่วนจะเตือนและบันทึก coverage ควรทำให้ครบก่อนสรุปผล
5. Manual roles ต้องรายงานว่าเป็น **oracle-role experiment** ไม่ใช่ความสามารถของระบบสกัดบทบาทอัตโนมัติ

ฟีเจอร์บทบาท 3 ช่อง: buyer_relation และ target_relation (unknown/match/mismatch), role_reversed (unknown/no/yes) ใช้ casefold/space normalization และ marker ว่างเป็น unknown ไม่มี company entity linker หรือ alias resolver ดูคู่มือ [annotation](docs/ROLE_ANNOTATION_TH.md)

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
- `model_*.json`, `vectorizer.json`: พารามิเตอร์ CategoricalNB, ขอบแบ่ง cosine, vocabulary และ IDF (ไม่ใช้ pickle); รอบเก่าเก็บพารามิเตอร์ของวิธีเดิม
- `clustering_reference.json`, `cluster_predictions.csv`: ข้อมูลอ้างอิงและผลจัดกลุ่ม เมื่อ test เป็น Pilot ที่มีคู่ครบ
- `stdout.log`, `report.md`: log และสรุปผลต่อรอบ
- `uploaded_source.bin`: ไฟล์ upload ต้นฉบับ เมื่อรันจากไฟล์ที่นำเข้า

ใช้ค่าใน manifest ของรอบนั้นเป็นหลัก ไม่เขียนทับรอบเก่า การรัน custom algorithm ต้องอัปเดตคำอธิบายวิธีเอง; ข้อความ workflow บนหน้าเว็บหมายถึงโค้ดเริ่มต้น

## รันจาก Terminal / ทำซ้ำ

```sh
.venv/bin/python run_experiment.py --dataset small_A
.venv/bin/python run_experiment.py --dataset small_B
.venv/bin/python run_experiment.py --input data/my_pairs.xlsx --role-source manual --note 'annotator/version'
.venv/bin/python run_experiment.py --dataset full
.venv/bin/python -m unittest test_workbench test_nb test_cluster test_annotation -v
```

รันซ้ำจากบันทึกเดิม: ใช้ไฟล์ dataset.csv และ algorithm.py ของรอบนั้นผ่าน `--input` และ `--algorithm` พร้อม seed/role-source/note ตาม config.json หรือรัน `python worker.py <สำเนาโฟลเดอร์บันทึก>` ด้วย environment เวอร์ชันเดียวกัน (ทำสำเนาก่อน เพราะ worker เขียนผลในโฟลเดอร์นั้น)

## ข้อมูลและข้อจำกัด

Pilot แนบมาในแอป: ECB+ 42 ข่าว 4 focal acquisition events / 2 topics, 424 คู่ เป็น subset ของ full; labels จาก event clusters ต้นฉบับ ไม่ได้สร้างจากบริษัท Full ต้องอยู่ข้างแอปที่ `../nlp_datasets_2026-10-26/full/ecbplus` (104,840 pairs, 982 ข่าว หลายโดเมน)

- Full split เป็น custom topic split ไม่ใช่ paper split; negative sampling 3:1 ไม่ใช่สัดส่วนข่าวจริง
- Pilot topics อยู่ใน full test ดังนั้น full run หลังตรวจ pilot เป็น execution check ห้ามนำเสนอว่าเป็นผล finance held-out ใหม่
- ใช้ gold selected event contexts ไม่ได้ตรวจหา event mentions เอง full มีหลาย mention ในบริบทเดียว โค้ดตั้งต้นใช้ context cosine ไม่ได้ encode trigger ตำแหน่ง จึงแยก mention ที่บริบทเหมือนกันไม่ได้
- B³ เป็นผล connected-components บน Pilot คู่ครบเท่านั้น ไม่ใช่ CoNLL F1; ห้ามเทียบ pairwise F1 ตรง ๆ กับตัววัด clustering ของงาน coreference
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
- Categorical Naive Bayes: https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.CategoricalNB.html
- CohTP เป็นบริบท/แรงจูงใจจากที่คุยกัน ไม่อ้างว่าไฟล์นี้ใช้ implementation ของผู้เขียน
