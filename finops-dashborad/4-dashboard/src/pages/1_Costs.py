"""FinOps Dashboard — Cost Analysis Page."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS
from utils.currency import convert, fmt

st.set_page_config(page_title="Costs · FinOps", page_icon="💰", layout="wide")
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

    sub_filter = None
    subs_resp = get("/subscriptions")
    if subs_resp and subs_resp.get("data"):
        sub_map = {"All Subscriptions": None}
        for s in subs_resp["data"]:
            sub_map[s.get("name", s["id"])] = s["id"]
        selected = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]

    limit = st.selectbox("Top N Services", [10, 20, 30, 50], index=1)
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("💰 Cost Analysis")
st.caption(f"Last {days} days")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────────────
base_params = {"days": days}
if sub_filter:
    base_params["subscription_id"] = sub_filter

summary = get("/costs/summary",            base_params)
daily   = get("/costs/daily",              base_params)
by_svc  = get("/costs/by-service",         {**base_params, "limit": limit})
by_sub  = get("/costs/by-subscription",    {"days": days})
by_rg   = get("/costs/by-resource-group",  {**base_params, "limit": 15})

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
disp_currency = st.session_state.get("_currency", "USD")

if summary and summary.get("data"):
    d = summary["data"]
    src_cur = d.get("currency", "USD")
    total     = convert(d.get("total_cost", 0),      src_cur, disp_currency)
    prev      = convert(d.get("prev_period_cost", 0), src_cur, disp_currency)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        f"Total Spend ({disp_currency})",
        fmt(total, disp_currency),
        delta=f"{d['change_pct']:+.1f}% vs prev" if d.get("change_pct") is not None else None,
        delta_color="inverse",
    )
    c2.metric("Previous Period",  fmt(prev, disp_currency))
    c3.metric("Period Start",     d.get("period_start", "—"))
    c4.metric("Period End",       d.get("period_end",   "—"))

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Daily Trend", "By Service", "By Subscription", "By Resource Group"])

# ── Daily Trend ───────────────────────────────────────────────────────────────
with tab1:
    if daily and daily.get("data"):
        df = pd.DataFrame(daily["data"])
        df["date"] = pd.to_datetime(df["date"])
        src_cur = df["currency"].iloc[0] if "currency" in df else "USD"
        df["disp_cost"] = df["total_cost"].apply(lambda x: convert(x, src_cur, disp_currency))
        df["rolling_avg"] = df["disp_cost"].rolling(7, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["date"],
            y=df["disp_cost"],
            name="Daily Cost",
            marker_color=COLORS["blue"],
            opacity=0.75,
            hovertemplate=f"%{{x|%b %d}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["rolling_avg"],
            name="7-Day Avg",
            line=dict(color=COLORS["amber"], width=2),
            hovertemplate=f"%{{x|%b %d}}<br>Avg: {disp_currency} %{{y:,.2f}}<extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=420, xaxis_title=None, yaxis_title=f"Cost ({disp_currency})")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Daily Cost Data")
        display_df = df[["date", "disp_cost"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["disp_cost"] = display_df["disp_cost"].round(2)
        display_df.columns = ["Date", f"Cost ({disp_currency})"]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No daily cost data. Run a sync from the Home page.")

# ── By Service ────────────────────────────────────────────────────────────────
with tab2:
    if by_svc and by_svc.get("data"):
        df_svc = pd.DataFrame(by_svc["data"])
        src_cur2 = df_svc["currency"].iloc[0] if "currency" in df_svc else "USD"
        df_svc["disp_cost"] = df_svc["total_cost"].apply(lambda x: convert(x, src_cur2, disp_currency))
        total_cost = df_svc["disp_cost"].sum()
        df_svc["share_pct"] = (df_svc["disp_cost"] / total_cost * 100).round(1)

        col_chart, col_donut = st.columns([3, 2])
        with col_chart:
            fig = go.Figure(go.Bar(
                x=df_svc["disp_cost"],
                y=df_svc["service_name"],
                orientation="h",
                marker=dict(
                    color=df_svc["disp_cost"],
                    colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                    showscale=False,
                ),
                hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(
                height=max(350, len(df_svc) * 30),
                yaxis=dict(autorange="reversed"),
                xaxis_title=f"Cost ({disp_currency})",
                yaxis_title=None,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_donut:
            top10 = df_svc.head(10)
            fig2 = go.Figure(go.Pie(
                labels=top10["service_name"],
                values=top10["disp_cost"],
                hole=0.45,
                hovertemplate=f"%{{label}}<br><b>{disp_currency} %{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
            ))
            apply_plotly_theme(fig2)
            fig2.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Service Cost Breakdown")
        display_df = df_svc[["service_name", "disp_cost", "share_pct"]].copy()
        display_df["disp_cost"] = display_df["disp_cost"].round(2)
        display_df.columns = ["Service", f"Cost ({disp_currency})", "Share %"]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No service cost data. Run a sync from the Home page.")

# ── By Subscription ───────────────────────────────────────────────────────────
with tab3:
    if by_sub and by_sub.get("data"):
        df_sub = pd.DataFrame(by_sub["data"])
        src_cur3 = df_sub["currency"].iloc[0] if "currency" in df_sub else "USD"
        df_sub["disp_cost"] = df_sub["total_cost"].apply(lambda x: convert(x, src_cur3, disp_currency))

        # resolve subscription names
        subs_data = {}
        subs_resp2 = get("/subscriptions")
        if subs_resp2 and subs_resp2.get("data"):
            for s in subs_resp2["data"]:
                subs_data[s["id"]] = s.get("name", s["id"])
        df_sub["sub_name"] = df_sub["subscription_id"].apply(lambda x: subs_data.get(x, x))

        fig = px.pie(
            df_sub,
            values="disp_cost",
            names="sub_name",
            hole=0.4,
            color_discrete_sequence=[
                COLORS["blue"], COLORS["blue2"], COLORS["teal"],
                COLORS["purple"], COLORS["amber"],
            ],
        )
        apply_plotly_theme(fig)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

        display_df = df_sub[["sub_name", "disp_cost"]].copy()
        display_df["disp_cost"] = display_df["disp_cost"].round(2)
        display_df.columns = ["Subscription", f"Cost ({disp_currency})"]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No subscription cost data.")

# ── By Resource Group ─────────────────────────────────────────────────────────
with tab4:
    if by_rg and by_rg.get("data"):
        df_rg = pd.DataFrame(by_rg["data"])
        src_cur4 = df_rg["currency"].iloc[0] if "currency" in df_rg else "USD"
        df_rg["disp_cost"] = df_rg["total_cost"].apply(lambda x: convert(x, src_cur4, disp_currency))

        fig = go.Figure(go.Bar(
            x=df_rg["resource_group"],
            y=df_rg["disp_cost"],
            marker_color=COLORS["teal"],
            hovertemplate=f"%{{x}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(
            height=380,
            xaxis_title=None,
            yaxis_title=f"Cost ({disp_currency})",
            xaxis_tickangle=-35,
        )
        st.plotly_chart(fig, use_container_width=True)

        display_df = df_rg[["resource_group", "disp_cost"]].copy()
        display_df["disp_cost"] = display_df["disp_cost"].round(2)
        display_df.columns = ["Resource Group", f"Cost ({disp_currency})"]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No resource group cost data.")
