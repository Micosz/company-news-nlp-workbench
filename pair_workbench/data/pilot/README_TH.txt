ชุดเล็ก: M&A event-coreference pilot ภาษาอังกฤษ

มีอะไรบ้าง
- documents.csv / documents.jsonl: ข่าว 42 ชิ้น ข้อความประกอบใหม่จาก tokens ของ ECB+
- event_mentions.csv: เลือก original gold mention ของการซื้อกิจการหลัก 1 รายการต่อข่าว
- all_focal_event_mentions.csv: gold mentions ที่กล่าวถึงการซื้อกิจการหลักทั้งหมด 111 รายการ
- pairs.csv: 424 คู่ข้ามข่าว ภายในผู้ซื้อ/topic เดียวกัน
  เหตุการณ์เดียวกัน 220 คู่, คนละเหตุการณ์ 204 คู่
- pilot_two_fold_assignments.csv: fold A ฝึก AMD/ทดสอบ HP; fold B กลับกัน
- roles_to_annotate.csv: ฟอร์มผู้ซื้อ/บริษัทเป้าหมาย พร้อม focal mention และข้อความหลักฐานให้ตรวจ
- inspect_data.ipynb: เปิดอ่านตัวอย่างและรันตรวจโครงสร้างได้
- tools/load_pairs.py: อ่าน pairs พร้อม join ข้อความโดยไม่ส่ง gold ID เป็น features
- tools/check_packages.py: ตรวจป้ายกำกับ, รหัสอ้างอิง, และการแบ่ง fold

กลุ่มเหตุการณ์หลักจากต้นฉบับ
AMD–ATI 8 ข่าว / AMD–SeaMicro 15 ข่าว / HP–EDS 7 ข่าว / HP–EYP 12 ข่าว
ชื่อเหล่านี้เป็นคำอธิบายชุดคัดเลือก ไม่ใช่ output ของโมเดลหรือ gold role annotations ใหม่

เริ่มอ่านด้วย Python (ใช้ standard library; Python 3.10 ขึ้นไป)
หลังแตก ZIP เปิด terminal ในโฟลเดอร์ small:

python3 tools/check_packages.py --root .
python3 tools/load_pairs.py --root . --fold A --split train
python3 tools/load_pairs.py --root . --fold A --split test --output examples_test.csv

หากเขียนโค้ดเอง
from pathlib import Path
import sys
sys.path.insert(0, str(Path('tools').resolve()))
from load_pairs import iter_examples
train = list(iter_examples('.', split='train', fold='A'))
test = list(iter_examples('.', split='test', fold='A'))

แต่ละ example มี text_a, text_b, trigger_a, trigger_b และ label (0/1)
pair_id ใช้อ้างอิงผลเท่านั้น ห้ามนำไปรวมเป็นข้อความฝึก
ใช้ folds เดียวกันและวิธีจำแนกเดียวกันเมื่อเทียบ text-only กับ text+roles
ควร fit TF-IDF บน train เท่านั้น แล้ว transform test ด้วย vocabulary เดิม
ยังไม่มี features ของ buyer/target ที่ตรวจแล้ว ต้องทำ roles_to_annotate.csv ก่อน
หากใช้ gold roles ใน test ให้เรียก oracle-role experiment; อย่าอ้างเป็นผลของระบบดึงอัตโนมัติ

ข้อจำกัด
- ใช้ตรวจว่ากระบวนการทำงานครบ ไม่เพียงพอสรุป improvement ทั่วไปจากเพียง 4 ดีล
- pair label ตัดสิน focal event mention ที่ระบุไว้ ไม่ได้บอกว่าข่าวทั้งสองทุกประโยคเหมือนกัน
- 424 คู่ไม่ใช่ตัวอย่างอิสระ 424 ตัวอย่าง เพราะหลายคู่ใช้ข่าวชิ้นเดียวกัน
- ไม่มี dev set; อย่าปรับ threshold โดยดูผล test ของ fold นั้น
- small อยู่ใน full; อย่านับซ้ำหรือฝึกจาก full แล้วถือว่า small เป็น test อิสระ
- ใน full custom split topic 43/44 อยู่ใน test การฝึกจาก small จะทำให้ส่วนนี้ไม่เป็น held-out
- ตัด 3 ข่าวจาก topic 44 ที่ไม่มี gold anchor หลักใน selected sentences ออก
  ได้แก่ 44_13ecbplus, 44_1ecbplus, 44_9ecbplus
- ข่าวมาจากชุดข้อมูลเก่า ใช้ทดลอง NLP ไม่ใช่ข้อมูลเหตุการณ์ปัจจุบัน

ที่มาและสิทธิ์
ECB+: https://github.com/cltl/ecbPlus
Cybulska and Vossen (2014). Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution.
ป้ายกำกับ CC BY 3.0; ดู licenses/ecbplus/ ข้อความข่าวยังมีเจ้าของลิขสิทธิ์ต้นฉบับ
source manifest และผลตรวจ: dataset_summary.json, data_quality_checks.json
