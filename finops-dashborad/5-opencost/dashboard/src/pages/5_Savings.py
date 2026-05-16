"""K8s Cost Dashboard — Savings & Rightsizing Recommendations."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import savings_request_sizing, savings_cluster_sizing, allocation, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(page_title="Savings · K8s Cost", page_icon="💡", layout="wide")
apply_theme()

with st.sidebar:
    st.markdown("## 💡 Savings & Rightsizing")
    st.markdown("---")
    window = st.selectbox(
        "Analysis window",
        ["7d", "30d"],
        index=1,
        format_func=lambda w: {"7d": "Last 7 days", "30d": "Last 30 days"}.get(w, w),
        help="Efficiency data window for rightsizing analysis.",
    )
    cpu_target   = st.slider("CPU target utilization %",   40, 90, 65)
    ram_target   = st.slider("RAM target utilization %",   40, 90, 65)
    st.markdown("---")
    st.caption("K8s Cost Dashboard")

st.title("💡 Savings & Rightsizing")
st.caption(
    "Container request rightsizing + cluster node rightsizing recommendations "
    "powered by OpenCost savings APIs."
)

# ─────────────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading savings data…"):
    req_savings   = savings_request_sizing()
    clus_savings  = savings_cluster_sizing()
    alloc_raw     = allocation(window=window, aggregate="deployment", accumulate=True)

alloc_rows = flatten_allocation(alloc_raw)
df_alloc   = pd.DataFrame(alloc_rows) if alloc_rows else pd.DataFrame()

# ── KPIs ─────────────────────────────────────────────────────────────────────
total_alloc = df_alloc["total_cost"].sum() if not df_alloc.empty else 0.0

# Estimate savings from over-provisioned workloads
over_prov_cost = 0.0
if not df_alloc.empty and "efficiency" in df_alloc.columns:
    df_over = df_alloc[(df_alloc["efficiency"] < cpu_target) & (df_alloc["name"] != "__idle__")]
    over_prov_cost = df_over["total_cost"].sum() * (1 - cpu_target / 100)

cluster_savings_amt = 0.0
if clus_savings and isinstance(clus_savings, dict):
    cluster_savings_amt = clus_savings.get("monthlySavings", 0.0) or 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Est. Request Rightsizing Savings", f"${over_prov_cost:,.2f}/mo",
          help="From reducing CPU/RAM requests on over-provisioned containers")
c2.metric("Est. Cluster Rightsizing Savings", f"${cluster_savings_amt:,.2f}/mo",
          help="From right-sizing node pool capacity")
c3.metric("Total Addressable Savings",
          f"${over_prov_cost + cluster_savings_amt:,.2f}/mo")
c4.metric("Over-provisioned Workloads",
          len(df_alloc[df_alloc["efficiency"] < cpu_target]) if not df_alloc.empty else 0,
          help=f"Workloads below {cpu_target}% efficiency target")

st.divider()

tab_req, tab_cluster, tab_priority = st.tabs([
    "🔧 Request Rightsizing", "🖥️ Cluster Rightsizing", "🎯 Priority Matrix"
])

# ── Tab 1: Request rightsizing ────────────────────────────────────────────────
with tab_req:
    st.subheader("Container Request Rightsizing")
    st.caption(
        "Recommendations to reduce CPU/RAM resource requests to match actual usage. "
        f"Target utilization: CPU {cpu_target}%, RAM {ram_target}%."
    )

    if req_savings and isinstance(req_savings, dict):
        recs = req_savings.get("recommendations", [])
        if recs:
            rows_r = []
            for r in recs:
                if not isinstance(r, dict):
                    continue
                rows_r.append({
                    "namespace":  r.get("namespace", ""),
                    "controller": r.get("controllerName", ""),
                    "container":  r.get("containerName", ""),
                    "current_cpu_req":  r.get("currentCPURequest", 0),
                    "recommended_cpu":  r.get("recommendedCPU", 0),
                    "current_ram_req":  r.get("currentRAMRequest", 0),
                    "recommended_ram":  r.get("recommendedRAM", 0),
                    "cpu_savings":  r.get("monthlyCPUSavings", 0),
                    "ram_savings":  r.get("monthlyRAMSavings", 0),
                    "total_savings": r.get("monthlyCPUSavings", 0) + r.get("monthlyRAMSavings", 0),
                })
            df_req = pd.DataFrame(rows_r).sort_values("total_savings", ascending=False)

            col_chart, col_table = st.columns([1, 2])
            with col_chart:
                top_r = df_req.head(10)
                fig = go.Figure(go.Bar(
                    x=top_r["total_savings"],
                    y=top_r["controller"] + "/" + top_r["container"],
                    orientation="h",
                    marker_color=COLORS["green"],
                    hovertemplate="%{y}<br><b>$%{x:,.2f}/mo savings</b><extra></extra>",
                ))
                apply_plotly_theme(fig)
                fig.update_layout(
                    height=320, yaxis=dict(autorange="reversed"),
                    xaxis_title="Monthly Savings (USD)", yaxis_title=None, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

            with col_table:
                df_req_disp = df_req[["namespace", "controller", "container",
                                      "cpu_savings", "ram_savings", "total_savings"]].head(20).copy()
                df_req_disp["cpu_savings"]   = df_req_disp["cpu_savings"].map(lambda x: f"${x:,.2f}")
                df_req_disp["ram_savings"]   = df_req_disp["ram_savings"].map(lambda x: f"${x:,.2f}")
                df_req_disp["total_savings"] = df_req_disp["total_savings"].map(lambda x: f"${x:,.2f}")
                df_req_disp.columns = ["Namespace", "Controller", "Container",
                                       "CPU Savings/mo", "RAM Savings/mo", "Total/mo"]
                st.dataframe(df_req_disp, use_container_width=True, height=300)
        else:
            st.success("No rightsizing recommendations — all containers are well-sized!")
    else:
        # Fallback: derive from allocation data manually
        st.info("OpenCost requestSizingV2 API not available. Showing efficiency-based analysis instead.")
        if not df_alloc.empty and "efficiency" in df_alloc.columns:
            df_over = (
                df_alloc[(df_alloc["efficiency"] < cpu_target) & (df_alloc["name"] != "__idle__")]
                .copy()
                .sort_values("total_cost", ascending=False)
            )
            df_over["est_savings"] = df_over["total_cost"] * (1 - cpu_target / 100)

            fig2 = go.Figure(go.Bar(
                x=df_over["est_savings"].head(15),
                y=df_over["name"].head(15),
                orientation="h",
                marker_color=COLORS["amber"],
                hovertemplate="%{y}<br>Est. savings: <b>$%{x:,.2f}/mo</b><extra></extra>",
            ))
            apply_plotly_theme(fig2)
            fig2.update_layout(
                height=360, yaxis=dict(autorange="reversed"),
                xaxis_title="Estimated Monthly Savings", showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

            st.caption(f"Showing top over-provisioned workloads (efficiency < {cpu_target}%)")
            df_over_disp = df_over[["name", "efficiency", "total_cost", "est_savings"]].head(20).copy()
            df_over_disp["total_cost"] = df_over_disp["total_cost"].map(lambda x: f"${x:,.2f}")
            df_over_disp["est_savings"] = df_over_disp["est_savings"].map(lambda x: f"${x:,.2f}")
            df_over_disp["efficiency"] = df_over_disp["efficiency"].map(lambda x: f"{x:.1f}%")
            df_over_disp.columns = ["Workload", "Efficiency", "Current Cost", "Est. Savings/mo"]
            st.dataframe(df_over_disp, use_container_width=True, height=300)

# ── Tab 2: Cluster rightsizing ────────────────────────────────────────────────
with tab_cluster:
    st.subheader("Node Pool Rightsizing")
    if clus_savings and isinstance(clus_savings, dict):
        recs = clus_savings.get("recommendations", [])
        if recs:
            for r in (recs if isinstance(recs, list) else [recs]):
                if not isinstance(r, dict):
                    continue
                current = r.get("currentNodeCount", "N/A")
                recommended = r.get("recommendedNodeCount", "N/A")
                savings = r.get("monthlySavings", 0.0)
                pool = r.get("nodePoolName", "default")

                with st.expander(f"Node pool: {pool}  —  save ${savings:,.2f}/month"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Nodes",     current)
                    c2.metric("Recommended Nodes", recommended)
                    c3.metric("Monthly Savings",   f"${savings:,.2f}")
                    if r.get("recommendedNodeType"):
                        st.info(f"Recommended node type: **{r['recommendedNodeType']}**")
        else:
            st.success("Node pool is already right-sized for current workloads.")
    else:
        st.info(
            "Cluster rightsizing API not available. "
            "This requires OpenCost v1.107+ with cluster sizing enabled."
        )
        st.markdown("""
**Manual cluster rightsizing checklist:**

- Enable **Cluster Autoscaler** — automatically removes underutilized nodes
- Check node utilization in the **Nodes** page
- For idle > 40%: reduce min node count in AKS node pool
- For dev workloads: consider **Spot node pool** (60-80% cheaper)
- Use `kubectl top nodes` to see live CPU/mem usage

```bash
# Check current node utilization
kubectl top nodes

# Scale down a node pool
az aks nodepool scale \
  --name apppool \
  --cluster-name finops-aks \
  --resource-group rg-finops-prod-core \
  --node-count 1
```
""")

# ── Tab 3: Priority Matrix ────────────────────────────────────────────────────
with tab_priority:
    st.subheader("🎯 Savings Priority Matrix")
    st.caption("X = implementation effort (Low → High), Y = estimated monthly savings. Focus top-left.")

    if not df_alloc.empty:
        df_mat = df_alloc[df_alloc["name"] != "__idle__"].copy()
        df_mat["est_savings"] = df_mat.apply(
            lambda r: r["total_cost"] * max(0, 1 - cpu_target / 100)
            if r.get("efficiency", 100) < cpu_target else 0, axis=1
        )
        df_mat = df_mat[df_mat["est_savings"] > 0].nlargest(30, "est_savings")
        df_mat["effort"] = df_mat["efficiency"].apply(
            lambda e: 1 if e < 20 else 2 if e < 50 else 3
        )
        effort_labels = {1: "Low", 2: "Medium", 3: "High"}
        df_mat["effort_label"] = df_mat["effort"].map(effort_labels)
        df_mat["size"] = (df_mat["est_savings"] / df_mat["est_savings"].max() * 50 + 10).clip(10, 60)
        df_mat["color"] = df_mat.apply(
            lambda r: COLORS["green"] if r["effort"] == 1
            else COLORS["amber"] if r["effort"] == 2
            else COLORS["red"], axis=1
        )

        fig = go.Figure(go.Scatter(
            x=df_mat["effort"],
            y=df_mat["est_savings"],
            mode="markers+text",
            text=df_mat["name"].str.split("/").str[-1],
            textposition="top center",
            marker=dict(
                size=df_mat["size"], color=df_mat["color"],
                opacity=0.85, line=dict(color="white", width=1),
            ),
            customdata=df_mat[["est_savings", "efficiency", "effort_label"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Savings: $%{customdata[0]:,.2f}/mo<br>"
                "Efficiency: %{customdata[1]:.1f}%<br>"
                "Effort: %{customdata[2]}<extra></extra>"
            ),
        ))
        fig.add_hline(
            y=df_mat["est_savings"].median(),
            line_dash="dot", line_color=COLORS["slate"],
            annotation_text="Median savings", annotation_position="bottom right",
        )
        apply_plotly_theme(fig)
        fig.update_layout(
            height=480,
            xaxis=dict(
                title="Implementation Effort",
                tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"],
            ),
            yaxis_title="Est. Monthly Savings (USD)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        col1, col2 = st.columns(2)
        with col1:
            quick_wins = df_mat[df_mat["effort"] == 1]
            st.metric("Quick Wins (Low effort)", len(quick_wins),
                      f"${quick_wins['est_savings'].sum():,.2f}/mo")
        with col2:
            high_impact = df_mat[df_mat["est_savings"] >= df_mat["est_savings"].median()]
            st.metric("High Impact (above median)", len(high_impact),
                      f"${high_impact['est_savings'].sum():,.2f}/mo")
    else:
        st.info("Allocation data not available. Check OpenCost connection.")
