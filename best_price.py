# best_price_scanner_app.py

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Best Price Scanner – Covered Calls",
    layout="centered"
)

# ---------- Mean Reversion Probability Logic ----------

def mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl):
    score = 0
    notes = []

    # Distance from mean
    dist_pct = abs((price - sma20) / sma20 * 100)
    if 3 <= dist_pct <= 10:
        score += 1
        notes.append("Price stretched from mean")
    else:
        notes.append("Price not stretched enough")

    # RSI signals
    if rsi > 70 or rsi < 30:
        score += 1
        notes.append("RSI extreme (reversion likely)")
    elif 40 <= rsi <= 60:
        notes.append("RSI neutral (normalizing)")
    else:
        notes.append("RSI not signaling reversion")

    # ADX weakening
    if adx < 30:
        score += 1
        notes.append("Weak trend (reversion more likely)")
    else:
        notes.append("Strong trend (reversion less likely)")

    # VWAP alignment
    if (price > vwap and sma20 < price) or (price < vwap and sma20 > price):
        score += 1
        notes.append("VWAP alignment supports reversion")
    else:
        notes.append("VWAP not aligned")

    # Bollinger band touch
    if price >= bbu or price <= bbl:
        score += 1
        notes.append("Band touch (strong reversal signal)")
    else:
        notes.append("No band touch")

    # Final probability label
    if score >= 4:
        prob = "High"
    elif score >= 2:
        prob = "Medium"
    else:
        prob = "Low"

    return prob, notes


# ---------- Core Scanner Logic ----------

def evaluate_ticker(t):
    price = t["price"]
    sma20 = t["sma20"]
    sma50 = t["sma50"]
    ivr = t["ivr"]
    atr = t["atr"]
    rsi = t["rsi"]
    adx = t["adx"]
    vwap = t["vwap"]
    bbu = t["bbu"]
    bbl = t["bbl"]

    atr_pct = atr / price * 100 if price else 0
    dist_st_pct = (price - sma20) / sma20 * 100 if sma20 else 0

    score = 0
    notes = []

    # Valuation vs mean
    if (sma50 <= price <= sma20) or (price < sma50):
        score += 1
        val_label = "Good value (near/under mean)"
        notes.append("Price near/under mean (good value)")
    else:
        val_label = "Above mean (worse value)"
        notes.append("Price above mean (worse value)")

    # Trend safety
    if adx < 30 and price >= sma50:
        score += 1
        trend_label = "Trend stable above 50-SMA"
        notes.append("Trend stable above 50-SMA")
    else:
        trend_label = "Trend strong or below 50-SMA (caution)"
        notes.append("Trend strong or below 50-SMA (caution)")

    # RSI timing
    if 40 <= rsi <= 60:
        score += 1
        rsi_label = "RSI ideal (40–60)"
        notes.append("RSI in ideal buy zone")
    elif rsi > 70:
        rsi_label = "RSI overbought (>70)"
        notes.append("RSI overbought")
    else:
        rsi_label = "RSI not ideal"
        notes.append("RSI not ideal")

    # Stability
    if atr_pct < 3:
        score += 1
        atr_label = "Stable (ATR% < 3)"
        notes.append("ATR% stable (good for covered calls)")
    else:
        atr_label = "Jumpy (ATR% ≥ 3)"
        notes.append("ATR% high (jumpy)")

    # Premium quality
    if 20 <= ivr <= 50:
        score += 1
        ivr_label = "IVR good (20–50)"
        notes.append("IVR good for premium")
    elif ivr < 20:
        ivr_label = "IVR low (<20)"
        notes.append("IVR low (weak premium)")
    else:
        ivr_label = "IVR high (>50, risky)"
        notes.append("IVR high (risky but rich premium)")

    # Final action
    if score >= 4:
        action = "BUY for covered calls"
    elif score >= 2:
        action = "WAIT"
    else:
        action = "AVOID"

    return {
        "atr_pct": atr_pct,
        "dist_st_pct": dist_st_pct,
        "score": score,
        "action": action,
        "val_label": val_label,
        "trend_label": trend_label,
        "rsi_label": rsi_label,
        "atr_label": atr_label,
        "ivr_label": ivr_label,
        "notes": notes,
    }


# ---------- UI ----------

st.title("📊 Best Price Scanner – Covered Calls")

st.markdown(
    "Enter your ticker data and get a **Buy / Wait / Avoid** decision "
    "specifically optimized for **buying shares to sell covered calls**."
)

with st.sidebar:
    st.header("Ticker Inputs")

    ticker = st.text_input("Ticker", value="KSS").upper()

    price = st.number_input("Price", min_value=0.0, value=13.05, step=0.01)
    ivr = st.number_input("IV Rank", min_value=0.0, max_value=100.0, value=33.0, step=1.0)
    atr = st.number_input("ATR", min_value=0.0, value=0.24, step=0.01)
    rsi = st.number_input("RSI", min_value=0.0, max_value=100.0, value=68.98, step=0.1)
    adx = st.number_input("ADX", min_value=0.0, max_value=100.0, value=32.57, step=0.1)

    vwap = st.number_input("VWAP", min_value=0.0, value=12.97, step=0.01)
    bbu = st.number_input("Bollinger Upper (BBU)", min_value=0.0, value=13.27, step=0.01)
    bbl = st.number_input("Bollinger Lower (BBL)", min_value=0.0, value=11.55, step=0.01)

    sma20 = st.number_input("SMA 20", min_value=0.0, value=12.36, step=0.01)
    sma50 = st.number_input("SMA 50", min_value=0.0, value=12.76, step=0.01)

    run = st.button("Run Best Price Scan")

if run:
    data = {
        "price": price,
        "ivr": ivr,
        "atr": atr,
        "rsi": rsi,
        "adx": adx,
        "vwap": vwap,
        "bbu": bbu,
        "bbl": bbl,
        "sma20": sma20,
        "sma50": sma50,
    }

    result = evaluate_ticker(data)

    st.subheader(f"Result for **{ticker}**")

    # Mean Price directly under results
    mean_price = sma20
    st.metric("Mean Price", f"{mean_price:.2f}")

    # Mean Reversion Probability
    prob, mr_notes = mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl)

    st.markdown("### Mean Reversion Probability")
    st.metric("Reversion Likelihood", prob)

    st.write("**Why:**")
    for n in mr_notes:
        st.write(f"- {n}")

    st.markdown("---")

    # Top summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Action", result["action"])
    with col2:
        st.metric("Score (0–5)", result["score"])
    with col3:
        st.metric("ATR %", f"{result['atr_pct']:.2f}%")

    st.markdown("---")

    # Valuation panel
    st.markdown("### 1. Valuation vs Mean")

    colv1, colv2, colv3 = st.columns(3)
    with colv1:
        st.metric("Mean Price (SMA 20)", f"{mean_price:.2f}")
    with colv2:
        st.metric("Long-Term Mean (SMA 50)", f"{sma50:.2f}")
    with colv3:
        st.metric("Current Price", f"{price:.2f}")

    st.write(f"**Distance from Mean:** {result['dist_st_pct']:.2f}%")
    st.write(f"**Valuation Status:** {result['val_label']}")

    st.markdown("---")

    # Trend & stability
    st.markdown("### 2. Trend & Stability")
    colt1, colt2, colt3 = st.columns(3)
    with colt1:
        st.metric("ADX", f"{adx:.2f}")
    with colt2:
        st.metric("VWAP", f"{vwap:.2f}")
    with colt3:
        st.metric("ATR", f"{atr:.2f}")

    st.write(f"**Trend Status:** {result['trend_label']}")
    st.write(f"**Stability Status:** {result['atr_label']}")

    st.markdown("---")

    # Timing & premium
    st.markdown("### 3. Timing & Premium")
    colr1, colr2, colr3 = st.columns(3)
    with colr1:
        st.metric("RSI", f"{rsi:.2f}")
    with colr2:
        st.metric("BB Upper", f"{bbu:.2f}")
    with colr3:
        st.metric("BB Lower", f"{bbl:.2f}")

    st.write(f"**RSI Status:** {result['rsi_label']}")
    st.write(f"**Premium Status (IVR):** {result['ivr_label']}")

    st.markdown("---")

    # Notes
    st.markdown("### 4. Notes / Rationale")
    for n in result["notes"]:
        st.write(f"- {n}")

else:
    st.info("Set your inputs in the sidebar and click **Run Best Price Scan**.")
