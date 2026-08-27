import requests
from bs4 import BeautifulSoup
import json
import os
import re
import sys
import time

SANOOK_BASE = 'https://news.sanook.com/lotto'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'th-TH,th;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://news.sanook.com/',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

THAI_MONTHS = {
    'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03',
    'เมษายน': '04', 'พฤษภาคม': '05', 'มิถุนายน': '06',
    'กรกฎาคม': '07', 'สิงหาคม': '08', 'กันยายน': '09',
    'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
}
THAI_MONTHS_REV = {v: k for k, v in THAI_MONTHS.items()}

# ผลรางวัลที่ต้องมีครบทุกช่อง ถ้าขาดแปลว่าหวยยังออกไม่ครบ → ยังไม่บันทึก
# digits/count/reward เป็นค่าตั้งต้น ส่วนค่าจริงอ่านจากหัวข้อบนหน้าเว็บอีกที
SPEC = {
    'prizeFirst':               {'digits': 6, 'count': 1,   'reward': '6000000', 'name': 'รางวัลที่ 1'},
    'prizeFirstNear':           {'digits': 6, 'count': 2,   'reward': '100000',  'name': 'รางวัลข้างเคียงรางวัลที่ 1'},
    'prizeSecond':              {'digits': 6, 'count': 5,   'reward': '200000',  'name': 'รางวัลที่ 2'},
    'prizeThird':               {'digits': 6, 'count': 10,  'reward': '80000',   'name': 'รางวัลที่ 3'},
    'prizeFourth':              {'digits': 6, 'count': 50,  'reward': '40000',   'name': 'รางวัลที่ 4'},
    'prizeFifth':               {'digits': 6, 'count': 100, 'reward': '20000',   'name': 'รางวัลที่ 5'},
    'runningNumberFrontThree':  {'digits': 3, 'count': 2,   'reward': '4000',    'name': 'รางวัลเลขหน้า 3 ตัว'},
    'runningNumberBackThree':   {'digits': 3, 'count': 2,   'reward': '4000',    'name': 'รางวัลเลขท้าย 3 ตัว'},
    'runningNumberBackTwo':     {'digits': 2, 'count': 1,   'reward': '2000',    'name': 'รางวัลเลขท้าย 2 ตัว'},
}

PRIZE_ORDER = ['prizeFirst', 'prizeFirstNear', 'prizeSecond',
               'prizeThird', 'prizeFourth', 'prizeFifth']
RUNNING_ORDER = ['runningNumberFrontThree', 'runningNumberBackThree',
                 'runningNumberBackTwo']

# ป้ายกำกับบนหน้า sanook → id ของเรา (เทียบแบบตัดช่องว่างออก)
# เรียงจากเจาะจงมากไปน้อย เพราะ 'ข้างเคียงรางวัลที่1' มีคำว่า 'รางวัลที่1' อยู่ด้วย
LABEL_MAP = [
    ('ข้างเคียงรางวัลที่1', 'prizeFirstNear'),
    ('เลขหน้า3ตัว',        'runningNumberFrontThree'),
    ('เลขท้าย3ตัว',        'runningNumberBackThree'),
    ('เลขท้าย2ตัว',        'runningNumberBackTwo'),
    ('รางวัลที่1',         'prizeFirst'),
    ('รางวัลที่2',         'prizeSecond'),
    ('รางวัลที่3',         'prizeThird'),
    ('รางวัลที่4',         'prizeFourth'),
    ('รางวัลที่5',         'prizeFifth'),
]


def id_to_thai_date(id: str) -> str:
    day = int(id[0:2])
    month = id[2:4]
    year = id[4:8]
    return f'{day} {THAI_MONTHS_REV.get(month, month)} {year}'


def id_sort_key(draw_id: str) -> tuple:
    """เรียงงวดจากใหม่ไปเก่าโดยดูจาก id (DDMMYYYY พ.ศ.) ไม่พึ่งลำดับบนหน้าเว็บ"""
    try:
        return (int(draw_id[4:8]), int(draw_id[2:4]), int(draw_id[0:2]))
    except ValueError:
        return (0, 0, 0)


def fetch_page(url: str, attempts: int = 3) -> BeautifulSoup:
    for i in range(attempts):
        try:
            # ใส่ query กัน cache ของ CDN ไม่ให้ส่งหน้าเก่าที่ผลยังไม่ออกกลับมา
            r = requests.get(url, headers=HEADERS, timeout=20,
                             params={'_': int(time.time())})
            r.raise_for_status()
            r.encoding = 'utf-8'
            return BeautifulSoup(r.text, 'lxml')
        except Exception as e:
            print(f'  ⚠️  fetch failed ({i + 1}/{attempts}) {url}: {e}')
            if i + 1 < attempts:
                time.sleep(2 * (i + 1))
    print(f'  ❌ fetch failed {url}')
    return None


def label_to_id(label_text: str) -> str:
    """แปลงหัวข้อรางวัลเป็น id — ตัดช่องว่างออกก่อนเทียบ กัน sanook เปลี่ยนการเว้นวรรค"""
    flat = re.sub(r'\s+', '', label_text)
    for needle, pid in LABEL_MAP:
        if needle in flat:
            return pid
    return None


def official_count(label_text: str, default: int) -> int:
    """อ่านจำนวนรางวัลจากหัวข้อจริง เช่น 'มี 50 รางวัลๆละ 40,000 บาท' → 50"""
    m = re.search(r'(\d+)\s*รางวัลๆ', label_text)
    return int(m.group(1)) if m else default


def official_reward(label_text: str, default: str) -> str:
    """อ่านเงินรางวัลจากหัวข้อจริง เช่น 'รางวัลละ 6,000,000 บาท' → '6000000'"""
    m = re.search(r'ละ\s*([\d,]+)\s*บาท', label_text)
    return m.group(1).replace(',', '') if m else default


def collect_blocks(soup: BeautifulSoup) -> dict:
    """
    ดึงเลขจาก DOM จริง ไม่ใช่การ scan ข้อความทั้งหน้า
    โครงสร้าง sanook: หัวข้อ p.title__reward กับเลข .lotto__number อยู่ในกล่องเดียวกัน
    ผูกหัวข้อกับเลขแบบนี้ทำให้ไม่หลุดไปหยิบเลขของรางวัลอื่น หรือหยิบจำนวนเงิน
    (เช่น '4,000 บาท' ที่เคยกลายเป็นเลข 000)
    """
    found = {}
    for label_el in soup.select('p.title__reward'):
        block = label_el.parent
        if block is None:
            continue
        label_text = label_el.get_text(' ', strip=True)
        pid = label_to_id(label_text)
        if not pid or pid in found:
            continue

        digits = SPEC[pid]['digits']
        raw = [el.get_text(strip=True) for el in block.select('.lotto__number')]
        # รับเฉพาะเลขที่จำนวนหลักถูกต้อง → 'xxx' / 'xxxxxx' ตอนหวยยังไม่ออกถูกตัดทิ้ง
        nums = [t for t in raw if re.fullmatch(r'\d{%d}' % digits, t)]

        found[pid] = {
            'numbers': nums,
            'placeholders': len(raw) - len(nums),
            'count': official_count(label_text, SPEC[pid]['count']),
            'reward': official_reward(label_text, SPEC[pid]['reward']),
        }
    return found


def parse_lotto_page(soup: BeautifulSoup, draw_id: str):
    """คืน (data, problems) — ถ้า problems ไม่ว่างแปลว่าผลยังไม่ครบ ห้ามบันทึก"""
    date_el = soup.find(['h1', 'h2'], string=re.compile(r'\d{4}'))
    date_text = date_el.get_text(strip=True) if date_el else id_to_thai_date(draw_id)

    found = collect_blocks(soup)
    problems = []

    for pid in PRIZE_ORDER + RUNNING_ORDER:
        blk = found.get(pid)
        if blk is None:
            problems.append(f'{pid}: ไม่พบหัวข้อบนหน้าเว็บ')
        elif blk['placeholders'] and not blk['numbers']:
            problems.append(f'{pid}: ยังเป็น xxx (ยังไม่ออกรางวัล)')
        elif len(blk['numbers']) != blk['count']:
            problems.append(
                f'{pid}: ได้ {len(blk["numbers"])} เลข แต่ต้องมี {blk["count"]}')

    if problems:
        return None, problems

    def block(pid):
        return {'id': pid, 'name': SPEC[pid]['name'], 'reward': found[pid]['reward'],
                'amount': found[pid]['count'], 'number': found[pid]['numbers']}

    return {'date': date_text, 'endpoint': f'{SANOOK_BASE}/check/{draw_id}/',
            'prizes': [block(pid) for pid in PRIZE_ORDER],
            'runningNumbers': [block(pid) for pid in RUNNING_ORDER]}, []


def is_valid_file(path: str) -> bool:
    """ไฟล์เดิมข้อมูลครบถูกต้องไหม — ถ้าไม่ครบจะ scrape ซ้ำให้เอง"""
    try:
        with open(path, encoding='utf-8') as f:
            res = json.load(f)['response']
    except Exception:
        return False

    blocks = {b['id']: b for b in res.get('prizes', []) + res.get('runningNumbers', [])}
    for pid, spec in SPEC.items():
        blk = blocks.get(pid)
        if not blk:
            return False
        nums = blk.get('number', [])
        if len(nums) != spec['count']:
            return False
        if not all(isinstance(n, str) and re.fullmatch(r'\d{%d}' % spec['digits'], n)
                   for n in nums):
            return False
    return True


def get_draw_list() -> list:
    print('📋 checking sanook for new draws...')
    soup = fetch_page(f'{SANOOK_BASE}/')
    if not soup:
        return []

    seen = set()
    results = []
    for a in soup.find_all('a', href=re.compile(r'/lotto/check/\d{8}')):
        m = re.search(r'/lotto/check/(\d{8})', a['href'])
        if m and m.group(1) not in seen:
            draw_id = m.group(1)
            seen.add(draw_id)
            results.append({'id': draw_id, 'date': id_to_thai_date(draw_id)})

    print(f'  found {len(results)} draws on sanook')
    return results


def scrape_draw(draw_id: str):
    url = f'{SANOOK_BASE}/check/{draw_id}/'
    print(f'  🔍 scraping {url}')
    soup = fetch_page(url)
    if not soup:
        return None, ['โหลดหน้าเว็บไม่สำเร็จ']
    return parse_lotto_page(soup, draw_id)


def main():
    repair = '--repair' in sys.argv
    os.makedirs(DATA_DIR, exist_ok=True)

    draw_list = get_draw_list()

    # รวมงวดที่เคยเก็บไว้แล้วด้วย เผื่อหน้าแรกของ sanook ลิสต์มาไม่ครบ
    known = {d['id'] for d in draw_list}
    for fn in os.listdir(DATA_DIR):
        m = re.fullmatch(r'(\d{8})\.json', fn)
        if m and m.group(1) not in known:
            known.add(m.group(1))
            draw_list.append({'id': m.group(1), 'date': id_to_thai_date(m.group(1))})

    draw_list.sort(key=lambda d: id_sort_key(d['id']), reverse=True)

    # scrape งวดที่ยังไม่มีไฟล์ หรือไฟล์เดิมข้อมูลไม่ครบ
    # (งวดที่เคย scrape ตอนหวยออกไม่ครบจะถูกเก็บใหม่ให้อัตโนมัติ)
    todo = []
    for draw in draw_list:
        out_path = os.path.join(DATA_DIR, f'{draw["id"]}.json')
        if repair or not os.path.exists(out_path) or not is_valid_file(out_path):
            todo.append(draw)

    if not todo:
        print('✅ ข้อมูลครบทุกงวดแล้ว ไม่ต้อง scrape')
    else:
        print(f'🆕 ต้อง scrape {len(todo)} งวด...')
        for draw in todo:
            data, problems = scrape_draw(draw['id'])
            if data:
                out_path = os.path.join(DATA_DIR, f'{draw["id"]}.json')
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump({'status': 'success', 'response': data}, f,
                              ensure_ascii=False, indent=2)
                print(f'  💾 saved {draw["id"]}.json')
            else:
                # ไม่เขียนทับไฟล์เดิม ปล่อยให้ cron รอบถัดไปมาเก็บใหม่
                print(f'  ⏳ ข้าม {draw["id"]} (ผลยังไม่ครบ): {"; ".join(problems[:3])}')
            time.sleep(1)

    # list.json เก็บเฉพาะงวดที่ข้อมูลครบจริง
    available = []
    for draw in draw_list:
        path = os.path.join(DATA_DIR, f'{draw["id"]}.json')
        if os.path.exists(path) and is_valid_file(path):
            available.append({
                'id': draw['id'],
                'url': f'/data/{draw["id"]}.json',
                'date': draw['date'],
            })

    with open(os.path.join(DATA_DIR, 'list.json'), 'w', encoding='utf-8') as f:
        json.dump({'status': 'success', 'response': available}, f,
                  ensure_ascii=False, indent=2)
    print(f'✅ list.json updated with {len(available)} draws')

    # latest.json → งวดล่าสุดที่ข้อมูลครบ
    if available:
        latest_id = available[0]['id']
        with open(os.path.join(DATA_DIR, f'{latest_id}.json'), encoding='utf-8') as f:
            latest_data = json.load(f)
        with open(os.path.join(DATA_DIR, 'latest.json'), 'w', encoding='utf-8') as f:
            json.dump(latest_data, f, ensure_ascii=False, indent=2)
        print(f'✅ latest.json → {latest_id}')


if __name__ == '__main__':
    main()
