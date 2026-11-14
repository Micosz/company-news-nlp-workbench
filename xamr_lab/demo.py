"""Run the research engine on curated cases or user-entered event fields."""
import hashlib
import json
from functools import lru_cache
from urllib.error import URLError
from urllib.request import urlopen

from engine import BASE, c_clustering, constrained, event_graphs, interval, load_dataset, pair_counts
from setup_data import COMMIT, FILES


CUSTOM_BODY_LIMIT = 32_000
REAL_DATASET = 'ann1-dev'
REAL_REPORTS = {
    '12_19ecb.xml_27': 'เรือ INS Mysore ของอินเดียถูกส่งไปปฏิบัติการในอ่าวเอเดน',
    '12_5ecbplus.xml_10': 'เรือ INS Sukanya ถูกส่งไปลาดตระเวนต่อต้านโจรสลัดในอ่าวเอเดน',
    '12_6ecbplus.xml_6': 'รายงานระบุว่าเรือ INS Sukanya กำลังปฏิบัติภารกิจต่อต้านโจรสลัดในอ่าวเอเดน',
    '12_9ecbplus.xml_5': 'อีกเอกสารกล่าวถึงการส่งเรือ INS Sukanya ไปปฏิบัติภารกิจในอ่าวเอเดน',
}
REAL_SOURCE = f'https://github.com/ahmeshaf/gpt_coref/blob/{COMMIT}/project/annotations/ecb/{FILES[REAL_DATASET]}'


CASES = {
    'separate': {
        'summary': 'สะพานเดียวกันปิดสองครั้ง โดยเปิดให้ใช้งานตามปกติระหว่างสองรอบ',
        'reports': [
            ('A', 'เทศบาลปิดสะพานริเวอร์เพื่อตรวจโครงสร้างในวันที่ 3 มีนาคม', '2026-03-03', 'first'),
            ('B', 'การจราจรถูกเบี่ยงหลังเทศบาลปิดสะพานริเวอร์ในวันที่ 3 มีนาคม', '2026-03-03', 'first'),
            ('C', 'เทศบาลปิดสะพานริเวอร์อีกครั้งในวันที่ 10 มีนาคม', '2026-03-10', 'second'),
            ('D', 'เทศบาลปิดสะพานริเวอร์ในวันที่ 10 มีนาคมหลังเปิดใช้งานได้หลายวัน', '2026-03-10', 'second'),
        ],
    },
    'continuous': {
        'summary': 'สะพานปิดต่อเนื่องครั้งเดียว รายงานแต่ละชิ้นอ้างถึงคนละวันระหว่างการปิด',
        'reports': [
            ('A', 'เทศบาลเริ่มปิดสะพานริเวอร์ในวันที่ 3 มีนาคม', '2026-03-03', 'one'),
            ('B', 'สะพานริเวอร์ยังปิดในวันที่ 5 มีนาคม หลังเทศบาลเริ่มซ่อม', '2026-03-05', 'one'),
            ('C', 'สะพานริเวอร์ยังปิดต่อเนื่องในวันที่ 8 มีนาคม', '2026-03-08', 'one'),
        ],
    },
}


def validate_tolerance(tolerance_days):
    if type(tolerance_days) is not int or not 0 <= tolerance_days <= 14:
        raise ValueError('ระยะห่างที่ยอมได้ต้องอยู่ระหว่าง 0–14 วัน')


@lru_cache(maxsize=1)
def real_mentions():
    if (BASE / 'data' / f'{REAL_DATASET}.json').is_file():
        tasks, _ = load_dataset(REAL_DATASET)
    else:
        url = f'https://raw.githubusercontent.com/ahmeshaf/gpt_coref/{COMMIT}/project/annotations/ecb/{FILES[REAL_DATASET]}'
        try:
            with urlopen(url, timeout=10) as response:
                raw = response.read(5_000_001)
        except (OSError, URLError) as error:
            raise ValueError('โหลดชุดข่าวจริงไม่ได้ กรุณาลองใหม่หรือดาวน์โหลดข้อมูลสำหรับโหมด local') from error
        expected = json.loads((BASE / 'dataset_checksums.json').read_text())[REAL_DATASET]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('ตรวจสอบชุดข่าวจริงไม่ผ่าน: checksum ไม่ตรง')
        tasks = json.loads(raw)
    by_id = {task['mention_id']: task for task in tasks}
    return [{**by_id[mention_id], 'text': summary} for mention_id, summary in REAL_REPORTS.items()]


def run_demo(case, tolerance_days):
    validate_tolerance(tolerance_days)
    if case == 'real':
        return compare_mentions(
            real_mentions(), tolerance_days,
            summary='ข่าวจริงจาก ECB+ ชุด Ann1 dev สรุปเป็นภาษาไทย วันและคำตอบอ้างอิงมาจาก annotation ของชุดข้อมูล',
            reference='คำตอบอ้างอิงจาก ECB+',
            source=REAL_SOURCE,
        )
    if case not in CASES:
        raise ValueError('กรุณาเลือกเคสตัวอย่าง')
    example = CASES[case]
    tasks = [
        {
            'mention_id': mention_id,
            'topic': 'bridge closure',
            'doc_id': 'demo-' + mention_id,
            'sentence_id': '1',
            'lemma': 'close',
            'roleset_id': 'close.01',
            'arg0': 'เทศบาล',
            'arg1': 'สะพานริเวอร์',
            'argL': 'เขตริเวอร์',
            'argT': event_date,
            'gold_cluster': gold,
            'text': sentence,
        }
        for mention_id, sentence, event_date, gold in example['reports']
    ]
    return compare_mentions(tasks, tolerance_days, example['summary'], reference='คำตอบของเคสจำลอง')


def run_custom_demo(body):
    if not isinstance(body, dict):
        raise ValueError('ข้อมูลต้องเป็น JSON object')
    tolerance_days = body.get('tolerance_days')
    validate_tolerance(tolerance_days)
    reports = body.get('reports')
    if not isinstance(reports, list) or not 2 <= len(reports) <= 8:
        raise ValueError('กรุณากรอกข่าว 2–8 ชิ้น')
    tasks = []
    fields = {'text': 500, 'action': 80, 'actor': 100, 'target': 100, 'location': 100, 'date': 10}
    for i, report in enumerate(reports):
        if not isinstance(report, dict):
            raise ValueError('ข้อมูลข่าวไม่ถูกต้อง')
        values = {}
        for field, limit in fields.items():
            value = report.get(field, '')
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f'ข่าวชิ้นที่ {i + 1} มีข้อมูลเกินขนาดหรือชนิดข้อมูลไม่ถูกต้อง')
            values[field] = ' '.join(value.split())
        if any(not values[field] for field in ('text', 'action', 'actor', 'target')):
            raise ValueError(f'ข่าวชิ้นที่ {i + 1} ต้องมีข้อความ ประเภทเหตุการณ์ ผู้กระทำ และสิ่งที่เกี่ยวข้อง')
        if any('/' in values[field] for field in ('action', 'actor', 'target', 'location')):
            raise ValueError('กรอกคำกำกับหนึ่งค่าต่อช่องโดยไม่ใช้เครื่องหมาย /')
        if values['date'] and not interval(values['date']):
            raise ValueError('วันเกิดเหตุต้องอยู่ในรูปแบบ YYYY-MM-DD หรือเว้นว่าง')
        mention_id = chr(ord('A') + i)
        tasks.append({
            'mention_id': mention_id,
            'topic': 'demo',
            'doc_id': 'user-' + mention_id,
            'sentence_id': '1',
            'roleset_id': values['action'].casefold(),
            'arg0': values['actor'].casefold(),
            'arg1': values['target'].casefold(),
            'argL': values['location'].casefold(),
            'argT': values['date'],
            'text': values['text'],
        })
    return compare_mentions(tasks, tolerance_days, 'ข่าวและข้อมูลเหตุการณ์ที่คุณกรอก')


def compare_mentions(tasks, tolerance_days, summary, reference=None, source=None):
    ids, nested, location_time = event_graphs(tasks)
    graph = nested + location_time
    dates = [interval(mention['argT']) for mention in tasks]
    temporal, blocked = constrained(graph, ids, dates, tolerance_days)
    gold = [mention['gold_cluster'] for mention in tasks] if reference else None
    display_ids = {mention_id: chr(ord('A') + i) for i, mention_id in enumerate(ids)}
    results = {}
    for method, predictions in [('baseline', c_clustering(graph, ids)), ('temporal', temporal)]:
        clusters = {}
        for mention_id, cluster_id in predictions:
            clusters.setdefault(cluster_id, []).append(display_ids[mention_id])
        results[method] = {'groups': list(clusters.values())}
        if gold is not None:
            counts = pair_counts(gold, [cluster_id for _, cluster_id in predictions])
            results[method].update(wrong_merges=counts['fp'], wrong_splits=counts['fn'])
    return {
        'summary': summary,
        'mentions': [
            {
                'id': display_ids[task['mention_id']],
                'text': task['text'],
                'date': task['argT'],
                'source_id': task['mention_id'] if source else None,
            }
            for task in tasks
        ],
        'reference': reference,
        'source': source,
        'expected_groups': len(set(gold)) if gold is not None else None,
        'tolerance_days': tolerance_days,
        'results': results,
        'blocked': [{key: display_ids[value] for key, value in edge.items()} for edge in blocked],
    }
