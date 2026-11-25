import streamlit as st
import pandas as pd
from grading import score_equity_full, fetch_and_score_top_crypto

def render_top_picks():
    st.subheader("🏆 NC5 Top 30 Multi-Asset Dynamic Ranking & Selection")
    top30_universe = st.radio("Equity Weighting Profile", ["S&P 500", "Russell"], horizontal=True, key="top30_univ")
    top30_univ_key = "sp500" if top30_universe == "S&P 500" else "russell"

    if st.button("Generate Top 30 Ranked Portfolio"):
        with st.spinner("Scoring candidate universe..."):
            stock_candidates = ["AAPL", "MSFT", "NVDA", "GOOGL", "JPM", "BAC", "V", "MA", "UNH", "JNJ", "LLY", "PFE", "AMZN", "TSLA", "HD", "NKE", "PG", "COST", "WMT", "KO", "XOM", "CVX", "COP", "HON", "UPS", "CAT", "LIN", "FCX", "NEE", "DUK", "AMT", "PLD"]
            bond_candidates = ["LQD", "VCIT", "HYG", "ANGL", "SPIB", "USIG", "TLT", "BND"]
            scored_equities = [score_equity_full(s, universe=top30_univ_key) for s in (stock_candidates + bond_candidates)]
            df_equities = pd.DataFrame(scored_equities)
            df_crypto = fetch_and_score_top_crypto(10)
            df_combined = pd.concat([df_equities, df_crypto], ignore_index=True).sort_values(by="NC5_Master_Grade", ascending=False)
            st.success("Top 30 Portfolio Generated!")
            st.dataframe(df_combined[["Ticker", "Universe", "Name", "Sector", "Price", "NC5_Master_Grade", "Triggered_Patterns", "F1_Valuation", "F2_Consensus", "F5_RangePos"]].head(30), use_container_width=True, hide_index=True)
