"""FinOps Dashboard — Home / Overview Page."""
import datetime as dt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get, post
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PLOTLY_CONFIG
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
# Service categorisation (used by Sankey)
# ─────────────────────────────────────────────────────────────────────────────
_CAT_KW = {
    "Compute":            ["virtual machine", "compute", "aks", "kubernetes", "container",
                           "function", "app service", "batch", "cloud service", "spring"],
    "Storage":            ["storage", "blob", "disk", "backup", "archive", "files",
                           "data lake", "recovery", "netapp", "site recovery"],
    "Network":            ["bandwidth", "vnet", "virtual network", "dns", "cdn", "vpn",
                           "gateway", "load balancer", "front door", "bastion",
                           "expressroute", "public ip", "firewall", "nat", "traffic manager", "ddos"],
    "Database":           ["sql", "mysql", "postgresql", "cosmos", "redis", "mariadb",
                           "synapse", "database", "data factory", "databricks"],
    "Monitor & Security": ["monitor", "log analytics", "application insights", "sentinel",
                           "defender", "security", "key vault"],
}


def _cat(name: str) -> str:
    s = name.lower()
    for cat, kws in _CAT_KW.items():
        if any(k in s for k in kws):
            return cat
    return "Other"


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    days = st.selectbox(
        "Period", [7, 14, 30, 60, 90], index=2,
        format_func=lambda d: f"Last {d} days",
    )
    disp_currency = st.session_state.get("_currency", "USD")
    budget_val    = float(st.session_state.get("_monthly_budget", 0.0))
    monthly_budget = st.number_input(
        f"Monthly Budget ({disp_currency})",
        min_value=0.0, value=budget_val, step=100.0,
        help="Monthly spending limit for the budget tracker",
    )
    st.session_state["_monthly_budget"] = monthly_budget

    if st.button("🔄 Sync All Data", use_container_width=True):
        with st.spinner("Syncing all data from Azure…"):
            resp = post("/sync/all", params={"days": days})
        st.success("Sync complete!") if resp else st.error("Sync failed — check API logs.")
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚡ FinOps Overview")
st.caption(f"Azure Cost Intelligence · Last {days} days · {disp_currency}")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────────────
summary   = get("/costs/summary",    {"days": days})
daily     = get("/costs/daily",      {"days": days})
by_svc    = get("/costs/by-service", {"days": days, "limit": 20})
adv_summ  = get("/advisor/summary")
adv_recs  = get("/advisor",          {"category": "Cost"})
tag_check = get("/resources",        {"limit": 500})

# ─────────────────────────────────────────────────────────────────────────────
# Derive totals
# ─────────────────────────────────────────────────────────────────────────────
total      = 0.0
prev       = 0.0
change_pct = None
avg_daily  = 0.0
src_cur    = "USD"

if summary and summary.get("data"):
    d         = summary["data"]
    src_cur   = d.get("currency", "USD")
    total     = convert(d.get("total_cost", 0),       src_cur, disp_currency)
    prev      = convert(d.get("prev_period_cost", 0), src_cur, disp_currency)
    change_pct = d.get("change_pct")
    avg_daily  = total / max(days, 1)

adv_by_impact: dict = {}   # impact → {count, savings}
total_adv_savings = 0.0
total_adv_count   = 0
if adv_summ and adv_summ.get("data"):
    for row in adv_summ["data"]:
        if row.get("category") == "Cost":
            imp  = row.get("impact", "Low")
            sav  = convert(row.get("total_savings", 0), "USD", disp_currency)
            cnt  = row.get("count", 0)
            adv_by_impact[imp] = {"savings": sav, "count": cnt}
            total_adv_savings += sav
            total_adv_count   += cnt

budget_pct = (total / monthly_budget * 100) if monthly_budget > 0 and total > 0 else 0

# ─────────────────────────────────────────────────────────────────────────────
# KPI row — 5 cards
# ─────────────────────────────────────────────────────────────────────────────
if total > 0:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        f"Total Spend ({disp_currency})", fmt(total, disp_currency),
        delta=f"{change_pct:+.1f}% vs prev" if change_pct is not None else None,
        delta_color="inverse",
    )
    k2.metric("Previous Period",      fmt(prev,          disp_currency))
    k3.metric("Avg Daily Spend",      fmt(avg_daily,     disp_currency))
    k4.metric(
        f"Savings Potential ({disp_currency})", fmt(total_adv_savings, disp_currency),
        help=f"{total_adv_count} open Azure Advisor Cost recommendations",
    )
    if monthly_budget > 0:
        status_icon = "🔴" if budget_pct >= 100 else "🟡" if budget_pct >= 75 else "🟢"
        k5.metric("Budget Used", f"{budget_pct:.1f}%",
                  delta=f"{status_icon} {'Over' if budget_pct >= 100 else f'{100-budget_pct:.0f}% left'}",
                  delta_color="inverse" if budget_pct >= 100 else "normal")
    else:
        k5.metric("Days in Period", f"{days}d")
else:
    st.info("No cost data. Use **Sync All Data** in the sidebar to pull from Azure.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Cost Summary  +  Savings Summary  (Azure portal style)
# ─────────────────────────────────────────────────────────────────────────────
col_cost_summ, col_sav_summ = st.columns(2)

with col_cost_summ:
    st.subheader("📊 Cost Summary")
    if total > 0:
        # Large billed cost
        esr = change_pct if change_pct is not None else 0.0
        esr_color = COLORS["red"] if esr > 0 else COLORS["green"]
        st.markdown(
            f"<div style='display:flex; align-items:flex-end; gap:24px; margin-bottom:12px;'>"
            f"<div>"
            f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase; letter-spacing:0.08em;'>"
            f"Billed Cost</div>"
            f"<div style='font-size:38px; font-weight:700; color:#f1f5f9; letter-spacing:-0.02em;'>"
            f"{fmt(total, disp_currency)}</div>"
            f"</div>"
            f"<div style='margin-bottom:6px;'>"
            f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase;'>Period Change</div>"
            f"<div style='font-size:22px; font-weight:700; color:{esr_color};'>"
            f"{esr:+.1f}%</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Horizontal bar breakdown
        rows = [
            ("Current Period",  total,             COLORS["blue"]),
            ("Previous Period", prev,              COLORS["blue2"]),
            ("Avg Daily × 30", avg_daily * 30,     COLORS["teal"]),
        ]
        max_val = max(r[1] for r in rows) or 1
        for label, val, color in rows:
            pct = val / max_val * 100
            st.markdown(
                f"<div style='margin-bottom:10px;'>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:3px;'>"
                f"<span style='color:#94a3b8; font-size:12px;'>{label}</span>"
                f"<span style='color:#e2e8f0; font-size:12px; font-weight:600;'>{fmt(val, disp_currency)}</span>"
                f"</div>"
                f"<div style='background:rgba(255,255,255,0.06); border-radius:4px; height:8px;'>"
                f"<div style='background:{color}; border-radius:4px; height:8px; width:{pct:.1f}%; "
                f"transition:width 0.4s ease;'></div></div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No cost data yet.")

with col_sav_summ:
    st.subheader("💰 Savings Summary")
    if total_adv_savings > 0:
        st.markdown(
            f"<div style='display:flex; align-items:flex-end; gap:24px; margin-bottom:12px;'>"
            f"<div>"
            f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase; letter-spacing:0.08em;'>"
            f"Total Savings Available</div>"
            f"<div style='font-size:38px; font-weight:700; color:{COLORS['green']}; letter-spacing:-0.02em;'>"
            f"{fmt(total_adv_savings, disp_currency)}</div>"
            f"</div>"
            f"<div style='margin-bottom:6px;'>"
            f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase;'>Recommendations</div>"
            f"<div style='font-size:22px; font-weight:700; color:#60a5fa;'>{total_adv_count}</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        impact_cfg = [
            ("High",   COLORS["red"],   "High Impact"),
            ("Medium", COLORS["amber"], "Medium Impact"),
            ("Low",    COLORS["green"], "Low Impact"),
        ]
        max_sav = max((adv_by_impact.get(i, {}).get("savings", 0) for i in ["High", "Medium", "Low"]), default=1) or 1
        for impact, color, label in impact_cfg:
            info = adv_by_impact.get(impact, {})
            sav  = info.get("savings", 0)
            cnt  = info.get("count", 0)
            pct  = sav / max_sav * 100 if max_sav > 0 else 0
            st.markdown(
                f"<div style='margin-bottom:10px;'>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:3px;'>"
                f"<span style='color:{color}; font-size:12px; font-weight:600;'>"
                f"<span style='display:inline-block; width:8px; height:8px; border-radius:50%; "
                f"background:{color}; margin-right:6px;'></span>{label}</span>"
                f"<span style='color:#e2e8f0; font-size:12px; font-weight:600;'>"
                f"{fmt(sav, disp_currency)} "
                f"<span style='color:#64748b; font-weight:400;'>({cnt} recs)</span></span>"
                f"</div>"
                f"<div style='background:rgba(255,255,255,0.06); border-radius:4px; height:8px;'>"
                f"<div style='background:{color}; border-radius:4px; height:8px; width:{pct:.1f}%; "
                f"transition:width 0.4s ease;'></div></div></div>",
                unsafe_allow_html=True,
            )
    elif total_adv_savings == 0 and total_adv_count > 0:
        st.markdown(
            f"<div style='text-align:center; padding:24px 0;'>"
            f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;'>"
            f"Open Recommendations</div>"
            f"<div style='font-size:52px; font-weight:700; color:{COLORS['amber']}; line-height:1;'>"
            f"{total_adv_count}</div>"
            f"<div style='color:#94a3b8; font-size:12px; margin-top:8px;'>"
            f"Savings amounts pending — check Advisor sync</div>"
            f"<div style='color:#60a5fa; font-size:12px; margin-top:4px;'>"
            f"→ See Advisor page for full details</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No Advisor savings data. Run a sync or check Advisor is enabled in Azure.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Budget Tracker
# ─────────────────────────────────────────────────────────────────────────────
if monthly_budget > 0 and total > 0:
    remaining = max(0.0, monthly_budget - total)
    status    = "🔴 Over Budget" if budget_pct >= 100 else "🟡 Approaching Limit" if budget_pct >= 75 else "🟢 On Track"

    st.subheader(f"{status} — Budget Tracker")
    st.progress(min(budget_pct / 100, 1.0))

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Spent",     fmt(total,          disp_currency))
    b2.metric("Budget",    fmt(monthly_budget, disp_currency))
    b3.metric("Remaining", fmt(remaining,      disp_currency))
    b4.metric("% Used",    f"{budget_pct:.1f}%",
              delta=f"{'Over' if budget_pct >= 100 else f'{100-budget_pct:.0f}% left'}",
              delta_color="inverse" if budget_pct >= 100 else "normal")
    st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Daily Trend  +  Forecast
# ─────────────────────────────────────────────────────────────────────────────
col_trend, col_forecast = st.columns([3, 1])
df_daily = pd.DataFrame()
anomaly_count = 0

with col_trend:
    st.subheader("📅 Daily Cost Trend")
    if daily and daily.get("data"):
        df_daily = pd.DataFrame(daily["data"])
        df_daily["date"] = pd.to_datetime(df_daily["date"])
        sc = df_daily["currency"].iloc[0] if "currency" in df_daily.columns else "USD"
        df_daily["disp_cost"] = df_daily["total_cost"].apply(lambda x: convert(x, sc, disp_currency))
        df_daily["rolling_avg"] = df_daily["disp_cost"].rolling(7, min_periods=1).mean()

        mean_c = df_daily["disp_cost"].mean()
        std_c  = df_daily["disp_cost"].std(ddof=0)
        thresh = mean_c + 2 * std_c
        df_daily["is_anomaly"] = df_daily["disp_cost"] > thresh
        anomaly_count = int(df_daily["is_anomaly"].sum())
        anomalies = df_daily[df_daily["is_anomaly"]]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_daily["date"], y=df_daily["disp_cost"],
            mode="lines+markers", name="Daily Cost",
            line=dict(color=COLORS["blue"], width=2.5),
            marker=dict(size=5, color=COLORS["blue"]),
            fill="tozeroy", fillcolor="rgba(0,120,212,0.07)",
            hovertemplate=f"%{{x|%b %d}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df_daily["date"], y=df_daily["rolling_avg"],
            mode="lines", name="7-Day Avg",
            line=dict(color=COLORS["amber"], width=1.5, dash="dot"),
            hovertemplate=f"%{{x|%b %d}}<br>Avg: {disp_currency} %{{y:,.2f}}<extra></extra>",
        ))
        if anomaly_count > 0:
            fig.add_trace(go.Scatter(
                x=anomalies["date"], y=anomalies["disp_cost"],
                mode="markers", name="⚠ Spike",
                marker=dict(color=COLORS["red"], size=12, symbol="circle",
                            line=dict(color="white", width=1.5)),
                hovertemplate=f"⚠ Spike: {disp_currency} %{{y:,.2f}}<extra></extra>",
            ))
        apply_plotly_theme(fig)
        fig.update_layout(
            height=320, xaxis_title=None,
            yaxis_title=f"Cost ({disp_currency})",
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        if anomaly_count > 0:
            st.warning(
                f"⚠ **{anomaly_count} cost spike(s)** — days exceeding "
                f"{disp_currency} {thresh:,.2f} (mean + 2σ). See Costs → Daily Trend for details."
            )
    else:
        st.info("No daily cost data. Use Sync All Data.")

with col_forecast:
    st.subheader("📈 Forecast")
    if len(df_daily) >= 5:
        today      = dt.date.today()
        yr, mo     = today.year, today.month
        next_mo    = dt.date(yr + (mo == 12), (mo % 12) + 1, 1)
        days_left  = (next_mo - today).days

        x_vals   = np.arange(len(df_daily))
        y_vals   = df_daily["disp_cost"].values
        coeffs   = np.polyfit(x_vals, y_vals, 1)
        future_y = np.maximum(0, np.poly1d(coeffs)(np.arange(len(df_daily), len(df_daily) + days_left)))
        proj_rem = float(future_y.sum())
        proj_tot = float(df_daily["disp_cost"].sum()) + proj_rem
        over = monthly_budget > 0 and proj_tot > monthly_budget

        st.metric("MTD Spend",            fmt(df_daily["disp_cost"].sum(), disp_currency))
        st.metric("Projected Remaining",  fmt(proj_rem, disp_currency))
        st.metric(
            "Projected Month Total", fmt(proj_tot, disp_currency),
            delta="⚠ Over budget" if over else "✓ Under budget" if monthly_budget > 0 else None,
            delta_color="inverse" if over else "normal",
        )
        st.caption(f"Linear trend · {days_left} days left")
    else:
        st.info("Need ≥ 5 days of data.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Cost Flow — Sankey: Total → Categories → Top Services
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🔀 Cost Flow — Total → Categories → Services")
st.caption("How your spend flows from total budget through service categories to individual services.")

if by_svc and by_svc.get("data"):
    df_svc = pd.DataFrame(by_svc["data"])
    sc2 = df_svc["currency"].iloc[0] if "currency" in df_svc.columns else "USD"
    df_svc["disp_cost"] = df_svc["total_cost"].apply(lambda x: convert(x, sc2, disp_currency))
    df_svc["category"]  = df_svc["service_name"].apply(_cat)

    # Build category totals
    cat_totals = df_svc.groupby("category")["disp_cost"].sum().sort_values(ascending=False)
    categories = cat_totals.index.tolist()

    # Top 8 services across all categories for the right-most nodes
    top_svcs = df_svc.nlargest(8, "disp_cost")

    # Sankey node list
    #  0          = "Total Spend"
    #  1..C       = categories
    #  C+1..end   = individual services
    node_labels = [f"Total\n{fmt(total, disp_currency)}"]
    cat_colors  = {
        "Compute":            "#3b82f6",
        "Storage":            "#8b5cf6",
        "Network":            "#06b6d4",
        "Database":           "#f59e0b",
        "Monitor & Security": "#10b981",
        "Other":              "#64748b",
    }
    node_colors = ["#0078D4"]
    for cat in categories:
        node_labels.append(cat)
        node_colors.append(cat_colors.get(cat, "#64748b"))
    for _, row in top_svcs.iterrows():
        svc_short = row["service_name"][:28]
        node_labels.append(svc_short)
        node_colors.append(_rgba(cat_colors.get(row["category"], "#64748b"), 0.73))

    cat_idx  = {cat: i + 1 for i, cat in enumerate(categories)}
    svc_rows = {row["service_name"]: len(categories) + 1 + j
                for j, (_, row) in enumerate(top_svcs.iterrows())}

    sources, targets, values, link_colors = [], [], [], []

    # Total → each category
    for cat in categories:
        sources.append(0)
        targets.append(cat_idx[cat])
        values.append(float(cat_totals[cat]))
        link_colors.append(_rgba(cat_colors.get(cat, "#64748b"), 0.33))

    # Category → individual top services
    for _, row in top_svcs.iterrows():
        cat = row["category"]
        sources.append(cat_idx[cat])
        targets.append(svc_rows[row["service_name"]])
        values.append(float(row["disp_cost"]))
        link_colors.append(_rgba(cat_colors.get(cat, "#64748b"), 0.27))

    fig_sankey = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20, thickness=22,
            label=node_labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate="%{source.label} → %{target.label}<br>"
                          f"<b>{disp_currency} %{{value:,.2f}}</b><extra></extra>",
        ),
    ))
    apply_plotly_theme(fig_sankey)
    fig_sankey.update_layout(
        height=420,
        font=dict(family="Inter", size=11, color="#cbd5e1"),
    )
    st.plotly_chart(fig_sankey, use_container_width=True, config=PLOTLY_CONFIG)
else:
    st.info("No service data for cost flow. Run a sync first.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Top Services  +  Distribution
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🏆 Top Services by Cost")
    if by_svc and by_svc.get("data") and "df_svc" in dir():
        df_top = df_svc.head(10).copy()
        df_top["share_pct"] = (df_top["disp_cost"] / df_top["disp_cost"].sum() * 100).round(1)

        fig2 = go.Figure(go.Bar(
            x=df_top["disp_cost"],
            y=df_top["service_name"],
            orientation="h",
            marker=dict(
                color=df_top["disp_cost"],
                colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                showscale=False,
            ),
            text=df_top["share_pct"].apply(lambda p: f"{p:.1f}%"),
            textposition="outside",
            hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b> (%{{text}})<extra></extra>",
        ))
        apply_plotly_theme(fig2)
        fig2.update_layout(
            height=320, showlegend=False,
            xaxis_title=f"Cost ({disp_currency})",
            yaxis=dict(autorange="reversed"), yaxis_title=None,
            margin=dict(r=60),
        )
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No service data.")

with col_right:
    st.subheader("🥧 Cost Distribution")
    if by_svc and by_svc.get("data") and "df_svc" in dir():
        top5      = df_svc.head(5)
        other_val = df_svc["disp_cost"].iloc[5:].sum()
        if other_val > 0:
            other_row = pd.DataFrame([{"service_name": "Other Services", "disp_cost": other_val}])
            pie_df = pd.concat([top5[["service_name", "disp_cost"]], other_row], ignore_index=True)
        else:
            pie_df = top5[["service_name", "disp_cost"]]

        fig_pie = go.Figure(go.Pie(
            labels=pie_df["service_name"],
            values=pie_df["disp_cost"],
            hole=0.45,
            hovertemplate=f"%{{label}}<br><b>{disp_currency} %{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
        ))
        apply_plotly_theme(fig_pie)
        fig_pie.update_layout(height=320, legend=dict(orientation="v", font=dict(size=10)))
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No data.")

# ─────────────────────────────────────────────────────────────────────────────
# Category Breakdown  (bar chart — matches the Sankey categories)
# ─────────────────────────────────────────────────────────────────────────────
if by_svc and by_svc.get("data") and "df_svc" in dir():
    st.divider()
    st.subheader("📦 Cost by Category")
    cat_df = df_svc.groupby("category")["disp_cost"].sum().reset_index()
    cat_df = cat_df.sort_values("disp_cost", ascending=False)
    cat_df["share_pct"] = (cat_df["disp_cost"] / cat_df["disp_cost"].sum() * 100).round(1)
    cat_df["color"] = cat_df["category"].map({
        "Compute": "#3b82f6", "Storage": "#8b5cf6", "Network": "#06b6d4",
        "Database": "#f59e0b", "Monitor & Security": "#10b981", "Other": "#64748b",
    })

    fig_cat = go.Figure(go.Bar(
        x=cat_df["category"],
        y=cat_df["disp_cost"],
        marker_color=cat_df["color"],
        text=cat_df["share_pct"].apply(lambda p: f"{p:.1f}%"),
        textposition="outside",
        hovertemplate=f"%{{x}}<br><b>{disp_currency} %{{y:,.2f}}</b> (%{{text}})<extra></extra>",
    ))
    apply_plotly_theme(fig_cat)
    fig_cat.update_layout(
        height=280, xaxis_title=None,
        yaxis_title=f"Cost ({disp_currency})",
        showlegend=False,
    )
    st.plotly_chart(fig_cat, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption(
        "**Compute** — VMs, AKS, Functions, App Service  ·  "
        "**Storage** — Storage Accounts, Blob, Managed Disks, Backup, Data Lake  ·  "
        "**Network** — Bandwidth, VNet, CDN, VPN Gateway, Load Balancer  ·  "
        "**Database** — SQL, PostgreSQL, Cosmos DB, Redis, Synapse  ·  "
        "**Monitor & Security** — Log Analytics, Defender, Key Vault, Sentinel"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Advisor Cost Opportunities
# ─────────────────────────────────────────────────────────────────────────────
if adv_by_impact:
    st.divider()
    st.subheader("💡 Azure Advisor Cost Opportunities")
    impact_order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_impacts = sorted(adv_by_impact.keys(), key=lambda x: impact_order.get(x, 3))
    cols = st.columns(min(len(sorted_impacts), 4))
    for i, impact in enumerate(sorted_impacts[:4]):
        with cols[i]:
            color = {"High": COLORS["red"], "Medium": COLORS["amber"],
                     "Low": COLORS["green"]}.get(impact, "#94a3b8")
            sav = adv_by_impact[impact]["savings"]
            cnt = adv_by_impact[impact]["count"]
            sav_line = (f"<div style='color:#60a5fa; font-size:15px; font-weight:600;'>"
                        f"Save {fmt(sav, disp_currency)}</div>") if sav > 0 else ""
            st.markdown(
                f"<div style='border:1px solid {color}44; border-radius:12px; "
                f"padding:18px 16px; background:{color}0d; text-align:center;'>"
                f"<div style='color:{color}; font-size:11px; font-weight:700; "
                f"text-transform:uppercase; letter-spacing:0.08em;'>{impact} Impact</div>"
                f"<div style='font-size:28px; font-weight:700; color:#f1f5f9; margin:6px 0;'>{cnt}</div>"
                f"<div style='color:#94a3b8; font-size:12px; margin-bottom:6px;'>Recommendations</div>"
                f"{sav_line}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Show the actual recommendations below the summary cards
    if adv_recs and adv_recs.get("data"):
        recs = adv_recs["data"]
        recs.sort(key=lambda r: impact_order.get(r.get("impact", "Low"), 3))
        label = f"📋 What are these {total_adv_count} recommendations? (click to expand)"
        with st.expander(label):
            _ic = {"High": COLORS["red"], "Medium": COLORS["amber"], "Low": COLORS["green"]}
            for rec in recs[:10]:
                impact  = rec.get("impact", "")
                color   = _ic.get(impact, "#94a3b8")
                desc    = rec.get("short_description", "No description")
                resource = rec.get("resource_name") or "N/A"
                sraw    = rec.get("potential_savings") or 0
                sav_str = fmt(convert(sraw, rec.get("currency", "USD"), disp_currency), disp_currency) if sraw else "—"
                st.markdown(
                    f"<div style='border-left:3px solid {color}; padding:8px 14px; margin-bottom:8px; "
                    f"background:rgba(255,255,255,0.02); border-radius:0 8px 8px 0;'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<span style='color:{color}; font-size:10px; font-weight:700; "
                    f"text-transform:uppercase; letter-spacing:0.06em;'>{impact} impact</span>"
                    f"<span style='color:{COLORS['green']}; font-size:12px; font-weight:600;'>"
                    f"{sav_str}/yr</span></div>"
                    f"<div style='color:#e2e8f0; font-size:13px; margin-top:4px;'>{desc}</div>"
                    f"<div style='color:#64748b; font-size:11px; margin-top:3px;'>"
                    f"Resource: {resource[:60]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            if len(recs) > 10:
                st.caption(f"Showing 10 of {len(recs)} — visit the Advisor page for the full list.")

# ─────────────────────────────────────────────────────────────────────────────
# Efficiency Scorecard  — tag compliance + waste grade
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("🎯 Efficiency Scorecard")

total_res = 0
tagged_res = 0
tag_pct = 0.0

if tag_check and tag_check.get("data"):
    df_tc = pd.DataFrame(tag_check["data"])
    total_res = len(df_tc)
    if "tags" in df_tc.columns and total_res > 0:
        tagged_res = int(df_tc["tags"].apply(lambda t: bool(t)).sum())
        tag_pct = tagged_res / total_res * 100

# Waste score: advisor recs (0-50 pts) + tag gap (0-30 pts)
adv_waste  = min(50, total_adv_count * 5)
tag_waste  = int((100 - tag_pct) * 0.30) if total_res > 0 else 0
waste_score = min(100, adv_waste + tag_waste)

if   waste_score < 20: waste_grade, g_color = "A", COLORS["green"]
elif waste_score < 40: waste_grade, g_color = "B", COLORS["teal"]
elif waste_score < 60: waste_grade, g_color = "C", COLORS["amber"]
elif waste_score < 80: waste_grade, g_color = "D", COLORS["red"]
else:                  waste_grade, g_color = "F", "#dc2626"

tc_color = COLORS["green"] if tag_pct >= 80 else COLORS["amber"] if tag_pct >= 50 else COLORS["red"]

ec1, ec2, ec3, ec4 = st.columns(4)
ec1.metric(
    "Tag Compliance",
    f"{tag_pct:.0f}%",
    f"{tagged_res}/{total_res} resources tagged" if total_res else "Run resource sync",
)
ec2.metric(
    "Advisor Open Recommendations",
    total_adv_count,
    f"{fmt(total_adv_savings, disp_currency)} potential" if total_adv_savings > 0 else "No savings data",
)
ec3.metric(
    "Untagged Resources",
    total_res - tagged_res,
    help="Resources with no tags — cannot be allocated to a team or workload",
)
ec4.markdown(
    f"<div style='background:rgba(255,255,255,0.02); border:1px solid {g_color}44; "
    f"border-radius:12px; padding:16px 20px;'>"
    f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase; "
    f"letter-spacing:0.08em; margin-bottom:4px;'>Efficiency Grade</div>"
    f"<div style='font-size:44px; font-weight:800; color:{g_color}; line-height:1;'>{waste_grade}</div>"
    f"<div style='color:#64748b; font-size:11px; margin-top:4px;'>Waste Score {waste_score}/100</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# Tag compliance bar
st.markdown(
    f"<div style='margin-top:14px;'>"
    f"<div style='display:flex; justify-content:space-between; margin-bottom:4px;'>"
    f"<span style='color:#94a3b8; font-size:12px;'>Tag Compliance</span>"
    f"<span style='color:{tc_color}; font-size:12px; font-weight:600;'>{tag_pct:.0f}% — "
    f"{'Good' if tag_pct >= 80 else 'Needs Attention' if tag_pct >= 50 else 'Critical'}</span>"
    f"</div>"
    f"<div style='background:rgba(255,255,255,0.06); border-radius:4px; height:10px;'>"
    f"<div style='background:{tc_color}; border-radius:4px; height:10px; "
    f"width:{tag_pct:.0f}%; transition:width 0.4s ease;'></div></div>"
    f"<div style='color:#64748b; font-size:11px; margin-top:4px;'>"
    f"Target: ≥ 80% — tags enable cost allocation to teams, environments, and workloads</div>"
    f"</div>",
    unsafe_allow_html=True,
)
