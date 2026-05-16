"""K8s Cost Dashboard — Namespace Cost Analysis."""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import allocation, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(page_title="Namespaces · K8s Cost", page_icon="📦", layout="wide")
apply_theme()

with st.sidebar:
    st.markdown("## 📦 Namespace Analysis")
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
    show_idle = st.toggle("Include __idle__", value=False)
    st.markdown("---")
    st.caption("K8s Cost Dashboard")

st.title("📦 Namespace Cost Breakdown")
st.caption(f"Window: **{window}** · Cost per namespace with efficiency and composition")

with st.spinner("Loading…"):
    raw = allocation(window=window, aggregate="namespace", accumulate=True)

rows = flatten_allocation(raw)
df = pd.DataFrame(rows) if rows else pd.DataFrame()

if df.empty:
    st.warning("No namespace data. Check OpenCost connection.")
    st.stop()

if not show_idle:
    df = df[df["name"] != "__idle__"]

df = df.sort_values("total_cost", ascending=False).reset_index(drop=True)

# ── KPIs ─────────────────────────────────────────────────────────────────────
total = df["total_cost"].sum()
ns_count = len(df)
top_ns = df.iloc[0]["name"] if not df.empty else "N/A"
top_cost = df.iloc[0]["total_cost"] if not df.empty else 0.0
avg_eff = df["efficiency"].mean() if "efficiency" in df.columns else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Namespace Spend", f"${total:,.2f}")
c2.metric("Namespaces", ns_count)
c3.metric("Top Namespace", top_ns, f"${top_cost:,.2f}")
c4.metric("Avg Efficiency", f"{avg_eff:.1f}%")

st.divider()

tab_bar, tab_trend, tab_comp, tab_table = st.tabs([
    "📊 Bar Chart", "📈 Daily Trend", "🧩 Composition", "📋 Full Table"
])

# ── Tab 1: Bar chart ──────────────────────────────────────────────────────────
with tab_bar:
    top_n = st.slider("Top N namespaces", 5, min(30, len(df)), 15, key="ns_topn")
    df_plot = df.head(top_n)

    col_chart, col_kpi = st.columns([3, 1])
    with col_chart:
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
            height=max(350, top_n * 30),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Cost (USD)",
            yaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col_kpi:
        st.markdown("**Cost by component**")
        for label, col in [("CPU", "cpu_cost"), ("RAM", "ram_cost"),
                            ("Storage", "pv_cost"), ("Network", "network_cost")]:
            if col in df.columns:
                v = df[col].sum()
                pct = v / total * 100 if total > 0 else 0
                st.metric(label, f"${v:,.2f}", f"{pct:.1f}%")

# ── Tab 2: Daily trend ────────────────────────────────────────────────────────
with tab_trend:
    st.caption("Cost per namespace per day (accumulated over the window)")
    with st.spinner("Loading daily breakdown…"):
        trend_raw = allocation(window=window, aggregate="namespace", accumulate=False, step="1d")

    trend_rows = flatten_allocation(trend_raw)
    df_trend = pd.DataFrame(trend_rows) if trend_rows else pd.DataFrame()

    if df_trend.empty or "start" not in df_trend.columns:
        st.info("Daily trend data not available for this window.")
    else:
        df_trend = df_trend[df_trend["name"] != "__idle__"]
        pivot = df_trend.pivot_table(
            index="start", columns="name", values="total_cost", aggfunc="sum", fill_value=0
        )
        top_ns_list = df.head(8)["name"].tolist()
        cols_to_show = [c for c in top_ns_list if c in pivot.columns]

        fig2 = go.Figure()
        for i, ns in enumerate(cols_to_show):
            fig2.add_trace(go.Scatter(
                x=pivot.index,
                y=pivot[ns],
                mode="lines+markers",
                name=ns,
                line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                hovertemplate=f"{ns}<br>%{{x}}<br><b>$%{{y:,.2f}}</b><extra></extra>",
            ))
        apply_plotly_theme(fig2)
        fig2.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Cost (USD)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

# ── Tab 3: Composition ────────────────────────────────────────────────────────
with tab_comp:
    ns_sel = st.selectbox("Select namespace", df["name"].tolist(), key="ns_comp_sel")
    ns_row = df[df["name"] == ns_sel].iloc[0] if not df[df["name"] == ns_sel].empty else None
    if ns_row is not None:
        comp = {
            "CPU":     ns_row.get("cpu_cost", 0),
            "RAM":     ns_row.get("ram_cost", 0),
            "Storage": ns_row.get("pv_cost", 0),
            "Network": ns_row.get("network_cost", 0),
            "GPU":     ns_row.get("gpu_cost", 0),
        }
        comp = {k: v for k, v in comp.items() if v > 0}
        col_pie, col_detail = st.columns(2)
        with col_pie:
            fig3 = go.Figure(go.Pie(
                labels=list(comp.keys()),
                values=list(comp.values()),
                hole=0.5,
                marker=dict(colors=PALETTE[:len(comp)]),
                hovertemplate="%{label}<br><b>$%{value:,.2f}</b> (%{percent})<extra></extra>",
            ))
            apply_plotly_theme(fig3)
            fig3.update_layout(height=320)
            st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)
        with col_detail:
            st.markdown(f"**{ns_sel}**")
            st.metric("Total Cost",      f"${ns_row.get('total_cost', 0):,.2f}")
            st.metric("CPU Efficiency",  f"{ns_row.get('cpu_efficiency', 0):.1f}%")
            st.metric("RAM Efficiency",  f"{ns_row.get('ram_efficiency', 0):.1f}%")
            overall = ns_row.get("efficiency", 0)
            grade = "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D"
            st.metric("Overall Efficiency", f"{overall:.1f}%  (Grade {grade})")

# ── Tab 4: Full table ─────────────────────────────────────────────────────────
with tab_table:
    display_cols = {
        "name": "Namespace", "total_cost": "Total Cost", "cpu_cost": "CPU",
        "ram_cost": "RAM", "pv_cost": "Storage", "network_cost": "Network",
        "cpu_efficiency": "CPU Eff %", "ram_efficiency": "RAM Eff %", "efficiency": "Overall Eff %",
    }
    avail = {k: v for k, v in display_cols.items() if k in df.columns}
    df_disp = df[list(avail.keys())].rename(columns=avail).copy()
    for col in ["Total Cost", "CPU", "RAM", "Storage", "Network"]:
        if col in df_disp.columns:
            df_disp[col] = df_disp[col].map(lambda x: f"${x:,.2f}")

    # Export
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Namespaces")
    col_h, col_csv, col_xl = st.columns([7, 1, 1])
    with col_h:
        st.subheader("All Namespaces")
    with col_csv:
        st.download_button("⬇ CSV", df.to_csv(index=False).encode(), "namespaces.csv", "text/csv",
                           use_container_width=True, key="ns_csv")
    with col_xl:
        st.download_button("⬇ Excel", buf.getvalue(), "namespaces.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, key="ns_xl")
    st.dataframe(df_disp, use_container_width=True, height=400)
