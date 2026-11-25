import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from charts import render_interactive_chart
from grading import score_equity_full, get_sp500_tickers
from backtester import render_backtester
from top_picks import render_top_picks
from screener import render_custom_screener

st.set_page_config(page_title="NC5 Institutional Multi-Asset Screener & Master Grader", layout="wide")

st.title("📈 NC5 Institutional Multi-Asset Screener & Master Grader")
st.write("Live charting, multi-factor grading (F1–F11), S&P 500 / Russell index weighting, 1-week swing pattern detection, and dual-system backtesting.")

tab_chart, tab_swing, tab_top30, tab_backtest, tab_screener = st.tabs([
    "📊 Interactive Chart & Fundamentals",
    "🎯 1-Week Swing Pattern Scanner",
    "🏆 NC5 Top 30 Weekly Buys",
    "📅 NC5 Dual-System Backtester",
    "⚙️ Custom Asset Graders (NC5 Engine)"
])

with tab_chart:
    render_interactive_chart()

with tab_swing:
    st.subheader("🎯 NC5 1-Week Swing Trade & Pattern Scanner")
    col_sw1, col_sw2, col_sw3, col_sw4 = st.columns(4)
    with col_sw1:
        swing_universe = st.selectbox("Index Weighting Model", ["S&P 500", "Russell"], index=0, key="sw_univ")
    with col_sw2:
        min_grade = st.slider("Minimum NC5 Master Grade", min_value=50, max_value=95, value=70, step=5)
    with col_sw3:
        scan_limit = st.selectbox("Scan Universe Size", [25, 50, 100, 250, 500], index=1)
    with col_sw4:
        require_pattern = st.checkbox("Require Active Pattern", value=True)

    sw_univ_key = "sp500" if swing_universe == "S&P 500" else "russell"

    if st.button("Run 1-Week Swing Scan"):
        tickers_to_scan = get_sp500_tickers()[:scan_limit]
        progress_bar = st.progress(0)
        status_text = st.empty()
        scanned_results = []

        for idx, sym in enumerate(tickers_to_scan):
            status_text.text(f"Scanning {sym} ({idx + 1}/{len(tickers_to_scan)})...")
            res = score_equity_full(sym, universe=sw_univ_key)
            scanned_results.append(res)
            progress_bar.progress((idx + 1) / len(tickers_to_scan))

        status_text.empty()
        progress_bar.empty()
        df_scan = pd.DataFrame(scanned_results)
        df_filtered = df_scan[df_scan["NC5_Master_Grade"] >= min_grade]
        if require_pattern:
            df_filtered = df_filtered[df_filtered["Pattern_Count"] > 0]
        df_filtered = df_filtered.sort_values(by=["Pattern_Count", "NC5_Master_Grade"], ascending=[False, False])

        if not df_filtered.empty:
            st.success(f"Found {len(df_filtered)} qualified swing candidates!")
            st.dataframe(df_filtered[["Ticker", "Universe", "Name", "Sector", "Price", "NC5_Master_Grade", "Triggered_Patterns", "F1_Valuation", "F2_Consensus", "F5_RangePos"]], use_container_width=True, hide_index=True)
        else:
            st.warning("No stocks matched criteria in this batch.")

with tab_top30:
    render_top_picks()

with tab_backtest:
    render_backtester()

with tab_screener:
    render_custom_screener()
