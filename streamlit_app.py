import streamlit as st
import ccxt
import pandas as pd
import ta
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Analisa Crypto Real-Time", layout="wide")

# --- Styling for dark theme
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #d6d6d6; }
    .stButton>button { background-color: #111827; color: #d6d6d6; }
    </style>
    """, unsafe_allow_html=True
)

st.title("📊 Analisa Crypto — Dark Mode")
st.markdown("Pantau harga & sinyal otomatis (RSI, MACD, MA20). Refresh otomatis dapat diatur (10–300s).", unsafe_allow_html=True)

# --- Controls
col1, col2, col3 = st.columns([2,2,1])
with col1:
    symbol = st.selectbox("Pilih Koin", ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'PEPE/USDT', 'ADA/USDT'], index=0)
with col2:
    timeframe = st.selectbox("Pilih Timeframe", ['15m', '1h', '4h', '1d'], index=1)
with col3:
    refresh_rate = st.selectbox("Refresh (detik)", [10,20,30,60,90,120,180,240,300], index=3)

st.markdown("---")

exchange = ccxt.binance({
    'enableRateLimit': True,
})

@st.cache_data(ttl=30)
def get_data(symbol: str, timeframe: str, limit: int = 200):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def compute_indicators(df: pd.DataFrame):
    if df.empty:
        return df
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['ma20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
    return df

def generate_signal(df: pd.DataFrame):
    if df.empty or df.shape[0] < 35:
        return "NO DATA", "#AAAAAA"
    rsi = df['rsi'].iloc[-1]
    macd = df['macd'].iloc[-1]
    signal = df['signal'].iloc[-1]
    if rsi < 30 and macd > signal:
        return "BUY 📈", "#22c55e"
    elif rsi > 70 and macd < signal:
        return "SELL 📉", "#ef4444"
    else:
        return "HOLD ⚖️", "#94a3b8"

# --- Fetch and compute
df = get_data(symbol, timeframe, limit=300)
df = compute_indicators(df)
status_text, status_color = generate_signal(df)

# Top metrics
colA, colB, colC, colD = st.columns(4)
colA.metric("Harga Terakhir (USDT)", f"{df['close'].iloc[-1]:,.6f}" if not df.empty else "N/A")
colB.metric("RSI (14)", f"{df['rsi'].iloc[-1]:.2f}" if 'rsi' in df.columns and not df.empty else "N/A")
colC.metric("MACD", f"{df['macd'].iloc[-1]:.6f}" if 'macd' in df.columns and not df.empty else "N/A")
colD.metric("Sinyal", f"{status_text}")

st.markdown(f"<div style='padding:8px;border-radius:6px;background-color:{status_color};color:#071123;text-align:center;font-weight:600'>{status_text}</div>", unsafe_allow_html=True)

# --- Plots: Candlestick (top), RSI & MACD (bottom)
if not df.empty:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        specs=[[{"rowspan":1}], [{"rowspan":1}], [{"rowspan":1}]],
                        vertical_spacing=0.06,
                        subplot_titles=(f"{symbol} Price", "RSI (14)", "MACD"))
    # Candlestick + MA20
    fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='OHLC'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ma20'], mode='lines', name='MA20'), row=1, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['rsi'], mode='lines', name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", row=2, col=1)
    # MACD and Signal
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['macd'], mode='lines', name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['signal'], mode='lines', name='Signal'), row=3, col=1)

    fig.update_layout(height=800, template='plotly_dark', showlegend=True)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # example to avoid gaps (not strict)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Tidak ada data untuk ditampilkan. Coba ganti simbol atau timeframe.")

st.markdown("---")
st.caption("Source: Binance public API via ccxt. Indikator dibuat dengan library ta.")

# --- Auto refresh logic: use a countdown and rerun
countdown_placeholder = st.empty()
if refresh_rate > 0:
    for i in range(refresh_rate, 0, -1):
        countdown_placeholder.info(f"Auto-refresh dalam: {i} detik. (Reload otomatis)")
        time.sleep(1)
    st.experimental_rerun()
