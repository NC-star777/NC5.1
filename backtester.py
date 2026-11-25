import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from patterns import detect_patterns

def render_backtester():
    st.subheader("📅 NC5 Dual-System Rotational & Swing Backtester")
    st.markdown("Test either the **Regular Multi-Asset Rotational System** or the **1-Week Swing Trade Pattern System** historically.")

    backtest_system = st.radio("Select Backtest System", ["Regular Multi-Asset Rotational System", "1-Week Swing Trade Pattern System"], horizontal=True)
    bt_period = st.selectbox("Backtest Period", options=["6mo", "1y", "2y", "3y", "5y"], index=1, key="bt_per")
    bt_capital = st.number_input("Starting Capital ($)", value=100000.0, step=10000.0, key="bt_cap")
    top_n = st.slider("Top Active Picks Weekly", min_value=3, max_value=15, value=8, key="bt_topn")

    if st.button("Run Backtest Simulation"):
        with st.spinner(f"Running simulation for {backtest_system}..."):
            try:
                universe_all = [
                    "AAPL", "MSFT", "NVDA", "JPM", "BAC", "UNH", "JNJ", "AMZN", "TSLA", "PG",
                    "COST", "XOM", "CVX", "HON", "UPS", "LIN", "NEE", "GOOGL", "META", "AMT",
                    "LQD", "VCIT", "HYG", "SPY"
                ]
                raw_data = yf.download(universe_all, period=bt_period, interval="1wk", progress=False)

                if isinstance(raw_data.columns, pd.MultiIndex):
                    data = raw_data['Close'] if 'Close' in raw_data.columns.levels[0] else raw_data.xs('Close', level=0, axis=1, drop_level=True)
                else:
                    data = raw_data

                data = data.dropna(how="all")
                if data.empty or "SPY" not in data.columns:
                    st.error("Insufficient historical data retrieved.")
                else:
                    spy_prices = data["SPY"]
                    asset_prices = data.drop(columns=["SPY"], errors="ignore")
                    weekly_returns = asset_prices.pct_change().shift(-1).dropna()

                    portfolio_values = [bt_capital]
                    dates = [asset_prices.index[0]]
                    curr_cap = bt_capital

                    for i in range(len(asset_prices) - 1):
                        date_curr = asset_prices.index[i]
                        date_next = asset_prices.index[i+1]
                        window_slice = asset_prices.iloc[:i+1]

                        if backtest_system == "Regular Multi-Asset Rotational System":
                            past_perf = window_slice.tail(4).pct_change().sum()
                            valid_perf = past_perf.dropna()
                            if len(valid_perf) >= top_n:
                                top_picks = valid_perf.nlargest(top_n).index.tolist()
                                if date_curr in weekly_returns.index:
                                    next_week_ret = weekly_returns.loc[date_curr, top_picks].mean()
                                    curr_cap *= (1 + (next_week_ret if not pd.isna(next_week_ret) else 0.0))
                        else:
                            qualified_picks = []
                            for col in asset_prices.columns:
                                stock_hist = yf.Ticker(col).history(period="3mo")
                                if not stock_hist.empty and len(stock_hist) > 50:
                                    p_setups = detect_patterns(stock_hist)
                                    if len(p_setups) > 0:
                                        qualified_picks.append(col)
                            
                            if qualified_picks and date_curr in weekly_returns.index:
                                valid_picks = [p for p in qualified_picks if p in weekly_returns.columns]
                                if valid_picks:
                                    next_week_ret = weekly_returns.loc[date_curr, valid_picks].mean()
                                    curr_cap *= (1 + (next_week_ret if not pd.isna(next_week_ret) else 0.0))

                        portfolio_values.append(curr_cap)
                        dates.append(date_next)

                    spy_norm = (spy_prices / spy_prices.iloc[0]) * bt_capital
                    final_val = portfolio_values[-1]
                    net_pct = ((final_val - bt_capital) / bt_capital) * 100
                    spy_final = spy_norm.iloc[-1]
                    spy_pct = ((spy_final - bt_capital) / bt_capital) * 100

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Strategy Ending Value", f"${final_val:,.2f}", f"{net_pct:+.2f}%")
                    m2.metric("S&P 500 Benchmark", f"${spy_final:,.2f}", f"{spy_pct:+.2f}%")
                    m3.metric("Alpha Generated", f"{net_pct - spy_pct:+.2f}%")

                    fig_bt = go.Figure()
                    fig_bt.add_trace(go.Scatter(x=dates, y=portfolio_values, mode="lines", name=backtest_system, line=dict(color="green", width=2)))
                    fig_bt.add_trace(go.Scatter(x=spy_norm.index, y=spy_norm, mode="lines", name="S&P 500 (SPY)", line=dict(color="gray", dash="dash")))
                    fig_bt.update_layout(title=f"Backtest Comparison: {backtest_system}", xaxis_title="Date", yaxis_title="Portfolio Value ($)", height=500)
                    st.plotly_chart(fig_bt, use_container_width=True)
            except Exception as e:
                st.error(f"Error running backtest: {e}")
