"""FinOps Dashboard — OpenCost: World-Class Kubernetes Cost Intelligence.

Six-tab layout:
  🏠 Executive  |  📊 Cost Allocation  |  🖥️ Assets
  💡 Savings    |  ☁️  Cloud Costs      |  📋 Reports

Features:
  Statistical anomaly detection on cost trends
  Linear-regression cost forecasting (next 7 days)
  Period-over-period comparison (current vs previous window)
  Namespace × day cost heatmap
  Efficiency grading A–F per workload / namespace
  Cluster health score (0–100) with component breakdown
  Savings ROI timeline (all sources aggregated)
  Chargeback report by Kubernetes label
  Budget vs Actual tracker (session-persistent)
  Carbon footprint estimation
  Multi-currency display (12 currencies)
  Full CSV / Excel / JSON export on every table
"""
import io
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.currency import convert, fmt as cfmt, currency_selector, CURRENCY_SYMBOLS
from utils.opencost_api import (
    abandoned_workloads,
    allocation,
    cloud_costs,
    cloud_costs_enabled,
    cluster_sizing,
    custom_cost_total,
    custom_cost_timeseries,
    flatten_allocation,
    flatten_pv_assets,
    is_online,
    node_assets,
    pv_assets,
    request_sizing,
    unclaimed_volumes,
    underutilized_nodes,
)
from utils.theme import COLORS, PLOTLY_CONFIG, apply_plotly_theme, apply_theme

# ─────────────────────────────────────────────────────────────────────────────
# Page bootstrap
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="OpenCost · FinOps", page_icon="☸️", layout="wide")
require_auth()
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = [
    "#5470C6", "#91CC75", "#FAC858", "#EE6666", "#73C0DE",
    "#3BA272", "#FC8452", "#9A60B4", "#EA7CCC", "#48CAE4",
    "#0077B6", "#F4A261",
]
_ANOM_CLR     = "#EF4444"
_FCST_CLR     = "#A78BFA"
_IDLE_CLR     = "#475569"

_GRADE_CLR = {
    "A+": "#22C55E", "A": "#4ADE80",
    "B":  "#86EFAC",
    "C":  "#FBBF24",
    "D":  "#F97316",
    "F":  "#EF4444",
}

_WINDOW_OPTS = {
    "1d":        "Today",
    "7d":        "Last 7 days",
    "30d":       "Last 30 days",
    "lastweek":  "Last week",
    "lastmonth": "Last month",
}
_DOUBLE_WIN = {
    "1d": "2d", "7d": "14d", "30d": "60d",
    "lastweek": "14d", "lastmonth": "60d",
}
_WIN_DAYS = {"1d": 1, "7d": 7, "30d": 30, "lastweek": 7, "lastmonth": 30}

_AGG_OPTS = ["namespace", "deployment", "pod", "controller", "service", "container"]
_LABEL_OPTS = [
    "team", "environment", "env", "app", "app.kubernetes.io/name",
    "app.kubernetes.io/part-of", "owner", "cost-center", "project",
    "service", "tier", "component",
]

# Carbon: rough estimate — $1 cloud compute ≈ 2 kWh, global avg 0.233 kgCO₂/kWh
_CARBON_FACTOR = 2 * 0.233

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
if "oc_budgets" not in st.session_state:
    st.session_state["oc_budgets"] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _grade(eff: float) -> tuple[str, str]:
    """(letter, hex_color) for efficiency %."""
    if eff >= 85: return "A",  _GRADE_CLR["A"]
    if eff >= 70: return "B",  _GRADE_CLR["B"]
    if eff >= 50: return "C",  _GRADE_CLR["C"]
    if eff >= 30: return "D",  _GRADE_CLR["D"]
    return "F", _GRADE_CLR["F"]


def _health_score(
    avg_eff: float,
    idle_pct: float,
    sav_ratio: float,
    anom_count: int,
) -> tuple[float, str, str]:
    """(score 0-100, grade letter, hex_color)."""
    eff_s  = min(avg_eff / 80, 1.0)           * 100
    idle_s = max(0.0, (20 - idle_pct) / 20)   * 100
    sav_s  = max(0.0, (0.25 - sav_ratio) / 0.25) * 100
    anom_s = max(0.0, (4 - anom_count) / 4)   * 100
    score  = min(100.0, max(0.0,
        eff_s * 0.35 + idle_s * 0.25 + sav_s * 0.25 + anom_s * 0.15
    ))
    if score >= 90: return score, "A+", _GRADE_CLR["A+"]
    if score >= 80: return score, "A",  _GRADE_CLR["A"]
    if score >= 70: return score, "B",  _GRADE_CLR["B"]
    if score >= 60: return score, "C",  _GRADE_CLR["C"]
    if score >= 40: return score, "D",  _GRADE_CLR["D"]
    return score, "F", _GRADE_CLR["F"]


def _detect_anomalies(values: pd.Series, z: float = 2.0) -> pd.Series:
    """Boolean mask: True where |value - mean| > z * std."""
    if len(values) < 3:
        return pd.Series([False] * len(values), index=values.index)
    mu, sigma = values.mean(), values.std()
    if sigma == 0:
        return pd.Series([False] * len(values), index=values.index)
    return (values - mu).abs() > z * sigma


def _forecast(
    dates: list[str],
    vals: list[float],
    n: int = 7,
) -> tuple[list[str], list[float]]:
    """Linear-regression forecast n days ahead. Returns (future_dates, predicted)."""
    if len(vals) < 2:
        return [], []
    x = np.arange(len(vals), dtype=float)
    y = np.array(vals, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fx = np.arange(len(vals), len(vals) + n, dtype=float)
    fy = np.maximum(0, slope * fx + intercept).tolist()
    if dates:
        last = pd.Timestamp(dates[-1])
        fdates = [(last + pd.Timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(n)]
    else:
        fdates = [f"+{i + 1}d" for i in range(n)]
    return fdates, fy


def _c(usd: float) -> float:
    """USD → selected display currency."""
    return convert(usd, "USD", st.session_state.get("oc_currency", "USD"))


def _f(usd: float, dec: int = 2) -> str:
    """Format USD amount in selected display currency."""
    cur = st.session_state.get("oc_currency", "USD")
    sym = CURRENCY_SYMBOLS.get(cur, cur + " ")
    val = _c(usd)
    return f"{sym}{val:,.0f}" if cur == "JPY" else f"{sym}{val:,.{dec}f}"


def _excel_bytes(df: pd.DataFrame, sheet: str = "Data") -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet)
    return buf.getvalue()


def _progress_bar_html(pct: float, color: str) -> str:
    pct = min(100, max(0, pct))
    return (
        f'<div style="background:#1e293b;border-radius:4px;height:8px;margin:4px 0">'
        f'<div style="background:{color};width:{pct:.1f}%;height:8px;border-radius:4px"></div>'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    _online = is_online()
    if _online:
        st.success("OpenCost ✓ Online")
    else:
        st.error("OpenCost · Connecting…")
    st.markdown("---")
    currency_selector(key="oc_currency")
    st.caption("FinOps Platform · OpenCost")

# Currency helpers — resolved once per render after sidebar sets session state
_cur_code = st.session_state.get("oc_currency", "USD")
_sym      = CURRENCY_SYMBOLS.get(_cur_code, _cur_code + " ")
_rate     = _c(1.0)   # 1 USD → selected currency multiplier

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0.15rem'>☸️ OpenCost — Kubernetes Cost Intelligence</h2>"
    "<p style='color:#64748B;font-size:0.85rem;margin-top:0'>"
    "Real-time K8s cost monitoring · "
    "<a href='https://opencost.io' target='_blank' style='color:#5470C6'>opencost.io</a>"
    "</p>",
    unsafe_allow_html=True,
)
if not _online:
    st.error("OpenCost is unreachable. Run: `kubectl get pods -n opencost`")

# ─────────────────────────────────────────────────────────────────────────────
# Inline controls
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
with c1:
    window = st.selectbox(
        "Window", list(_WINDOW_OPTS.keys()), index=1,
        format_func=lambda w: _WINDOW_OPTS.get(w, w),
        label_visibility="collapsed", help="Cost window for all views",
    )
with c2:
    aggregate = st.selectbox(
        "Aggregate", _AGG_OPTS, index=0,
        label_visibility="collapsed", help="Group by dimension",
    )
with c3:
    label_key = st.selectbox(
        "Chargeback label", _LABEL_OPTS, index=0,
        label_visibility="collapsed", help="Kubernetes label for chargeback",
    )
    _custom = st.text_input(
        "Custom label", placeholder="e.g. cost-center",
        label_visibility="collapsed", key="oc_custom_lbl",
    )
    if _custom.strip():
        label_key = _custom.strip()
with c4:
    show_idle = st.toggle("Show idle", value=False, help="Include __idle__ allocations")
with c5:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻ Refresh", use_container_width=True, help="Clear cache and reload"):
        st.cache_data.clear()

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Data fetch
# ─────────────────────────────────────────────────────────────────────────────
_prev_win = _DOUBLE_WIN.get(window, "14d")
_win_days = _WIN_DAYS.get(window, 7)

with st.spinner("Loading cost data…"):
    ns_raw        = allocation(window=window, aggregate="namespace",             accumulate=True)
    agg_raw       = allocation(window=window, aggregate=aggregate,               accumulate=True)
    lbl_raw       = allocation(window=window, aggregate=f"label:{label_key}",    accumulate=True)
    trend_raw     = allocation(window=window, aggregate="namespace",             accumulate=False, step="1d")
    ext_raw       = allocation(window=_prev_win, aggregate="namespace",          accumulate=False, step="1d")
    agg_trend_raw = allocation(window=window, aggregate=aggregate,               accumulate=False, step="1d")
    nd_raw        = node_assets(window=window)
    pv_raw        = pv_assets(window=window)
    req_recs      = request_sizing()
    clus_recs     = cluster_sizing()
    aband_recs    = abandoned_workloads()
    unclaimed_v   = unclaimed_volumes()
    underutil_n   = underutilized_nodes()
    _cc_on        = cloud_costs_enabled()
    cc_svc_raw    = cloud_costs(window=window, aggregate="service",  accumulate="day") if _cc_on else []
    cc_cat_raw    = cloud_costs(window=window, aggregate="category", accumulate="all") if _cc_on else []
    cc_trend_raw  = cloud_costs(window=window, aggregate="provider", accumulate="day") if _cc_on else []
    cust_raw      = custom_cost_total(window=window)
    cust_ts_raw   = custom_cost_timeseries(window=window)

# ─────────────────────────────────────────────────────────────────────────────
# Build DataFrames
# ─────────────────────────────────────────────────────────────────────────────
def _to_df(raw):
    rows = flatten_allocation(raw)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

df_ns    = _to_df(ns_raw)
df_agg   = _to_df(agg_raw)
df_lbl   = _to_df(lbl_raw)
df_trend = _to_df(trend_raw)
df_ext   = _to_df(ext_raw)

# Node assets
nd_rows = [
    {
        "name":       n,
        "type":       p.get("nodeType", ""),
        "region":     p.get("region", ""),
        "provider":   (p.get("providerID", "") or "").split(":")[0] or "azure",
        "cpu_cores":  p.get("cpuCores") or 0,
        "ram_gb":     round((p.get("ramBytes") or 0) / (1024 ** 3), 1),
        "cpu_cost":   p.get("cpuCost",   0.0) or 0.0,
        "ram_cost":   p.get("ramCost",   0.0) or 0.0,
        "total_cost": p.get("totalCost", 0.0) or 0.0,
    }
    for bucket in (nd_raw or []) if isinstance(bucket, dict)
    for n, p in bucket.items() if isinstance(p, dict)
]
df_nd = pd.DataFrame(nd_rows) if nd_rows else pd.DataFrame()

pv_rows = flatten_pv_assets(pv_raw)
df_pv   = pd.DataFrame(pv_rows) if pv_rows else pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# Derived metrics
# ─────────────────────────────────────────────────────────────────────────────
df_ns_act  = df_ns[df_ns["name"] != "__idle__"].copy()  if not df_ns.empty  else pd.DataFrame()
df_agg_act = df_agg[df_agg["name"] != "__idle__"].copy() if not df_agg.empty else pd.DataFrame()

total_k8s  = df_ns["total_cost"].sum()    if not df_ns.empty else 0.0
idle_cost  = (df_ns[df_ns["name"] == "__idle__"]["total_cost"].sum()
              if not df_ns.empty else 0.0)
idle_pct   = (idle_cost / total_k8s * 100) if total_k8s > 0 else 0.0
avg_eff    = df_ns_act["efficiency"].mean()  if not df_ns_act.empty else 0.0
total_cpu  = df_ns["cpu_cost"].sum()   if not df_ns.empty else 0.0
total_ram  = df_ns["ram_cost"].sum()   if not df_ns.empty else 0.0
total_pv_c = df_ns["pv_cost"].sum()    if not df_ns.empty else 0.0
total_net  = df_ns["network_cost"].sum() if not df_ns.empty else 0.0
total_gpu  = df_ns["gpu_cost"].sum()   if not df_ns.empty else 0.0
nd_total   = df_nd["total_cost"].sum() if not df_nd.empty else 0.0
pv_total   = df_pv["total_cost"].sum() if not df_pv.empty else 0.0

cost_per_hr = (total_k8s / _win_days / 24) if _win_days > 0 else 0.0

# Unit costs
cpu_cores_tot = df_nd["cpu_cores"].sum() if not df_nd.empty else 0
ram_gb_tot    = df_nd["ram_gb"].sum()    if not df_nd.empty else 0
cpu_hr_rate   = (total_cpu / cpu_cores_tot / _win_days / 24) if (cpu_cores_tot > 0 and _win_days > 0) else 0.0
ram_hr_rate   = (total_ram / ram_gb_tot    / _win_days / 24) if (ram_gb_tot    > 0 and _win_days > 0) else 0.0

# Savings potential
def _sum_savings(recs, key1="monthlyCPUSavings", key2="monthlyRAMSavings"):
    return sum((r.get(key1, 0) or 0) + (r.get(key2, 0) or 0)
               for r in (recs or []) if isinstance(r, dict))

sav_rs      = _sum_savings(req_recs)
sav_clus    = (clus_recs.get("monthlySavings", 0.0) or 0.0) if isinstance(clus_recs, dict) else 0.0
sav_uncl    = sum((r.get("monthlyCost",    0) or 0) for r in (unclaimed_v or []) if isinstance(r, dict))
sav_aband   = sum((r.get("monthlyCost",    0) or 0) for r in (aband_recs  or []) if isinstance(r, dict))
sav_under   = sum((r.get("monthlySavings", 0) or 0) for r in (underutil_n or []) if isinstance(r, dict))
sav_total   = sav_rs + sav_clus + sav_uncl + sav_aband + sav_under
monthly_est = (total_k8s / _win_days * 30) if _win_days > 0 and total_k8s > 0 else max(total_k8s, 1)
sav_ratio   = sav_total / monthly_est

# Daily totals + anomaly detection
df_daily = pd.DataFrame()
anom_dates: list[str] = []
if not df_trend.empty and "start" in df_trend.columns:
    df_daily = (
        df_trend[df_trend["name"] != "__idle__"]
        .groupby("start", as_index=False)["total_cost"].sum()
        .sort_values("start")
    )
    if len(df_daily) >= 3:
        mask = _detect_anomalies(df_daily["total_cost"])
        df_daily["is_anomaly"] = mask
        anom_dates = df_daily.loc[mask, "start"].tolist()

anom_count = len(anom_dates)

# Forecast
fcst_dates: list[str] = []
fcst_vals:  list[float] = []
if len(df_daily) >= 3:
    fcst_dates, fcst_vals = _forecast(
        df_daily["start"].tolist(),
        df_daily["total_cost"].tolist(),
        n=min(7, _win_days),
    )

# Period comparison (split extended window into halves)
df_prev = pd.DataFrame()
df_curr = pd.DataFrame()
if not df_ext.empty and "start" in df_ext.columns:
    all_dates = sorted(df_ext["start"].unique())
    mid = len(all_dates) // 2
    df_prev = (
        df_ext[df_ext["start"].isin(all_dates[:mid])]
        .groupby("name", as_index=False)["total_cost"].sum()
        .rename(columns={"total_cost": "prev_cost"})
    )
    df_curr = (
        df_ext[df_ext["start"].isin(all_dates[mid:])]
        .groupby("name", as_index=False)["total_cost"].sum()
        .rename(columns={"total_cost": "curr_cost"})
    )

# Health score
h_score, h_grade, h_color = _health_score(avg_eff, idle_pct, sav_ratio, anom_count)

# Carbon
carbon_kg = total_k8s * _CARBON_FACTOR

# ─────────────────────────────────────────────────────────────────────────────
# KPI strip (9 metrics)
# ─────────────────────────────────────────────────────────────────────────────
k = st.columns(9)
k[0].metric("Total Spend",   _f(total_k8s))
k[1].metric("Rate",          _f(cost_per_hr, 4) + "/hr")
k[2].metric("CPU",           _f(total_cpu))
k[3].metric("Memory",        _f(total_ram))
k[4].metric("PV Storage",    _f(total_pv_c))
k[5].metric("Network",       _f(total_net))
k[6].metric("Efficiency",    f"{avg_eff:.1f}%")
k[7].metric("Idle",          _f(idle_cost), f"{idle_pct:.1f}%", delta_color="inverse")
k[8].metric("Health",        h_grade, f"{h_score:.0f}/100",
            delta_color="normal" if h_score >= 70 else "inverse")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Main tab bar
# ─────────────────────────────────────────────────────────────────────────────
(
    tab_exec, tab_alloc, tab_assets,
    tab_savings, tab_cloud, tab_reports,
) = st.tabs([
    "🏠 Executive",
    "📊 Cost Allocation",
    "🖥️ Assets",
    "💡 Savings",
    "☁️ Cloud Costs",
    "📋 Reports",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EXECUTIVE
# ══════════════════════════════════════════════════════════════════════════════
with tab_exec:

    _grade_desc = {
        "A+": "Excellent — cluster is highly optimised",
        "A":  "Very Good — minor improvements available",
        "B":  "Good — some savings opportunities exist",
        "C":  "Fair — significant cost waste detected",
        "D":  "Poor — urgent action recommended",
        "F":  "Critical — major cost waste in progress",
    }

    col_badge, col_wins = st.columns([1, 2])

    # ── Health badge ──────────────────────────────────────────────────────────
    with col_badge:
        st.markdown(
            f"""<div style="
                background:linear-gradient(135deg,#1e293b,#0f172a);
                border:2px solid {h_color};border-radius:16px;
                padding:28px 20px;text-align:center;
                box-shadow:0 0 28px {h_color}44;margin-bottom:12px">
                <div style="font-size:76px;font-weight:900;color:{h_color};line-height:1">{h_grade}</div>
                <div style="font-size:22px;font-weight:600;color:#e2e8f0;margin-top:8px">{h_score:.0f} / 100</div>
                <div style="font-size:12px;color:#94a3b8;margin-top:4px">Cluster Health Score</div>
                <div style="font-size:11px;color:{h_color};margin-top:10px">{_grade_desc.get(h_grade,'')}</div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Score component bars
        st.markdown("**Score Components**")
        _eff_s  = min(avg_eff / 80, 1.0)             * 100
        _idle_s = max(0.0, (20 - idle_pct) / 20)     * 100
        _sav_s  = max(0.0, (0.25 - sav_ratio) / 0.25) * 100
        _anom_s = max(0.0, (4 - anom_count) / 4)     * 100
        for lbl, score in [
            ("Efficiency",        _eff_s),
            ("Idle Control",      _idle_s),
            ("Cost Optimisation", _sav_s),
            ("Stability",         _anom_s),
        ]:
            _c2 = "#22c55e" if score >= 80 else "#fbbf24" if score >= 50 else "#ef4444"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;margin:3px 0">'
                f'<span style="color:#94a3b8;font-size:12px">{lbl}</span>'
                f'<span style="color:{_c2};font-size:12px;font-weight:600">{score:.0f}%</span>'
                f'</div>'
                + _progress_bar_html(score, _c2),
                unsafe_allow_html=True,
            )

        if anom_count:
            st.error(f"⚠️ {anom_count} cost spike(s) in the {_WINDOW_OPTS.get(window)} window")

    # ── Quick wins ────────────────────────────────────────────────────────────
    with col_wins:
        st.markdown("**Top Cost Drivers**")
        if not df_ns_act.empty:
            top5 = df_ns_act.nlargest(5, "total_cost").copy()
            top5["pct"] = (top5["total_cost"] / max(total_k8s, 1) * 100).round(1)
            fig_top = go.Figure(go.Bar(
                x=top5["total_cost"],
                y=top5["name"],
                orientation="h",
                marker=dict(
                    color=top5["total_cost"],
                    colorscale=[[0, "#1e3a5f"], [1, PALETTE[0]]],
                    showscale=False,
                ),
                text=[f"{_f(v)}  ({p:.1f}%)" for v, p in zip(top5["total_cost"], top5["pct"])],
                textposition="outside",
                hovertemplate="%{y}<br><b>%{text}</b><extra></extra>",
            ))
            apply_plotly_theme(fig_top)
            fig_top.update_layout(
                height=210, margin=dict(l=0, r=0, t=0, b=0),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(showticklabels=False), showlegend=False,
            )
            st.plotly_chart(fig_top, use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown("**Top Savings Opportunities**")
        wins = []
        if req_recs:
            best = max(
                (r for r in req_recs if isinstance(r, dict)),
                key=lambda r: (r.get("monthlyCPUSavings", 0) or 0) + (r.get("monthlyRAMSavings", 0) or 0),
                default=None,
            )
            if best:
                s = (best.get("monthlyCPUSavings", 0) or 0) + (best.get("monthlyRAMSavings", 0) or 0)
                wins.append(("🔧", "Rightsize container", best.get("controllerName", ""), s))
        if unclaimed_v:
            wins.append(("💾", "Delete unclaimed PVs", f"{len(unclaimed_v)} volumes", sav_uncl))
        if aband_recs:
            wins.append(("🚫", "Remove abandoned workloads", f"{len(aband_recs)} workloads", sav_aband))
        if underutil_n:
            wins.append(("📉", "Downsize underutilised nodes", f"{len(underutil_n)} nodes", sav_under))
        if idle_cost > 0.01:
            wins.append(("💤", "Reduce idle allocation", f"{idle_pct:.1f}% idle", idle_cost))
        wins.sort(key=lambda x: x[3], reverse=True)

        for icon, action, detail, saving in wins[:5]:
            _wc = "#22c55e" if saving > 100 else "#fbbf24" if saving > 10 else "#64748b"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
                f'background:#1e293b;border-radius:8px;margin-bottom:6px;border-left:3px solid {_wc}">'
                f'<span style="font-size:18px">{icon}</span>'
                f'<div style="flex:1">'
                f'<div style="color:#e2e8f0;font-size:13px;font-weight:500">{action}</div>'
                f'<div style="color:#64748b;font-size:11px">{detail}</div>'
                f'</div>'
                f'<div style="color:{_wc};font-size:13px;font-weight:600">{_f(saving)}/mo</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if not wins:
            st.success("No major savings opportunities — cluster is well optimised!")

    st.divider()

    # ── Efficiency distribution + period comparison ───────────────────────────
    col_ef, col_per = st.columns(2)

    with col_ef:
        st.markdown("**Efficiency Distribution by Namespace**")
        if not df_ns_act.empty:
            gcounts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            for eff in df_ns_act["efficiency"]:
                gcounts[_grade(eff)[0]] += 1
            gdata = {k: v for k, v in gcounts.items() if v > 0}
            if gdata:
                fig_ef = go.Figure(go.Pie(
                    labels=list(gdata.keys()),
                    values=list(gdata.values()),
                    hole=0.6,
                    marker=dict(colors=[_GRADE_CLR.get(g, "#64748b") for g in gdata]),
                    textinfo="label+value",
                    hovertemplate="%{label}: %{value} namespaces (%{percent})<extra></extra>",
                ))
                apply_plotly_theme(fig_ef)
                _a_count = gcounts.get("A", 0)
                fig_ef.update_layout(
                    height=260, margin=dict(l=0, r=0, t=0, b=0),
                    annotations=[dict(
                        text=f"{_a_count} A-grade",
                        x=0.5, y=0.5, font_size=13, font_color="#4ade80", showarrow=False,
                    )],
                    legend=dict(orientation="h", yanchor="bottom", y=-0.12),
                )
                st.plotly_chart(fig_ef, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No allocation data available.")

    with col_per:
        st.markdown(f"**Period Comparison** — current vs previous {_WINDOW_OPTS.get(window)}")
        if not df_prev.empty and not df_curr.empty:
            df_comp = (
                df_prev.merge(df_curr, on="name", how="outer")
                .fillna(0)
                .query("name != '__idle__'")
            )
            df_comp["change_pct"] = (
                (df_comp["curr_cost"] - df_comp["prev_cost"])
                / df_comp["prev_cost"].replace(0, np.nan) * 100
            ).fillna(0)
            df_comp = df_comp.nlargest(8, "curr_cost")
            bar_colors = [
                _ANOM_CLR if c > 25 else PALETTE[0] if c >= 0 else PALETTE[1]
                for c in df_comp["change_pct"]
            ]
            fig_comp = go.Figure(go.Bar(
                x=df_comp["change_pct"], y=df_comp["name"], orientation="h",
                marker_color=bar_colors,
                text=[f"{c:+.1f}%" for c in df_comp["change_pct"]],
                textposition="outside",
                hovertemplate="%{y}<br>Δ %{x:+.1f}%<extra></extra>",
            ))
            apply_plotly_theme(fig_comp)
            fig_comp.update_layout(
                height=260, margin=dict(l=0, r=0, t=0, b=0),
                yaxis=dict(autorange="reversed"),
                xaxis_title="% Change vs Previous Period", showlegend=False,
            )
            fig_comp.add_vline(x=0, line_color="#475569", line_width=1)
            st.plotly_chart(fig_comp, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info(f"Period comparison needs ≥ {_win_days * 2} days of data.")

    st.divider()

    # ── Summary metrics row ───────────────────────────────────────────────────
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Savings Potential", _f(sav_total) + "/mo",
               f"{sav_ratio * 100:.1f}% of monthly spend", delta_color="inverse")
    sm2.metric("Anomalies Detected",  anom_count,
               "cost spikes this period", delta_color="inverse" if anom_count else "off")
    sm3.metric("Est. Carbon Footprint", f"{carbon_kg:.1f} kg CO₂e",
               f"{_win_days}d window", help="$1 cloud ≈ 2 kWh × 0.233 kgCO₂/kWh")
    sm4.metric("Monthly Carbon Est.", f"{carbon_kg / _win_days * 30:.0f} kg CO₂e",
               "extrapolated")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COST ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_alloc:

    df_view = df_agg.copy() if not df_agg.empty else pd.DataFrame()
    if not show_idle and not df_view.empty:
        df_view = df_view[df_view["name"] != "__idle__"]
    if not df_view.empty:
        df_view = df_view.sort_values("total_cost", ascending=False).reset_index(drop=True)

    # ── Trend chart with anomalies + forecast ─────────────────────────────────
    if not df_trend.empty and "start" in df_trend.columns:
        df_tr = df_trend.copy()
        if not show_idle:
            df_tr = df_tr[df_tr["name"] != "__idle__"]

        pivot = df_tr.pivot_table(
            index="start", columns="name", values="total_cost",
            aggfunc="sum", fill_value=0,
        )
        top_ns = (
            df_ns_act.nlargest(10, "total_cost")["name"].tolist()
            if not df_ns_act.empty else []
        )
        chart_cols = [c for c in top_ns if c in pivot.columns]
        other_cols = [c for c in pivot.columns if c not in chart_cols and c != "__idle__"]
        daily_total = pivot[chart_cols + other_cols].sum(axis=1)
        anom_mask   = _detect_anomalies(daily_total)

        # Pre-convert pivot values to selected currency for display
        pivot_c = pivot * _rate
        daily_total_c = daily_total * _rate

        fig_trend_chart = go.Figure()

        for i, ns in enumerate(chart_cols):
            fig_trend_chart.add_trace(go.Bar(
                name=ns, x=pivot_c.index, y=pivot_c[ns],
                marker_color=PALETTE[i % len(PALETTE)],
                hovertemplate=f"<b>{ns}</b><br>%{{x}}<br>{_sym}%{{y:,.4f}}<extra></extra>",
            ))
        if other_cols:
            fig_trend_chart.add_trace(go.Bar(
                name="other", x=pivot_c.index, y=pivot_c[other_cols].sum(axis=1),
                marker_color="#94A3B8",
                hovertemplate=f"<b>other</b><br>%{{x}}<br>{_sym}%{{y:,.4f}}<extra></extra>",
            ))
        if show_idle and "__idle__" in pivot_c.columns:
            fig_trend_chart.add_trace(go.Bar(
                name="idle", x=pivot_c.index, y=pivot_c["__idle__"],
                marker_color=_IDLE_CLR,
            ))

        # Anomaly markers
        if anom_mask.any():
            fig_trend_chart.add_trace(go.Scatter(
                name="Anomaly",
                x=daily_total_c.index[anom_mask].tolist(),
                y=daily_total_c[anom_mask].tolist(),
                mode="markers",
                marker=dict(color=_ANOM_CLR, size=14, symbol="diamond",
                            line=dict(color="white", width=2)),
                hovertemplate=f"<b>Anomaly</b><br>%{{x}}<br>{_sym}%{{y:,.4f}}<extra></extra>",
            ))

        # Forecast
        if fcst_dates and fcst_vals and len(daily_total) > 0:
            bridge_x = [daily_total_c.index[-1]] + fcst_dates
            bridge_y = [daily_total_c.iloc[-1]]  + [v * _rate for v in fcst_vals]
            fig_trend_chart.add_trace(go.Scatter(
                name="Forecast", x=bridge_x, y=bridge_y,
                mode="lines+markers",
                line=dict(color=_FCST_CLR, dash="dot", width=2),
                marker=dict(color=_FCST_CLR, size=6),
                hovertemplate=f"<b>Forecast</b><br>%{{x}}<br>{_sym}%{{y:,.4f}}<extra></extra>",
            ))

        apply_plotly_theme(fig_trend_chart)
        fig_trend_chart.update_layout(
            barmode="stack", height=320, margin=dict(l=0, r=0, t=8, b=0),
            yaxis=dict(tickprefix=_sym), yaxis_title=f"Cost ({_cur_code})",
            xaxis_title=None, plot_bgcolor="#0F172A", paper_bgcolor="#0F172A",
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                        font=dict(size=11)),
        )
        st.plotly_chart(fig_trend_chart, use_container_width=True, config=PLOTLY_CONFIG)

        if anom_count:
            st.warning(
                f"⚠️ **{anom_count} cost spike(s)** detected: {', '.join(anom_dates)}  "
                f"(exceeded 2σ from period mean)"
            )
        if fcst_dates:
            st.caption(
                f"📈 Forecast: **{_f(sum(fcst_vals))}** projected over next "
                f"{len(fcst_dates)} days (linear trend). "
                f"Monthly run-rate: **{_f(cost_per_hr * 24 * 30)}**"
            )
    else:
        st.info("Daily trend not available for this window.")

    # ── Allocation table ───────────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:#64748B;font-size:0.8rem;margin:6px 0'>"
        f"<b>{aggregate.capitalize()}</b> · {len(df_view)} items · "
        f"{_WINDOW_OPTS.get(window)}</p>",
        unsafe_allow_html=True,
    )

    if not df_view.empty:
        # Add grade column
        df_view = df_view.copy()
        df_view["grade"] = df_view["efficiency"].apply(lambda e: _grade(e)[0])

        # Period comparison columns
        if not df_prev.empty and not df_curr.empty and aggregate == "namespace":
            _comp = df_prev.merge(df_curr, on="name", how="outer").fillna(0)
            df_view = df_view.merge(_comp, on="name", how="left")
            df_view["Δ%"] = (
                (df_view.get("curr_cost", pd.Series(dtype=float)) -
                 df_view.get("prev_cost", pd.Series(dtype=float)))
                / df_view.get("prev_cost", pd.Series(dtype=float)).replace(0, np.nan) * 100
            ).fillna(0).round(1)

        dl1, dl2, _ = st.columns([1, 1, 8])
        with dl1:
            st.download_button("⬇ CSV",
                df_view.to_csv(index=False).encode(),
                f"opencost_{aggregate}_{window}.csv", "text/csv",
                key="alloc_csv", use_container_width=True)
        with dl2:
            st.download_button("⬇ Excel",
                _excel_bytes(df_view, "Allocation"),
                f"opencost_{aggregate}_{window}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="alloc_xl", use_container_width=True)

        # Build display table
        _col_map = {
            "name":         aggregate.capitalize(),
            "grade":        "Grade",
            "cpu_cost":     "CPU",
            "gpu_cost":     "GPU",
            "ram_cost":     "Memory",
            "pv_cost":      "PV",
            "network_cost": "Network",
            "shared_cost":  "Shared",
            "total_cost":   "Total",
            "efficiency":   "Efficiency %",
        }
        if "Δ%" in df_view.columns:
            _col_map["Δ%"] = "Period Δ%"

        existing = {k: v for k, v in _col_map.items() if k in df_view.columns}
        df_disp = df_view[list(existing.keys())].copy()

        # Share column
        _total_share = df_disp["total_cost"].sum() if "total_cost" in df_disp.columns else 1
        if _total_share > 0:
            _ins = list(df_disp.columns).index("total_cost") + 1
            df_disp.insert(_ins, "share%", (df_disp["total_cost"] / _total_share * 100).round(1))

        # Format
        for col in ["cpu_cost", "gpu_cost", "ram_cost", "pv_cost", "network_cost",
                    "shared_cost", "total_cost"]:
            if col in df_disp.columns:
                df_disp[col] = df_disp[col].apply(lambda x: _f(x, 4))
        if "efficiency" in df_disp.columns:
            df_disp["efficiency"] = df_disp["efficiency"].map(lambda x: f"{x:.1f}%")
        if "share%" in df_disp.columns:
            df_disp["share%"] = df_disp["share%"].map(lambda x: f"{x:.1f}%")
        if "Δ%" in df_disp.columns:
            df_disp["Δ%"] = df_disp["Δ%"].map(lambda x: f"{x:+.1f}%")

        rename_map = dict(existing)
        rename_map["share%"] = "% of Total"
        df_disp.rename(columns={k: v for k, v in rename_map.items() if k in df_disp.columns},
                       inplace=True)
        st.dataframe(df_disp, use_container_width=True,
                     height=min(600, max(300, len(df_disp) * 36 + 38)))
    else:
        st.info(f"No data for **{aggregate}** · **{_WINDOW_OPTS.get(window)}**")

    # ── Heatmap ───────────────────────────────────────────────────────────────
    if not df_trend.empty and "start" in df_trend.columns:
        with st.expander("🔥 Cost Heatmap — namespace × day", expanded=False):
            df_heat = df_trend[df_trend["name"] != "__idle__"].copy()
            _top_heat = (
                df_heat.groupby("name")["total_cost"].sum()
                .nlargest(15).index.tolist()
            )
            heat_pivot = (
                df_heat[df_heat["name"].isin(_top_heat)]
                .pivot_table(index="name", columns="start", values="total_cost",
                             aggfunc="sum", fill_value=0)
            )
            if not heat_pivot.empty:
                fig_heat = px.imshow(
                    heat_pivot * _rate,
                    color_continuous_scale=[
                        [0.0, "#0f172a"], [0.2, "#1e3a5f"],
                        [0.6, PALETTE[0]], [1.0, "#EE6666"],
                    ],
                    aspect="auto",
                    labels={"color": f"Cost ({_cur_code})"},
                )
                apply_plotly_theme(fig_heat)
                fig_heat.update_layout(
                    height=max(320, len(heat_pivot) * 30),
                    margin=dict(l=0, r=0, t=8, b=0),
                    xaxis_title=None, yaxis_title=None,
                    coloraxis_colorbar=dict(title=_sym, tickprefix=_sym),
                )
                st.plotly_chart(fig_heat, use_container_width=True, config=PLOTLY_CONFIG)

    # ── Breakdown chart ───────────────────────────────────────────────────────
    if not df_view.empty:
        with st.expander("📊 Cost breakdown by component", expanded=False):
            _slider_df = df_agg_act if not df_agg_act.empty else df_view
            top_n = st.slider("Top N", 5, min(30, max(5, len(_slider_df))), 15,
                              key="alloc_top")
            _df_b = (df_agg_act if not df_agg_act.empty else df_view).head(top_n)
            if not _df_b.empty:
                fig_bar = go.Figure()
                for metric, color, label in [
                    ("cpu_cost",     PALETTE[0], "CPU"),
                    ("ram_cost",     PALETTE[1], "Memory"),
                    ("pv_cost",      PALETTE[3], "PV"),
                    ("network_cost", PALETTE[4], "Network"),
                    ("gpu_cost",     PALETTE[2], "GPU"),
                ]:
                    if metric in _df_b.columns:
                        vals = pd.to_numeric(_df_b[metric], errors="coerce").fillna(0)
                        if vals.sum() > 0:
                            fig_bar.add_trace(go.Bar(
                                name=label, y=_df_b["name"], x=vals * _rate, orientation="h",
                                marker_color=color,
                                hovertemplate=f"{label}: {_sym}%{{x:,.4f}}<extra>%{{y}}</extra>",
                            ))
                apply_plotly_theme(fig_bar)
                fig_bar.update_layout(
                    barmode="stack", height=max(320, top_n * 28),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title=f"Cost ({_cur_code})", xaxis=dict(tickprefix=_sym),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    margin=dict(l=0, r=10, t=30, b=0),
                )
                st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)

    # ── Efficiency scatter ────────────────────────────────────────────────────
    if not df_agg_act.empty and "cpu_efficiency" in df_agg_act.columns:
        with st.expander("⚡ CPU vs Memory Efficiency Scatter", expanded=False):
            _df_s = df_agg_act.head(40).copy()
            _mx = _df_s["total_cost"].max() or 1
            fig_sc = go.Figure(go.Scatter(
                x=_df_s["cpu_efficiency"],
                y=_df_s.get("ram_efficiency", _df_s["efficiency"]),
                mode="markers+text",
                text=_df_s["name"].str.split("/").str[-1],
                textposition="top center",
                marker=dict(
                    size=(_df_s["total_cost"] / _mx * 50 + 8).clip(8, 58),
                    color=_df_s["efficiency"],
                    colorscale=[[0, "#ef4444"], [0.5, "#fbbf24"], [1, "#22c55e"]],
                    showscale=True,
                    colorbar=dict(title="Eff%", ticksuffix="%"),
                    opacity=0.85, line=dict(color="white", width=1),
                ),
                customdata=pd.DataFrame({
                    "cost_c": _df_s["total_cost"] * _rate,
                    "eff":    _df_s["efficiency"],
                }).values,
                hovertemplate=f"<b>%{{text}}</b><br>CPU: %{{x:.1f}}%<br>RAM: %{{y:.1f}}%<br>"
                              f"Cost: {_sym}%{{customdata[0]:,.4f}}<br>Eff: %{{customdata[1]:.1f}}%<extra></extra>",
            ))
            fig_sc.add_hline(y=50, line_dash="dash", line_color="#475569", opacity=0.5)
            fig_sc.add_vline(x=50, line_dash="dash", line_color="#475569", opacity=0.5)
            apply_plotly_theme(fig_sc)
            fig_sc.update_layout(
                height=460, showlegend=False, margin=dict(l=0, r=0, t=8, b=0),
                xaxis=dict(title="CPU Efficiency %", range=[-5, 110]),
                yaxis=dict(title="RAM Efficiency %", range=[-5, 110]),
            )
            st.caption("Bottom-left: over-provisioned AND expensive — highest rightsizing ROI.")
            st.plotly_chart(fig_sc, use_container_width=True, config=PLOTLY_CONFIG)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ASSETS
# ══════════════════════════════════════════════════════════════════════════════
with tab_assets:

    nd_tot   = df_nd["total_cost"].sum() if not df_nd.empty else 0.0
    util_pct = ((nd_tot - idle_cost) / nd_tot * 100) if nd_tot > 0 else 0.0

    a1, a2, a3, a4, a5, a6 = st.columns(6)
    a1.metric("Node Total",      _f(nd_tot))
    a2.metric("Nodes",           len(df_nd))
    a3.metric("$/vCPU-hr",       _f(cpu_hr_rate, 4))
    a4.metric("$/GB-hr",         _f(ram_hr_rate, 5))
    a5.metric("Storage (PV)",    _f(pv_total))
    a6.metric("Utilisation",     f"{util_pct:.1f}%")

    at1, at2, at3 = st.tabs(["🖥️ Nodes", "💾 Storage / PV", "⚠️ Unclaimed PVs"])

    # ── Nodes ──────────────────────────────────────────────────────────────────
    with at1:
        if not df_nd.empty:
            _nd_d = df_nd.copy()
            _nd_d["cpu_cost_d"]   = _nd_d["cpu_cost"].apply(lambda x: _f(x, 4))
            _nd_d["ram_cost_d"]   = _nd_d["ram_cost"].apply(lambda x: _f(x, 4))
            _nd_d["total_cost_d"] = _nd_d["total_cost"].apply(lambda x: _f(x, 4))
            _nd_d["ram_gb_d"]     = _nd_d["ram_gb"].map(lambda x: f"{x:.1f} GB")
            _nd_d["cpu_cores_d"]  = _nd_d["cpu_cores"].map(lambda x: f"{x} vCPU")
            _nd_show = _nd_d.rename(columns={
                "name": "Node", "type": "Type", "region": "Region",
                "provider": "Provider",
                "cpu_cores_d": "CPU", "ram_gb_d": "RAM",
                "cpu_cost_d": "CPU Cost", "ram_cost_d": "RAM Cost",
                "total_cost_d": "Total",
            })
            show_cols = [c for c in ["Node","Type","Region","Provider","CPU","RAM",
                                     "CPU Cost","RAM Cost","Total"] if c in _nd_show.columns]
            st.dataframe(_nd_show[show_cols], use_container_width=True,
                         height=min(500, max(250, len(_nd_show) * 36 + 38)))

            col_bar, col_gauge = st.columns([3, 1])
            with col_bar:
                fig_nd = go.Figure()
                for col, pal, lbl in [("cpu_cost", PALETTE[0], "CPU"),
                                       ("ram_cost", PALETTE[1], "Memory")]:
                    if col in df_nd.columns:
                        fig_nd.add_trace(go.Bar(
                            name=lbl, y=df_nd["name"], x=df_nd[col] * _rate, orientation="h",
                            marker_color=pal,
                            hovertemplate=f"{lbl}: {_sym}%{{x:,.4f}}<extra>%{{y}}</extra>",
                        ))
                apply_plotly_theme(fig_nd)
                fig_nd.update_layout(
                    barmode="stack", height=max(240, len(df_nd) * 36),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title=f"Cost ({_cur_code})", xaxis=dict(tickprefix=_sym),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    margin=dict(l=0, r=10, t=30, b=0),
                )
                st.plotly_chart(fig_nd, use_container_width=True, config=PLOTLY_CONFIG)

            with col_gauge:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=util_pct,
                    title={"text": "Utilisation", "font": {"size": 13}},
                    number={"suffix": "%", "font": {"size": 22}},
                    gauge={
                        "axis": {"range": [0, 100], "ticksuffix": "%"},
                        "bar":  {"color": PALETTE[0]},
                        "steps": [
                            {"range": [0,  50], "color": "#450a0a"},
                            {"range": [50, 75], "color": "#451a03"},
                            {"range": [75, 100], "color": "#052e16"},
                        ],
                        "threshold": {"line": {"color": "white", "width": 2}, "value": 70},
                    },
                ))
                apply_plotly_theme(fig_g)
                fig_g.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_g, use_container_width=True, config=PLOTLY_CONFIG)

            st.download_button("⬇ Node CSV", df_nd.to_csv(index=False).encode(),
                               f"opencost_nodes_{window}.csv", "text/csv",
                               key="nd_csv", use_container_width=False)
        else:
            st.info("No node asset data available.")

    # ── Storage / PV ──────────────────────────────────────────────────────────
    with at2:
        if not df_pv.empty:
            _df_pvs = df_pv.sort_values("total_cost", ascending=False).reset_index(drop=True)
            col_c, col_t = st.columns([3, 2])
            with col_c:
                _pv_cost_c = _df_pvs["total_cost"] * _rate
                fig_pv = go.Figure(go.Bar(
                    x=_pv_cost_c, y=_df_pvs["pv"], orientation="h",
                    marker=dict(
                        color=_pv_cost_c,
                        colorscale=[[0, "#1e3a5f"], [1, PALETTE[0]]],
                        showscale=False,
                    ),
                    text=[f"{_f(v, 4)}  {g:.1f} GB"
                          for v, g in zip(_df_pvs["total_cost"], _df_pvs["gb"])],
                    textposition="outside",
                    hovertemplate=f"<b>%{{y}}</b><br>{_sym}%{{x:,.4f}}<extra></extra>",
                ))
                apply_plotly_theme(fig_pv)
                fig_pv.update_layout(
                    height=max(280, len(_df_pvs) * 30),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title=f"Cost ({_cur_code})", xaxis=dict(tickprefix=_sym),
                    showlegend=False, margin=dict(l=0, r=10, t=8, b=0),
                )
                st.plotly_chart(fig_pv, use_container_width=True, config=PLOTLY_CONFIG)
            with col_t:
                _pv_d = _df_pvs.copy()
                _pv_d["total_cost"] = _pv_d["total_cost"].map(lambda x: _f(x, 4))
                _pv_d["gb"] = _pv_d["gb"].map(lambda x: f"{x:.1f} GB")
                _pv_d.rename(columns={
                    "pv": "Volume", "total_cost": "Cost", "gb": "Size",
                    "namespace": "Namespace", "claim": "PVC", "storage_class": "Class",
                }, inplace=True)
                sc = [c for c in ["Volume","Namespace","PVC","Class","Size","Cost"]
                      if c in _pv_d.columns]
                st.dataframe(_pv_d[sc], use_container_width=True,
                             height=min(500, max(250, len(_pv_d) * 36 + 38)))
        else:
            st.info("No PersistentVolume cost data available.")

    # ── Unclaimed PVs ─────────────────────────────────────────────────────────
    with at3:
        if unclaimed_v:
            _unc = pd.DataFrame([
                {
                    "volume":        r.get("volumeName", r.get("name", "")),
                    "storage_class": r.get("storageClass", ""),
                    "gb":            round((r.get("size", 0) or 0) / 1024 ** 3, 1),
                    "monthly_cost":  r.get("monthlyCost", 0.0) or 0.0,
                }
                for r in unclaimed_v if isinstance(r, dict)
            ])
            if not _unc.empty:
                st.error(
                    f"**{len(_unc)} unclaimed PVs** — wasting "
                    f"**{_f(_unc['monthly_cost'].sum())}/mo**. "
                    "Delete or reclaim to recover this cost."
                )
                _unc["monthly_cost"] = _unc["monthly_cost"].map(lambda x: _f(x))
                _unc["gb"] = _unc["gb"].map(lambda x: f"{x:.1f} GB")
                _unc.columns = ["Volume", "Storage Class", "Size", "Monthly Cost"]
                st.dataframe(_unc, use_container_width=True, height=320)
            else:
                st.success("No unclaimed PersistentVolumes found.")
        else:
            st.success("No unclaimed PersistentVolumes found.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SAVINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_savings:

    # ── Summary banner ────────────────────────────────────────────────────────
    if sav_total > 0:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#052e16,#0f172a);'
            f'border:1px solid #22c55e;border-radius:12px;padding:16px 20px;'
            f'margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<div style="font-size:28px;font-weight:700;color:#22c55e">{_f(sav_total)}/mo</div>'
            f'<div style="font-size:13px;color:#86efac;margin-top:2px">'
            f'Total identifiable savings · {sav_ratio*100:.1f}% of monthly spend</div>'
            f'</div>'
            f'<div style="font-size:40px">💡</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Request Rightsizing", _f(sav_rs)   + "/mo")
    s2.metric("Cluster Rightsizing", _f(sav_clus)  + "/mo")
    s3.metric("Unclaimed Volumes",   _f(sav_uncl)  + "/mo")
    s4.metric("Abandoned Workloads", _f(sav_aband) + "/mo")
    s5.metric("Underutil Nodes",     _f(sav_under) + "/mo")

    # ── Savings distribution + ROI timeline ──────────────────────────────────
    if sav_total > 0:
        col_pie, col_roi = st.columns(2)

        with col_pie:
            _sav_labels = []
            _sav_vals   = []
            for lbl, val in [
                ("Request Rightsizing", sav_rs),
                ("Cluster Rightsizing", sav_clus),
                ("Unclaimed PVs",       sav_uncl),
                ("Abandoned Workloads", sav_aband),
                ("Underutil Nodes",     sav_under),
            ]:
                if val > 0:
                    _sav_labels.append(lbl)
                    _sav_vals.append(val)
            if _sav_labels:
                fig_sav_pie = go.Figure(go.Pie(
                    labels=_sav_labels, values=[v * _rate for v in _sav_vals], hole=0.55,
                    marker=dict(colors=PALETTE[:len(_sav_labels)]),
                    hovertemplate=f"%{{label}}<br><b>{_sym}%{{value:,.2f}}/mo</b> (%{{percent}})<extra></extra>",
                ))
                apply_plotly_theme(fig_sav_pie)
                fig_sav_pie.update_layout(
                    height=260, margin=dict(l=0, r=0, t=0, b=0),
                    annotations=[dict(text=_f(sav_total) + "/mo", x=0.5, y=0.5,
                                      font_size=13, font_color="#e2e8f0", showarrow=False)],
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15),
                )
                st.markdown("**Savings by Category**")
                st.plotly_chart(fig_sav_pie, use_container_width=True, config=PLOTLY_CONFIG)

        with col_roi:
            st.markdown("**Projected ROI Timeline**")
            _months = list(range(1, 13))
            # Quick wins (low effort) available from month 1; investments from month 3
            _quick  = sav_uncl + sav_aband
            _medium = sav_rs + sav_under
            _invest = sav_clus
            _cumulative = [
                (_quick + (m >= 2) * _medium + (m >= 4) * _invest) * m * _rate
                for m in _months
            ]
            fig_roi = go.Figure()
            fig_roi.add_trace(go.Bar(
                x=[f"M{m}" for m in _months],
                y=_cumulative,
                marker=dict(
                    color=_cumulative,
                    colorscale=[[0, "#052e16"], [0.5, "#16a34a"], [1, "#22c55e"]],
                    showscale=False,
                ),
                text=[_f(v) for v in _cumulative],
                textposition="outside",
                hovertemplate=f"Month %{{x}}<br>Cumulative: <b>{_sym}%{{y:,.0f}}</b><extra></extra>",
            ))
            apply_plotly_theme(fig_roi)
            fig_roi.update_layout(
                height=260, margin=dict(l=0, r=0, t=8, b=0),
                yaxis_title="Cumulative Savings", yaxis=dict(tickprefix=_sym),
                xaxis_title=None, showlegend=False,
            )
            st.caption("Assumes: M1 quick wins, M2 rightsizing, M4 cluster changes.")
            st.plotly_chart(fig_roi, use_container_width=True, config=PLOTLY_CONFIG)

    st.divider()

    # ── 5 savings sub-tabs ────────────────────────────────────────────────────
    sav_t1, sav_t2, sav_t3, sav_t4, sav_t5 = st.tabs([
        "🔧 Request Rightsizing",
        "🖥️ Cluster Sizing",
        "🎯 Priority Matrix",
        "🚫 Abandoned Workloads",
        "📉 Underutilised Nodes",
    ])

    with sav_t1:
        if req_recs:
            _rs = pd.DataFrame([
                {
                    "namespace":  r.get("namespace", ""),
                    "controller": r.get("controllerName", ""),
                    "container":  r.get("containerName", ""),
                    "cpu_sav":    r.get("monthlyCPUSavings", 0) or 0,
                    "ram_sav":    r.get("monthlyRAMSavings",  0) or 0,
                    "total_sav":  (r.get("monthlyCPUSavings", 0) or 0)
                                  + (r.get("monthlyRAMSavings", 0) or 0),
                }
                for r in req_recs if isinstance(r, dict)
            ]).sort_values("total_sav", ascending=False)
            fig_rs = go.Figure(go.Bar(
                x=(_rs["total_sav"] * _rate).head(15),
                y=(_rs["controller"] + "/" + _rs["container"]).head(15),
                orientation="h", marker_color=PALETTE[1],
                hovertemplate=f"%{{y}}<br><b>{_sym}%{{x:,.2f}}/mo</b><extra></extra>",
            ))
            apply_plotly_theme(fig_rs)
            fig_rs.update_layout(height=360, yaxis=dict(autorange="reversed"),
                                 xaxis_title=f"Monthly Savings ({_sym})", showlegend=False)
            st.plotly_chart(fig_rs, use_container_width=True, config=PLOTLY_CONFIG)
            for c in ["cpu_sav", "ram_sav", "total_sav"]:
                _rs[c] = _rs[c].map(lambda x: _f(x))
            _rs.columns = ["Namespace","Controller","Container","CPU/mo","RAM/mo","Total/mo"]
            st.dataframe(_rs, use_container_width=True, height=300)
            st.download_button("⬇ CSV", _rs.to_csv(index=False).encode(),
                               "rightsizing.csv", "text/csv", key="rs_csv")
        elif not df_agg_act.empty and "efficiency" in df_agg_act.columns:
            _over = df_agg_act[df_agg_act["efficiency"] < 65].copy()
            _over["est_savings"] = _over["total_cost"] * (1 - 65 / 100)
            st.caption("requestSizingV2 API unavailable — efficiency-based estimate (65% target).")
            fig_est = go.Figure(go.Bar(
                x=(_over["est_savings"] * _rate).head(15), y=_over["name"].head(15),
                orientation="h", marker_color=PALETTE[2],
                hovertemplate=f"%{{y}}<br>Est. {_sym}%{{x:,.2f}}/mo<extra></extra>",
            ))
            apply_plotly_theme(fig_est)
            fig_est.update_layout(height=340, yaxis=dict(autorange="reversed"),
                                  xaxis_title="Est. Monthly Savings", showlegend=False)
            st.plotly_chart(fig_est, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.success("No rightsizing recommendations — all containers are well-sized!")

    with sav_t2:
        if isinstance(clus_recs, dict) and clus_recs.get("recommendations"):
            recs = clus_recs["recommendations"]
            if not isinstance(recs, list):
                recs = [recs]
            for r in recs:
                if not isinstance(r, dict):
                    continue
                pool = r.get("nodePoolName", "default")
                savings = r.get("monthlySavings", 0.0)
                with st.expander(f"Node pool: {pool} — save {_f(savings)}/mo"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Nodes",     r.get("currentNodeCount",     "N/A"))
                    c2.metric("Recommended Nodes", r.get("recommendedNodeCount", "N/A"))
                    c3.metric("Monthly Savings",   _f(savings))
        else:
            st.info("Cluster sizing API unavailable or cluster is already optimal.")
            st.code(
                "kubectl top nodes\n"
                "az aks nodepool scale --name apppool \\\n"
                "  --cluster-name finops-aks \\\n"
                "  --resource-group rg-finops-prod-core --node-count 1",
                language="bash",
            )

    with sav_t3:
        if not df_agg_act.empty and "efficiency" in df_agg_act.columns:
            _mat = df_agg_act[df_agg_act["efficiency"] < 65].nlargest(30, "total_cost").copy()
            if not _mat.empty:
                _mat["est_savings"] = _mat["total_cost"] * (1 - 65 / 100)
                _mat["effort"]      = _mat["efficiency"].apply(
                    lambda e: 1 if e < 20 else (2 if e < 50 else 3)
                )
                _emap = {1: "Low", 2: "Medium", 3: "High"}
                _cmap = {1: PALETTE[1], 2: PALETTE[2], 3: PALETTE[3]}
                _mat["effort_lbl"] = _mat["effort"].map(_emap)
                _mat["color"]      = _mat["effort"].map(_cmap)
                _mat["sz"] = (_mat["est_savings"] / _mat["est_savings"].max() * 50 + 10).clip(10, 60)
                fig_mat = go.Figure(go.Scatter(
                    x=_mat["effort"], y=_mat["est_savings"],
                    mode="markers+text",
                    text=_mat["name"].str.split("/").str[-1],
                    textposition="top center",
                    marker=dict(size=_mat["sz"], color=_mat["color"],
                                opacity=0.85, line=dict(color="white", width=1)),
                    customdata=pd.DataFrame({
                        "sav_c": _mat["est_savings"] * _rate,
                        "eff":   _mat["efficiency"],
                        "lbl":   _mat["effort_lbl"],
                    }).values,
                    hovertemplate=f"<b>%{{text}}</b><br>Savings: {_sym}%{{customdata[0]:,.2f}}/mo<br>"
                                  "Efficiency: %{customdata[1]:.1f}%<br>"
                                  "Effort: %{customdata[2]}<extra></extra>",
                ))
                fig_mat.add_hline(y=_mat["est_savings"].median(), line_dash="dot",
                                  line_color="#475569",
                                  annotation_text="Median", annotation_position="bottom right")
                apply_plotly_theme(fig_mat)
                fig_mat.update_layout(
                    height=440,
                    xaxis=dict(title="Implementation Effort",
                               tickvals=[1, 2, 3], ticktext=["Low","Medium","High"]),
                    yaxis_title=f"Est. Monthly Savings ({_cur_code})",
                    showlegend=False,
                )
                st.caption("Top-left quadrant (low effort, high savings) = act first.")
                st.plotly_chart(fig_mat, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.success("All workloads are above 65% efficiency — no priority actions needed.")
        else:
            st.info("Insufficient allocation data for priority matrix.")

    with sav_t4:
        if aband_recs:
            _ab = pd.DataFrame([
                {
                    "namespace":    r.get("namespace", ""),
                    "workload":     r.get("controllerName", r.get("name", "")),
                    "kind":         r.get("controllerKind", ""),
                    "monthly_cost": r.get("monthlyCost", 0.0) or 0.0,
                }
                for r in aband_recs if isinstance(r, dict)
            ])
            if not _ab.empty:
                st.error(
                    f"**{len(_ab)} abandoned workloads** — "
                    f"{_f(_ab['monthly_cost'].sum())}/mo wasted"
                )
                fig_ab = go.Figure(go.Bar(
                    y=_ab["workload"].head(20), x=(_ab["monthly_cost"] * _rate).head(20),
                    orientation="h", marker_color=PALETTE[3],
                    hovertemplate=f"%{{y}}<br>{_sym}%{{x:,.2f}}/mo<extra></extra>",
                ))
                apply_plotly_theme(fig_ab)
                fig_ab.update_layout(
                    height=max(260, min(len(_ab), 20) * 28),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title="Monthly Cost", showlegend=False,
                )
                st.plotly_chart(fig_ab, use_container_width=True, config=PLOTLY_CONFIG)
                _ab["monthly_cost"] = _ab["monthly_cost"].map(lambda x: _f(x))
                _ab.columns = ["Namespace","Workload","Kind","Monthly Cost"]
                st.dataframe(_ab, use_container_width=True, height=300)
            else:
                st.success("No abandoned workloads found.")
        else:
            st.success("No abandoned workloads found.")

    with sav_t5:
        if underutil_n:
            _un = pd.DataFrame([
                {
                    "node":       r.get("nodeName", r.get("name", "")),
                    "cpu_util":   round((r.get("cpuUtilization", 0) or 0) * 100, 1),
                    "ram_util":   round((r.get("ramUtilization", 0) or 0) * 100, 1),
                    "savings_mo": r.get("monthlySavings", 0.0) or 0.0,
                }
                for r in underutil_n if isinstance(r, dict)
            ])
            if not _un.empty:
                st.warning(
                    f"**{len(_un)} underutilised nodes** — "
                    f"{_f(_un['savings_mo'].sum())}/mo recoverable"
                )
                col_ub, col_ut = st.columns([2, 1])
                with col_ub:
                    fig_un = go.Figure()
                    fig_un.add_trace(go.Bar(
                        name="CPU Util %", y=_un["node"], x=_un["cpu_util"],
                        orientation="h", marker_color=PALETTE[0],
                    ))
                    fig_un.add_trace(go.Bar(
                        name="RAM Util %", y=_un["node"], x=_un["ram_util"],
                        orientation="h", marker_color=PALETTE[1],
                    ))
                    apply_plotly_theme(fig_un)
                    fig_un.update_layout(
                        barmode="group", height=max(260, len(_un) * 36),
                        yaxis=dict(autorange="reversed"),
                        xaxis=dict(title="Utilisation %", range=[0, 110]),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    fig_un.add_vline(x=50, line_dash="dash", line_color="#475569", opacity=0.5)
                    st.plotly_chart(fig_un, use_container_width=True, config=PLOTLY_CONFIG)
                with col_ut:
                    _un_d = _un.copy()
                    _un_d["savings_mo"] = _un_d["savings_mo"].map(lambda x: _f(x))
                    _un_d["cpu_util"]   = _un_d["cpu_util"].map(lambda x: f"{x:.1f}%")
                    _un_d["ram_util"]   = _un_d["ram_util"].map(lambda x: f"{x:.1f}%")
                    _un_d.columns = ["Node","CPU Util","RAM Util","Savings/mo"]
                    st.dataframe(_un_d, use_container_width=True, height=320)
            else:
                st.success("All nodes are well-utilised.")
        else:
            st.success("All nodes are well-utilised.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CLOUD COSTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_cloud:

    if not _cc_on:
        st.info(
            "**Cloud Costs not yet enabled.**\n\n"
            "Run `1-infrastructure/scripts/setup-opencost-azure.sh --part-b` "
            "to create the billing export and K8s secret, then ensure "
            "`opencost.cloudCost.enabled: true` in helm values."
        )
    else:
        # Build DataFrames
        svc_rows = [
            {"service": svc, "cost": p.get("cost", p.get("totalCost", 0.0)) or 0.0}
            for bucket in (cc_svc_raw or []) if isinstance(bucket, dict)
            for svc, p in bucket.items() if isinstance(p, dict)
        ]
        df_cc_svc = (
            pd.DataFrame(svc_rows)
            .groupby("service", as_index=False)["cost"].sum()
            .sort_values("cost", ascending=False)
            .reset_index(drop=True)
        ) if svc_rows else pd.DataFrame()

        cat_rows = [
            {"category": cat, "cost": p.get("cost", p.get("totalCost", 0.0)) or 0.0}
            for bucket in (cc_cat_raw or []) if isinstance(bucket, dict)
            for cat, p in bucket.items() if isinstance(p, dict)
        ]
        df_cc_cat = (
            pd.DataFrame(cat_rows)
            .groupby("category", as_index=False)["cost"].sum()
        ) if cat_rows else pd.DataFrame()

        # Daily cloud trend
        trend_rows = [
            {"date": bucket.get("start", "")[:10], "provider": svc,
             "cost": p.get("cost", p.get("totalCost", 0.0)) or 0.0}
            for bucket in (cc_trend_raw or []) if isinstance(bucket, dict)
            for svc, p in bucket.items() if isinstance(p, dict)
        ]
        df_cc_trend = pd.DataFrame(trend_rows) if trend_rows else pd.DataFrame()

        total_cc = df_cc_svc["cost"].sum() if not df_cc_svc.empty else 0.0

        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Cloud Total",  _f(total_cc))
        cc2.metric("Services",     len(df_cc_svc) if not df_cc_svc.empty else 0)
        cc3.metric("Categories",   len(df_cc_cat) if not df_cc_cat.empty else 0)

        # Daily trend
        if not df_cc_trend.empty and "date" in df_cc_trend.columns:
            _dt = df_cc_trend.groupby("date", as_index=False)["cost"].sum().sort_values("date")
            if len(_dt) > 1:
                _dt_anom = _detect_anomalies(_dt["cost"])
                fig_cct = go.Figure()
                _dt_cost_c = _dt["cost"] * _rate
                fig_cct.add_trace(go.Scatter(
                    x=_dt["date"], y=_dt_cost_c, mode="lines+markers",
                    name="Cloud Spend", line=dict(color=PALETTE[0], width=2),
                    marker=dict(color=[
                        _ANOM_CLR if _dt_anom.iloc[i] else PALETTE[0]
                        for i in range(len(_dt))
                    ], size=8),
                    hovertemplate=f"%{{x}}<br><b>{_sym}%{{y:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig_cct)
                fig_cct.update_layout(
                    height=220, margin=dict(l=0,r=0,t=8,b=0),
                    yaxis=dict(tickprefix=_sym), xaxis_title=None,
                    yaxis_title=f"Cloud Cost ({_cur_code})", showlegend=False,
                )
                st.markdown("**Daily Cloud Spend Trend**")
                st.plotly_chart(fig_cct, use_container_width=True, config=PLOTLY_CONFIG)

        cc_t1, cc_t2 = st.tabs(["📊 By Service", "🗂️ By Category"])

        with cc_t1:
            if not df_cc_svc.empty:
                col_ch, col_tb = st.columns([3, 2])
                with col_ch:
                    _svc_cost_c = df_cc_svc["cost"] * _rate
                    fig_ccs = go.Figure(go.Bar(
                        x=_svc_cost_c, y=df_cc_svc["service"], orientation="h",
                        marker=dict(
                            color=_svc_cost_c,
                            colorscale=[[0, "#1e3a5f"], [1, PALETTE[0]]],
                            showscale=False,
                        ),
                        text=[_f(v) for v in df_cc_svc["cost"]],
                        textposition="outside",
                        hovertemplate=f"%{{y}}<br><b>{_sym}%{{x:,.2f}}</b><extra></extra>",
                    ))
                    apply_plotly_theme(fig_ccs)
                    fig_ccs.update_layout(
                        height=max(300, len(df_cc_svc) * 28),
                        yaxis=dict(autorange="reversed"),
                        xaxis_title=f"Cost ({_cur_code})", xaxis=dict(tickprefix=_sym),
                        showlegend=False, margin=dict(l=0,r=10,t=8,b=0),
                    )
                    st.plotly_chart(fig_ccs, use_container_width=True, config=PLOTLY_CONFIG)
                with col_tb:
                    _ccs_d = df_cc_svc.copy()
                    _ccs_d["share"] = (_ccs_d["cost"] / total_cc * 100).round(1)
                    _ccs_d["cost"]  = _ccs_d["cost"].map(lambda x: _f(x))
                    _ccs_d["share"] = _ccs_d["share"].map(lambda x: f"{x:.1f}%")
                    _ccs_d.columns = ["Service","Cost","% of Total"]
                    st.dataframe(_ccs_d, use_container_width=True,
                                 height=min(500, max(250, len(_ccs_d)*36+38)))
                    st.download_button("⬇ CSV", df_cc_svc.to_csv(index=False).encode(),
                                       f"cloud_costs_{window}.csv", "text/csv", key="cc_csv")
            else:
                st.info("No cloud service data yet — billing export data arrives within 15–30 min of first run.")

        with cc_t2:
            if not df_cc_cat.empty:
                tot_cat = df_cc_cat["cost"].sum()
                col_pie, col_tb2 = st.columns([2, 2])
                with col_pie:
                    fig_pie = go.Figure(go.Pie(
                        labels=df_cc_cat["category"],
                        values=df_cc_cat["cost"] * _rate,
                        hole=0.55, marker=dict(colors=PALETTE[:len(df_cc_cat)]),
                        hovertemplate=f"%{{label}}<br><b>{_sym}%{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
                    ))
                    apply_plotly_theme(fig_pie)
                    fig_pie.update_layout(
                        height=320,
                        annotations=[dict(text=_f(tot_cat, 0), x=0.5, y=0.5,
                                          font_size=15, font_color="#E2E8F0", showarrow=False)],
                        margin=dict(l=0,r=0,t=8,b=0),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)
                with col_tb2:
                    _cat_d = df_cc_cat.sort_values("cost", ascending=False).copy()
                    _cat_d["share"] = (_cat_d["cost"] / tot_cat * 100).round(1)
                    _cat_d["cost"]  = _cat_d["cost"].map(lambda x: _f(x))
                    _cat_d["share"] = _cat_d["share"].map(lambda x: f"{x:.1f}%")
                    _cat_d.columns = ["Category","Cost","% of Total"]
                    st.dataframe(_cat_d, use_container_width=True,
                                 height=min(400, max(200, len(_cat_d)*36+38)))
            else:
                st.info("No category data available.")

    # ── External / Custom Costs ───────────────────────────────────────────────
    st.divider()
    st.markdown("**🔌 External / Custom Costs**")
    st.caption("Third-party services billed outside Kubernetes (Datadog, Snowflake, SaaS).")
    if cust_raw:
        _cr = [
            {"service": name, "cost": p.get("cost", p.get("totalCost", 0.0)) or 0.0}
            for bucket in cust_raw if isinstance(bucket, dict)
            for name, p in bucket.items() if isinstance(p, dict)
        ]
        if _cr:
            _df_cr = (
                pd.DataFrame(_cr)
                .sort_values("cost", ascending=False)
                .reset_index(drop=True)
            )
            _df_cr["cost"] = _df_cr["cost"].map(lambda x: _f(x))
            _df_cr.columns = ["External Service","Cost"]
            st.dataframe(_df_cr, use_container_width=True, height=260)
        else:
            st.info("No external cost data.")
    else:
        st.info("No custom costs configured.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_reports:

    rep_t1, rep_t2, rep_t3, rep_t4 = st.tabs([
        "🏷️ Chargeback",
        "💰 Budget vs Actual",
        "🌱 Carbon Footprint",
        "📥 Export Centre",
    ])

    # ── Chargeback ─────────────────────────────────────────────────────────────
    with rep_t1:
        st.markdown(f"**Chargeback by label: `{label_key}`**")
        st.caption(
            "Costs attributed to Kubernetes workloads carrying this label. "
            "Unlabelled cost appears as `__unallocated__`."
        )
        if not df_lbl.empty:
            df_cb = df_lbl[df_lbl["name"] != "__idle__"].copy()
            df_cb = df_cb.sort_values("total_cost", ascending=False).reset_index(drop=True)
            total_cb = df_cb["total_cost"].sum()

            # Bar chart
            fig_cb = go.Figure(go.Bar(
                x=df_cb["total_cost"].head(20),
                y=df_cb["name"].head(20),
                orientation="h",
                marker=dict(
                    color=df_cb["total_cost"].head(20),
                    colorscale=[[0, "#1e3a5f"], [1, PALETTE[0]]],
                    showscale=False,
                ),
                text=[_f(v) for v in df_cb["total_cost"].head(20)],
                textposition="outside",
                hovertemplate="%{y}<br><b>%{text}</b><extra></extra>",
            ))
            apply_plotly_theme(fig_cb)
            fig_cb.update_layout(
                height=max(320, min(len(df_cb), 20) * 28),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(showticklabels=False), showlegend=False,
                margin=dict(l=0,r=0,t=8,b=0),
            )
            st.plotly_chart(fig_cb, use_container_width=True, config=PLOTLY_CONFIG)

            # Chargeback table
            _cb_d = df_cb.copy()
            _cb_d["share%"] = (_cb_d["total_cost"] / max(total_cb, 1) * 100).round(1)
            for col in ["cpu_cost","gpu_cost","ram_cost","pv_cost","network_cost","total_cost"]:
                if col in _cb_d.columns:
                    _cb_d[col] = _cb_d[col].apply(lambda x: _f(x, 4))
            if "efficiency" in _cb_d.columns:
                _cb_d["efficiency"] = _cb_d["efficiency"].map(lambda x: f"{x:.1f}%")
            _cb_d["share%"] = _cb_d["share%"].map(lambda x: f"{x:.1f}%")
            _cb_d.rename(columns={
                "name": label_key.capitalize(), "cpu_cost": "CPU", "gpu_cost": "GPU",
                "ram_cost": "Memory", "pv_cost": "PV", "network_cost": "Network",
                "total_cost": "Total", "efficiency": "Efficiency", "share%": "% of Total",
            }, inplace=True)
            st.dataframe(_cb_d, use_container_width=True,
                         height=min(500, max(300, len(_cb_d)*36+38)))

            cb1, cb2 = st.columns(2)
            with cb1:
                st.download_button(
                    "⬇ Chargeback CSV",
                    df_lbl.to_csv(index=False).encode(),
                    f"chargeback_{label_key}_{window}.csv", "text/csv",
                    key="cb_csv",
                )
            with cb2:
                st.download_button(
                    "⬇ Chargeback Excel",
                    _excel_bytes(df_lbl, "Chargeback"),
                    f"chargeback_{label_key}_{window}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="cb_xl",
                )
        else:
            st.info(
                f"No workloads found with label `{label_key}`. "
                "Try a different label key in the controls bar above."
            )

    # ── Budget vs Actual ───────────────────────────────────────────────────────
    with rep_t2:
        st.markdown("**Namespace Budget Tracker**")
        st.caption(
            "Set a budget for each namespace. Values are in USD and persist for this session. "
            "Edit the **Budget (USD)** column inline."
        )
        if not df_ns_act.empty:
            cur = st.session_state.get("oc_currency", "USD")

            # Build budget rows; seed defaults at 120% of current cost
            for _, row in df_ns_act.iterrows():
                ns = row["name"]
                if ns not in st.session_state["oc_budgets"]:
                    st.session_state["oc_budgets"][ns] = round(row["total_cost"] * 1.2, 4)

            _act_col    = f"Actual ({_cur_code})"
            _bgt_col    = f"Budget ({_cur_code})"
            budget_rows = []
            for _, row in df_ns_act.sort_values("total_cost", ascending=False).iterrows():
                ns     = row["name"]
                actual = row["total_cost"]
                budget = st.session_state["oc_budgets"].get(ns, actual * 1.2)
                used   = (actual / budget * 100) if budget > 0 else 0
                status = "🔴 Over" if used > 100 else "🟡 Near" if used > 80 else "🟢 OK"
                budget_rows.append({
                    "Namespace": ns,
                    _act_col:    round(_c(actual), 4),
                    _bgt_col:    round(_c(budget), 4),
                    "% Used":    round(used, 1),
                    "Status":    status,
                })
            df_bgt = pd.DataFrame(budget_rows)

            edited = st.data_editor(
                df_bgt,
                use_container_width=True,
                disabled=["Namespace", _act_col, "% Used", "Status"],
                hide_index=True,
                key="budget_editor",
                height=min(500, max(300, len(df_bgt)*36+52)),
            )
            # Persist edited budgets — convert back from display currency to USD
            for _, row in edited.iterrows():
                bgt_usd = float(row[_bgt_col]) / _rate if _rate else float(row[_bgt_col])
                st.session_state["oc_budgets"][row["Namespace"]] = bgt_usd

            # Visualise budget utilisation
            _over_bgt = edited[edited["% Used"] > 80].sort_values("% Used", ascending=False)
            if not _over_bgt.empty:
                st.error(
                    f"**{len(_over_bgt[_over_bgt['% Used']>100])} namespaces over budget**, "
                    f"{len(_over_bgt[(_over_bgt['% Used']>80)&(_over_bgt['% Used']<=100)])} near limit."
                )
            fig_bgt = go.Figure()
            fig_bgt.add_trace(go.Bar(
                name="Actual", y=edited["Namespace"], x=edited[_act_col],
                orientation="h", marker_color=PALETTE[0],
                hovertemplate=f"%{{y}}<br>Actual: {_sym}%{{x:,.4f}}<extra></extra>",
            ))
            fig_bgt.add_trace(go.Scatter(
                name="Budget", y=edited["Namespace"], x=edited[_bgt_col],
                mode="markers",
                marker=dict(color="#fbbf24", size=10, symbol="diamond"),
                hovertemplate=f"%{{y}}<br>Budget: {_sym}%{{x:,.4f}}<extra></extra>",
            ))
            apply_plotly_theme(fig_bgt)
            fig_bgt.update_layout(
                barmode="overlay", height=max(280, len(edited)*30),
                yaxis=dict(autorange="reversed"),
                xaxis_title=f"Cost ({_cur_code})", xaxis=dict(tickprefix=_sym),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=0,r=10,t=30,b=0),
            )
            st.plotly_chart(fig_bgt, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No namespace data available for budget tracking.")

    # ── Carbon Footprint ───────────────────────────────────────────────────────
    with rep_t3:
        st.markdown("**Carbon Footprint Estimate**")
        st.caption(
            "Methodology: $1 of cloud compute ≈ 2 kWh × 0.233 kgCO₂e/kWh (global average). "
            "Actual values depend on your Azure region and renewable energy mix."
        )

        cf1, cf2, cf3, cf4 = st.columns(4)
        cf1.metric(f"{_win_days}-day CO₂",  f"{carbon_kg:.1f} kg")
        cf2.metric("Monthly Est.",          f"{carbon_kg / _win_days * 30:.0f} kg")
        cf3.metric("Annual Est.",           f"{carbon_kg / _win_days * 365:.0f} kg")
        cf4.metric("Trees to offset/yr",
                   f"{carbon_kg / _win_days * 365 / 21:.0f}",
                   "1 tree absorbs ~21 kg CO₂/yr")

        if not df_ns_act.empty:
            _cf = df_ns_act[["name","total_cost"]].copy()
            _cf["carbon_kg"]  = _cf["total_cost"] * _CARBON_FACTOR
            _cf["carbon_mon"] = (_cf["carbon_kg"] / _win_days * 30).round(1)
            _cf = _cf.sort_values("carbon_kg", ascending=False).reset_index(drop=True)

            fig_carbon = go.Figure(go.Bar(
                x=_cf["carbon_kg"].head(15),
                y=_cf["name"].head(15),
                orientation="h",
                marker=dict(
                    color=_cf["carbon_kg"].head(15),
                    colorscale=[[0, "#052e16"], [0.5, "#16a34a"], [1, "#86efac"]],
                    showscale=False,
                ),
                text=[f"{v:.1f} kg" for v in _cf["carbon_kg"].head(15)],
                textposition="outside",
                hovertemplate="%{y}<br><b>%{x:.1f} kgCO₂e</b><extra></extra>",
            ))
            apply_plotly_theme(fig_carbon)
            fig_carbon.update_layout(
                height=max(280, min(len(_cf),15)*28),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Carbon (kgCO₂e)", showlegend=False,
                margin=dict(l=0,r=10,t=8,b=0),
            )
            st.markdown(f"**Top Emitters — {_WINDOW_OPTS.get(window)}**")
            st.plotly_chart(fig_carbon, use_container_width=True, config=PLOTLY_CONFIG)

            _cf["cost_disp"]    = _cf["total_cost"].map(lambda x: _f(x))
            _cf["carbon_disp"]  = _cf["carbon_kg"].map(lambda x: f"{x:.2f} kg")
            _cf["carbon_mon_d"] = _cf["carbon_mon"].map(lambda x: f"{x:.1f} kg")
            _cf_show = _cf[["name","cost_disp","carbon_disp","carbon_mon_d"]].copy()
            _cf_show.columns = ["Namespace","Cost","CO₂e (period)","CO₂e (monthly)"]
            st.dataframe(_cf_show, use_container_width=True,
                         height=min(400, max(250, len(_cf_show)*36+38)))
            st.download_button(
                "⬇ Carbon Report CSV",
                _cf_show.to_csv(index=False).encode(),
                f"carbon_{window}.csv", "text/csv", key="carbon_csv",
            )
        else:
            st.info("No allocation data for carbon breakdown.")

    # ── Export Centre ──────────────────────────────────────────────────────────
    with rep_t4:
        st.markdown("**Export Centre — Download all data**")

        exports = {
            "Namespace Allocation":  df_ns,
            f"{aggregate.capitalize()} Allocation": df_agg,
            f"Chargeback ({label_key})": df_lbl,
            "Daily Trend":           df_trend,
            "Nodes":                 df_nd,
            "PersistentVolumes":     df_pv,
        }
        for name_exp, df_exp in exports.items():
            if df_exp is not None and not df_exp.empty:
                safe = name_exp.replace(" ","_").replace("/","_").lower()
                ec1, ec2, ec3 = st.columns([3, 1, 1])
                ec1.markdown(f"**{name_exp}** — {len(df_exp)} rows")
                with ec2:
                    st.download_button(
                        "CSV", df_exp.to_csv(index=False).encode(),
                        f"{safe}_{window}.csv", "text/csv",
                        key=f"exp_csv_{safe}", use_container_width=True,
                    )
                with ec3:
                    st.download_button(
                        "Excel", _excel_bytes(df_exp, name_exp[:30]),
                        f"{safe}_{window}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"exp_xl_{safe}", use_container_width=True,
                    )
                st.divider()

        # Full JSON snapshot
        st.markdown("**Full JSON Snapshot**")
        snapshot = {
            "window":    window,
            "aggregate": aggregate,
            "metrics": {
                "total_cost_usd":   total_k8s,
                "cost_per_hr_usd":  cost_per_hr,
                "efficiency_pct":   avg_eff,
                "idle_pct":         idle_pct,
                "health_score":     h_score,
                "health_grade":     h_grade,
                "savings_potential_usd_mo": sav_total,
                "carbon_kg":        carbon_kg,
                "anomaly_count":    anom_count,
                "anomaly_dates":    anom_dates,
            },
            "namespace_allocation": df_ns.to_dict(orient="records") if not df_ns.empty else [],
            "savings": {
                "request_rightsizing": sav_rs,
                "cluster_rightsizing": sav_clus,
                "unclaimed_pvs":       sav_uncl,
                "abandoned_workloads": sav_aband,
                "underutil_nodes":     sav_under,
            },
        }
        st.download_button(
            "⬇ Full JSON Snapshot",
            json.dumps(snapshot, indent=2, default=str).encode(),
            f"opencost_snapshot_{window}.json", "application/json",
            key="exp_json", use_container_width=False,
        )
        st.caption(
            f"Snapshot includes: namespace allocation, KPIs, health score, "
            f"anomaly dates, savings breakdown — window: {_WINDOW_OPTS.get(window)}"
        )
