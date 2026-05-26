import streamlit as st
import pandas as pd
import math

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
        "High": "#1f8b4c",
        "Medium": "#e3b341",
        "Low": "#c0392b"
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

# ---------- Buy/Hold/Sell Color Block ----------

def render_bhs_block(label: str, reason: str):
    color_map = {
        "BUY": "#1f8b4c",
        "HOLD": "#e3b341",
        "SELL": "#c0392b"
    }
    color = color_map.get(label, "#555555")

    html = f"""
    <div style="
        background-color:{color};
        padding:1rem 1.25rem;
        border-radius:0.5rem;
        color:white;
        margin-bottom:1rem;
        font-size:1.25rem;">
        <strong>{label}</strong><br>
        <span style="font-size:1rem;">{reason}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
# ---------- Mean Reversion Probability Logic ----------

def mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl):
    score = 0
    notes = []

    dist_pct = abs((price - sma20) / sma20 * 100) if sma20 else 0
    if 3 <= dist_pct <= 10:
        score += 1
        notes.append("Price stretched 3–10% from SMA 20 (good reversion zone).")
    else:
        notes.append("Price not significantly stretched from SMA 20.")

    if rsi > 70 or rsi < 30:
        score += 1
        notes.append("RSI extreme — strong reversion signal.")
    elif 40 <= rsi <= 60:
        notes.append("RSI neutral.")
    else:
        notes.append("RSI not signaling reversion.")

    if adx < 30:
        score += 1
        notes.append("Weak trend (ADX < 30).")
    else:
        notes.append("Strong trend (ADX ≥ 30).")

    if (price > vwap and sma20 < price) or (price < vwap and sma20 > price):
        score += 1
        notes.append("VWAP alignment supports reversion.")
    else:
        notes.append("VWAP not aligned.")

    if price >= bbu or price <= bbl:
        score += 1
        notes.append("Bollinger band touch — strong signal.")
    else:
        notes.append("No band touch.")

    if score >= 4:
        prob = "High"
    elif score >= 2:
        prob = "Medium"
    else:
        prob = "Low"

    return prob, score, notes

# ---------- Buy Zone Logic ----------

def buy_zone_indicator(price, sma20, sma50):
    lower_mean = min(sma20, sma50)
    upper_mean = max(sma20, sma50)

    if lower_mean <= price <= upper_mean:
        label = "Inside mean buy zone"
    elif price < lower_mean:
        label = "Deep value zone"
    else:
        label = "Above mean zone"

    return label, BUY_ZONE_DESCRIPTIONS[label], lower_mean, upper_mean

# ---------- Core Scanner Logic ----------

def evaluate_ticker(t):
    price = t["price"]
    sma20 = t["sma20"]
    sma50 = t["sma50"]
    ivr = t["ivr"]
    atr = t["atr"]
    rsi = t["rsi"]
    adx = t["adx"]

    atr_pct = atr / price * 100 if price else 0
    dist_st_pct = (price - sma20) / sma20 * 100 if sma20 else 0

    score = 0
    notes = []

    if (sma50 <= price <= sma20) or (price < sma50):
        score += 1
        val_label = "Good value (near/under mean)"
    else:
        val_label = "Above mean (worse value)"

    if adx < 30 and price >= sma50:
        score += 1
        trend_label = "Trend stable above 50-SMA"
    else:
        trend_label = "Trend strong or below 50-SMA"

    if 40 <= rsi <= 60:
        score += 1
        rsi_label = "RSI ideal (40–60)"
    elif rsi > 70:
        rsi_label = "RSI overbought"
    else:
        rsi_label = "RSI not ideal"

    if atr_pct < 3:
        score += 1
        atr_label = "Stable (ATR% < 3)"
    else:
        atr_label = "Jumpy (ATR% ≥ 3)"

    if 20 <= ivr <= 50:
        score += 1
        ivr_label = "IVR good (20–50)"
    elif ivr < 20:
        ivr_label = "IVR low"
    else:
        ivr_label = "IVR high"

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
    }

# ---------- Buy / Hold / Sell Classifier ----------

def classify_buy_hold_sell(result, price, sma20, sma50, prob):
    score = result["score"]
    downtrend = price < sma50
    above_mean = price > sma20

    if score <= 1 or (downtrend and prob == "Low") or (prob == "Low" and above_mean):
        return "SELL", "Weak conditions: downtrend, low reversion probability, or poor score."

    if score >= 4 and prob in ["High", "Medium"] and price <= sma20:
        return "BUY", "Strong alignment: value, trend, timing, and premium."

    return "HOLD", "Mixed conditions — not strong enough for BUY, not weak enough for SELL."

# ---------- Risk Profile ----------

def risk_profile(atr_pct, adx, ivr):
    risk_score = 0
    tags = []

    if atr_pct < 2:
        tags.append("Low volatility")
    elif atr_pct < 4:
        tags.append("Moderate volatility")
        risk_score += 1
    else:
        tags.append("High volatility")
        risk_score += 2

    if adx < 20:
        tags.append("Weak trend")
    elif adx < 35:
        tags.append("Moderate trend")
        risk_score += 1
    else:
        tags.append("Strong trend")
        risk_score += 2

    if ivr < 20:
        tags.append("Low premium")
    elif ivr <= 50:
        tags.append("Balanced premium")
    else:
        tags.append("Aggressive premium")
        risk_score += 1

    if risk_score <= 1:
        level = "Low"
    elif risk_score == 2:
        level = "Moderate"
    else:
        level = "High"

    return level, tags

# ---------- Covered Call Yield Projection ----------

def covered_call_yield(price, premium, days_to_expiry):
    if price <= 0 or days_to_expiry <= 0:
        return 0.0, 0.0

    yield_pct = premium / price * 100
    annualized = yield_pct * (365 / days_to_expiry)
    return yield_pct, annualized

# ---------- Scenario Runner ----------

def run_scenario(price, sma20, sma50, ivr, atr, rsi, adx, vwap, bbu, bbl):
    t = {
        "price": price,
        "sma20": sma20,
        "sma50": sma50,
        "ivr": ivr,
        "atr": atr,
        "rsi": rsi,
        "adx": adx,
        "vwap": vwap,
        "bbu": bbu,
        "bbl": bbl,
    }
    result = evaluate_ticker(t)
    prob, mr_score, mr_notes = mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl)
    bhs_label, bhs_reason = classify_buy_hold_sell(result, price, sma20, sma50, prob)
    return result, prob, mr_score, mr_notes, bhs_label, bhs_reason
# ---------- UI ----------

st.title("📊 Best Price Scanner – Covered Calls")

with st.sidebar:
    st.header("Ticker Inputs")

    ticker = st.text_input("Ticker", value="KSS").upper()

    price = st.number_input("Price", min_value=0.0, value=13.05, step=0.01)
    ivr = st.number_input("IV Rank", min_value=0.0, max_value=100.0, value=33.0, step=1.0)
    atr = st.number_input("ATR", min_value=0.0, value=0.24, step=0.01)
    rsi = st.number_input("RSI", min_value=0.0, max_value=100.0, value=68.98, step=0.1)
    adx = st.number_input("ADX", min_value=0.0, max_value=100.0, value=32.57, step=0.1)

    vwap = st.number_input("VWAP", min_value=0.0, value=12.97, step=0.01)
    bbu = st.number_input("BB Upper", min_value=0.0, value=13.27, step=0.01)
    bbl = st.number_input("BB Lower", min_value=0.0, value=11.55, step=0.01)

    sma20 = st.number_input("SMA 20", min_value=0.0, value=12.36, step=0.01)
    sma50 = st.number_input("SMA 50", min_value=0.0, value=12.76, step=0.01)

    st.subheader("Covered Call Inputs")
    cc_premium = st.number_input("Call Premium", min_value=0.0, value=0.35, step=0.01)
    cc_days = st.number_input("Days to Expiry", min_value=1, value=30, step=1)

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
    prob, mr_score, mr_notes = mean_reversion_probability(price, sma20, rsi, adx, vwap, bbu, bbl)

    st.subheader(f"Result for **{ticker}**")

    # ---------- BUY / HOLD / SELL BLOCK AT TOP ----------
    bhs_label, bhs_reason = classify_buy_hold_sell(result, price, sma20, sma50, prob)
    render_bhs_block(bhs_label, bhs_reason)
    # Mean Reversion Probability
    st.markdown("### Mean Reversion Probability")
    render_probability_block(prob)
    st.metric("Mean Reversion Score", mr_score)

    st.write("**Why this probability was assigned:**")
    for n in mr_notes:
        st.write(f"- {n}")

    st.markdown("#### Why Probability Can Be Low Even Near the Mean")
    st.write(
        "Even when price is close to the mean, mean reversion probability can still be **Low** because "
        "the scanner uses five independent signals, not just price distance."
    )

    st.markdown("---")

    # Covered Call Assessment
    st.markdown("### Covered Call Assessment")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Scanner Action", result["action"])
    with col2:
        st.metric("Score", result["score"])
    with col3:
        st.metric("ATR %", f"{result['atr_pct']:.2f}%")

    st.markdown("---")

    # Risk Profile
    st.markdown("### Risk Profile")
    risk_level, risk_tags = risk_profile(result["atr_pct"], adx, ivr)
    st.metric("Risk Level", risk_level)
    for tag in risk_tags:
        st.write(f"- {tag}")

    st.markdown("---")

    # Covered Call Yield
    st.markdown("### Covered Call Yield Projection")
    yld, yld_ann = covered_call_yield(price, cc_premium, cc_days)
    st.metric("Yield for Period", f"{yld:.2f}%")
    st.metric("Annualized Yield", f"{yld_ann:.2f}%")

    st.markdown("---")

    # Scenario Analysis
    st.markdown("### Scenario Analysis")
    with st.expander("Try different scenarios"):
        s_price = st.slider("Scenario Price", price * 0.7, price * 1.3, price)
        s_rsi = st.slider("Scenario RSI", 0.0, 100.0, rsi)
        s_adx = st.slider("Scenario ADX", 0.0, 100.0, adx)

        s_result, s_prob, s_mr_score, s_mr_notes, s_bhs_label, s_bhs_reason = run_scenario(
            s_price, sma20, sma50, ivr, atr, s_rsi, s_adx, vwap, bbu, bbl
        )

        st.write(f"**Scenario Signal:** {s_bhs_label}")
        st.write(s_bhs_reason)

    st.markdown("---")

    # Notes
    st.markdown("### Notes / Rationale")
    st.write(f"- Valuation: {result['val_label']}")
    st.write(f"- Trend: {result['trend_label']}")
    st.write(f"- RSI: {result['rsi_label']}")
    st.write(f"- ATR: {result['atr_label']}")
    st.write(f"- IVR: {result['ivr_label']}")

else:
    st.info("Set your inputs and click Run Best Price Scan.")
