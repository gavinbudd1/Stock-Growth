"""
Stock price vs. company growth
Type a ticker and compare how the share price moved against revenue,
net income or EPS. Data: Yahoo Finance via yfinance.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

BLUE, ORANGE = "#2a78d6", "#eb6834"

METRICS = {
    "Revenue": ["Total Revenue", "Operating Revenue"],
    "Net income": ["Net Income", "Net Income Common Stockholders"],
    "EPS (diluted)": ["Diluted EPS", "Basic EPS"],
}
POPULAR = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "COST"]

st.set_page_config(page_title="Price vs. Growth", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      div[data-testid="stMetric"] {
          background: rgba(127,127,127,0.06);
          border: 1px solid rgba(127,127,127,0.15);
          border-radius: 12px; padding: 14px 18px;
      }
      .verdict {border-radius: 12px; padding: 14px 18px; margin: 6px 0 18px;
                border: 1px solid rgba(127,127,127,0.2);}
      .verdict b {font-weight: 600;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"

with st.sidebar:
    st.header("📈 Price vs. Growth")
    st.text_input("Ticker symbol", key="ticker", placeholder="e.g. AAPL")
    st.caption("Quick picks")
    cols = st.columns(4)
    def _pick(sym):
        st.session_state.ticker = sym

    for i, sym in enumerate(POPULAR):
        cols[i % 4].button(sym, width="stretch", on_click=_pick, args=(sym,))

    st.divider()
    metric = st.selectbox("Growth measure", list(METRICS))
    freq = st.radio("Reporting period", ["Annual", "Quarterly"], horizontal=True)
    indexed_pref = st.toggle("Index both lines to 100", value=True,
                             help="Starts both lines at 100 so you compare growth, not dollars.")
    st.divider()
    st.caption("Data from Yahoo Finance. Free data covers about 4 years "
               "(annual) or 5 quarters. Not investment advice.")

ticker = st.session_state.ticker.strip().upper()


# ---------- Data ----------
@st.cache_data(ttl=3600, show_spinner=False)
def load(sym: str, quarterly: bool):
    t = yf.Ticker(sym)
    stmt = t.quarterly_income_stmt if quarterly else t.income_stmt
    prices = t.history(period="max", auto_adjust=True)["Close"]
    try:
        info = t.info or {}
    except Exception:
        info = {}
    return stmt, prices, info


def pick_row(stmt: pd.DataFrame, candidates):
    for row in candidates:
        if row in stmt.index:
            s = stmt.loc[row].dropna()
            if not s.empty:
                return s
    return None


def fmt_big(v: float, per_share: bool = False) -> str:
    if per_share:
        return f"${v:,.2f}"
    for div, suf in [(1e12, "T"), (1e9, "B"), (1e6, "M")]:
        if abs(v) >= div:
            return f"${v / div:,.1f}{suf}"
    return f"${v:,.0f}"


if not ticker:
    st.info("Enter a ticker in the sidebar to get started.")
    st.stop()

with st.spinner(f"Loading {ticker}…"):
    try:
        stmt, prices, info = load(ticker, freq == "Quarterly")
    except Exception as e:
        st.error(f"Couldn't load data for **{ticker}**: {e}")
        st.stop()

if prices is None or prices.empty or stmt is None or stmt.empty:
    st.error(f"No data found for **{ticker}**. Check the symbol and try again.")
    st.stop()

fund = pick_row(stmt, METRICS[metric])
if fund is None:
    st.error(f"{metric} isn't available for **{ticker}**. Try another measure.")
    st.stop()

fund.index = pd.to_datetime(fund.index).tz_localize(None)
fund = fund.sort_index().astype(float)
prices.index = pd.to_datetime(prices.index).tz_localize(None)

start, end = fund.index[0], fund.index[-1]
prices = prices[prices.index >= start - pd.Timedelta(days=7)]
if prices.empty:
    st.error("Price history doesn't reach back to the first report date.")
    st.stop()

indexed = indexed_pref
if fund.iloc[0] <= 0 and indexed_pref:
    st.warning(f"{metric} was zero or negative at the start, so indexing would "
               "be misleading. Showing actual values instead.")
    indexed = False

# ---------- Header ----------
name = info.get("longName") or ticker
sub = " · ".join(x for x in [info.get("sector"), info.get("industry"),
                             info.get("exchange")] if x)
st.title(f"{name} ({ticker})")
if sub:
    st.caption(sub)

# ---------- Metrics ----------
p0, p1 = prices.asof(start), prices.asof(end)
price_chg = (p1 / p0 - 1) * 100
fund_chg = (fund.iloc[-1] / fund.iloc[0] - 1) * 100 if fund.iloc[0] > 0 else None
per_share = metric.startswith("EPS")
period_lbl = f"{start:%b %Y} → {end:%b %Y}"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest price", f"${prices.iloc[-1]:,.2f}")
m2.metric(f"Latest {metric}", fmt_big(fund.iloc[-1], per_share))
m3.metric("Price change", f"{price_chg:+.0f}%", help=period_lbl)
m4.metric(f"{metric} change", f"{fund_chg:+.0f}%" if fund_chg is not None else "n/a",
          help=period_lbl)

# ---------- Verdict ----------
if fund_chg is not None:
    gap = price_chg - fund_chg
    if abs(gap) < 15:
        msg = (f"🟰 Over {period_lbl}, the stock price and {metric.lower()} grew "
               f"<b>roughly in step</b> ({price_chg:+.0f}% vs {fund_chg:+.0f}%).")
    elif gap > 0:
        msg = (f"🔺 The stock price <b>outran the business</b>: price {price_chg:+.0f}% "
               f"vs {metric.lower()} {fund_chg:+.0f}% over {period_lbl}. "
               "Investors are paying more per dollar of results than before.")
    else:
        msg = (f"🔻 The business <b>outgrew the stock price</b>: {metric.lower()} "
               f"{fund_chg:+.0f}% vs price {price_chg:+.0f}% over {period_lbl}. "
               "The stock is cheaper per dollar of results than before.")
    st.markdown(f'<div class="verdict">{msg}</div>', unsafe_allow_html=True)

# ---------- Chart ----------
price_line = prices / prices.iloc[0] * 100 if indexed else prices
fund_line = fund / fund.iloc[0] * 100 if indexed else fund

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=price_line.index, y=price_line, name="Stock price",
    line=dict(width=2, color=BLUE),
    hovertemplate="%{y:,.1f}<extra>Price</extra>",
))
fig.add_trace(go.Scatter(
    x=fund_line.index, y=fund_line, name=metric,
    mode="lines+markers", yaxis="y" if indexed else "y2",
    line=dict(width=2.5, dash="dash", color=ORANGE),
    marker=dict(size=9, line=dict(width=2, color="white")),
    hovertemplate="%{y:,.1f}<extra>" + metric + "</extra>",
))
if indexed:
    fig.add_hline(y=100, line=dict(color="rgba(127,127,127,0.4)", width=1, dash="dot"))

layout = dict(
    height=520,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis=dict(title="Indexed (start = 100)" if indexed else "Price ($)",
               gridcolor="rgba(127,127,127,0.15)"),
    xaxis=dict(showgrid=False),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
if not indexed:
    layout["yaxis2"] = dict(title=metric, overlaying="y", side="right", showgrid=False)
fig.update_layout(**layout)
st.plotly_chart(fig, width="stretch")

st.caption("Price is adjusted for splits and dividends. When the blue line sits above "
           "the orange one, the stock has grown faster than the business.")

# ---------- Table ----------
with st.expander("See the numbers"):
    table = pd.DataFrame({
        "Report date": fund.index.strftime("%Y-%m-%d"),
        metric: [fmt_big(v, per_share) for v in fund],
        "Price that day": [f"${prices.asof(d):,.2f}" for d in fund.index],
    })
    st.dataframe(table, width="stretch", hide_index=True)
