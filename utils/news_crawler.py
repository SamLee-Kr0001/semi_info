from duckduckgo_search import DDGS
import pandas as pd
from datetime import datetime, timedelta

# Mapping countries to DuckDuckGo regions
# US: us-en, KR: kr-kr, JP: jp-jp, TW: tw-tzh, CN: cn-zh
COUNTRY_REGIONS = {
    "USA": "us-en",
    "Korea": "kr-kr",
    "Japan": "jp-jp",
    "Taiwan": "tw-tzh",
    "China": "cn-zh"
}

def fetch_news(keywords, countries, period_str="1m"):
    """
    Fetch news based on keywords and countries.
    period_str: '1m', '3m', '6m', 'custom' (custom not fully supported by DDG naturally, requires post-filtering)
    DDG supports 'd', 'w', 'm' (month), 'y'.
    We will map:
    1m -> 'm'
    3m -> 'm' (and fetch more/filter? DDG only allows 'd', 'w', 'm', 'y' usually or specific ranges)
    Actually DDG python lib `timelimit` arg supports 'd', 'w', 'm', 'y'.
    For >1 month, we might need 'y' and filter locally, or just 'm' for recent.
    """
    
    results = []
    
    # Determine timelimit
    timelimit = 'm' # Default 1 month
    if period_str == '1m':
        timelimit = 'm'
    elif period_str == '3m':
        timelimit = 'y' # Fetch year then filter? Or just accept 'y' limits
    elif period_str == '6m':
        timelimit = 'y'
        
    ddgs = DDGS()
    
    for country in countries:
        region = COUNTRY_REGIONS.get(country, "us-en")
        for keyword in keywords:
            # Construct query
            # Adding specialized query terms might help (e.g. "semiconductor")
            query = f"{keyword}"
            
            try:
                # max_results set to 20 per keyword/country to keep it snappy
                news_items = ddgs.news(keywords=query, region=region, safesearch='off', timelimit=timelimit, max_results=10)
                
                for item in news_items:
                    # item keys: date, title, body, url, image, source
                    results.append({
                        "keyword": keyword,
                        "country": country,
                        "title": item.get('title'),
                        "source": item.get('source'),
                        "date": item.get('date'),
                        "url": item.get('url'),
                        "summary": item.get('body')
                    })
            except Exception as e:
                print(f"Error fetching {keyword} in {country}: {e}")
                
    df = pd.DataFrame(results)
    
    # Post-filtering for dates if necessary (e.g. if we fetched 'y' but only want 3 months)
    if not df.empty and period_str in ['3m', '6m']:
        try:
            df['date_obj'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
            now = pd.Timestamp.now(tz='UTC')
            
            days = 30
            if period_str == '3m': days = 90
            if period_str == '6m': days = 180
            
            cutoff = now - timedelta(days=days)
            df = df[df['date_obj'] >= cutoff]
            # storage cleanup
            df = df.drop(columns=['date_obj'])
        except Exception as e:
            pass
            
    return df
