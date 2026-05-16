"""FinOps Dashboard — Home / Overview Page."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get, post
from utils.theme import apply_theme, apply_plotly_theme, COLORS
from utils.currency import convert, fmt

st.set_page_config(
    page_title="FinOps Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    days = st.selectbox(
        "Period",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda d: f"Last {d} days",
    )
    if st.button("🔄 Sync All Data", use_container_width=True):
        with st.spinner("Syncing all data from Azure…"):
            resp = post("/sync/all", params={"days": days})
        if resp:
            st.success("Sync complete!")
        else:
            st.error("Sync failed — check Platform API connection.")
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚡ FinOps Overview")
st.caption(f"Azure Cost Intelligence · Last {days} days")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch data (parallel requests handled by individual calls)
# ─────────────────────────────────────────────────────────────────────────────
summary    = get("/costs/summary",    {"days": days})
daily      = get("/costs/daily",      {"days": days})
by_svc     = get("/costs/by-service", {"days": days, "limit": 5})
adv_summ   = get("/advisor/summary")

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
disp_currency = st.session_state.get("_currency", "USD")

if summary and summary.get("data"):
    d = summary["data"]
    src_currency = d.get("currency", "USD")
    total      = convert(d.get("total_cost", 0),      src_currency, disp_currency)
    prev_total = convert(d.get("prev_period_cost", 0), src_currency, disp_currency)
    change_pct = d.get("change_pct")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            f"Total Spend ({disp_currency})",
            fmt(total, disp_currency),
            delta=f"{change_pct:+.1f}% vs prev period" if change_pct is not None else None,
            delta_color="inverse",
        )
    with c2:
        st.metric("Previous Period", fmt(prev_total, disp_currency))
    with c3:
        avg_daily = total / max(days, 1)
        st.metric("Avg Daily Spend", fmt(avg_daily, disp_currency))
    with c4:
        total_advisor_count   = 0
        total_advisor_savings = 0.0
        if adv_summ and adv_summ.get("data"):
            for row in adv_summ["data"]:
                if row.get("category") == "Cost":
                    total_advisor_count  += row.get("count", 0)
                    # Advisor savings are stored in USD by Azure
                    total_advisor_savings += convert(
                        row.get("total_savings", 0), "USD", disp_currency
                    )
        st.metric(
            f"Savings Potential ({disp_currency})",
            fmt(total_advisor_savings, disp_currency),
            help=f"{total_advisor_count} open Azure Advisor Cost recommendations",
        )
else:
    st.info("No cost data found. Use **Sync All Data** in the sidebar to pull data from Azure.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Charts: daily trend + top services
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Daily Cost Trend")
    if daily and daily.get("data"):
        df = pd.DataFrame(daily["data"])
        df["date"] = pd.to_datetime(df["date"])
        src_cur = df.get("currency", pd.Series(["USD"])).iloc[0] if "currency" in df else "USD"
        df["disp_cost"] = df["total_cost"].apply(lambda x: convert(x, src_cur, disp_currency))
        df["rolling_avg"] = df["disp_cost"].rolling(7, min_periods=1).mean()
        sym = disp_currency

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["disp_cost"],
            mode="lines+markers",
            name="Daily Cost",
            line=dict(color=COLORS["blue"], width=2.5),
            marker=dict(size=5, color=COLORS["blue"]),
            fill="tozeroy",
            fillcolor="rgba(0,120,212,0.07)",
            hovertemplate=f"%{{x|%b %d}}<br><b>{sym} %{{y:,.2f}}</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["rolling_avg"],
            mode="lines",
            name="7-Day Avg",
            line=dict(color=COLORS["amber"], width=1.5, dash="dot"),
            hovertemplate=f"%{{x|%b %d}}<br>Avg: {sym} %{{y:,.2f}}<extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(
            height=300,
            showlegend=True,
            xaxis_title=None,
            yaxis_title=f"Cost ({disp_currency})",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No daily cost data yet.")

with col_right:
    st.subheader("Top 5 Services")
    if by_svc and by_svc.get("data"):
        df_svc = pd.DataFrame(by_svc["data"])
        src_cur2 = df_svc.get("currency", pd.Series(["USD"])).iloc[0] if "currency" in df_svc else "USD"
        df_svc["disp_cost"] = df_svc["total_cost"].apply(lambda x: convert(x, src_cur2, disp_currency))
        sym = disp_currency
        fig2 = go.Figure(go.Bar(
            x=df_svc["disp_cost"],
            y=df_svc["service_name"],
            orientation="h",
            marker_color=COLORS["blue"],
            hovertemplate=f"%{{y}}<br><b>{sym} %{{x:,.2f}}</b><extra></extra>",
        ))
        apply_plotly_theme(fig2)
        fig2.update_layout(
            height=300,
            showlegend=False,
            xaxis_title=f"Cost ({disp_currency})",
            yaxis_title=None,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No service cost data yet.")

# ─────────────────────────────────────────────────────────────────────────────
# Advisor recommendations summary
# ─────────────────────────────────────────────────────────────────────────────
if adv_summ and adv_summ.get("data"):
    cost_rows = [r for r in adv_summ["data"] if r.get("category") == "Cost"]
    if cost_rows:
        st.divider()
        st.subheader("Azure Advisor Cost Opportunities")
        impact_order = {"High": 0, "Medium": 1, "Low": 2}
        cost_rows.sort(key=lambda r: impact_order.get(r.get("impact", "Low"), 3))
        cols = st.columns(min(len(cost_rows), 4))
        for i, row in enumerate(cost_rows[:4]):
            with cols[i]:
                impact = row.get("impact", "")
                color  = {
                    "High":   COLORS["red"],
                    "Medium": COLORS["amber"],
                    "Low":    COLORS["green"],
                }.get(impact, "#94a3b8")
                st.markdown(
                    f"<div style='border:1px solid {color}44; border-radius:12px; "
                    f"padding:18px 16px; background:{color}0d; text-align:center;'>"
                    f"<div style='color:{color}; font-size:11px; font-weight:700; "
                    f"text-transform:uppercase; letter-spacing:0.08em;'>{impact} Impact</div>"
                    f"<div style='font-size:28px; font-weight:700; color:#f1f5f9; margin:6px 0;'>"
                    f"{row.get('count', 0)}</div>"
                    f"<div style='color:#94a3b8; font-size:12px; margin-bottom:6px;'>Recommendations</div>"
                    f"<div style='color:#60a5fa; font-size:15px; font-weight:600;'>"
                    f"Save ${row.get('total_savings', 0):,.0f}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
