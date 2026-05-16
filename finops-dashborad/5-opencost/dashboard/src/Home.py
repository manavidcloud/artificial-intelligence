"""K8s Cost Dashboard — Home (Overview).

Powered by OpenCost REST API.
Deploy guide: finops-dashborad/5-opencost/README.md
"""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import allocation, assets, health, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(
    page_title="K8s Cost Dashboard",
    page_icon="☸️",
    layout="wide",
)
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☸️ K8s Cost Dashboard")
    st.markdown("---")
    window = st.selectbox(
        "Time window",
        ["1d", "7d", "30d", "lastweek", "lastmonth"],
        index=1,
        format_func=lambda w: {
            "1d": "Today", "7d": "Last 7 days", "30d": "Last 30 days",
            "lastweek": "Last week", "lastmonth": "Last month",
        }.get(w, w),
    )
    st.markdown("---")
    _online = health()
    if _online:
        st.success("OpenCost: Online")
    else:
        st.error("OpenCost: Offline")
        st.caption("Deploy OpenCost — see 5-opencost/README.md")
    st.markdown("---")
    st.caption("Powered by OpenCost · https://opencost.io")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("☸️ Kubernetes Cost Overview")
st.caption(
    f"Real-time pod / namespace / workload cost allocation · window: **{window}**"
)

if not _online:
    st.warning(
        "OpenCost is not reachable. Make sure it's deployed and the "
        "`OPENCOST_URL` environment variable points to the correct endpoint."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Fetch data
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading cost data…"):
    ns_raw   = allocation(window=window, aggregate="namespace",   accumulate=True)
    wl_raw   = allocation(window=window, aggregate="deployment",  accumulate=True)
    nd_raw   = assets(window=window, aggregate="node")

ns_rows = flatten_allocation(ns_raw)
wl_rows = flatten_allocation(wl_raw)

df_ns = pd.DataFrame(ns_rows) if ns_rows else pd.DataFrame()
df_wl = pd.DataFrame(wl_rows) if wl_rows else pd.DataFrame()

# Node asset rows
nd_rows = []
for bucket in (nd_raw or []):
    if not isinstance(bucket, dict):
        continue
    for name, props in bucket.items():
        if not isinstance(props, dict):
            continue
        nd_rows.append({
            "node": name,
            "cpu_cost":    props.get("cpuCost", 0.0),
            "ram_cost":    props.get("ramCost", 0.0),
            "total_cost":  props.get("totalCost", 0.0),
            "cpu_cores":   (props.get("cpuCores") or 0),
            "ram_gb":      round((props.get("ramBytes") or 0) / (1024**3), 1),
        })
df_nd = pd.DataFrame(nd_rows) if nd_rows else pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
total_k8s    = df_ns["total_cost"].sum() if not df_ns.empty else 0.0
ns_count     = len(df_ns[df_ns["name"] != "__idle__"]) if not df_ns.empty else 0
node_count   = len(df_nd) if not df_nd.empty else 0

# Idle cost
idle_cost = 0.0
if not df_ns.empty and "name" in df_ns.columns:
    idle_rows = df_ns[df_ns["name"] == "__idle__"]
    idle_cost = idle_rows["total_cost"].sum()

idle_pct = (idle_cost / total_k8s * 100) if total_k8s > 0 else 0.0

# Avg efficiency
avg_eff = df_ns["efficiency"].mean() if (not df_ns.empty and "efficiency" in df_ns.columns) else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total K8s Spend",   f"${total_k8s:,.2f}",  help=f"Window: {window}")
c2.metric("Namespaces",        ns_count,               help="Active namespaces")
c3.metric("Nodes",             node_count,             help="Cluster nodes")
c4.metric("Idle Cost",         f"${idle_cost:,.2f}",  f"{idle_pct:.1f}% of total",
          delta_color="inverse", help="Cost of unused capacity")
c5.metric("Avg Efficiency",    f"{avg_eff:.1f}%",      help="Mean CPU+RAM efficiency")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Main charts
# ─────────────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

# ── Namespace spend bar chart ─────────────────────────────────────────────────
with col_l:
    st.subheader("💰 Cost by Namespace")
    if not df_ns.empty:
        df_plot = df_ns[df_ns["name"] != "__idle__"].nlargest(15, "total_cost")
        fig = go.Figure(go.Bar(
            x=df_plot["total_cost"],
            y=df_plot["name"],
            orientation="h",
            marker=dict(
                color=df_plot["total_cost"],
                colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                showscale=False,
            ),
            text=[f"${v:,.2f}" for v in df_plot["total_cost"]],
            textposition="outside",
            hovertemplate="%{y}<br><b>$%{x:,.2f}</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(
            height=400,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Cost (USD)",
            yaxis_title=None,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No namespace data available.")

# ── Cost composition donut ────────────────────────────────────────────────────
with col_r:
    st.subheader("📊 Cost Composition")
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
            labels=list(comp.keys()),
            values=list(comp.values()),
            hole=0.55,
            marker=dict(colors=PALETTE[:len(comp)]),
            textinfo="label+percent",
            hovertemplate="%{label}<br><b>$%{value:,.2f}</b> (%{percent})<extra></extra>",
        ))
        apply_plotly_theme(fig2)
        fig2.update_layout(
            height=400,
            annotations=[dict(
                text=f"${total_k8s:,.0f}",
                x=0.5, y=0.5, font_size=18, font_color=COLORS["text"],
                showarrow=False,
            )],
        )
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No composition data.")

st.divider()

# ── Efficiency heatmap (namespace × metric) ───────────────────────────────────
st.subheader("⚡ Namespace Efficiency Heatmap")
st.caption("CPU and RAM efficiency = actual usage / requested resources. Low values = over-provisioned.")
if not df_ns.empty and "cpu_efficiency" in df_ns.columns:
    df_eff = (
        df_ns[df_ns["name"] != "__idle__"]
        .nlargest(20, "total_cost")[["name", "cpu_efficiency", "ram_efficiency", "efficiency", "total_cost"]]
        .copy()
    )
    df_eff = df_eff.sort_values("total_cost", ascending=False)

    def _eff_color(val: float) -> str:
        if val >= 80:
            return "background-color: #15803d; color: white"
        if val >= 50:
            return "background-color: #d97706; color: white"
        return "background-color: #dc2626; color: white"

    df_eff_disp = df_eff.rename(columns={
        "name": "Namespace", "cpu_efficiency": "CPU Eff %",
        "ram_efficiency": "RAM Eff %", "efficiency": "Overall Eff %",
        "total_cost": "Total Cost",
    })
    df_eff_disp["Total Cost"] = df_eff_disp["Total Cost"].map(lambda x: f"${x:,.2f}")
    st.dataframe(
        df_eff_disp.style
        .applymap(_eff_color, subset=["CPU Eff %", "RAM Eff %", "Overall Eff %"]),
        use_container_width=True,
        height=320,
    )
else:
    st.info("Efficiency data not available.")

st.divider()

# ── Top workloads table ───────────────────────────────────────────────────────
st.subheader("🏆 Top 10 Workloads by Cost")
if not df_wl.empty:
    df_top = (
        df_wl[df_wl["name"] != "__idle__"]
        .nlargest(10, "total_cost")[["name", "cpu_cost", "ram_cost", "total_cost", "efficiency"]]
        .copy()
    )
    df_top["Share"] = (df_top["total_cost"] / df_top["total_cost"].sum() * 100).map(lambda x: f"{x:.1f}%")
    df_top_disp = df_top.rename(columns={
        "name": "Workload", "cpu_cost": "CPU", "ram_cost": "RAM",
        "total_cost": "Total", "efficiency": "Eff %",
    })
    for c in ["CPU", "RAM", "Total"]:
        df_top_disp[c] = df_top_disp[c].map(lambda x: f"${x:,.2f}")
    st.dataframe(df_top_disp, use_container_width=True, height=320)

    # Download
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_wl.to_excel(w, index=False, sheet_name="Workloads")
    st.download_button(
        "⬇ Export workloads (Excel)",
        data=buf.getvalue(),
        file_name="k8s_workloads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("No workload data. Run a sync or check OpenCost connection.")
