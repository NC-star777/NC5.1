import pandas as pd
import numpy as np

def detect_patterns(hist):
    if hist is None or len(hist) < 200:
        return []

    patterns_found = []
    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]
    volume = hist["Volume"]

    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain_2 = gain.rolling(2).mean()
    avg_loss_2 = loss.rolling(2).mean()
    rs_2 = avg_gain_2 / avg_loss_2.replace(0, np.nan)
    rsi_2 = 100 - (100 / (1 + rs_2))
    rsi_2 = rsi_2.fillna(100)

    curr_close = close.iloc[-1]
    curr_low = low.iloc[-1]
    curr_atr = atr_14.iloc[-1]

    # --- PATTERN 1: High-Tight Bull Flag ---
    ret_5d = (curr_close - close.iloc[-6]) / close.iloc[-6]
    flag_vol_low = volume.iloc[-4:].mean() < (volume.iloc[-10:-4].mean() * 0.7)
    flag_tight = (high.iloc[-4:].max() - low.iloc[-4:].min()) < (2.5 * curr_atr)
    if ret_5d > 0.08 and flag_tight and flag_vol_low and curr_close >= high.iloc[-4:-1].max():
        patterns_found.append("High-Tight Bull Flag")

    # --- PATTERN 2: 20-Day SMA Pullback ---
    is_uptrend = (curr_close > sma_50.iloc[-1]) and (sma_50.iloc[-1] > sma_200.iloc[-1]) and (sma_20.iloc[-1] > sma_20.iloc[-5])
    touched_sma20 = abs(curr_low - sma_20.iloc[-1]) <= (0.007 * curr_close) or (curr_low <= sma_20.iloc[-1] and curr_close >= sma_20.iloc[-1])
    is_green_day = curr_close > hist["Open"].iloc[-1]
    if is_uptrend and touched_sma20 and is_green_day:
        patterns_found.append("20-Day SMA Pullback")

    # --- PATTERN 3: NR7 / Volatility Squeeze ---
    daily_range = high - low
    is_nr7 = daily_range.iloc[-1] == daily_range.iloc[-7:].min()
    if is_uptrend and is_nr7 and (curr_close > sma_20.iloc[-1]):
        patterns_found.append("NR7 Volatility Squeeze")

    # --- PATTERN 4: RSI(2) Oversold Dip ---
    if (curr_close > sma_200.iloc[-1]) and (rsi_2.iloc[-2] < 10 or rsi_2.iloc[-1] < 12):
        patterns_found.append("RSI(2) Oversold Dip")

    # --- PATTERN 5: Post-Earnings Box Breakout ---
    recent_volumes = volume.iloc[-7:]
    recent_gaps = (high.iloc[-7:] - low.iloc[-7:].shift(1)) / low.iloc[-7:].shift(1)
    had_earnings_spike = (recent_gaps > 0.04).any() and (recent_volumes > (volume.rolling(20).mean().iloc[-1] * 2.0)).any()
    box_tight = (high.iloc[-4:].max() - low.iloc[-4:].min()) < (3.0 * curr_atr)
    if had_earnings_spike and box_tight and (curr_close >= high.iloc[-5:-1].max()):
        patterns_found.append("Post-Earnings Box Breakout")

    return patterns_found
