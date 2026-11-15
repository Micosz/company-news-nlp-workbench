# ทดลอง TF-IDF + Naive Bayes กับ X-AMR

## โปรโตคอลที่ตรึงก่อนรัน

พอร์ตขั้นข้อความจาก `pair_workbench/algorithms/pair_experiment.py` ตามเดิม ใช้ข้อความประโยคของ mention, normalize แบบ NFC + HTML unescape + ยุบช่องว่าง, TF-IDF word 1–2 grams (min_df 1, max_features 30,000, L2), cosine, ตัดเป็นช่วงด้วย quantile 1/3 และ 2/3 จากคู่ฝึก ลบขอบช่วงที่ซ้ำ และใช้ CategoricalNB (alpha 1, min_categories 3, empirical class prior) วิธีนี้เป็น baseline จากงานเดิม ไม่ใช่วิธีจาก paper ปี 2026

ฝึกและประเมิน Ann1/Ann2 แยกตามไฟล์ของผู้เขียน ตรวจ train/dev ไม่ทับกันที่ topic, document หรือ mention ให้ topic ใช้สร้างคู่เท่านั้น สร้างทุกคู่ของคนละเอกสารใน topic เดียวกันโดยไม่สุ่มหรือปรับสมดุล ใช้คู่ที่มี `(topic, gold_cluster)` เดียวกันเป็น positive สำหรับการฝึก/วัดผลเท่านั้น ไม่ป้อน roleset, topic, ID หรือ gold เข้า TF-IDF/ตัวจำแนก

เลือก threshold จาก 5-fold GroupKFold บน train โดยถือ topic ทั้งกลุ่ม และ fit vocabulary, IDF, ขอบช่วง cosine และตัวจำแนกใหม่ภายใน fold train เท่านั้น ค่าให้เลือกคือ 0.01, 0.05, 0.10, 0.25 และ 0.50 ตัวเลือก 0.50 คือค่าดั้งเดิม ใช้ค่าเฉลี่ย CoNLL F1 ของคลัสเตอร์ใน fold validation เป็นเกณฑ์ ถ้าเสมอให้ใช้ threshold สูงกว่า เมื่อเลือกแล้วบันทึก config ก่อนเปิดข้อมูล dev ใน runner และ fit ใหม่ด้วย train ทั้งชุด รายงานทั้งค่าที่เลือกและค่า 0.50 ไม่ปรับเกณฑ์หลังอ่าน dev

คู่ที่ posterior ถึง threshold เป็นเส้นในกราฟที่มี mentions ครบทุกตัว ใช้ connected components แบบ X-AMR รวม singleton คู่ในข่าวเดียวกันไม่ได้เป็นเส้นตรงของ NB แต่อาจเชื่อมกันผ่านข่าวอื่น OR ใช้กราฟ X-AMR ตามเดิม รวมเส้นในเอกสารเดียวกันได้ เป็นตัวอ้างอิงที่ใช้ข้อมูลคำกำกับมากกว่า รายงาน OR ที่จำกัดเฉพาะคนละเอกสารเพิ่มเพื่อดูผลของพื้นที่คู่ให้เทียบกันได้ ทั้งหมดวัด CoNLL/Pair F1 บน mentions และ gold เดียวกัน ไม่ตัดแถวตาม coverage

ตัวประเมิน X-AMR เดิมใช้ raw gold ID ตรง ๆ สำหรับ dev ถ้าพบ ID ซ้ำข้าม topic ต้องรายงานทั้งผล raw benchmark และผล topic-scoped แยกกัน ห้ามเปลี่ยนคำกำกับต้นฉบับ ส่วน CV ใช้ topic-scoped gold เพราะพบเลขดิบซ้ำข้าม topic ใน train ไม่ใช้ Ann1 เทียบข้าม annotator เป็นผลทดสอบอิสระ และไม่เปิด test_common ในการรันนี้ รัน train CV และ dev ครั้งเดียวตามแผน จากนั้นรันซ้ำเพื่อยืนยันผล แล้วหยุดที่การวิเคราะห์ข้อจำกัด

## ผลรัน · 15 พฤศจิกายน 2026 (เวลาไทย)

| ชุด | Mentions / เอกสาร / หัวข้อ | คู่ผู้สมัคร | Positive | Negative | Positive ที่ครอบคลุมจากทุกคู่ |
|---|---:|---:|---:|---:|---:|
| Ann1 train | 3,194 / 570 / 25 | 226,600 | 11,934 | 214,666 | 94.37% |
| Ann2 train | 3,194 / 570 / 25 | 226,593 | 11,934 | 214,659 | 94.37% |
| Ann1 และ Ann2 dev | 1,245 / 196 / 8 ต่อชุด | 96,099 | 5,569 | 90,530 | 94.66% |

ตรวจแล้ว train/dev ไม่ทับ topic, doc หรือ mention ภายในแต่ละ annotator ทั้งสอง dev มี mention IDs เหมือนกันทั้งหมด ใน train ฝั่ง Ann1 มี `31_11ecb.xml_45` ที่ไม่มีใน Ann2 และ Ann2 มี `25_10ecb.xml_22` ที่ไม่มีใน Ann1 ใช้แต่ละชุดตามเดิมโดยไม่ join พบ train raw ID `6`, `7`, `9` ซ้ำข้าม topic ในทั้งสองชุด ส่วน dev ไม่มี raw ID ที่ชนข้าม topic จึงใช้ผล raw ตาม evaluator เดิมได้ ตัวอย่าง raw ID `10000000055` พบใน topic 10 ของ train และ topic 35 ของ dev ในทั้งสอง annotator จึงไม่ใช้ ID นี้เชื่อมข้อมูลข้าม split

| Threshold | Ann1 train CV CoNLL F1 เฉลี่ย | Ann2 train CV CoNLL F1 เฉลี่ย |
|---|---:|---:|
| 0.01 | 29.7744% | 29.7726% |
| 0.05 | 31.0501% | 31.0485% |
| 0.10 | 30.3139% | 30.3123% |
| 0.25 | 34.4008% | 34.4025% |
| **0.50** | **34.4008%** | **34.4025%** |

| ชุด | วิธี | CoNLL F1 | Pair P | Pair R | Pair F1 | FP | FN | กลุ่ม |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Ann1 dev | OR | 79.7689% | 80.49% | 64.95% | 71.89% | 926 | 2,062 | 470 |
| Ann1 dev | OR คนละเอกสาร | 79.6556% | 80.56% | 64.88% | 71.88% | 921 | 2,066 | 476 |
| Ann2 dev | OR | 77.1198% | 78.43% | 60.70% | 68.44% | 982 | 2,312 | 479 |
| Ann2 dev | OR คนละเอกสาร | 76.7655% | 78.40% | 60.53% | 68.32% | 981 | 2,322 | 487 |
| ทั้งสอง dev | NB (0.50 เดิมและจาก CV) | 29.6492% | 0% | 0% | 0% | 0 | 5,883 | 1,245 |

ทั้งสองชุดเลือก 0.50 ด้วยกฎตัดสินกรณีเสมอ และ NB ไม่เลือกเส้นเลย คะแนน CoNLL ที่ยังมากกว่าศูนย์มาจากการให้คะแนนระดับคลัสเตอร์เมื่อทุก mention เป็น singleton; ตัวชี้วัดรายคู่แสดงว่าไม่มีคู่ที่ระบบทายว่าเหมือนกัน คลาสบวกมีเพียงประมาณ 5.27% ในคู่ฝึก และตัวจำแนกมี posterior เพียงสามค่าเพราะใช้ฟีเจอร์เดียวแบบสามช่วง ค่าสูงสุดบน dev คือ 0.10171 (Ann1) และ 0.10163 (Ann2) โดยช่วงสูงสุดมีคู่บวก 4,364 คู่ แต่มีคู่ลบ 60,267 และ 60,235 ตามลำดับ ดังนั้นการลด threshold อย่างเดียวจะรับคู่จำนวนมากพร้อมกัน และ connected components อาจขยายข้อผิดพลาดทางอ้อม คะแนนของ threshold ที่ต่ำกว่าในการเลือกแบบ CV ก็ต่ำกว่าการเลือก 0.50 รอบนี้จึงหยุดโดยไม่ปรับจาก dev

OR แบบคนละเอกสารยังให้ผลดีกว่ามาก จึงอธิบายความต่างด้วยกฎห้ามเส้นในเอกสารเดียวกันอย่างเดียวไม่ได้ OR ใช้คำกำกับเหตุการณ์ ผู้เกี่ยวข้อง สถานที่และเวลาของผู้เขียน ส่วน NB ใช้เฉพาะข้อความประโยค ผลนี้บอกข้อจำกัดของ baseline ที่พอร์ตมา และยังไม่วัดวิธีเรียนรู้ที่ใช้ฟีเจอร์หลากหลายหรือวิธีจัดกลุ่มอื่น

## รันซ้ำและหลักฐานในเครื่อง

การรันใช้ Python 3.12.15, scikit-learn 1.9.1, numpy 2.3.5 และ scipy 1.18.1 ของ Pair Workbench แล้วเพิ่มโมดูล pure Python ของ CoVal, click, tqdm, typer และ typing_extensions จากเครื่องเดิม ตัวประเมิน CoVal มาจาก commit ที่ตรึงใน `xamr_lab/requirements.txt` ไม่ต้องเปลี่ยน dependency ของเว็บ การรันครั้งนี้ไม่ติดตั้งโมเดลหรือเรียก API

```sh
# จาก root ของ repo เมื่อมีทั้งสอง virtualenv ตามที่ใช้ในเครื่องนี้
xamr_text_deps=$(mktemp -d)
xamr_pure_modules="$PWD/.venv-xamr/lib/python3.9/site-packages"
for xamr_module in coval click tqdm typer typing_extensions.py; do
  ln -s "$xamr_pure_modules/$xamr_module" "$xamr_text_deps/$xamr_module"
done
PYTHONPATH="$xamr_text_deps" pair_workbench/.venv/bin/python xamr_lab/tfidf_nb.py --annotator ann1
PYTHONPATH="$xamr_text_deps" pair_workbench/.venv/bin/python xamr_lab/tfidf_nb.py --annotator ann2
(cd xamr_lab && PYTHONPATH="$xamr_text_deps" ../pair_workbench/.venv/bin/python -m unittest -q test_tfidf_nb)
```

ผลอยู่ใต้ `xamr_lab/runs/tfidf-nb/` รอบ Ann1 `20261115T154501-99efeecd` และ Ann2 `20261115T154501-2ed56bb5` เก็บ config ที่ freeze ก่อนโหลด dev, commit และ hashes, รายละเอียด folds และ bins, metrics, posterior รายคู่, clusters, coverage และเวลา CV+fit ประมาณ 2.42 วินาทีต่อชุด และเวลา infer/จัดกลุ่ม dev ประมาณ 0.11 วินาที ไม่รวม scorer รันซ้ำแล้วทั้ง CSV, folds และ config ตรงกัน ตรวจ OR ราย mention ตรงกับผลเดิมและตรวจ posterior บน fixture ตรงกับโค้ด Pair Workbench ผ่าน 3 tests ใหม่และ 28 tests เดิม
