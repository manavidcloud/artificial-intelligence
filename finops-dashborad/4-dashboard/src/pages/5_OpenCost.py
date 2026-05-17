"""FinOps Dashboard — OpenCost: Kubernetes Cost Allocation.

OpenCost runs in the `opencost` namespace and is deployed as part of the
core platform stack (Helm values: 4-dashboard/k8s/opencost-helm-values.yaml).

OPENCOST_URL defaults to the in-cluster service; override via deployment env var.
"""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PLOTLY_CONFIG
from utils.opencost_api import (
    is_online, allocation, node_assets, request_sizing, cluster_sizing,
    flatten_allocation,
)

st.set_page_config(
    page_title="OpenCost · FinOps",
    page_icon="☸️",
    layout="wide",
)
require_auth()
apply_theme()

PALETTE = [
    COLORS["blue"], COLORS["teal"], COLORS["green"],
    "#7C3AED", COLORS["amber"], "#DB2777", "#0891B2",
    COLORS["red"], "#8B5CF6", "#F59E0B", "#10B981", "#EF4444",
]

_WINDOW_LABELS = {
    "1d": "Today", "7d": "Last 7 days", "30d": "Last 30 days",
    "lastweek": "Last week", "lastmonth": "Last month",
}
_COMMON_LABELS = [
    "team", "environment", "env", "app", "app.kubernetes.io/name",
    "app.kubernetes.io/part-of", "owner", "cost-center", "project",
    "service", "tier", "component",
]

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    st.subheader("☸️ K8s Cost Settings")

    window = st.selectbox(
        "Time window",
        list(_WINDOW_LABELS.keys()),
        index=1,
        format_func=lambda w: _WINDOW_LABELS.get(w, w),
    )
    aggregate_wl = st.radio(
        "Workload aggregate", ["deployment", "pod", "controller"], index=0
    )
    label_key = st.selectbox(
        "Label (chargeback)", _COMMON_LABELS, index=0,
        help="Label key used for cost allocation in the Labels tab.",
    )
    custom_lbl = st.text_input("Custom label key", placeholder="e.g. cost-center")
    if custom_lbl.strip():
        label_key = custom_lbl.strip()

    st.markdown("---")
    _online = is_online()
    if _online:
        st.success("OpenCost: Online ✓")
    else:
        st.error("OpenCost: Connecting…")
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("☸️ Kubernetes Cost Allocation")
st.caption(
    "Real-time pod / namespace / workload cost breakdown from your AKS cluster · "
    f"Window: **{_WINDOW_LABELS.get(window, window)}** · "
    "Powered by [OpenCost](https://opencost.io)"
)

if not _online:
    st.error(
        "OpenCost is not reachable at the configured endpoint. "
        "Check that the `opencost` namespace pods are Running: "
        "`kubectl get pods -n opencost`"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Fetch all data
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading Kubernetes cost data…"):
    ns_raw  = allocation(window=window, aggregate="namespace",   accumulate=True)
    wl_raw  = allocation(window=window, aggregate=aggregate_wl,  accumulate=True)
    nd_raw  = node_assets(window=window)
    lbl_raw = allocation(window=window, aggregate=f"label:{label_key}", accumulate=True)
    req_recs  = request_sizing()
    clus_recs = cluster_sizing()
    # Daily trend (non-accumulated, step=1d)
    trend_raw = allocation(window=window, aggregate="namespace", accumulate=False, step="1d")

ns_rows    = flatten_allocation(ns_raw)
wl_rows    = flatten_allocation(wl_raw)
lbl_rows   = flatten_allocation(lbl_raw)
trend_rows = flatten_allocation(trend_raw)

df_ns    = pd.DataFrame(ns_rows)    if ns_rows    else pd.DataFrame()
df_wl    = pd.DataFrame(wl_rows)    if wl_rows    else pd.DataFrame()
df_lbl   = pd.DataFrame(lbl_rows)   if lbl_rows   else pd.DataFrame()
df_trend = pd.DataFrame(trend_rows) if trend_rows else pd.DataFrame()

# Node assets
nd_parsed = []
for bucket in (nd_raw or []):
    if not isinstance(bucket, dict):
        continue
    for name, props in bucket.items():
        if not isinstance(props, dict):
            continue
        nd_parsed.append({
            "node":       name,
            "cpu_cost":   props.get("cpuCost", 0.0) or 0.0,
            "ram_cost":   props.get("ramCost", 0.0) or 0.0,
            "total_cost": props.get("totalCost", 0.0) or 0.0,
            "cpu_cores":  props.get("cpuCores") or 0,
            "ram_gb":     round((props.get("ramBytes") or 0) / (1024 ** 3), 1),
        })
df_nd = pd.DataFrame(nd_parsed) if nd_parsed else pd.DataFrame()

# Derived totals
df_ns_active = df_ns[df_ns["name"] != "__idle__"] if not df_ns.empty else pd.DataFrame()
total_k8s  = df_ns["total_cost"].sum() if not df_ns.empty else 0.0
idle_cost  = df_ns[df_ns["name"] == "__idle__"]["total_cost"].sum() if not df_ns.empty else 0.0
idle_pct   = (idle_cost / total_k8s * 100) if total_k8s > 0 else 0.0
avg_eff    = df_ns_active["efficiency"].mean() if not df_ns_active.empty else 0.0

# ─────────────────────────────────────────────────────────────────────────────
# KPI strip
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("K8s Total Spend",   f"${total_k8s:,.2f}")
c2.metric("Namespaces",        len(df_ns_active))
c3.metric("Nodes",             len(df_nd))
c4.metric("Idle Cost",         f"${idle_cost:,.2f}",
          f"{idle_pct:.1f}% waste", delta_color="inverse")
c5.metric("Avg Efficiency",    f"{avg_eff:.1f}%")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
(tab_overview, tab_namespaces, tab_workloads,
 tab_nodes, tab_labels, tab_savings) = st.tabs([
    "🏠 Overview",
    "📦 Namespaces",
    "🚀 Workloads",
    "🖥️ Nodes",
    "🏷️ Labels / Chargeback",
    "💡 Savings",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Cost by Namespace")
        if not df_ns_active.empty:
            df_p = df_ns_active.nlargest(15, "total_cost")
            fig = go.Figure(go.Bar(
                x=df_p["total_cost"], y=df_p["name"], orientation="h",
                marker=dict(color=df_p["total_cost"],
                            colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                            showscale=False),
                text=[f"${v:,.2f}" for v in df_p["total_cost"]],
                textposition="outside",
                hovertemplate="%{y}<br><b>$%{x:,.2f}</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(
                height=420, yaxis=dict(autorange="reversed"),
                xaxis_title="Cost (USD)", yaxis_title=None, showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No namespace data.")

    with col_r:
        st.subheader("Cost Composition")
        if not df_ns.empty:
            comp = {
                "CPU":     df_ns["cpu_cost"].sum(),
                "RAM":     df_ns["ram_cost"].sum(),
                "Storage": df_ns["pv_cost"].sum(),
                "Network": df_ns["network_cost"].sum(),
                "GPU":     df_ns["gpu_cost"].sum(),
                "Idle":    idle_cost,
            }
            comp = {k: v for k, v in comp.items() if v > 0}
            fig2 = go.Figure(go.Pie(
                labels=list(comp.keys()), values=list(comp.values()),
                hole=0.55, marker=dict(colors=PALETTE[:len(comp)]),
                textinfo="label+percent",
                hovertemplate="%{label}<br><b>$%{value:,.2f}</b> (%{percent})<extra></extra>",
            ))
            apply_plotly_theme(fig2)
            fig2.update_layout(
                height=420,
                annotations=[dict(text=f"${total_k8s:,.0f}", x=0.5, y=0.5,
                                  font_size=16, font_color=COLORS["text"], showarrow=False)],
            )
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No composition data.")

    # Efficiency heatmap
    st.subheader("Efficiency Heatmap (top 15 namespaces by cost)")
    if not df_ns_active.empty and "cpu_efficiency" in df_ns_active.columns:
        df_eff = df_ns_active.nlargest(15, "total_cost").copy()

        def _style(val):
            if val >= 80: return "background-color:#15803d;color:white"
            if val >= 50: return "background-color:#d97706;color:white"
            return "background-color:#dc2626;color:white"

        df_eff_disp = df_eff[["name", "total_cost", "cpu_efficiency", "ram_efficiency", "efficiency"]].copy()
        df_eff_disp["total_cost"] = df_eff_disp["total_cost"].map(lambda x: f"${x:,.2f}")
        df_eff_disp.columns = ["Namespace", "Cost", "CPU Eff %", "RAM Eff %", "Overall %"]
        st.dataframe(
            df_eff_disp.style.applymap(_style, subset=["CPU Eff %", "RAM Eff %", "Overall %"]),
            use_container_width=True, height=340,
        )
    else:
        st.info("Efficiency data not available.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — NAMESPACES
# ══════════════════════════════════════════════════════════════════════════════
with tab_namespaces:
    show_idle = st.toggle("Include __idle__", value=False, key="ns_idle_tog")
    df_ns_tab = df_ns.copy() if not df_ns.empty else pd.DataFrame()
    if not show_idle and not df_ns_tab.empty:
        df_ns_tab = df_ns_tab[df_ns_tab["name"] != "__idle__"]
    if not df_ns_tab.empty and "total_cost" in df_ns_tab.columns:
        df_ns_tab = df_ns_tab.sort_values("total_cost", ascending=False).reset_index(drop=True)

    ns_t1, ns_t2, ns_t3 = st.tabs(["📊 Bar (stacked)", "📈 Daily Trend", "📋 Table"])

    with ns_t1:
        if not df_ns_tab.empty:
            top_n = st.slider("Top N", 5, min(30, len(df_ns_tab)), 15, key="ns_n")
            df_p = df_ns_tab.head(top_n)
            fig = go.Figure()
            for metric, color, label in [
                ("cpu_cost", COLORS["blue"], "CPU"), ("ram_cost", COLORS["teal"], "RAM"),
                ("pv_cost", "#7C3AED", "Storage"), ("network_cost", COLORS["amber"], "Network"),
            ]:
                if metric in df_p.columns and df_p[metric].sum() > 0:
                    fig.add_trace(go.Bar(
                        name=label, y=df_p["name"], x=df_p[metric], orientation="h",
                        marker_color=color,
                        hovertemplate=f"{label}: $%{{x:,.2f}}<extra>%{{y}}</extra>",
                    ))
            apply_plotly_theme(fig)
            fig.update_layout(
                barmode="stack", height=max(350, top_n * 30),
                yaxis=dict(autorange="reversed"), xaxis_title="Cost (USD)", yaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No namespace data.")

    with ns_t2:
        if not df_trend.empty and "start" in df_trend.columns:
            df_tr = df_trend[df_trend["name"] != "__idle__"]
            pivot = df_tr.pivot_table(
                index="start", columns="name", values="total_cost", aggfunc="sum", fill_value=0
            )
            top_ns = df_ns_tab.head(8)["name"].tolist() if not df_ns_tab.empty else []
            cols_show = [c for c in top_ns if c in pivot.columns]
            fig2 = go.Figure()
            for i, ns in enumerate(cols_show):
                fig2.add_trace(go.Scatter(
                    x=pivot.index, y=pivot[ns], mode="lines+markers", name=ns,
                    line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                    hovertemplate=f"{ns}<br>%{{x}}<br><b>$%{{y:,.2f}}</b><extra></extra>",
                ))
            apply_plotly_theme(fig2)
            fig2.update_layout(
                height=380, xaxis_title="Date", yaxis_title="Cost (USD)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("Daily trend not available for this window.")

    with ns_t3:
        if not df_ns_tab.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_ns_tab.to_excel(w, index=False, sheet_name="Namespaces")
            col_h, col_csv, col_xl = st.columns([7, 1, 1])
            with col_h: st.subheader("All Namespaces")
            with col_csv:
                st.download_button("⬇ CSV", df_ns_tab.to_csv(index=False).encode(),
                                   "namespaces.csv", "text/csv", key="ns_csv",
                                   use_container_width=True)
            with col_xl:
                st.download_button("⬇ Excel", buf.getvalue(), "namespaces.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="ns_xl", use_container_width=True)
            df_ns_disp = df_ns_tab[["name", "total_cost", "cpu_cost", "ram_cost",
                                    "pv_cost", "cpu_efficiency", "ram_efficiency"]].copy()
            for c in ["total_cost", "cpu_cost", "ram_cost", "pv_cost"]:
                df_ns_disp[c] = df_ns_disp[c].map(lambda x: f"${x:,.2f}")
            df_ns_disp.columns = ["Namespace", "Total", "CPU", "RAM",
                                   "Storage", "CPU Eff %", "RAM Eff %"]
            st.dataframe(df_ns_disp, use_container_width=True, height=400)
        else:
            st.info("No namespace data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WORKLOADS
# ══════════════════════════════════════════════════════════════════════════════
with tab_workloads:
    df_wl_tab = df_wl[df_wl["name"] != "__idle__"].copy() if not df_wl.empty else pd.DataFrame()
    if not df_wl_tab.empty and "total_cost" in df_wl_tab.columns:
        df_wl_tab = df_wl_tab.sort_values("total_cost", ascending=False).reset_index(drop=True)
    wl_total  = df_wl_tab["total_cost"].sum() if not df_wl_tab.empty else 0.0

    wl_t1, wl_t2 = st.tabs(["📊 Top Workloads", "🔵 Cost vs Efficiency"])

    with wl_t1:
        if not df_wl_tab.empty:
            top_w = st.slider("Top N", 5, min(50, len(df_wl_tab)), 20, key="wl_n")
            df_pw = df_wl_tab.head(top_w)
            fig = go.Figure()
            for metric, color, label in [
                ("cpu_cost", COLORS["blue"], "CPU"), ("ram_cost", COLORS["teal"], "RAM"),
                ("pv_cost", "#7C3AED", "Storage"), ("network_cost", COLORS["amber"], "Network"),
            ]:
                if metric in df_pw.columns and df_pw[metric].sum() > 0:
                    fig.add_trace(go.Bar(
                        name=label, y=df_pw["name"], x=df_pw[metric], orientation="h",
                        marker_color=color,
                        hovertemplate=f"{label}: $%{{x:,.2f}}<extra>%{{y}}</extra>",
                    ))
            apply_plotly_theme(fig)
            fig.update_layout(
                barmode="stack", height=max(400, top_w * 26),
                yaxis=dict(autorange="reversed"), xaxis_title="Cost (USD)", yaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No workload data.")

    with wl_t2:
        if not df_wl_tab.empty and "efficiency" in df_wl_tab.columns:
            df_sc = df_wl_tab.head(40).copy()
            _max_cost = df_sc["total_cost"].max()
            df_sc["size"] = (df_sc["total_cost"] / _max_cost * 55 + 8).clip(8, 60)
            _med = df_wl_tab["total_cost"].median()
            df_sc["color"] = df_sc.apply(
                lambda r: COLORS["green"] if (r["efficiency"] >= 50 and r["total_cost"] >= _med)
                else COLORS["red"] if (r["efficiency"] < 50 and r["total_cost"] >= _med)
                else COLORS["blue"] if r["efficiency"] >= 50
                else COLORS["amber"], axis=1
            )
            fig2 = go.Figure(go.Scatter(
                x=df_sc["cpu_efficiency"], y=df_sc["ram_efficiency"],
                mode="markers+text",
                text=df_sc["name"].str.split("/").str[-1],
                textposition="top center",
                marker=dict(size=df_sc["size"], color=df_sc["color"],
                            opacity=0.8, line=dict(color="white", width=1)),
                customdata=df_sc["total_cost"].map(lambda v: f"${v:,.2f}"),
                hovertemplate="<b>%{text}</b><br>CPU: %{x:.1f}%<br>RAM: %{y:.1f}%<br>Cost: %{customdata}<extra></extra>",
            ))
            fig2.add_hline(y=50, line_dash="dash", line_color=COLORS["slate"], opacity=0.5)
            fig2.add_vline(x=50, line_dash="dash", line_color=COLORS["slate"], opacity=0.5)
            apply_plotly_theme(fig2)
            fig2.update_layout(
                height=480,
                xaxis=dict(title="CPU Efficiency %", range=[-5, 110]),
                yaxis=dict(title="RAM Efficiency %", range=[-5, 110]),
                showlegend=False,
            )
            st.caption("Bottom-left = over-provisioned & expensive — prime rightsizing targets.")
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No efficiency data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NODES
# ══════════════════════════════════════════════════════════════════════════════
with tab_nodes:
    nd_total   = df_nd["total_cost"].sum() if not df_nd.empty else 0.0
    utilized   = df_ns_active["total_cost"].sum() if not df_ns_active.empty else 0.0
    util_pct   = ((nd_total - idle_cost) / nd_total * 100) if nd_total > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Node Total Cost", f"${nd_total:,.2f}")
    c2.metric("Nodes", len(df_nd))
    c3.metric("Cluster Utilization", f"{util_pct:.1f}%")
    c4.metric("Idle Cost", f"${idle_cost:,.2f}", f"{idle_pct:.1f}%", delta_color="inverse")

    nd_t1, nd_t2 = st.tabs(["📊 Node Costs", "💤 Idle Analysis"])

    with nd_t1:
        if not df_nd.empty:
            col_bar, col_gauge = st.columns([2, 1])
            with col_bar:
                fig = go.Figure()
                for metric, color, label in [
                    ("cpu_cost", COLORS["blue"], "CPU"), ("ram_cost", COLORS["teal"], "RAM")
                ]:
                    fig.add_trace(go.Bar(
                        name=label, y=df_nd["node"], x=df_nd[metric], orientation="h",
                        marker_color=color,
                        hovertemplate=f"{label}: $%{{x:,.2f}}<extra>%{{y}}</extra>",
                    ))
                apply_plotly_theme(fig)
                fig.update_layout(
                    barmode="stack", height=max(280, len(df_nd) * 36),
                    yaxis=dict(autorange="reversed"), xaxis_title="Cost (USD)", yaxis_title=None,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

            with col_gauge:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=util_pct,
                    title={"text": "Utilization"},
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100], "ticksuffix": "%"},
                        "bar":  {"color": COLORS["blue"]},
                        "steps": [
                            {"range": [0, 50],  "color": COLORS["red"]},
                            {"range": [50, 75], "color": COLORS["amber"]},
                            {"range": [75, 100],"color": COLORS["green"]},
                        ],
                        "threshold": {"line": {"color": "white", "width": 3}, "value": 70},
                    },
                ))
                apply_plotly_theme(fig_g)
                fig_g.update_layout(height=280)
                st.plotly_chart(fig_g, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No node data. Check OpenCost connection.")

    with nd_t2:
        col_pie, col_tips = st.columns(2)
        with col_pie:
            fig3 = go.Figure(go.Pie(
                labels=["Utilized", "Idle"],
                values=[max(0, nd_total - idle_cost), idle_cost],
                hole=0.55,
                marker=dict(colors=[COLORS["green"], COLORS["red"]]),
                hovertemplate="%{label}<br><b>$%{value:,.2f}</b> (%{percent})<extra></extra>",
            ))
            apply_plotly_theme(fig3)
            fig3.update_layout(height=280, annotations=[dict(
                text=f"{idle_pct:.0f}%<br>idle", x=0.5, y=0.5,
                font_size=15, font_color=COLORS["red"], showarrow=False,
            )])
            st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tips:
            if idle_pct > 40:
                st.error(f"**{idle_pct:.0f}% idle** — critical over-provisioning.\n\n"
                         "- Reduce node pool min count\n- Enable Cluster Autoscaler\n"
                         "- Use Spot nodes for dev workloads")
            elif idle_pct > 20:
                st.warning(f"**{idle_pct:.0f}% idle** — moderate waste.\n\n"
                           "- Set resource requests on all pods\n"
                           "- Enable HPA for variable workloads\n"
                           "- Consider KEDA for event-driven scaling")
            else:
                st.success(f"**{idle_pct:.0f}% idle** — healthy utilization.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — LABELS / CHARGEBACK
# ══════════════════════════════════════════════════════════════════════════════
with tab_labels:
    st.subheader(f"Cost by label: `{label_key}`")
    st.caption("Change the label key in the sidebar. Use for team chargeback / showback reporting.")

    df_lbl_tab = df_lbl[df_lbl["name"] != "__idle__"].copy() if not df_lbl.empty else pd.DataFrame()
    if not df_lbl_tab.empty and "total_cost" in df_lbl_tab.columns:
        df_lbl_tab = df_lbl_tab.sort_values("total_cost", ascending=False).reset_index(drop=True)
    lbl_total  = df_lbl_tab["total_cost"].sum() if not df_lbl_tab.empty else 0.0

    if df_lbl_tab.empty:
        st.warning(f"No data for label `{label_key}`. Make sure your pods have this label set.")
    else:
        lbl_t1, lbl_t2 = st.tabs(["📊 Bar / Donut", "💳 Chargeback Report"])

        with lbl_t1:
            col_bar, col_pie = st.columns(2)
            with col_bar:
                fig = go.Figure(go.Bar(
                    x=df_lbl_tab["total_cost"], y=df_lbl_tab["name"], orientation="h",
                    marker=dict(color=list(range(len(df_lbl_tab))),
                                colorscale="Blues", showscale=False),
                    text=[f"${v:,.2f}  ({v/lbl_total*100:.1f}%)" for v in df_lbl_tab["total_cost"]],
                    textposition="outside",
                    hovertemplate=f"{label_key}: %{{y}}<br><b>$%{{x:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig)
                fig.update_layout(
                    height=max(300, len(df_lbl_tab) * 32),
                    yaxis=dict(autorange="reversed"), xaxis_title="Cost (USD)",
                    yaxis_title=None, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

            with col_pie:
                top_p = df_lbl_tab.head(10).copy()
                others = lbl_total - top_p["total_cost"].sum()
                if others > 0:
                    top_p = pd.concat([top_p, pd.DataFrame([{"name": "Other", "total_cost": others}])],
                                      ignore_index=True)
                fig2 = go.Figure(go.Pie(
                    labels=top_p["name"], values=top_p["total_cost"], hole=0.55,
                    marker=dict(colors=PALETTE[:len(top_p)]),
                    hovertemplate=f"{label_key}: %{{label}}<br><b>$%{{value:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig2)
                fig2.update_layout(height=300, annotations=[dict(
                    text=f"${lbl_total:,.0f}", x=0.5, y=0.5,
                    font_size=15, font_color=COLORS["text"], showarrow=False,
                )])
                st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

        with lbl_t2:
            df_cb = df_lbl_tab.copy()
            df_cb["Share %"] = (df_cb["total_cost"] / lbl_total * 100).round(2)
            totals_row = pd.DataFrame([{
                "name": "TOTAL", "cpu_cost": df_cb["cpu_cost"].sum(),
                "ram_cost": df_cb["ram_cost"].sum(), "total_cost": lbl_total, "Share %": 100.0,
            }])
            df_cb_final = pd.concat([df_cb, totals_row], ignore_index=True)
            for c in ["cpu_cost", "ram_cost", "total_cost"]:
                df_cb_final[c] = df_cb_final[c].map(lambda x: f"${x:,.2f}")
            df_cb_final.columns = [label_key if col == "name" else col for col in df_cb_final.columns]

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_cb_final.to_excel(w, index=False, sheet_name=f"Chargeback")
            col_h, col_xl = st.columns([8, 1])
            with col_h:
                st.subheader("Chargeback / Showback Report")
                st.caption(f"Label: `{label_key}` · Window: `{window}`")
            with col_xl:
                st.download_button(
                    "⬇ Excel", buf.getvalue(), f"chargeback_{label_key}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="cb_xl", use_container_width=True,
                )
            st.dataframe(df_cb_final, use_container_width=True, height=360)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — SAVINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_savings:
    cpu_target = st.slider("CPU efficiency target %", 40, 90, 65, key="sav_cpu")

    # Estimate from allocation if API recs not available
    df_over = pd.DataFrame()
    if not df_wl.empty and "efficiency" in df_wl.columns:
        df_over = (
            df_wl[(df_wl["efficiency"] < cpu_target) & (df_wl["name"] != "__idle__")]
            .copy()
            .sort_values("total_cost", ascending=False)
        )
        df_over["est_savings"] = df_over["total_cost"] * (1 - cpu_target / 100)

    api_savings = sum(
        (r.get("monthlyCPUSavings", 0) or 0) + (r.get("monthlyRAMSavings", 0) or 0)
        for r in req_recs if isinstance(r, dict)
    ) if req_recs else 0.0

    clus_savings = (clus_recs.get("monthlySavings", 0.0) or 0.0) if isinstance(clus_recs, dict) else 0.0
    est_savings  = df_over["est_savings"].sum() if not df_over.empty else 0.0
    total_savings = (api_savings or est_savings) + clus_savings

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Request Rightsizing", f"${api_savings or est_savings:,.2f}/mo")
    c2.metric("Cluster Rightsizing", f"${clus_savings:,.2f}/mo")
    c3.metric("Total Addressable",   f"${total_savings:,.2f}/mo")
    c4.metric("Over-provisioned", len(df_over) if not df_over.empty else 0)

    sav_t1, sav_t2, sav_t3 = st.tabs(["🔧 Request Rightsizing", "🖥️ Cluster", "🎯 Priority Matrix"])

    with sav_t1:
        if req_recs:
            rows_r = []
            for r in req_recs:
                if not isinstance(r, dict):
                    continue
                rows_r.append({
                    "namespace":  r.get("namespace", ""),
                    "controller": r.get("controllerName", ""),
                    "container":  r.get("containerName", ""),
                    "cpu_sav":    r.get("monthlyCPUSavings", 0) or 0,
                    "ram_sav":    r.get("monthlyRAMSavings", 0) or 0,
                    "total_sav":  (r.get("monthlyCPUSavings", 0) or 0) + (r.get("monthlyRAMSavings", 0) or 0),
                })
            df_rr = pd.DataFrame(rows_r).sort_values("total_sav", ascending=False)
            fig = go.Figure(go.Bar(
                x=df_rr["total_sav"].head(15),
                y=(df_rr["controller"] + "/" + df_rr["container"]).head(15),
                orientation="h", marker_color=COLORS["green"],
                hovertemplate="%{y}<br><b>$%{x:,.2f}/mo</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(height=380, yaxis=dict(autorange="reversed"),
                              xaxis_title="Monthly Savings", showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            for c in ["cpu_sav", "ram_sav", "total_sav"]:
                df_rr[c] = df_rr[c].map(lambda x: f"${x:,.2f}")
            df_rr.columns = ["Namespace", "Controller", "Container", "CPU/mo", "RAM/mo", "Total/mo"]
            st.dataframe(df_rr, use_container_width=True, height=300)
        elif not df_over.empty:
            st.caption("OpenCost requestSizingV2 not available — showing efficiency-based estimate.")
            fig = go.Figure(go.Bar(
                x=df_over["est_savings"].head(15),
                y=df_over["name"].head(15), orientation="h",
                marker_color=COLORS["amber"],
                hovertemplate="%{y}<br>Est. savings: <b>$%{x:,.2f}/mo</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(height=360, yaxis=dict(autorange="reversed"),
                              xaxis_title="Est. Monthly Savings", showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.success("No rightsizing recommendations — all containers are well-sized!")

    with sav_t2:
        if clus_recs and isinstance(clus_recs, dict) and clus_recs.get("recommendations"):
            for r in (clus_recs["recommendations"] if isinstance(clus_recs["recommendations"], list)
                      else [clus_recs["recommendations"]]):
                if not isinstance(r, dict):
                    continue
                pool = r.get("nodePoolName", "default")
                savings = r.get("monthlySavings", 0.0)
                with st.expander(f"Node pool: {pool}  —  save ${savings:,.2f}/mo"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Nodes",     r.get("currentNodeCount", "N/A"))
                    c2.metric("Recommended Nodes", r.get("recommendedNodeCount", "N/A"))
                    c3.metric("Monthly Savings",   f"${savings:,.2f}")
        else:
            st.info("Cluster sizing API not available or already optimal.")
            st.markdown("""
**Manual cluster rightsizing checklist:**
- Enable **Cluster Autoscaler** on the AKS node pool
- Target idle % < 20 — see Nodes tab for current idle
- For dev workloads: consider a **Spot node pool** (60-80% cheaper)

```bash
# Check live node utilization
kubectl top nodes

# Scale down if over-provisioned
az aks nodepool scale --name apppool \\
  --cluster-name finops-aks --resource-group rg-finops-prod-core --node-count 1
```
""")

    with sav_t3:
        if not df_over.empty:
            df_mat = df_over.nlargest(30, "est_savings").copy()
            df_mat["effort"] = df_mat["efficiency"].apply(
                lambda e: 1 if e < 20 else 2 if e < 50 else 3
            )
            effort_map = {1: "Low", 2: "Medium", 3: "High"}
            df_mat["effort_label"] = df_mat["effort"].map(effort_map)
            df_mat["size"] = (df_mat["est_savings"] / df_mat["est_savings"].max() * 50 + 10).clip(10, 60)
            df_mat["color"] = df_mat["effort"].map({
                1: COLORS["green"], 2: COLORS["amber"], 3: COLORS["red"]
            })
            fig = go.Figure(go.Scatter(
                x=df_mat["effort"], y=df_mat["est_savings"],
                mode="markers+text", text=df_mat["name"].str.split("/").str[-1],
                textposition="top center",
                marker=dict(size=df_mat["size"], color=df_mat["color"],
                            opacity=0.85, line=dict(color="white", width=1)),
                customdata=df_mat[["est_savings", "efficiency", "effort_label"]].values,
                hovertemplate="<b>%{text}</b><br>Savings: $%{customdata[0]:,.2f}/mo<br>"
                              "Efficiency: %{customdata[1]:.1f}%<br>Effort: %{customdata[2]}<extra></extra>",
            ))
            fig.add_hline(y=df_mat["est_savings"].median(), line_dash="dot",
                          line_color=COLORS["slate"],
                          annotation_text="Median", annotation_position="bottom right")
            apply_plotly_theme(fig)
            fig.update_layout(
                height=460,
                xaxis=dict(title="Effort", tickvals=[1, 2, 3],
                           ticktext=["Low", "Medium", "High"]),
                yaxis_title="Est. Monthly Savings (USD)",
                showlegend=False,
            )
            st.caption("Focus on low-effort, high-savings workloads (left-high area).")
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("Allocation data not available for priority matrix.")
