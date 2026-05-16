"""K8s Cost Dashboard — Workload Cost Analysis (Deployments / DaemonSets / StatefulSets)."""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import allocation, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(page_title="Workloads · K8s Cost", page_icon="🚀", layout="wide")
apply_theme()

with st.sidebar:
    st.markdown("## 🚀 Workloads")
    st.markdown("---")
    window = st.selectbox(
        "Time window",
        ["1d", "7d", "30d", "lastweek", "lastmonth"],
        index=2,
        format_func=lambda w: {
            "1d": "Today", "7d": "Last 7 days", "30d": "Last 30 days",
            "lastweek": "Last week", "lastmonth": "Last month",
        }.get(w, w),
    )
    aggregate_by = st.radio("Aggregate by", ["deployment", "pod", "controller"], index=0)
    st.markdown("---")
    st.caption("K8s Cost Dashboard")

st.title("🚀 Workload Cost Analysis")
st.caption(f"Window: **{window}** · Aggregated by: **{aggregate_by}**")

with st.spinner("Loading workload data…"):
    raw = allocation(window=window, aggregate=aggregate_by, accumulate=True)

rows = flatten_allocation(raw)
df = pd.DataFrame(rows) if rows else pd.DataFrame()

if df.empty:
    st.info("No workload data. OpenCost may need a few minutes to collect metrics.")
    st.stop()

df = df[df["name"] != "__idle__"].sort_values("total_cost", ascending=False).reset_index(drop=True)
total = df["total_cost"].sum()

# ── KPIs ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Workload Cost", f"${total:,.2f}")
c2.metric("Workloads", len(df))
c3.metric("Top Workload", df.iloc[0]["name"] if not df.empty else "N/A",
          f"${df.iloc[0]['total_cost']:,.2f}" if not df.empty else "")
avg_eff = df["efficiency"].mean() if "efficiency" in df.columns else 0.0
c4.metric("Avg Efficiency", f"{avg_eff:.1f}%")

st.divider()

tab_chart, tab_scatter, tab_table = st.tabs([
    "📊 Top Workloads", "🔵 Cost vs Efficiency", "📋 Full Table"
])

# ── Tab 1: Horizontal bar ─────────────────────────────────────────────────────
with tab_chart:
    top_n = st.slider("Top N", 5, min(50, len(df)), 20, key="wl_topn")
    df_plot = df.head(top_n)
    df_plot["share_pct"] = (df_plot["total_cost"] / total * 100).round(1)

    fig = go.Figure()
    for metric, color, label in [
        ("cpu_cost",  COLORS["blue"],   "CPU"),
        ("ram_cost",  COLORS["teal"],   "RAM"),
        ("pv_cost",   COLORS["purple"], "Storage"),
        ("network_cost", COLORS["amber"], "Network"),
    ]:
        if metric in df_plot.columns and df_plot[metric].sum() > 0:
            fig.add_trace(go.Bar(
                name=label,
                y=df_plot["name"],
                x=df_plot[metric],
                orientation="h",
                marker_color=color,
                hovertemplate=f"{label}: $%{{x:,.2f}}<extra>%{{y}}</extra>",
            ))
    apply_plotly_theme(fig)
    fig.update_layout(
        barmode="stack",
        height=max(400, top_n * 26),
        yaxis=dict(autorange="reversed"),
        xaxis_title="Cost (USD)",
        yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    # Cumulative share (Pareto)
    st.subheader("Pareto — Cumulative Cost Share")
    df_pareto = df.head(top_n).copy()
    df_pareto["cumulative_pct"] = (
        df_pareto["total_cost"].cumsum() / total * 100
    )
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(
        x=df_pareto["name"], y=df_pareto["total_cost"],
        name="Cost", marker_color=COLORS["blue"],
        hovertemplate="%{x}<br><b>$%{y:,.2f}</b><extra></extra>",
    ))
    fig_p.add_trace(go.Scatter(
        x=df_pareto["name"], y=df_pareto["cumulative_pct"],
        name="Cumulative %", mode="lines+markers",
        line=dict(color=COLORS["amber"], width=2),
        yaxis="y2",
        hovertemplate="%{x}<br><b>%{y:.1f}%</b><extra></extra>",
    ))
    apply_plotly_theme(fig_p)
    fig_p.update_layout(
        height=320,
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Cost (USD)"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right",
                    range=[0, 110], ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_p, use_container_width=True, config=PLOTLY_CONFIG)

# ── Tab 2: Bubble — Cost vs Efficiency ───────────────────────────────────────
with tab_scatter:
    st.caption(
        "Bubble size = total cost. X = CPU efficiency, Y = RAM efficiency. "
        "Bottom-left = over-provisioned & expensive (prime rightsizing targets)."
    )
    df_sc = df.head(50).copy()
    df_sc["size"] = (df_sc["total_cost"] / df_sc["total_cost"].max() * 60 + 8).clip(8, 70)

    def _quad_color(row: pd.Series) -> str:
        high_eff = row["cpu_efficiency"] >= 50 and row["ram_efficiency"] >= 50
        high_cost = row["total_cost"] >= df_sc["total_cost"].median()
        if high_eff and high_cost:
            return COLORS["green"]
        if not high_eff and high_cost:
            return COLORS["red"]
        if high_eff:
            return COLORS["blue"]
        return COLORS["amber"]

    df_sc["color"] = df_sc.apply(_quad_color, axis=1)

    fig2 = go.Figure(go.Scatter(
        x=df_sc["cpu_efficiency"],
        y=df_sc["ram_efficiency"],
        mode="markers+text",
        text=df_sc["name"].str.split("/").str[-1],
        textposition="top center",
        marker=dict(
            size=df_sc["size"],
            color=df_sc["color"],
            opacity=0.8,
            line=dict(color="white", width=1),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "CPU Eff: %{x:.1f}%<br>"
            "RAM Eff: %{y:.1f}%<br>"
            "Cost: $" + df_sc["total_cost"].map(lambda v: f"{v:,.2f}").values.tolist()[0]
            + "<extra></extra>"
        ),
        customdata=df_sc["total_cost"].map(lambda v: f"${v:,.2f}"),
        hovertemplate="<b>%{text}</b><br>CPU: %{x:.1f}%<br>RAM: %{y:.1f}%<br>Cost: %{customdata}<extra></extra>",
    ))
    # Quadrant lines
    fig2.add_hline(y=50, line_dash="dash", line_color=COLORS["slate"], opacity=0.6)
    fig2.add_vline(x=50, line_dash="dash", line_color=COLORS["slate"], opacity=0.6)
    # Quadrant labels
    for (x, y, txt) in [
        (20, 80, "Over-provisioned CPU"), (80, 20, "Over-provisioned RAM"),
        (80, 80, "Efficient"), (20, 20, "Over-provisioned both"),
    ]:
        fig2.add_annotation(x=x, y=y, text=txt, showarrow=False,
                            font=dict(size=10, color=COLORS["muted"]))
    apply_plotly_theme(fig2)
    fig2.update_layout(
        height=500,
        xaxis=dict(title="CPU Efficiency %", range=[-5, 110]),
        yaxis=dict(title="RAM Efficiency %", range=[-5, 110]),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

# ── Tab 3: Full table ─────────────────────────────────────────────────────────
with tab_table:
    df_disp = df[["name", "total_cost", "cpu_cost", "ram_cost",
                  "pv_cost", "cpu_efficiency", "ram_efficiency", "efficiency"]].copy()
    df_disp["share"] = (df_disp["total_cost"] / total * 100).map(lambda x: f"{x:.1f}%")
    for c in ["total_cost", "cpu_cost", "ram_cost", "pv_cost"]:
        df_disp[c] = df_disp[c].map(lambda x: f"${x:,.2f}")
    df_disp = df_disp.rename(columns={
        "name": "Workload", "total_cost": "Total", "cpu_cost": "CPU", "ram_cost": "RAM",
        "pv_cost": "Storage", "cpu_efficiency": "CPU Eff %",
        "ram_efficiency": "RAM Eff %", "efficiency": "Overall Eff %", "share": "Share",
    })

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Workloads")
    col_h, col_csv, col_xl = st.columns([7, 1, 1])
    with col_h:
        st.subheader(f"All {aggregate_by.title()}s")
    with col_csv:
        st.download_button("⬇ CSV", df.to_csv(index=False).encode(),
                           "workloads.csv", "text/csv", use_container_width=True, key="wl_csv")
    with col_xl:
        st.download_button("⬇ Excel", buf.getvalue(), "workloads.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, key="wl_xl")
    st.dataframe(df_disp, use_container_width=True, height=420)
