import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from patterns import detect_patterns

SP500_WEIGHTS = {
    "f1": 0.30, "f2": 0.15, "f3": 0.04, "f4": 0.04,
    "f5": 0.10, "f6": 0.04, "f7": 0.04, "f8": 0.04,
    "f9": 0.10, "f10": 0.10, "f11": 0.05
}

RUSSELL_WEIGHTS = {
    "f1": 0.25, "f2": 0.10, "f3": 0.05, "f4": 0.04,
    "f5": 0.10, "f6": 0.04, "f7": 0.06, "f8": 0.08,
    "f9": 0.08, "f10": 0.10, "f11": 0.10
}

def clamp(val, low=1, high=100):
    return int(max(low, min(high, round(val))))

@st.cache_data(ttl=3600)
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        tables = pd.read_html(res.text)
        return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
    except Exception:
        return [
            "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "BAC", "V", "MA",
            "UNH", "JNJ", "LLY", "PFE", "HD", "NKE", "PG", "COST", "WMT", "KO", "XOM", "CVX",
            "COP", "HON", "UPS", "CAT", "LIN", "FCX", "NEE", "DUK", "AMT", "PLD"
        ]

@st.cache_data(ttl=3600)
def score_equity_full(ticker_symbol, universe="sp500"):
    try:
        tk = yf.Ticker(ticker_symbol)
        info = tk.info or {}
        hist = tk.history(period="1y")

        fwd_pe = info.get("forwardPE")
        growth_dec = info.get("earningsGrowth")
        if fwd_pe is None or fwd_pe <= 0:
            f1 = 50
        else:
            growth_pct = max(0.0, (growth_dec or 0.0) * 100.0)
            justified_pe = 10.0 + (2.0 * growth_pct)
            val_ratio = min(2.0, justified_pe / fwd_pe)
            f1 = clamp(50.0 * val_ratio)

        rec_mean = info.get("recommendationMean")
        f2 = 50 if rec_mean is None else clamp(100.0 - ((rec_mean - 1.0) * 25.0))

        rec_key = str(info.get("recommendationKey", "")).lower().strip()
        tech_map = {"strong_buy": 95, "buy": 75, "hold": 50, "sell": 25, "strong_sell": 5}
        f3 = tech_map.get(rec_key, 50)

        summary = str(info.get("longBusinessSummary", "")).lower()
        risk_flags = ["class action", "sec investigation", "department of justice"]
        f4 = 25 if any(flag in summary for flag in risk_flags) else 85

        if hist is None or len(hist) < 170:
            f5 = 50
        else:
            window = hist.tail(170)
            high_170, low_170, last_close = window["High"].max(), window["Low"].min(), window["Close"].iloc[-1]
            pos_ratio = 0.5 if high_170 == low_170 else (last_close - low_170) / (high_170 - low_170)
            f5 = clamp(100.0 - (abs(pos_ratio - 0.5) * 100.0))

        industry = str(info.get("industry", "")).lower()
        sticky_keywords = ["aerospace & defense", "software", "utilities", "healthcare", "semiconductors", "communications", "bonds", "credit", "etf"]
        f6 = 90 if any(k in industry for k in sticky_keywords) else 65

        insiders = info.get("heldPercentInsiders")
        f7 = 40 if insiders is None else clamp(50.0 + ((insiders * 100.0) * 2.0))

        fcf, mkt_cap = info.get("freeCashflow"), info.get("marketCap")
        if fcf is None or not mkt_cap or mkt_cap <= 0:
            f8 = 50
        else:
            fcf_yield = (fcf / mkt_cap) * 100.0
            f8 = 95 if fcf_yield > 7.0 else (75 if fcf_yield > 4.0 else (55 if fcf_yield > 0.0 else 15))

        inst = info.get("heldPercentInstitutions")
        f9 = 40 if inst is None else (90 if (inst * 100.0) > 70.0 else (70 if (inst * 100.0) >= 40.0 else (50 if (inst * 100.0) >= 10.0 else 20)))

        try:
            ed = tk.earnings_dates
            if ed is not None and not ed.empty:
                valid_ed = ed.dropna(subset=["Reported EPS", "EPS Estimate"])
                if not valid_ed.empty:
                    actual_eps, est_eps = valid_ed["Reported EPS"].iloc[0], valid_ed["EPS Estimate"].iloc[0]
                    surprise_pct = 0 if est_eps == 0 else ((actual_eps - est_eps) / abs(est_eps)) * 100.0
                    f10 = 100 if surprise_pct >= -5.0 else clamp(100.0 - (3.0 * abs(surprise_pct + 5.0)))
                else:
                    f10 = 50
            else:
                f10 = 50
        except Exception:
            f10 = 50

        f11 = 50
        try:
            bs = tk.balance_sheet
            if bs is not None and not bs.empty:
                curr_assets = bs.loc["Current Assets"].iloc[0] if "Current Assets" in bs.index else bs.iloc[0].iloc[0]
                curr_liab = bs.loc["Current Liabilities"].iloc[0] if "Current Liabilities" in bs.index else bs.iloc[1].iloc[0]
                if curr_liab > 0:
                    curr_ratio = curr_assets / curr_liab
                    f11 = clamp(50 + (25 if curr_ratio > 1.5 else (-25 if curr_ratio < 1.0 else 0)))
        except Exception:
            pass

        weights = SP500_WEIGHTS if universe.lower() == "sp500" else RUSSELL_WEIGHTS

        weighted_sum = (
            (f1 * weights["f1"]) + (f2 * weights["f2"]) + (f3 * weights["f3"]) + (f4 * weights["f4"]) +
            (f5 * weights["f5"]) + (f6 * weights["f6"]) + (f7 * weights["f7"]) + (f8 * weights["f8"]) +
            (f9 * weights["f9"]) + (f10 * weights["f10"]) + (f11 * weights["f11"])
        )
        master_grade = clamp(weighted_sum)
        detected_setups = detect_patterns(hist)
        patterns_str = ", ".join(detected_setups) if detected_setups else "None"

        price = info.get("currentPrice", hist["Close"].iloc[-1] if not hist.empty else 0)
        sector_name = info.get("sector", "Equities / Bonds")
        if not sector_name or sector_name == "Unknown":
            sector_name = "Fixed Income / ETF" if ticker_symbol in ["LQD", "VCIT", "HYG", "ANGL", "SPIB", "USIG", "TLT", "BND"] else "Equities"

        return {
            "Ticker": ticker_symbol, "Universe": universe.upper(), "Name": info.get("shortName", ticker_symbol),
            "Sector": sector_name, "Price": round(price, 2) if price else 0, "NC5_Master_Grade": master_grade,
            "Triggered_Patterns": patterns_str, "Pattern_Count": len(detected_setups),
            "F1_Valuation": f1, "F2_Consensus": f2, "F5_RangePos": f5
        }
    except Exception:
        return {
            "Ticker": ticker_symbol, "Universe": universe.upper(), "Name": ticker_symbol, "Sector": "Error",
            "Price": 0.0, "NC5_Master_Grade": 50, "Triggered_Patterns": "None", "Pattern_Count": 0,
            "F1_Valuation": 50, "F2_Consensus": 50, "F5_RangePos": 50
        }

@st.cache_data(ttl=1800)
def fetch_and_score_top_crypto(limit=10):
    try:
        base = "https://api.coingecko.com/api/v3"
        stablecoins = {"usdt", "usdc", "dai", "fdusd", "usde", "tusd", "pyusd", "usdd"}
        resp = requests.get(f"{base}/coins/markets", params={
            "vs_currency": "usd", "order": "market_cap_desc", "per_page": limit + 5,
            "page": 1, "sparkline": "false", "price_change_percentage": "30d"
        }, timeout=20)
        resp.raise_for_status()
        coins = [c for c in resp.json() if c["symbol"].lower() not in stablecoins][:limit]

        results = []
        for coin in coins:
            mkt_cap = coin.get("market_cap") or 0
            fdv = coin.get("fully_diluted_valuation") or mkt_cap
            vol_24h = coin.get("total_volume") or 0
            rank = coin.get("market_cap_rank") or 100

            circ_ratio = (mkt_cap / fdv) if fdv > 0 else 0.5
            f6_fdv = clamp(circ_ratio * 100.0)
            f1_conc = clamp(95 - (rank * 0.45))
            turnover_pct = (vol_24h / mkt_cap * 100.0) if mkt_cap > 0 else 0
            f2_vol = 92 if 2.0 <= turnover_pct <= 15.0 else (70 if turnover_pct <= 40.0 else 25)

            master_grade = clamp((f1_conc * 0.4) + (f2_vol * 0.4) + (f6_fdv * 0.2))
            results.append({
                "Ticker": coin["symbol"].upper(), "Universe": "CRYPTO", "Name": coin["name"],
                "Sector": "Cryptocurrency", "Price": coin["current_price"], "NC5_Master_Grade": master_grade,
                "Triggered_Patterns": "Crypto Momentum", "Pattern_Count": 1,
                "F1_Valuation": f1_conc, "F2_Consensus": f2_vol, "F5_RangePos": f6_fdv
            })
        return pd.DataFrame(results)
    except Exception:
        return pd.DataFrame()
