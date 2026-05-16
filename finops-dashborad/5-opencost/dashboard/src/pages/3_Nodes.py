"""K8s Cost Dashboard — Node Cost & Utilization."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import assets, allocation, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(page_title="Nodes · K8s Cost", page_icon="🖥️", layout="wide")
apply_theme()

with st.sidebar:
    st.markdown("## 🖥️ Nodes")
    st.markdown("---")
    window = st.selectbox(
        "Time window",
        ["1d", "7d", "30d"],
        index=1,
        format_func=lambda w: {"1d": "Today", "7d": "Last 7 days", "30d": "Last 30 days"}.get(w, w),
    )
    st.markdown("---")
    st.caption("K8s Cost Dashboard")

st.title("🖥️ Node Cost & Utilization")
st.caption(f"Window: **{window}** · Node-level cost breakdown and idle analysis")

with st.spinner("Loading node data…"):
    nd_raw = assets(window=window, aggregate="node")
    ns_raw = allocation(window=window, aggregate="namespace", accumulate=True)

# ── Parse node assets ─────────────────────────────────────────────────────────
nd_rows = []
for bucket in (nd_raw or []):
    if not isinstance(bucket, dict):
        continue
    for name, props in bucket.items():
        if not isinstance(props, dict):
            continue
        nd_rows.append({
            "node":       name,
            "cpu_cost":   props.get("cpuCost", 0.0),
            "ram_cost":   props.get("ramCost", 0.0),
            "total_cost": props.get("totalCost", 0.0),
            "cpu_cores":  props.get("cpuCores") or 0,
            "ram_gb":     round((props.get("ramBytes") or 0) / (1024 ** 3), 1),
            "provider_id": props.get("providerID") or "",
        })

df_nd = pd.DataFrame(nd_rows) if nd_rows else pd.DataFrame()

# Pod cost from namespace allocation (minus idle = utilized)
ns_rows = flatten_allocation(ns_raw)
df_ns = pd.DataFrame(ns_rows) if ns_rows else pd.DataFrame()
utilized = df_ns[df_ns["name"] != "__idle__"]["total_cost"].sum() if not df_ns.empty else 0.0
idle_total = df_ns[df_ns["name"] == "__idle__"]["total_cost"].sum() if not df_ns.empty else 0.0
total_nd = df_nd["total_cost"].sum() if not df_nd.empty else 0.0

if df_nd.empty:
    st.info("No node data. OpenCost may need a few minutes to collect metrics.")
    st.stop()

# ── KPIs ─────────────────────────────────────────────────────────────────────
idle_pct = (idle_total / total_nd * 100) if total_nd > 0 else 0.0
util_pct = 100 - idle_pct
total_cpu = df_nd["cpu_cores"].sum()
total_ram = df_nd["ram_gb"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Node Cost", f"${total_nd:,.2f}")
c2.metric("Nodes", len(df_nd))
c3.metric("Total vCPUs", f"{total_cpu:,.0f}")
c4.metric("Total RAM", f"{total_ram:,.0f} GB")
c5.metric("Utilization", f"{util_pct:.1f}%", f"${idle_total:,.2f} idle",
          delta_color="normal")

st.divider()

tab_overview, tab_idle, tab_table = st.tabs([
    "📊 Node Costs", "💤 Idle Analysis", "📋 Full Table"
])

# ── Tab 1: Node cost bars ─────────────────────────────────────────────────────
with tab_overview:
    df_nd_sorted = df_nd.sort_values("total_cost", ascending=False)

    col_bar, col_gauge = st.columns([2, 1])
    with col_bar:
        fig = go.Figure()
        for metric, color, label in [
            ("cpu_cost", COLORS["blue"],   "CPU"),
            ("ram_cost", COLORS["teal"],   "RAM"),
        ]:
            if metric in df_nd_sorted.columns:
                fig.add_trace(go.Bar(
                    name=label, y=df_nd_sorted["node"], x=df_nd_sorted[metric],
                    orientation="h", marker_color=color,
                    hovertemplate=f"{label}: $%{{x:,.2f}}<extra>%{{y}}</extra>",
                ))
        apply_plotly_theme(fig)
        fig.update_layout(
            barmode="stack",
            height=max(300, len(df_nd_sorted) * 36),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Cost (USD)", yaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col_gauge:
        # Utilization gauge
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=util_pct,
            delta={"reference": 70, "suffix": "%"},
            title={"text": "Cluster Utilization"},
            gauge={
                "axis": {"range": [0, 100], "ticksuffix": "%"},
                "bar":  {"color": COLORS["blue"]},
                "steps": [
                    {"range": [0,  50],  "color": COLORS["red"]},
                    {"range": [50, 75],  "color": COLORS["amber"]},
                    {"range": [75, 100], "color": COLORS["green"]},
                ],
                "threshold": {"line": {"color": "white", "width": 3}, "value": 70},
            },
            number={"suffix": "%"},
        ))
        apply_plotly_theme(fig_g)
        fig_g.update_layout(height=300, paper_bgcolor=COLORS["card"])
        st.plotly_chart(fig_g, use_container_width=True, config=PLOTLY_CONFIG)

        st.metric("Utilized", f"${utilized:,.2f}", f"{util_pct:.1f}%")
        st.metric("Idle",     f"${idle_total:,.2f}", f"{idle_pct:.1f}%", delta_color="inverse")

# ── Tab 2: Idle analysis ──────────────────────────────────────────────────────
with tab_idle:
    st.subheader("💤 Idle Cost Breakdown")
    st.caption(
        "Idle cost = node cost × (1 − pod_requests / node_capacity). "
        "High idle % means over-provisioned nodes — consider rightsizing or spot instances."
    )

    col_l, col_r = st.columns(2)
    with col_l:
        fig_pie = go.Figure(go.Pie(
            labels=["Utilized", "Idle"],
            values=[utilized, idle_total],
            hole=0.5,
            marker=dict(colors=[COLORS["green"], COLORS["red"]]),
            hovertemplate="%{label}<br><b>$%{value:,.2f}</b> (%{percent})<extra></extra>",
        ))
        apply_plotly_theme(fig_pie)
        fig_pie.update_layout(
            height=300,
            annotations=[dict(
                text=f"{idle_pct:.0f}%<br>idle",
                x=0.5, y=0.5, font_size=16, font_color=COLORS["red"],
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_r:
        st.markdown("#### Rightsizing Suggestions")
        if idle_pct > 40:
            st.error(
                f"**{idle_pct:.0f}% idle** — critical. Consider:\n"
                "- Reducing node count or VM size\n"
                "- Using Cluster Autoscaler\n"
                "- Switching to Spot/Preemptible nodes for dev workloads"
            )
        elif idle_pct > 20:
            st.warning(
                f"**{idle_pct:.0f}% idle** — moderate. Consider:\n"
                "- Setting resource requests/limits on all pods\n"
                "- Enabling KEDA for event-driven autoscaling\n"
                "- Using HPA for variable workloads"
            )
        else:
            st.success(
                f"**{idle_pct:.0f}% idle** — good utilization. "
                "Monitor for spikes and ensure Cluster Autoscaler is enabled."
            )

        monthly_idle = idle_total * (30 if "1d" in window else 1)
        st.metric("Est. Monthly Idle Cost", f"${monthly_idle:,.2f}",
                  help="Approximate monthly waste from idle capacity")

# ── Tab 3: Full table ─────────────────────────────────────────────────────────
with tab_table:
    df_disp = df_nd.copy()
    df_disp["cpu_cost"]   = df_disp["cpu_cost"].map(lambda x: f"${x:,.2f}")
    df_disp["ram_cost"]   = df_disp["ram_cost"].map(lambda x: f"${x:,.2f}")
    df_disp["total_cost"] = df_disp["total_cost"].map(lambda x: f"${x:,.2f}")
    df_disp = df_disp.rename(columns={
        "node": "Node", "cpu_cost": "CPU Cost", "ram_cost": "RAM Cost",
        "total_cost": "Total Cost", "cpu_cores": "vCPUs", "ram_gb": "RAM (GB)",
        "provider_id": "Provider ID",
    })
    st.subheader("All Nodes")
    st.dataframe(df_disp, use_container_width=True, height=380)
    st.download_button(
        "⬇ CSV", df_nd.to_csv(index=False).encode(), "nodes.csv", "text/csv", key="nd_csv"
    )
