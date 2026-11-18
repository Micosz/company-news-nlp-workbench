# ดูผลรายหัวข้อจาก run ที่รันแล้ว

ตัวเลขรวมใน `metrics.csv` บอกได้แค่ว่าวิธีไหนดีหรือแย่กว่า OR โดยรวม แต่ไม่บอกว่าส่วนต่างนั้นมาจากหัวข้อไหน
`analyze.py` อ่าน `predictions.csv` ของ run ที่รันไว้แล้ว แล้วเทียบแต่ละวิธีกับ OR ทีละหัวข้อ โดยไม่ต้องรันโมเดลใหม่

## วิธีใช้

รันจากโฟลเดอร์ `xamr_lab` ด้วย Python 3.12 ที่ติดตั้ง `requirements-test.txt` แล้ว

```sh
python analyze.py topics runs/<run_id>
python analyze.py topics runs/<run_id> --method OR_TFIDF
python analyze.py topics runs/<run_id> --method OR_TFIDF --out or_tfidf_topics.csv
```

- ไม่ใส่ `--method` จะเทียบทุกวิธีใน run กับ OR และได้ 1 ไฟล์ต่อวิธี ชื่อ `topics_<method>_vs_OR.csv` ในโฟลเดอร์ run
- `--baseline` เปลี่ยนวิธีที่ใช้เป็นฐานได้ (ค่าเริ่มต้น `OR`)
- `--out` ใช้ได้เมื่อระบุ `--method` เท่านั้น
- หน้าจอจะแสดงเฉพาะหัวข้อที่ FP หรือ FN เปลี่ยน ส่วนหัวข้อที่ไม่เปลี่ยนจะอยู่ในไฟล์ csv

## คอลัมน์ในไฟล์

| คอลัมน์ | ความหมาย |
|---|---|
| `topic` | หมายเลขหัวข้อของ ECB+ |
| `mentions` | จำนวน mention ในหัวข้อนั้น |
| `FP_<baseline>`, `FP_<method>` | คู่ mention ที่ระบบจับรวมกัน แต่ gold ไม่ได้อยู่กลุ่มเดียวกัน |
| `FP_change` | `FP_<method>` ลบ `FP_<baseline>` ค่าบวกแปลว่ารวมผิดเพิ่มขึ้น |
| `FN_<baseline>`, `FN_<method>` | คู่ที่ gold อยู่กลุ่มเดียวกัน แต่ระบบแยกออกจากกัน |
| `FN_change` | ค่าลบแปลว่ากู้คู่ที่เคยพลาดกลับมาได้ |
| `pair_F1_*`, `pair_F1_change` | Pair F1 ของหัวข้อนั้น (หน่วยเป็น %) และส่วนต่าง |
| `B3_F1_*`, `B3_F1_change` | B³ F1 ของหัวข้อนั้น (หน่วยเป็น %) และส่วนต่าง |

## วิธีนับ

- นับคู่จากขนาดกลุ่ม: กลุ่มขนาด n มี n(n−1)/2 คู่ ไม่ต้องไล่ทุกคู่ จึงเร็วแม้หัวข้อจะมี mention หลายร้อยตัว
- นับเฉพาะคู่ที่อยู่ในหัวข้อเดียวกัน หากวิธีใดรวม mention ข้ามหัวข้อ ผลรวม FP ในไฟล์นี้จะน้อยกว่า `metrics.csv` ได้
  ใน run Ann1/Ann2 dev ที่ตรวจแล้ว ผลรวมตรงกับ `metrics.csv` ทุกวิธี
- B³ เก็บผลรวม precision/recall ของแต่ละหัวข้อไว้ ไม่เก็บค่าเฉลี่ย จึงนำหลายหัวข้อมารวมกันใหม่ได้ภายหลัง
  ซึ่งจำเป็นสำหรับการสุ่มหัวข้อซ้ำใน bootstrap
- ไม่ได้คำนวณ MUC และ CEAF_e รายหัวข้อ CoNLL F1 รายหัวข้อยังดูได้จาก `topics.csv` ที่ `research_runner.py` เขียนไว้

## Test

```sh
python -m unittest test_analysis test_analyze
```

`test_analysis.py` ตรวจการนับเทียบกับการไล่ทุกคู่บนข้อมูลสุ่ม ส่วน `test_analyze.py` ตรวจคำสั่ง `topics` ทั้งคำสั่ง
