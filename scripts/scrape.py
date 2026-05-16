import requests
from bs4 import BeautifulSoup
import json
import os
import re

SANOOK_BASE = 'https://news.sanook.com/lotto'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'th-TH,th;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://news.sanook.com/',
}

THAI_MONTHS = {
    'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03',
    'เมษายน': '04', 'พฤษภาคม': '05', 'มิถุนายน': '06',
    'กรกฎาคม': '07', 'สิงหาคม': '08', 'กันยายน': '09',
    'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
}
THAI_MONTHS_REV = {v: k for k, v in THAI_MONTHS.items()}


def id_to_thai_date(id: str) -> str:
    day = int(id[0:2])
    month = id[2:4]
    year = id[4:8]
    return f'{day} {THAI_MONTHS_REV.get(month, month)} {year}'


def fetch_page(url: str) -> BeautifulSoup:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'lxml')
    except Exception as e:
        print(f'  ❌ fetch failed {url}: {e}')
        return None


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
            date_text = a.get_text(strip=True) or id_to_thai_date(draw_id)
            results.append({'id': draw_id, 'date': date_text})

    print(f'  found {len(results)} draws on sanook')
    return results


def parse_lotto_page(soup: BeautifulSoup, draw_id: str) -> dict:
    prizes = []
    running_numbers = []

    date_el = soup.find(['h1', 'h2'], string=re.compile(r'\d{4}'))
    date_text = date_el.get_text(strip=True) if date_el else id_to_thai_date(draw_id)

    full_text = soup.get_text()

    def find_numbers(label_patterns, length):
        pattern = r'\b\d{' + str(length) + r'}\b'
        for label in label_patterns:
            idx = full_text.find(label)
            if idx == -1:
                continue
            chunk = full_text[idx:idx + 300]
            nums = re.findall(pattern, chunk)
            if nums:
                return list(dict.fromkeys(nums))
        return []

    n = find_numbers(['รางวัลที่ 1', 'รางวัลที่1'], 6)
    if n:
        prizes.append({'id': 'prizeFirst', 'name': 'รางวัลที่ 1',
                        'reward': '6000000', 'amount': 1, 'number': n[:1]})

    n = find_numbers(['ข้างเคียงรางวัลที่ 1', 'รางวัลข้างเคียง'], 6)
    if n:
        prizes.append({'id': 'prizeFirstNear', 'name': 'รางวัลข้างเคียงรางวัลที่ 1',
                        'reward': '100000', 'amount': 2, 'number': n[:2]})

    for pid, pname, reward, max_count in [
        ('prizeSecond', 'รางวัลที่ 2', '200000', 5),
        ('prizeThird',  'รางวัลที่ 3', '80000',  10),
        ('prizeFourth', 'รางวัลที่ 4', '40000',  50),
        ('prizeFifth',  'รางวัลที่ 5', '20000',  100),
    ]:
        n = find_numbers([pname, pname.replace(' ', '')], 6)
        if n:
            prizes.append({'id': pid, 'name': pname, 'reward': reward,
                            'amount': len(n), 'number': n[:max_count]})

    n = find_numbers(['เลขหน้า 3 ตัว', 'เลขหน้า3ตัว'], 3)
    if n:
        running_numbers.append({'id': 'runningNumberFrontThree', 'name': 'รางวัลเลขหน้า 3 ตัว',
                                  'reward': '4000', 'amount': len(n), 'number': n[:2]})

    n = find_numbers(['เลขท้าย 3 ตัว', 'เลขท้าย3ตัว'], 3)
    if n:
        running_numbers.append({'id': 'runningNumberBackThree', 'name': 'รางวัลเลขท้าย 3 ตัว',
                                  'reward': '4000', 'amount': len(n), 'number': n[:2]})

    n = find_numbers(['เลขท้าย 2 ตัว', 'เลขท้าย2ตัว'], 2)
    if n:
        running_numbers.append({'id': 'runningNumberBackTwo', 'name': 'รางวัลเลขท้าย 2 ตัว',
                                  'reward': '2000', 'amount': len(n), 'number': n[:1]})

    if not prizes:
        print(f'  ⚠️  could not parse prizes for {draw_id}')
        return None

    return {'date': date_text, 'endpoint': f'{SANOOK_BASE}/check/{draw_id}/',
            'prizes': prizes, 'runningNumbers': running_numbers}


def scrape_draw(draw_id: str) -> dict:
    url = f'{SANOOK_BASE}/check/{draw_id}/'
    print(f'  🔍 scraping {url}')
    soup = fetch_page(url)
    if not soup:
        return None
    return parse_lotto_page(soup, draw_id)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    draw_list = get_draw_list()

    # ตรวจว่างวดไหนที่ยังไม่มีไฟล์ → scrape เฉพาะงวดใหม่
    new_draws = []
    for draw in draw_list:
        out_path = os.path.join(DATA_DIR, f'{draw["id"]}.json')
        if not os.path.exists(out_path):
            new_draws.append(draw)

    if not new_draws:
        print('✅ ไม่มีงวดใหม่ ไม่ต้อง scrape')
    else:
        print(f'🆕 พบ {len(new_draws)} งวดใหม่ กำลัง scrape...')
        for draw in new_draws:
            data = scrape_draw(draw['id'])
            if data:
                out_path = os.path.join(DATA_DIR, f'{draw["id"]}.json')
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump({'status': 'success', 'response': data}, f,
                              ensure_ascii=False, indent=2)
                print(f'  💾 saved {draw["id"]}.json')

    # อัปเดต list.json เสมอ (เผื่อมีงวดใหม่)
    available = []
    for draw in draw_list:
        if os.path.exists(os.path.join(DATA_DIR, f'{draw["id"]}.json')):
            available.append({
                'id': draw['id'],
                'url': f'/data/{draw["id"]}.json',
                'date': draw['date']
            })

    with open(os.path.join(DATA_DIR, 'list.json'), 'w', encoding='utf-8') as f:
        json.dump({'status': 'success', 'response': available}, f,
                  ensure_ascii=False, indent=2)
    print(f'✅ list.json updated with {len(available)} draws')

    # latest.json → งวดล่าสุด
    if available:
        latest_id = available[0]['id']
        latest_src = os.path.join(DATA_DIR, f'{latest_id}.json')
        if os.path.exists(latest_src):
            with open(latest_src, encoding='utf-8') as f:
                latest_data = json.load(f)
            with open(os.path.join(DATA_DIR, 'latest.json'), 'w', encoding='utf-8') as f:
                json.dump(latest_data, f, ensure_ascii=False, indent=2)
            print(f'✅ latest.json → {latest_id}')


if __name__ == '__main__':
    main()