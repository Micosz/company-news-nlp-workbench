# วิธีการทดลองที่นำไปปรับเขียนในรายงานได้

เอกสารนี้อธิบาย **โค้ดตั้งต้น** ใน algorithms/pair_experiment.py การแก้โค้ดภายหลังต้องแก้คำอธิบายให้ตรงกัน ไม่มีการอ้างว่าผลเพิ่มขึ้นแล้ว

## คำถามวิจัยและขอบเขต

เมื่อคงชุดข้อมูล การแบ่งข้อมูล และตัวจำแนกเดิมไว้ การเพิ่มคุณลักษณะความเข้ากันได้ของบทบาทผู้ซื้อและบริษัทเป้าหมาย ช่วยจำแนกคู่ข้อความที่กล่าวถึงเหตุการณ์เดียวกันได้หรือไม่?

หน่วยข้อมูลคือคู่ event contexts จากคนละข่าว เป้าหมาย y ∈ {0,1} ตาม gold event coreference ไม่ใช่หุ้นขึ้นลง ไม่ใช่ข่าวทั้งบทความเป็นเหตุการณ์เดียว และไม่ใช่ same-deal timeline classification

## การเตรียมข้อมูล

1. ใช้ gold event mentions/contexts ที่ผ่าน official sentence filter ของ ECB+ ตามไฟล์เตรียมข้อมูล ไม่ประเมินขั้น event detection
2. Normalization: HTML unescape → Unicode NFC → รวม whitespace → trim เก็บตัวเลขและถ้อยคำเดิมก่อนเข้าสู่ vectorizer
3. แบ่งตาม topic เพื่อไม่ให้เอกสารเดียวกันหรือกลุ่มดีลเดียวกันข้าม train/test มีตัวตรวจ document ID, group ID และข้อความตรงกันหลัง normalize
4. ทำ role annotation อย่างอิสระจาก labels; ถ้าใช้ชื่อบริษัทมาตรฐาน ให้กำหนดแนวทางและหลักฐานก่อนเปิดผล test

## ตัวแทนข้อความ

สร้าง vocabulary และ IDF จาก unique normalized contexts ใน TRAIN เท่านั้น เพื่อลดการนับบริบทซ้ำเพราะการสร้างหลายคู่

ใช้ scikit-learn TfidfVectorizer: lowercase=True, word n-grams (1,2), min_df=1, max_features=30,000, L2 normalization; ค่า smooth_idf=True, sublinear_tf=False และ tokenizer/token pattern เป็นค่าเริ่มต้นของเวอร์ชันที่บันทึก

เมื่อ vector ถูก L2-normalize, cosine(A,B) = v_A · v_B เป็นสเกลาร์ 1 ค่า ชื่อ/คำที่ไม่อยู่ใน vocabulary ของ train จะไม่มีคอลัมน์ใหม่ใน test

## Baseline กับส่วนที่เสนอ

**Baseline:** x = [cosine(A,B)]

**Proposal:** x' = [cosine(A,B), buyer_match, target_match, buyer_mismatch, target_mismatch, reversed_roles, buyer_both_known, target_both_known]

- match เป็น 1 เมื่อบทบาททั้งสองฝั่งมีข้อมูลและชื่อบริษัทตรงกันหลัง normalize/casefold
- mismatch เป็น 1 เมื่อทั้งสองฝั่งมีข้อมูลแต่ไม่ตรงกัน
- reversed_roles เป็น 1 เมื่อ A.buyer = B.target และ A.target = B.buyer โดยทั้งสี่ค่ามีข้อมูล
- known เป็น 1 เมื่อบทบาทนั้นมีข้อมูลทั้งสองฝั่ง; ค่าว่างไม่ถือว่า match

ทั้งสองโมเดล fit StandardScaler ด้วย TRAIN ของตัวเอง แล้วใช้ LogisticRegression ชนิดเดียวกัน: C=1.0, solver=liblinear, class_weight=balanced, max_iter=1000, random_state=374, intercept=True, L2 regularization ตามค่าเริ่มต้น

การทำนาย: P(y=1|x) ≥ 0.5 ให้ label 1 threshold และ hyperparameters ถูกตรึงก่อนรัน ไม่มีการ search/test tuning ในโค้ดเริ่มต้น ชุด dev ของ full ถูกเก็บแต่ไม่ใช้ fit หรือตัดสิน threshold ในรุ่นนี้

มี Majority reference (majority class ใน train) และ cosine-threshold reference เพิ่มเพื่อช่วยตีความ แต่ **ห้ามใช้ Cosine reference vs Proposal เป็นการแยกผลของ role features** เพราะตัว classifier ต่างกัน คู่ ablation ที่ควบคุมตัวแปรคือ Text baseline vs Text + roles เท่านั้น

## การวัดผล

Positive class = เหตุการณ์เดียวกัน

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2PR / (P + R)
- Macro F1 = ค่าเฉลี่ย F1 ของ class 0 และ 1
- Accuracy = (TP + TN) / จำนวนคู่
- ΔF1 = F1(Text + roles) − F1(Text baseline), เมื่อแสดง % ให้เรียกว่า “จุดเปอร์เซ็นต์”

กรณีตัวหารเป็นศูนย์ กำหนด metric นั้นเป็น 0 (zero_division=0) เก็บ confusion counts และผลทำนายทุกแถวไว้เสมอ

ดู FP ว่า buyer/target สลับหรือผิดตัวไหม และ FN ว่าพาดหัวใช้คำต่างกันไหม การดู test error เพื่อออกแบบรอบใหม่ทำให้ test กลายเป็นข้อมูลพัฒนา ต้องมี held-out ใหม่สำหรับข้อสรุปสุดท้าย

## สิ่งที่บันทึกและการตีความ

เก็บ snapshot โค้ด ข้อมูล split config seed SHA-256 เวอร์ชัน dependencies vocabulary/IDF coefficients/scaler และผลทำนาย พร้อม log แยกต่อ run เพื่อทำซ้ำได้

ผลแรกของ Pilot A: Text baseline P=0.5333, R=0.8276, F1=0.6486, Macro F1=0.4993; Pilot B: P=0.5621, R=0.7143, F1=0.6291, Macro F1=0.5401 ที่ค่าตั้งต้นเดิม (ดู run manifests สำหรับหลักฐาน)

**ตัวเลขนี้ยืนยันการรันได้ ไม่ได้ยืนยันคุณภาพหรือ improvement** ค่า F1 ของ positive class สูงกว่า 0.6 ยังไม่พอ: ถ้าทายเป็นเหตุการณ์เดียวกันทั้งหมด จะได้ F1 ประมาณ 0.6744 ใน A และ 0.6891 ใน B ดังนั้น baseline ขณะนี้ยังไม่ชนะวิธีง่ายนั้นใน positive F1 ต้องพิจารณา Macro F1/confusion และทดสอบส่วนเพิ่มจริงก่อน

บทบาทของข้อมูลจริงยังว่าง จึงยังไม่มีผล Text + roles บนข้อมูลจริง การทดสอบ branch นี้ใช้ข้อมูลจำลองสำหรับ unit test เท่านั้น ไม่ใช่ผลวิจัยและไม่ปรากฏในตารางผลจริง

งานนี้ยังมีเพียง 4 focal acquisition events / 2 company topics อย่าตีความ 424 คู่เป็น 424 ตัวอย่างอิสระ และอย่าใช้ pairwise F1 เทียบโดยตรงกับ clustering metrics ของ CohTP การเพิ่มข้อมูลพร้อม gold ที่อิสระและทดสอบเป็นกลุ่มเป็นขั้นถัดไปก่อนอ้างการนำไปใช้ทั่วไป
