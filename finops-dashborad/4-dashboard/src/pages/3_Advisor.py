"""FinOps Dashboard — Azure Advisor Recommendations Page."""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS

st.set_page_config(page_title="Advisor · FinOps", page_icon="💡", layout="wide")
require_auth()
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
sub_id_to_name: dict = {}

with st.sidebar:
    sidebar_user()
    st.markdown("---")
    impact_filter = st.selectbox("Impact Level", ["All", "High", "Medium", "Low"])
    sub_filter    = None
    subs_resp = get("/subscriptions")
    if subs_resp and subs_resp.get("data"):
        sub_map = {"All": None}
        for s in subs_resp["data"]:
            sub_map[s.get("name", s["id"])] = s["id"]
        # reverse map: uuid → friendly name (for display in recommendations)
        sub_id_to_name = {v: k for k, v in sub_map.items() if v is not None}
        selected   = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("💡 Azure Advisor Recommendations")
st.caption("Cost optimization opportunities identified by Azure Advisor")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────────────
advisor_params: dict = {"category": "Cost"}
if impact_filter != "All":
    advisor_params["impact"] = impact_filter
if sub_filter:
    advisor_params["subscription_id"] = sub_filter

advisor_resp = get("/advisor",         advisor_params)
summary_resp = get("/advisor/summary")

# ─────────────────────────────────────────────────────────────────────────────
# Summary KPIs
# ─────────────────────────────────────────────────────────────────────────────
if summary_resp and summary_resp.get("data"):
    cost_rows      = [r for r in summary_resp["data"] if r.get("category") == "Cost"]
    total_savings  = sum(r.get("total_savings", 0) for r in cost_rows)
    total_count    = sum(r.get("count", 0) for r in cost_rows)
    high_rows      = [r for r in cost_rows if r.get("impact") == "High"]
    high_savings   = sum(r.get("total_savings", 0) for r in high_rows)
    high_count     = sum(r.get("count", 0) for r in high_rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Recommendations",  total_count)
    c2.metric("Total Savings Potential", f"${total_savings:,.0f}")
    c3.metric("High-Impact Count",       high_count)
    c4.metric("High-Impact Savings",     f"${high_savings:,.0f}")

    # ── Impact breakdown charts ──────────────────────────────────────────────
    if cost_rows:
        st.divider()
        df_summ = pd.DataFrame(cost_rows)
        impact_colors = {
            "High":   COLORS["red"],
            "Medium": COLORS["amber"],
            "Low":    COLORS["green"],
        }

        col_bar, col_donut = st.columns(2)

        with col_bar:
            st.subheader("Recommendations by Impact")
            colors = [impact_colors.get(i, COLORS["blue"]) for i in df_summ["impact"]]
            fig = go.Figure(go.Bar(
                x=df_summ["impact"],
                y=df_summ["count"],
                marker_color=colors,
                hovertemplate="%{x}<br><b>%{y} recommendations</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(height=280, xaxis_title="Impact", yaxis_title="Count", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_donut:
            st.subheader("Savings by Impact")
            colors2 = [impact_colors.get(i, COLORS["blue"]) for i in df_summ["impact"]]
            fig2 = go.Figure(go.Pie(
                labels=df_summ["impact"],
                values=df_summ["total_savings"],
                hole=0.45,
                marker=dict(colors=colors2),
                hovertemplate="%{label}<br><b>$%{value:,.0f}</b><extra></extra>",
            ))
            apply_plotly_theme(fig2)
            fig2.update_layout(height=280)
            st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Recommendations list
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Recommendations")

if advisor_resp and advisor_resp.get("data"):
    data = advisor_resp["data"]
    st.caption(f"{len(data)} recommendations")

    impact_order = {"High": 0, "Medium": 1, "Low": 2}
    data.sort(key=lambda r: impact_order.get(r.get("impact", "Low"), 3))

    impact_colors = {
        "High":   COLORS["red"],
        "Medium": COLORS["amber"],
        "Low":    COLORS["green"],
    }

    for rec in data:
        impact  = rec.get("impact", "")
        color   = impact_colors.get(impact, "#94a3b8")
        savings = rec.get("potential_savings") or 0
        desc    = rec.get("short_description", "No description")
        savings_str = f"${savings:,.2f} {rec.get('currency', 'USD')}" if savings else "N/A"
        sub_id   = rec.get("subscription_id", "")
        sub_name = sub_id_to_name.get(sub_id, sub_id) if sub_id else "N/A"

        with st.expander(f"**[{impact}]** {desc[:90]}{'…' if len(desc) > 90 else ''}"):
            col_info, col_savings = st.columns([3, 1])
            with col_info:
                st.markdown(f"**Resource:** `{rec.get('resource_name', 'N/A')}`")
                st.markdown(f"**Description:** {desc}")
                if sub_id:
                    st.caption(f"Subscription: {sub_name}")
                if rec.get("resource_id"):
                    st.caption(f"Resource ID: {rec['resource_id']}")
            with col_savings:
                st.markdown(
                    f"<div style='text-align:center; padding:14px 10px; "
                    f"background:{color}0d; border:1px solid {color}44; border-radius:10px;'>"
                    f"<div style='color:#94a3b8; font-size:10px; font-weight:700; "
                    f"text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;'>Savings</div>"
                    f"<div style='color:{color}; font-size:18px; font-weight:700;'>{savings_str}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Export table ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Export Data")

    df_export = pd.DataFrame(data)
    display_cols = ["subscription_id", "impact", "short_description", "resource_name", "potential_savings", "currency"]
    available = [c for c in display_cols if c in df_export.columns]
    df_show = df_export[available].copy()

    # Replace subscription UUIDs with friendly names
    if "subscription_id" in df_show.columns:
        df_show["subscription_id"] = df_show["subscription_id"].apply(
            lambda x: sub_id_to_name.get(x, x) if x else x
        )

    df_show.columns = [c.replace("_", " ").title() for c in df_show.columns]
    st.dataframe(df_show, use_container_width=True)

    # Download buttons
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button(
            label="⬇ Download CSV",
            data=df_show.to_csv(index=False).encode("utf-8"),
            file_name="advisor_recommendations.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        _buf = io.BytesIO()
        with pd.ExcelWriter(_buf, engine="openpyxl") as _w:
            df_show.to_excel(_w, index=False, sheet_name="Recommendations")
        st.download_button(
            label="⬇ Download Excel",
            data=_buf.getvalue(),
            file_name="advisor_recommendations.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

else:
    st.info("No recommendations found. Adjust impact filter or run a sync from the Home page.")
