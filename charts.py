import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render_interactive_chart():
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    with col_ctrl1:
        chart_ticker = st.text_input("Ticker Symbol", value="AAPL", key="chart_tick").upper().strip()
    with col_ctrl2:
        timeframe = st.selectbox(
            "Chart Timeline",
            options=["1D (5m)", "5D (15m)", "1M (1h)", "6M (1d)", "YTD (1d)", "1Y (1d)", "2Y (1wk)", "5Y (1wk)", "Max (1mo)"],
            index=5
        )
    with col_ctrl3:
        chart_style = st.selectbox("Chart Style", ["Candlestick", "Line"], index=0)

    tf_map = {
        "1D (5m)": ("1d", "5m"), "5D (15m)": ("5d", "15m"), "1M (1h)": ("1mo", "1h"),
        "6M (1d)": ("6mo", "1d"), "YTD (1d)": ("ytd", "1d"), "1Y (1d)": ("1y", "1d"),
        "2Y (1wk)": ("2y", "1wk"), "5Y (1wk)": ("5y", "1wk"), "Max (1mo)": ("max", "1mo"),
    }
    yf_period, yf_interval = tf_map[timeframe]

    if chart_ticker:
        try:
            tk = yf.Ticker(chart_ticker)
            info = tk.info or {}
            hist = tk.history(period=yf_period, interval=yf_interval)

            if not hist.empty:
                curr_price = info.get("currentPrice", hist["Close"].iloc[-1])
                prev_close = info.get("previousClose", hist["Close"].iloc[0])
                diff, pct = curr_price - prev_close, ((curr_price - prev_close) / prev_close) * 100 if prev_close else 0

                div_rate = info.get("dividendRate")
                div_yield = info.get("dividendYield")
                div_pct = (div_rate / curr_price * 100) if (div_rate and curr_price > 0) else (div_yield * 100 if div_yield else 0.0)
                if div_pct > 35.0: 
                    div_pct = 0.0

                st.subheader(f"{info.get('longName', chart_ticker)} ({chart_ticker})")
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Price", f"${curr_price:,.2f}", f"{diff:+.2f} ({pct:+.2f}%)")
                m2.metric("Market Cap", f"${info.get('marketCap', 0)/1e9:,.1f}B")
                m3.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
                m4.metric("EPS (TTM)", f"${info.get('trailingEps', 'N/A')}")
                m5.metric("Volume", f"{info.get('volume', hist['Volume'].iloc[-1]):,.0f}")
                m6.metric("Div Yield", f"{div_pct:.2f}%")

                hist["MA20"] = hist["Close"].rolling(window=20).mean()
                hist["MA50"] = hist["Close"].rolling(window=50).mean()

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
                if chart_style == "Candlestick":
                    fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name="Price"), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Close"), row=1, col=1)

                fig.add_trace(go.Scatter(x=hist.index, y=hist["MA20"], mode="lines", name="20 MA", line=dict(color="orange")), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist["MA50"], mode="lines", name="50 MA", line=dict(color="cyan")), row=1, col=1)
                colors = ["green" if c >= o else "red" for c, o in zip(hist["Close"], hist["Open"])]
                fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], marker_color=colors, name="Volume"), row=2, col=1)

                fig.update_layout(height=600, xaxis_rangeslider_visible=False, dragmode="drawline", title=f"{chart_ticker} Chart ({timeframe})")
                st.plotly_chart(fig, use_container_width=True, config={"editable": True, "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"]})
        except Exception as e:
            st.error(f"Error loading chart: {e}")
