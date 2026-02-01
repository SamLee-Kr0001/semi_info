import yfinance as yf
import pandas as pd
import streamlit as st

SECTORS = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU", "TSMC": "TSM", "Intel": "INTC", "SMIC": "0981.HK"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO", "Qnity (Q)": "Q"}, # Note: 'Q' might be incorrect, relying on user input
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T", "KLA": "KLAC", "Hanmi": "042700.KS", "Jusung": "036930.KS"},
    "🧪 Materials": {"Shin-Etsu": "4063.T", "Sumitomo": "4005.T", "TOK": "4186.T", "Nissan Chem": "4021.T", "Merck": "MRK.DE", "Air Liquide": "AI.PA", "Linde": "LIN", "Soulbrain": "357780.KS", "Dongjin": "005290.KS", "ENF": "102710.KS", "Ycchem": "232140.KS"},
    "🔋 Others": {"Samsung SDI": "006400.KS"}
}

def get_stock_data():
    """Fetches stock data for defined sectors."""
    data = {}
    
    # Flatten the list of tickers to fetch in batch if possible, or iterate
    # yfinance handles batch well, but mixed exchanges can be tricky.
    # We will fetch individually or by sector to handle errors gracefully.
    
    for sector, companies in SECTORS.items():
        sector_data = []
        for name, ticker in companies.items():
            try:
                stock = yf.Ticker(ticker)
                # Get usage period '1d' to check today/yesterday
                # fast_info is better for real-time, but history is good for close
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[0] if len(hist) > 1 else current_price
                    change = current_price - prev_close
                    pct_change = (change / prev_close) * 100
                    
                    sector_data.append({
                        "name": name,
                        "ticker": ticker,
                        "price": current_price,
                        "change": change,
                        "pct_change": pct_change
                    })
                else:
                    # Fallback or error
                    pass
            except Exception as e:
                # print(f"Error fetching {ticker}: {e}")
                pass
        data[sector] = sector_data
        
    return data

def display_sidebar_stocks():
    st.sidebar.header("Global Stock Indices")
    
    if st.sidebar.button("🔄 Update Stocks"):
        st.cache_data.clear()
        
    # We cache the data fetch to avoid spamming the API on every interaction
    # Using st.cache_data with a simplified wrapper if needed, 
    # but for now calling direct or using a cached function wrapper in app.py is better.
    # For now, let's assume we pass the data in or call a cached function.
    pass 
