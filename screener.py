import streamlit as st
import pandas as pd
import yfinance as yf
from grading import score_equity_full

def render_custom_screener():
    st.subheader("⚙️ NC5 Custom Asset Grader Tool")
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        custom_input = st.text_input("Enter Ticker Symbols (comma-separated)", value="AAPL, LQD, BTC-USD, MSFT", key="custom_tick_input").upper()
    with col_s2:
        selected_universe = st.selectbox("Grading Universe", options=["S&P 500", "Russell"], index=0, key="custom_univ_sel")

    universe_key = "sp500" if selected_universe == "S&P 500" else "russell"

    if st.button("Run NC5 Custom Grader"):
        symbols = [s.strip() for s in custom_input.split(",") if s.strip()]
        custom_rows = []
        for sym in symbols:
            if "USD" in sym or sym in ["BTC", "ETH"]:
                tk_sym = sym if "-USD" in sym else f"{sym}-USD"
                try:
                    tk = yf.Ticker(tk_sym)
                    hist = tk.history(period="1mo")
                    price = hist["Close"].iloc[-1] if not hist.empty else 0
                    custom_rows.append({
                        "Ticker": sym.replace("-USD", ""), "Universe": universe_key.upper(), "Name": sym, "Sector": "Cryptocurrency",
                        "Price": round(price, 2), "NC5_Master_Grade": 75, "Triggered_Patterns": "Crypto Momentum",
                        "F1_Valuation": 75, "F2_Consensus": 75, "F5_RangePos": 75
                    })
                except Exception:
                    custom_rows.append({
                        "Ticker": sym, "Universe": universe_key.upper(), "Name": sym, "Sector": "Cryptocurrency",
                        "Price": 0.0, "NC5_Master_Grade": 50, "Triggered_Patterns": "None",
                        "F1_Valuation": 50, "F2_Consensus": 50, "F5_RangePos": 50
                    })
            else:
                custom_rows.append(score_equity_full(sym, universe=universe_key))

        if custom_rows:
            df_custom = pd.DataFrame(custom_rows).sort_values(by="NC5_Master_Grade", ascending=False)
            st.dataframe(df_custom[["Ticker", "Universe", "Name", "Sector", "Price", "NC5_Master_Grade", "Triggered_Patterns", "F1_Valuation", "F2_Consensus", "F5_RangePos"]], use_container_width=True, hide_index=True)
