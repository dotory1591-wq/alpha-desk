import streamlit as st
import yfinance as yf
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 🔑 API KEY
API_KEY = ""

try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", API_KEY)
    genai.configure(api_key=API_KEY)
except:
    pass
# ---------------------------------------------------------

st.set_page_config(page_title="Alpha Desk: Morning", layout="wide", page_icon="🌤️")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: Pretendard, sans-serif; }
    .stApp { background-color: #F8F9FA; color: #2C3E50; }
    .metric-card {
        background-color: #FFFFFF; border: 1px solid #E9ECEF;
        border-radius: 16px; padding: 24px; margin-bottom: 10px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
    }
    .ai-box {
        background-color: #F0F7FF; border-left: 4px solid #74A5FF;
        border-radius: 8px; padding: 16px; margin-top: 15px; 
        font-size: 0.95rem; color: #34495E; line-height: 1.6;
    }
    .update-time { font-size: 0.8rem; color: #95A5A6; text-align: right; margin-bottom: 10px; }
    .card-title { font-size: 1.2rem; font-weight: 800; color: #000000; } /* 카드 제목 완전 검정 */
    .card-price { font-size: 2.8rem; font-weight: 900; color: #000000; margin-top: 5px; } /* 가격 완전 검정 */
    .up-color { color: #E74C3C; font-weight: 800; } 
    .down-color { color: #3498DB; font-weight: 800; } 
    </style>
    """, unsafe_allow_html=True)

def get_korean_date():
    kr_time = datetime.now(pytz.timezone('Asia/Seoul'))
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{kr_time.year}년 {kr_time.month}월 {kr_time.day}일 {weekdays[kr_time.weekday()]}요일"

@st.cache_data(ttl=1800)
def get_weather_forecast():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=37.56&longitude=127.36&hourly=temperature_2m,weather_code&timezone=Asia%2FSeoul&forecast_days=1"
        res = requests.get(url, timeout=3).json()
        
        times = res['hourly']['time']
        temps = res['hourly']['temperature_2m']
        codes = res['hourly']['weather_code']
        
        current_hour = datetime.now().hour
        current_temp = temps[current_hour]
        
        weather_map = {
            0: "맑음 ☀️", 1: "대체로 맑음 🌤", 2: "흐림 ☁️", 3: "흐림 ☁️",
            45: "안개 🌫", 51: "이슬비 🌧", 61: "비 ☔️", 63: "비 ☔️",
            71: "눈 ☃️", 95: "뇌우 ⚡️"
        }
        condition_text = weather_map.get(codes[current_hour], "흐림 ☁️")
        
        df = pd.DataFrame({"Time": times, "Temp": temps})
        df['Time'] = pd.to_datetime(df['Time'])
        return current_temp, condition_text, df
    except:
        return None, None, None

def create_weather_chart(df):
    max_temp = df['Temp'].max()
    max_time = df.loc[df['Temp'].idxmax(), 'Time']
    
    fig = go.Figure()
    # 💡 선 두께를 3에서 4로 키워 더 선명하게
    fig.add_trace(go.Scatter(x=df['Time'], y=df['Temp'], mode='lines', fill='tozeroy', line=dict(color='#FFA726', width=4)))
    fig.add_annotation(
        x=max_time, y=max_temp, text=f"Max {max_temp}°",
        showarrow=True, arrowhead=1, yshift=10, 
        font=dict(color="#E74C3C", size=15, weight="bold"), bgcolor="#FFFFFF", bordercolor="#E9ECEF"
    )
    # 💡 텍스트 컬러 완벽한 검정(#000000) 및 폰트 사이즈 14로 확대
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0), height=140,
        xaxis=dict(showgrid=False, tickformat="%H시", color='#000000', tickfont=dict(size=14, color='#000000')), 
        yaxis=dict(showgrid=True, gridcolor='#BDC3C7', color='#000000', tickfont=dict(size=14, color='#000000')), showlegend=False
    )
    return fig

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo", interval="1d")
        if len(hist) < 2: return None
        
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        diff = curr - prev
        pct = (diff / prev) * 100
        
        now_kr = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%H:%M:%S")
        return {"curr": curr, "diff": diff, "pct": pct, "hist": hist, "time": now_kr}
    except:
        return None

def create_candle_chart(data):
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='#E74C3C', decreasing_line_color='#3498DB'
    )])
    # 💡 텍스트 컬러 완벽한 검정(#000000) 및 폰트 사이즈 14로 확대, 눈금선 색상 약간 더 진하게
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False,
        height=250, margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, color='#000000', tickfont=dict(size=14, color='#000000')), 
        yaxis=dict(showgrid=True, gridcolor='#BDC3C7', color='#000000', tickfont=dict(size=14, color='#000000'))
    )
    return fig

@st.cache_data(ttl=1800)
def get_official_news(ticker):
    search_ticker = "QQQ" if ticker == "TQQQ" else "SOXX" if ticker == "SOXL" else ticker
    url = f"https://finance.yahoo.com/rss/headline?s={search_ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    titles = []
    try:
        res = requests.get(url, headers=headers, timeout=5)
        root = ET.fromstring(res.text)
        for item in root.findall('.//item'):
            titles.append(item.find('title').text)
            if len(titles) >= 5: break
            
        if not titles:
            fallback = "MSFT" if ticker == "TQQQ" else "NVDA"
            res_fb = requests.get(f"https://finance.yahoo.com/rss/headline?s={fallback}", headers=headers, timeout=5)
            root_fb = ET.fromstring(res_fb.text)
            for item in root_fb.findall('.//item'):
                titles.append(item.find('title').text)
                if len(titles) >= 5: break
                
        return titles
    except:
        return []

@st.cache_data(ttl=3600)
def get_deep_analysis(ticker, change_rate, news_list):
    if not news_list:
        return "⚠️ 글로벌 증시 관련 뉴스가 없습니다. 기술적 분석을 참고하세요."

    try:
        news_txt = "\n".join([f"- {title}" for title in news_list])
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Role: Wall Street Expert. Target: {ticker} ETF. Today's Move: {change_rate}.
        News Found: {news_txt}
        Task: Explain WHY the ETF moved today in KOREAN based on the news above.
        Output: 3 bullet points, Professional and Positive tone.
        """
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"🚨 AI 에러 발생:<br><br>{str(e)}"

# =========================================================
# 🚀 메인 대시보드
# =========================================================
today_str = get_korean_date()

c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f"<div style='font-size:1.1rem; color:#000000; font-weight:700;'>{today_str}</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='color:#000000; font-weight:900; margin-top:-10px;'>🦅 Alpha Desk <span style='font-size:1rem; color:#3498DB; font-weight:600;'>| Morning Briefing</span></h2>", unsafe_allow_html=True)
with c2:
    if st.button("🔄 최신 데이터 불러오기"):
        st.cache_data.clear()
        st.rerun()

curr_temp, condition, weather_df = get_weather_forecast()
if weather_df is not None:
    weather_fig = create_weather_chart(weather_df)
    wc1, wc2 = st.columns([1, 4])
    with wc1:
        st.markdown(f"""
            <div class='metric-card' style='text-align:center; padding: 30px 10px;'>
                <div style='color:#000000; font-size:1rem; font-weight:700;'>NAMYANGJU</div>
                <div style='font-size:3.5rem; font-weight:900; color:#FFA726; line-height:1.2;'>{curr_temp}°</div>
                <div style='font-size:1.3rem; font-weight:800; color:#000000;'>{condition}</div>
            </div>
        """, unsafe_allow_html=True)
    with wc2:
        st.plotly_chart(weather_fig, use_container_width=True, config={'displayModeBar': False})

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

def draw_final_widget(col, name, ticker):
    with col:
        data_pack = get_stock_data(ticker)
        if data_pack:
            sign = "+" if data_pack['diff'] > 0 else ""
            color_class = "up-color" if data_pack['diff'] > 0 else "down-color"
            change_str = f"{sign}{data_pack['pct']:.2f}%"
            
            st.markdown(f"""
                <div class='metric-card'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span class='card-title'>{name}</span>
                        <div class='update-time'>🕒 {data_pack['time']}</div>
                    </div>
                    <div class='card-price'>
                        ${data_pack['curr']:.2f}
                    </div>
                    <div class='{color_class}' style='font-size:1.2rem;'>
                        {sign}{data_pack['diff']:.2f} ({change_str})
                    </div>
            """, unsafe_allow_html=True)
            
            fig = create_candle_chart(data_pack['hist'])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown(f"<div style='font-weight:900; color:#000000;'>✨ AI Market Insight</div>", unsafe_allow_html=True)
            with st.spinner(f"오늘의 시장을 읽고 있습니다..."):
                safe_news = get_official_news(ticker)
                insight = get_deep_analysis(ticker, change_str, safe_news)
                
            st.markdown(f"<div class='ai-box'>{insight}</div></div>", unsafe_allow_html=True)
        else:
            st.error(f"데이터 로딩 실패 ({ticker})")

draw_final_widget(col1, "NASDAQ 100 (TQQQ)", "TQQQ")
draw_final_widget(col2, "SEMICONDUCTOR (SOXL)", "SOXL")
