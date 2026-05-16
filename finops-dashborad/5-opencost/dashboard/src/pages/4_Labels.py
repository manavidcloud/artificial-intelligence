"""K8s Cost Dashboard — Cost Allocation by Label (team / environment / application)."""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import allocation, flatten_allocation
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PALETTE, PLOTLY_CONFIG

st.set_page_config(page_title="Labels · K8s Cost", page_icon="🏷️", layout="wide")
apply_theme()

_COMMON_LABELS = [
    "team", "environment", "env", "app", "app.kubernetes.io/name",
    "app.kubernetes.io/part-of", "owner", "cost-center", "project",
    "service", "tier", "component",
]

with st.sidebar:
    st.markdown("## 🏷️ Label Cost Allocation")
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
    label_key = st.selectbox(
        "Label key to aggregate by",
        options=_COMMON_LABELS,
        index=0,
        help="OpenCost aggregates costs by this Kubernetes label key.",
    )
    custom_label = st.text_input("Or enter a custom label key", placeholder="e.g. cost-center")
    if custom_label.strip():
        label_key = custom_label.strip()
    st.markdown("---")
    st.caption("K8s Cost Dashboard")

st.title("🏷️ Cost Allocation by Label")
st.caption(
    f"Window: **{window}** · Label: **{label_key}** — "
    "Chargeback-ready cost split by team, environment, or application."
)

with st.spinner(f"Loading costs by label `{label_key}`…"):
    raw = allocation(window=window, aggregate=f"label:{label_key}", accumulate=True)

rows = flatten_allocation(raw)
df = pd.DataFrame(rows) if rows else pd.DataFrame()

if df.empty:
    st.warning(
        f"No data for label `{label_key}`. "
        "Make sure your pods have this label set. Try a different label from the sidebar."
    )
    st.stop()

df = df[df["name"] != "__idle__"].sort_values("total_cost", ascending=False).reset_index(drop=True)
total = df["total_cost"].sum()

if df.empty:
    st.info("All cost is unallocated (no pods with this label found).")
    st.stop()

# ── KPIs ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Labeled Spend", f"${total:,.2f}")
c2.metric("Label Values", len(df))
c3.metric("Top Value", df.iloc[0]["name"], f"${df.iloc[0]['total_cost']:,.2f}")
untagged_pct = (df[df["name"].str.startswith("__")]["total_cost"].sum() / total * 100) if total else 0
c4.metric("Unallocated Cost", f"{untagged_pct:.1f}%",
          help="Cost from pods that have no value set for this label")

st.divider()

tab_bar, tab_pie, tab_chargeback, tab_table = st.tabs([
    "📊 Bar", "🍕 Donut", "💳 Chargeback Report", "📋 Full Table"
])

# ── Tab 1: Bar ────────────────────────────────────────────────────────────────
with tab_bar:
    fig = go.Figure(go.Bar(
        x=df["total_cost"],
        y=df["name"],
        orientation="h",
        marker=dict(
            color=list(range(len(df))),
            colorscale="Blues",
            showscale=False,
        ),
        text=[f"${v:,.2f}  ({v / total * 100:.1f}%)" for v in df["total_cost"]],
        textposition="outside",
        hovertemplate=f"{label_key}: %{{y}}<br><b>${{x:,.2f}}</b><extra></extra>",
    ))
    apply_plotly_theme(fig)
    fig.update_layout(
        height=max(350, len(df) * 32),
        yaxis=dict(autorange="reversed"),
        xaxis_title="Cost (USD)",
        yaxis_title=label_key,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

# ── Tab 2: Donut ──────────────────────────────────────────────────────────────
with tab_pie:
    top_n_pie = min(10, len(df))
    df_pie = df.head(top_n_pie).copy()
    others = total - df_pie["total_cost"].sum()
    if others > 0:
        df_pie = pd.concat([df_pie, pd.DataFrame([{"name": "Other", "total_cost": others}])],
                           ignore_index=True)
    fig2 = go.Figure(go.Pie(
        labels=df_pie["name"],
        values=df_pie["total_cost"],
        hole=0.55,
        marker=dict(colors=PALETTE[:len(df_pie)]),
        textinfo="label+percent",
        hovertemplate=f"{label_key}: %{{label}}<br><b>$%{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
    ))
    apply_plotly_theme(fig2)
    fig2.update_layout(
        height=420,
        annotations=[dict(
            text=f"${total:,.0f}",
            x=0.5, y=0.5, font_size=18, font_color=COLORS["text"], showarrow=False,
        )],
    )
    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

# ── Tab 3: Chargeback Report ──────────────────────────────────────────────────
with tab_chargeback:
    st.subheader("💳 Chargeback / Showback Report")
    st.caption(
        "Use this to charge teams for their Kubernetes infrastructure costs. "
        "Export to Excel and share with finance or engineering managers."
    )

    df_cb = df.copy()
    df_cb["Share %"]  = (df_cb["total_cost"] / total * 100).round(2)
    df_cb["CPU Cost"] = df_cb["cpu_cost"].map(lambda x: f"${x:,.2f}")
    df_cb["RAM Cost"] = df_cb["ram_cost"].map(lambda x: f"${x:,.2f}")
    df_cb["Storage"]  = df_cb.get("pv_cost", pd.Series(0, index=df_cb.index)).map(lambda x: f"${x:,.2f}")
    df_cb["Total"]    = df_cb["total_cost"].map(lambda x: f"${x:,.2f}")
    df_cb["Label"]    = df_cb["name"]

    df_cb_disp = df_cb[["Label", "CPU Cost", "RAM Cost", "Storage", "Total", "Share %"]].copy()

    # Totals row
    total_row = pd.DataFrame([{
        "Label": "TOTAL", "CPU Cost": f"${df['cpu_cost'].sum():,.2f}",
        "RAM Cost": f"${df['ram_cost'].sum():,.2f}",
        "Storage": f"${df.get('pv_cost', pd.Series(0)).sum():,.2f}",
        "Total": f"${total:,.2f}", "Share %": 100.0,
    }])
    df_cb_final = pd.concat([df_cb_disp, total_row], ignore_index=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_cb_final.to_excel(w, index=False, sheet_name=f"Chargeback_{label_key}")
    col_h, col_xl = st.columns([8, 1])
    with col_h:
        st.markdown(f"**Label: `{label_key}`** · Window: `{window}`")
    with col_xl:
        st.download_button(
            "⬇ Excel", buf.getvalue(), f"chargeback_{label_key}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, key="cb_xl",
        )
    st.dataframe(df_cb_final, use_container_width=True, height=360)

# ── Tab 4: Full Table ─────────────────────────────────────────────────────────
with tab_table:
    df_disp = df.copy()
    df_disp["share"] = (df_disp["total_cost"] / total * 100).map(lambda x: f"{x:.1f}%")
    for c in ["total_cost", "cpu_cost", "ram_cost"]:
        df_disp[c] = df_disp[c].map(lambda x: f"${x:,.2f}")
    df_disp = df_disp.rename(columns={
        "name": label_key, "total_cost": "Total", "cpu_cost": "CPU",
        "ram_cost": "RAM", "efficiency": "Eff %", "share": "Share",
    })
    available_cols = [c for c in [label_key, "Total", "CPU", "RAM", "Eff %", "Share"] if c in df_disp.columns]
    st.subheader(f"All values for label `{label_key}`")
    st.dataframe(df_disp[available_cols], use_container_width=True, height=400)
    st.download_button(
        "⬇ CSV", df.to_csv(index=False).encode(), f"labels_{label_key}.csv",
        "text/csv", key="lbl_csv",
    )
