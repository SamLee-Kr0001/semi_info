from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import feedparser
import time
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
import re

app = Flask(__name__)

# --- 설정 및 경로 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'keywords.json')
DRIVER_PATH = os.path.join(BASE_DIR, 'chromedriver.exe')

# 데이터 캐시 (서버 메모리에 임시 저장)
NEWS_CACHE = {}

# 초기 데이터 구조 (기업 정보 포함)
DEFAULT_DATA = {
    'info': {'name': "반도체 정보 & 이슈", 'keywords': []},
    'pr': {'name': "Photoresist (PR)", 'keywords': []},
    'wet': {'name': "Wet Chemical", 'keywords': []},
    'slurry': {'name': "CMP Slurry", 'keywords': []},
    'wafer': {'name': "Wafer", 'keywords': []},
    'company': {'name': "기업 정보", 'keywords': []} 
}

# --- DB 관리 (자동 병합 기능) ---
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=4)
        return DEFAULT_DATA

    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except:
            return DEFAULT_DATA
    
    # 새 카테고리(예: company)가 파일에 없으면 자동 추가
    is_modified = False
    for key, val in DEFAULT_DATA.items():
        if key not in data:
            data[key] = val
            is_modified = True
    
    if is_modified:
        save_db(data)
    
    return data

# --- 날짜 파싱 및 표준화 ---
def parse_date(date_str):
    """ 문자열 날짜를 datetime 객체로 변환 """
    if not date_str: return datetime.min
    now = datetime.now()
    date_str = str(date_str).strip()
    
    try:
        # 1. 상대 시간 (분/시간/일 전)
        numbers = re.findall(r'\d+', date_str)
        if numbers and any(x in date_str for x in ['분', 'min', 'm', '分钟', '시간', 'hour', 'h', '小时', '일', 'day', 'd', '天']):
            val = int(numbers[0])
            if any(x in date_str for x in ['분', 'min', 'm', '分钟']): return now - timedelta(minutes=val)
            if any(x in date_str for x in ['시간', 'hour', 'h', '小时']): return now - timedelta(hours=val)
            if any(x in date_str for x in ['일', 'day', 'd', '天']): return now - timedelta(days=val)

        # 2. 절대 날짜
        clean_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').strip()
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%y-%m-%d', '%d %b %Y'):
            try: return datetime.strptime(clean_str, fmt)
            except: continue
    except: pass
    
    # 파싱 실패 시 정렬에서 뒤로 밀리도록 처리
    return datetime.min

# --- 키워드 번역 (한글 -> 중문) ---
def translate_keywords(keywords):
    cn_keywords = []
    if not keywords: return []
    try:
        translator = GoogleTranslator(source='auto', target='zh-CN')
        for k in keywords[:5]: 
            cn_k = translator.translate(k)
            cn_keywords.append(cn_k)
    except:
        return keywords 
    return cn_keywords

# --- [핵심] 통합 크롤러 ---
def get_news_via_selenium(keywords):
    if not os.path.exists(DRIVER_PATH):
        print("[Error] chromedriver.exe가 없습니다.")
        return []
    if not keywords: return []

    print("\n[System] 크롤링 시작 (Google, Baidu, OFweek)...")
    cn_keywords = translate_keywords(keywords)
    limit_date = datetime.now() - timedelta(days=180) # 6개월 제한
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    articles = []
    driver = None

    try:
        service = Service(executable_path=DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)

        # 1. Google News
        try:
            query = " OR ".join([f'"{k}"' for k in keywords[:7]])
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko&tbs=qdr:m6"
            print(f"[Google] 수집 중...")
            driver.get(url)
            feed = feedparser.parse(driver.page_source)
            for entry in feed.entries:
                dt_obj = datetime.min
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6])
                else:
                    dt_obj = datetime.now()

                if dt_obj < limit_date: continue
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'date_obj': dt_obj,
                    'date_str': dt_obj.strftime('%Y-%m-%d %H:%M'),
                    'source': entry.source.title if hasattr(entry, 'source') else 'Google News',
                    'engine': 'Google'
                })
        except Exception as e: print(f"[Google] Error: {e}")

        # 2. Baidu News
        try:
            cn_query = " ".join(cn_keywords[:3])
            ts_start = int(limit_date.timestamp())
            ts_end = int(datetime.now().timestamp())
            gpc = f"stf={ts_start},{ts_end}|st={ts_start}|et={ts_end}"
            url = f"https://www.baidu.com/s?tn=news&wd={urllib.parse.quote(cn_query)}&gpc={urllib.parse.quote(gpc)}"
            print(f"[Baidu] 수집 중...")
            driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for item in soup.select('div.result-op, div.c-container'):
                try:
                    title_tag = item.select_one('h3 a')
                    if not title_tag: continue
                    title = title_tag.get_text().strip()
                    link = title_tag['href']
                    date_text = 'Recent'
                    date_tag = item.select_one('.c-age')
                    if date_tag: date_text = date_tag.get_text().strip()
                    
                    dt_obj = parse_date(date_text)
                    if dt_obj < limit_date: continue
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'date_obj': dt_obj,
                        'date_str': dt_obj.strftime('%Y-%m-%d %H:%M'),
                        'source': 'Baidu',
                        'engine': 'Baidu'
                    })
                except: continue
        except Exception as e: print(f"[Baidu] Error: {e}")

        # 3. OFweek (반도체/기업 전문)
        try:
            cn_query = cn_keywords[0] if cn_keywords else "Semiconductor"
            url = f"https://www.ofweek.com/search/search.html?keywords={urllib.parse.quote(cn_query)}&type=1"
            print(f"[OFweek] 수집 중...")
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for item in soup.select('div.list-article li, div.search-list li'): 
                try:
                    title_tag = item.select_one('h3 a')
                    if not title_tag: continue
                    title = title_tag.get_text().strip()
                    href = title_tag['href']
                    link = href if href.startswith('http') else "https:" + href
                    
                    date_text = 'Recent'
                    date_tag = item.select_one('span.time')
                    if date_tag: date_text = date_tag.get_text().strip()
                    
                    dt_obj = parse_date(date_text)
                    if dt_obj < limit_date: continue
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'date_obj': dt_obj,
                        'date_str': dt_obj.strftime('%Y-%m-%d %H:%M'),
                        'source': 'OFweek',
                        'engine': 'OFweek'
                    })
                except: continue
        except Exception as e: print(f"[OFweek] Error: {e}")

    except Exception as e:
        print(f"[Fatal Error] {e}")
    finally:
        if driver: driver.quit()

    # [정렬] 날짜 기준 내림차순 (최신순)
    articles.sort(key=lambda x: (x['date_obj'], x['title']), reverse=True)
    
    # [제한] 50개만 반환
    return articles[:50]

# --- API 라우트 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def api_news():
    cat = request.args.get('category', 'info')
    refresh = request.args.get('refresh', '0')
    
    db = load_db()
    if cat not in db: return jsonify([])
    data = db[cat]
    
    # 강제 새로고침(1)이거나 캐시에 없으면 크롤링
    if refresh == '1' or cat not in NEWS_CACHE:
        print(f"[API] Updating '{cat}'...")
        results = get_news_via_selenium(data['keywords'])
        NEWS_CACHE[cat] = results
    else:
        print(f"[API] Using Cache for '{cat}'")
        results = NEWS_CACHE[cat]
    
    return jsonify({
        'name': data['name'], 
        'keywords': data['keywords'], 
        'articles': results
    })

@app.route('/api/keyword', methods=['POST'])
def add_keyword():
    req = request.json
    cat = req.get('category')
    keyword = req.get('keyword')
    db = load_db()
    if cat in db and keyword and keyword not in db[cat]['keywords']:
        db[cat]['keywords'].append(keyword)
        save_db(db)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/keyword', methods=['DELETE'])
def del_keyword():
    req = request.json
    cat = req.get('category')
    keyword = req.get('keyword')
    db = load_db()
    if cat in db and keyword in db[cat]['keywords']:
        db[cat]['keywords'].remove(keyword)
        save_db(db)
        return jsonify({'success': True})
    return jsonify({'success': False})

if __name__ == '__main__':
    load_db() # 실행 시 DB 체크
    app.run(debug=True, port=5000)
