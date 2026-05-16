"""FinOps Dashboard — Resource Inventory Page."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS

st.set_page_config(page_title="Resources · FinOps", page_icon="🖥️", layout="wide")
require_auth()
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    st.subheader("Filters")
    type_filter     = st.text_input("Resource Type", placeholder="e.g. virtualmachines")
    rg_filter       = st.text_input("Resource Group",  placeholder="e.g. rg-prod-core")
    location_filter = st.text_input("Location",        placeholder="e.g. eastus")
    sub_filter      = None
    subs_resp = get("/subscriptions")
    if subs_resp and subs_resp.get("data"):
        sub_map = {"All": None}
        for s in subs_resp["data"]:
            sub_map[s.get("name", s["id"])] = s["id"]
        selected = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]
    limit = st.selectbox("Max Results", [100, 250, 500, 1000, 2000], index=2)
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("🖥️ Resource Inventory")
st.caption("Azure resources across all subscriptions, synced via Resource Graph")

# ─────────────────────────────────────────────────────────────────────────────
# Build query params
# ─────────────────────────────────────────────────────────────────────────────
params: dict = {"limit": limit}
if type_filter:     params["type"]            = type_filter
if rg_filter:       params["resource_group"]  = rg_filter
if location_filter: params["location"]        = location_filter
if sub_filter:      params["subscription_id"] = sub_filter

resources  = get("/resources",       params)
types_resp = get("/resources/types")

# ─────────────────────────────────────────────────────────────────────────────
# Summary KPIs
# ─────────────────────────────────────────────────────────────────────────────
total_resources = 0
if resources and resources.get("data"):
    total_resources = resources["count"]

total_types = 0
if types_resp and types_resp.get("data"):
    total_types = len(types_resp["data"])

c1, c2, c3 = st.columns(3)
c1.metric("Total Resources",  total_resources)
c2.metric("Resource Types",   total_types)
c3.metric("Showing",          min(total_resources, limit))

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Chart + Table
# ─────────────────────────────────────────────────────────────────────────────
if types_resp and types_resp.get("data"):
    col_chart, col_table = st.columns([1, 2])

    with col_chart:
        st.subheader("Resources by Type")
        df_types = pd.DataFrame(types_resp["data"]).head(15)
        df_types["short_type"] = df_types["type"].str.split("/").str[-1]

        fig = go.Figure(go.Bar(
            x=df_types["count"],
            y=df_types["short_type"],
            orientation="h",
            marker=dict(
                color=df_types["count"],
                colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                showscale=False,
            ),
            hovertemplate="%{y}<br><b>%{x} resources</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(
            height=max(350, len(df_types) * 28),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Count",
            yaxis_title=None,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.subheader(f"Resource List ({total_resources} found)")
        if resources and resources.get("data"):
            df = pd.DataFrame(resources["data"])
            display_cols = ["name", "type", "location", "resource_group", "subscription_id", "sku"]
            available = [c for c in display_cols if c in df.columns]
            df_display = df[available].copy()
            if "type" in df_display.columns:
                df_display["type"] = df_display["type"].str.split("/").str[-1]
            df_display.columns = [c.replace("_", " ").title() for c in df_display.columns]
            st.dataframe(df_display, use_container_width=True, height=450)
        else:
            st.info("No resources found with the current filters.")
else:
    st.info("No resource data. Run a sync from the Home page.")

# ─────────────────────────────────────────────────────────────────────────────
# Location breakdown
# ─────────────────────────────────────────────────────────────────────────────
if resources and resources.get("data"):
    df_all = pd.DataFrame(resources["data"])
    if "location" in df_all.columns:
        loc_counts = df_all["location"].value_counts().head(10).reset_index()
        loc_counts.columns = ["Location", "Count"]

        st.divider()
        st.subheader("Resources by Location")
        fig_loc = go.Figure(go.Bar(
            x=loc_counts["Location"],
            y=loc_counts["Count"],
            marker_color=COLORS["teal"],
            hovertemplate="%{x}<br><b>%{y} resources</b><extra></extra>",
        ))
        apply_plotly_theme(fig_loc)
        fig_loc.update_layout(height=280, xaxis_title=None, yaxis_title="Count")
        st.plotly_chart(fig_loc, use_container_width=True)
