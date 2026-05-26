# best_price_scanner_app.py

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Best Price Scanner – Covered Calls",
    layout="centered"
)

# ---------- Descriptions / Text Maps ----------

PROBABILITY_DESCRIPTIONS = {
    "High": "Very likely to revert soon — multiple reversal signals aligned.",
    "Medium": "Possible reversion — some signals aligned but not confirmed.",
    "Low": "Unlikely to revert now — few or no reversal signals present."
}

BUY_ZONE_DESCRIPTIONS = {
    "Inside mean buy zone": "Price is between SMA 50 and SMA 20 — classic fair-value buy area.",
    "Deep value zone": "Price is below SMA 50 — potentially cheap, but check trend risk.",
    "Above mean zone": "Price is above SMA 20 — more expensive, reversion risk is downward."
}


# ---------- UI Helpers ----------

def render_probability_block(prob: str):
    color_map = {
        "High": "#1f8b4c",    # green
        "Medium": "#e3b341",  # yellow
        "Low": "#c0392b"      # red
    }
    color = color_map.get(prob, "#555555")
    desc = PROBABILITY_DESCRIPTIONS.get(prob, "No description available.")

    html = f"""
    <div style="
        background-color:{color};
        padding:0.75rem 1rem;
        border-radius:0.5rem;
        color:white;
        margin-bottom:0.5rem;
        font-size:0.95rem;">
        <strong>{prob.upper()}</strong> – {desc}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------- Mean Reversion Probability Logic ----------

def mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl):
    score = 0
    notes = []

    # Distance from mean
    dist_pct = abs((price - sma20) / sma20 * 100) if sma20 else 0
    if 3 <= dist_pct <= 10:
        score += 1
        notes.append("Price stretched 3–10% from SMA 20 (good reversion zone).")
    else:
        notes.append("Price not significantly stretched from SMA 20.")

    # RSI signals
    if rsi > 70 or rsi < 30:
        score += 1
        notes.append("RSI extreme (overbought/oversold) — strong reversion signal.")
    elif 40 <= rsi <= 60:
        notes.append("RSI neutral (normalizing toward mean).")
    else:
        notes.append("RSI not clearly signaling reversion.")

    # ADX weakening
    if adx < 30:
        score += 1
        notes.append("Weak trend (ADX < 30) — mean reversion more likely.")
    else:
        notes.append("Strong trend (ADX ≥ 30) — trend may overpower reversion.")

    # VWAP alignment
    if (price > vwap and sma20 < price) or (price < vwap and sma20 > price):
        score += 1
        notes.append("VWAP alignment supports a move back toward the mean.")
    else:
        notes.append("VWAP not clearly aligned with reversion.")

    # Bollinger band touch
    if price >= bbu or price <= bbl:
        score += 1
        notes.append("Price touching Bollinger band — strong reversal / reversion signal.")
    else:
        notes.append("No Bollinger band touch yet.")

    # Final probability label
    if score >= 4:
        prob = "High"
    elif score >= 2:
        prob = "Medium"
    else:
        prob = "Low"

    return prob, score, notes


# ---------- Buy Zone Logic ----------

def buy_zone_indicator(price, sma20, sma50):
    if sma20 == 0 or sma50 == 0:
        return "Unknown", "Mean values missing — cannot determine buy zone."

    # Normalize so we always know the lower / upper mean
    lower_mean = min(sma20, sma50)
    upper_mean = max(sma20, sma50)

    if lower_mean <= price <= upper_mean:
        label = "Inside mean buy zone"
    elif price < lower_mean:
        label = "Deep value zone"
    else:
        label = "Above mean zone"

    desc = BUY_ZONE_DESCRIPTIONS.get(label, "No description available.")
    return label, desc, lower_mean, upper_mean


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
        notes.append("Price near or under mean — good value for accumulation.")
    else:
        val_label = "Above mean (worse value)"
        notes.append("Price above mean — paying a premium vs fair value.")

    # Trend safety
    if adx < 30 and price >= sma50:
        score += 1
        trend_label = "Trend stable above 50-SMA"
        notes.append("Trend stable and price above 50-SMA — structurally healthy.")
    else:
        trend_label = "Trend strong or below 50-SMA (caution)"
        notes.append("Trend strong or price below 50-SMA — use caution.")

    # RSI timing
    if 40 <= rsi <= 60:
        score += 1
        rsi_label = "RSI ideal (40–60)"
        notes.append("RSI in ideal zone — not overbought, not oversold.")
    elif rsi > 70:
        rsi_label = "RSI overbought (>70)"
        notes.append("RSI overbought — risk of pullback.")
    else:
        rsi_label = "RSI not ideal"
        notes.append("RSI not in ideal timing zone.")

    # Stability
    if atr_pct < 3:
        score += 1
        atr_label = "Stable (ATR% < 3)"
        notes.append("ATR% low — price behavior stable for covered calls.")
    else:
        atr_label = "Jumpy (ATR% ≥ 3)"
        notes.append("ATR% high — price is jumpy, riskier for covered calls.")

    # Premium quality
    if 20 <= ivr <= 50:
        score += 1
        ivr_label = "IVR good (20–50)"
        notes.append("IVR in sweet spot — decent premium without extreme risk.")
    elif ivr < 20:
        ivr_label = "IVR low (<20)"
        notes.append("IVR low — weak option premium.")
    else:
        ivr_label = "IVR high (>50, risky)"
        notes.append("IVR high — rich premium but higher risk.")

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
    "This tool evaluates a ticker for **buying shares to sell covered calls**, using "
    "mean reversion, volatility, and trend stability."
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
    st.metric("Mean Price (SMA 20)", f"{mean_price:.2f}")
    st.caption("SMA 20 is the short-term mean price used for timing entries.")

    # Mean Reversion Probability
    prob, mr_score, mr_notes = mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl)

    st.markdown("### Mean Reversion Probability")
    render_probability_block(prob)
    st.metric("Mean Reversion Score (0–5)", mr_score)
    st.caption("Higher scores mean more signals agreeing that price will revert back toward the mean.")

    st.write("**Why this probability was assigned:**")
    for n in mr_notes:
        st.write(f"- {n}")

    st.markdown("---")

    # Top summary
    st.markdown("### Overall Covered Call Assessment")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Action", result["action"])
    with col2:
        st.metric("Score (0–5)", result["score"])
    with col3:
        st.metric("ATR %", f"{result['atr_pct']:.2f}%")
    st.caption("Action and score summarize valuation, trend, timing, stability, and premium quality for covered calls.")

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

    st.write(f"**Distance from Mean (SMA 20):** {result['dist_st_pct']:.2f}%")
    st.write(f"**Valuation Status:** {result['val_label']}")
    st.caption("Distance from mean shows how stretched price is vs its short-term average.")

    # Buy Zone & Mean Range
    st.markdown("### Buy Zone & Mean Range")
    buy_label, buy_desc, lower_mean, upper_mean = buy_zone_indicator(price, sma20, sma50)
    st.metric("Mean Zone Range (SMA 50 → SMA 20)", f"{lower_mean:.2f} → {upper_mean:.2f}")
    st.write(f"**Buy Zone Indicator:** {buy_label}")
    st.write(buy_desc)
    st.caption("The mean zone is the band between SMA 50 and SMA 20 — a classic fair-value area for entries.")

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
    st.caption("Lower ADX and ATR% generally mean a calmer environment, better suited for covered calls.")

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
    st.caption("RSI helps with timing; IVR tells you how rich the option premium is relative to its history.")

    st.markdown("---")

    # Notes
    st.markdown("### 4. Notes / Rationale")
    for n in result["notes"]:
        st.write(f"- {n}")
    st.caption("These notes summarize why the scanner reached its conclusion for this ticker.")

else:
    st.info("Set your inputs in the sidebar and click **Run Best Price Scan**.")
