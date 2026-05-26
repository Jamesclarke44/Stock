# best_price_scanner_app.py

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
        return "Unknown", "Mean values missing — cannot determine buy zone.", 0, 0

    lower_mean = min(sma20, sma50)
    upper_mean = max(sma20, sma50)

    if lower_mean <= price <= upper_mean:
        label = "Inside mean buy zone"
    elif price < lower_mean:
        label = "Deep value zone"
        # keep description from map
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


# ---------- Buy / Hold / Sell Classifier ----------

def classify_buy_hold_sell(result, price, sma20, sma50, prob):
    """
    Rule-based Buy / Hold / Sell signal.
    Not financial advice – just how this model interprets conditions.
    """

    score = result["score"]
    dist_from_mean = result["dist_st_pct"]
    downtrend = price < sma50
    uptrend = price > sma50
    above_mean = price > sma20
    below_mean = price < sma20

    # SELL – aggressive, Barchart-style bias when things look weak
    if (
        score <= 1
        or (downtrend and prob == "Low")
        or (prob == "Low" and above_mean)
    ):
        label = "SELL"
        reason = (
            "Conditions are weak in this model: either strong/ongoing downtrend, low mean reversion probability, "
            "or very poor overall score. Risk of further downside or dead money is elevated."
        )

    # BUY – strong alignment
    elif (
        score >= 4
        and prob in ["High", "Medium"]
        and (below_mean or (min(sma20, sma50) <= price <= max(sma20, sma50)))
    ):
        label = "BUY"
        reason = (
            "Conditions are strong: good value vs mean, supportive trend/stability, and reasonable mean reversion "
            "probability. This is a favorable setup in this model."
        )

    # HOLD – everything in between
    else:
        label = "HOLD"
        reason = (
            "Conditions are mixed: not strong enough for a clear BUY, but not weak enough for a clear SELL. "
            "The model suggests waiting for clearer alignment in trend, valuation, and reversion signals."
        )

    return label, reason


# ---------- Risk Profile ----------

def risk_profile(atr_pct, adx, ivr):
    """
    Simple risk profile based on volatility, trend strength, and premium.
    """
    risk_score = 0
    tags = []

    # Volatility
    if atr_pct < 2:
        tags.append("Low volatility")
    elif atr_pct < 4:
        tags.append("Moderate volatility")
        risk_score += 1
    else:
        tags.append("High volatility")
        risk_score += 2

    # Trend strength
    if adx < 20:
        tags.append("Weak trend")
    elif adx < 35:
        tags.append("Moderate trend")
        risk_score += 1
    else:
        tags.append("Strong trend")
        risk_score += 2

    # Premium
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
    """
    Simple covered call yield and annualized yield.
    """
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


# ---------- What Would Need to Change for BUY ----------

def what_needs_to_change_for_buy(result, prob, price, sma20, sma50, rsi, adx, ivr, atr_pct):
    """
    Explain which levers would likely need to improve to flip to BUY.
    """
    messages = []

    if result["score"] < 4:
        messages.append(
            "- Overall scanner score is below 4. You would typically need at least one more category "
            "(valuation, trend, RSI timing, stability, or premium) to improve."
        )

    if prob == "Low":
        messages.append(
            "- Mean reversion probability is Low. A clearer stretch from the mean, RSI extreme, weaker trend (ADX < 30), "
            "VWAP alignment, or a Bollinger band touch would help."
        )

    if price > sma20:
        messages.append(
            "- Price is above the short-term mean (SMA 20). A pullback toward or slightly under the mean zone "
            "would improve value."
        )

    if adx >= 30:
        messages.append(
            "- ADX is elevated. A drop in ADX toward the low 20s would signal a weaker trend and better conditions "
            "for mean reversion and safer entries."
        )

    if not (20 <= ivr <= 50):
        messages.append(
            "- IVR is outside the 20–50 sweet spot. Moving into that range would balance premium and risk better."
        )

    if atr_pct >= 3:
        messages.append(
            "- ATR% is high. A calmer volatility regime (ATR% < 3) would reduce risk for covered calls."
        )

    if not messages:
        messages.append(
            "- Conditions are already close to BUY in this model. A small improvement in either mean reversion "
            "probability or scanner score could be enough."
        )

    return messages


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

    st.markdown("---")
    st.subheader("Covered Call Inputs (Optional)")
    cc_premium = st.number_input("Call Premium (per share)", min_value=0.0, value=0.35, step=0.01)
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

    st.subheader(f"Result for **{ticker}**")

    # Mean Price
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

    st.markdown("#### Why Probability Can Be Low Even Near the Mean")
    st.write(
        "Even when price is close to the mean (SMA 20), mean reversion probability can still be **Low** because "
        "the scanner uses five independent signals, not just price distance. Mean reversion requires multiple "
        "conditions to align: price stretch, RSI extremes, weakening trend (ADX), VWAP alignment, and Bollinger "
        "band touches. If only one of these is present (often just price stretch), the probability stays **Low**. "
        "Being near the mean is not enough — the market also needs to show signs of slowing, reversing, or losing trend strength."
    )

    st.markdown("---")

    # Buy / Hold / Sell
    bhs_label, bhs_reason = classify_buy_hold_sell(result, price, sma20, sma50, prob)

    st.markdown("### Overall Covered Call Assessment")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Scanner Action", result["action"])
    with col2:
        st.metric("Score (0–5)", result["score"])
    with col3:
        st.metric("ATR %", f"{result['atr_pct']:.2f}%")
    with col4:
        st.metric("Signal", bhs_label)

    st.caption(
        "Scanner Action is the covered-call specific view. The Buy / Hold / Sell Signal is a simplified summary "
        "of overall conditions in this model (not financial advice)."
    )

    st.markdown("#### Buy / Hold / Sell Explanation")
    st.write(bhs_reason)

    st.markdown("#### Scanner Interpretation: Buy / Wait / Avoid — With Explanation")
    st.write(
        "The scanner evaluates five categories: valuation vs mean, trend safety, RSI timing, stability (ATR%), "
        "and premium quality (IVR). Each category can add one point to the score. A total score of 4–5 is labeled "
        "**BUY for covered calls**, 2–3 is **WAIT**, and 0–1 is **AVOID**. This is not financial advice — it is simply "
        "how the scanner interprets the data. A stock is only a BUY when valuation, timing, trend, stability, and "
        "premium all align; if one or more of these are weak, the scanner will usually say **WAIT** instead of BUY."
    )

    st.markdown("#### What Would Need to Change for BUY (Model View)")
    needs = what_needs_to_change_for_buy(
        result, prob, price, sma20, sma50, rsi, adx, ivr, result["atr_pct"]
    )
    for m in needs:
        st.write(m)

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

    # Risk Profile
    st.markdown("### 4. Risk Profile")
    risk_level, risk_tags = risk_profile(result["atr_pct"], adx, ivr)
    st.metric("Risk Level", risk_level)
    st.write("**Risk Factors:**")
    for ttag in risk_tags:
        st.write(f"- {ttag}")
    st.caption("Risk level is based on volatility (ATR%), trend strength (ADX), and premium aggressiveness (IVR).")

    st.markdown("---")

    # Covered Call Yield Projection
    st.markdown("### 5. Covered Call Yield Projection")
    yld, yld_ann = covered_call_yield(price, cc_premium, cc_days)
    coly1, coly2 = st.columns(2)
    with coly1:
        st.metric("Yield for Period", f"{yld:.2f}%")
    with coly2:
        st.metric("Annualized Yield", f"{yld_ann:.2f}%")
    st.caption("Simple yield projection based on premium, underlying price, and days to expiry.")

    st.markdown("---")

    # Scenario Analysis
    st.markdown("### 6. Scenario Analysis")
    with st.expander("Try different price / RSI / ADX scenarios"):
        s_price = st.slider("Scenario Price", min_value=price * 0.7, max_value=price * 1.3, value=price, step=0.1)
        s_rsi = st.slider("Scenario RSI", min_value=0.0, max_value=100.0, value=rsi, step=1.0)
        s_adx = st.slider("Scenario ADX", min_value=0.0, max_value=100.0, value=adx, step=1.0)

        s_result, s_prob, s_mr_score, s_mr_notes, s_bhs_label, s_bhs_reason = run_scenario(
            s_price, sma20, sma50, ivr, atr, s_rsi, s_adx, vwap, bbu, bbl
        )

        st.write(f"**Scenario Mean Reversion Probability:** {s_prob}")
        st.write(f"**Scenario Scanner Score:** {s_result['score']}")
        st.write(f"**Scenario Signal (Buy / Hold / Sell):** {s_bhs_label}")
        st.write("**Scenario Interpretation:**")
        st.write(s_bhs_reason)

    st.markdown("---")

    # Notes
    st.markdown("### 7. Notes / Rationale")
    for n in result["notes"]:
        st.write(f"- {n}")
    st.caption("These notes summarize why the scanner reached its conclusion for this ticker.")

else:
    st.info("Set your inputs in the sidebar and click **Run Best Price Scan**.")
