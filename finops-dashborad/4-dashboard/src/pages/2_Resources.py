"""FinOps Dashboard — Resource Inventory Page."""
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PLOTLY_CONFIG

st.set_page_config(page_title="Resources · FinOps", page_icon="🖥️", layout="wide")
require_auth()
apply_theme()

# Resource types that are commonly found idle / orphaned
_IDLE_TYPES = [
    "microsoft.compute/disks",
    "microsoft.network/publicipaddresses",
    "microsoft.network/networkinterfaces",
    "microsoft.network/networksecuritygroups",
    "microsoft.network/routetables",
    "microsoft.network/loadbalancers",
    "microsoft.network/applicationgateways",
    "microsoft.compute/snapshots",
    "microsoft.compute/images",
]

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
        selected   = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]
    limit = st.selectbox("Max Results", [100, 250, 500, 1000, 2000], index=2)
    st.markdown("---")
    st.caption("FinOps Platform v1.0")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dl_header(title: str, df: pd.DataFrame, prefix: str) -> None:
    """Section title left, CSV + Excel buttons right — Azure portal style."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:30])
    col_title, col_csv, col_xlsx = st.columns([7, 1, 1])
    with col_title:
        st.subheader(title)
    with col_csv:
        st.download_button(
            "⬇ CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{prefix}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_{prefix}",
        )
    with col_xlsx:
        st.download_button(
            "⬇ Excel",
            data=buf.getvalue(),
            file_name=f"{prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"xlsx_{prefix}",
        )



def _render_type_chart(df_types: pd.DataFrame, chart_type: str) -> None:
    if chart_type == "Bar":
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
            height=max(320, len(df_types) * 28),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Count",
            yaxis_title=None,
            showlegend=False,
        )
    elif chart_type == "Pie":
        fig = go.Figure(go.Pie(
            labels=df_types["short_type"],
            values=df_types["count"],
            hole=0.4,
            hovertemplate="%{label}<br><b>%{value} resources</b> (%{percent})<extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=420, showlegend=True)
    else:  # Treemap
        fig = go.Figure(go.Treemap(
            labels=df_types["short_type"],
            parents=[""] * len(df_types),
            values=df_types["count"],
            textinfo="label+value",
            hovertemplate="%{label}<br><b>%{value} resources</b><extra></extra>",
            marker=dict(colorscale="Blues"),
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=420)

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def _render_location_chart(loc_counts: pd.DataFrame, chart_type: str) -> None:
    if chart_type == "Bar":
        fig = go.Figure(go.Bar(
            x=loc_counts["Location"],
            y=loc_counts["Count"],
            marker_color=COLORS["teal"],
            hovertemplate="%{x}<br><b>%{y} resources</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=300, xaxis_title=None, yaxis_title="Count", showlegend=False)
    elif chart_type == "Pie":
        fig = go.Figure(go.Pie(
            labels=loc_counts["Location"],
            values=loc_counts["Count"],
            hole=0.4,
            hovertemplate="%{label}<br><b>%{value} resources</b> (%{percent})<extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=380)
    else:  # Treemap
        fig = go.Figure(go.Treemap(
            labels=loc_counts["Location"],
            parents=[""] * len(loc_counts),
            values=loc_counts["Count"],
            textinfo="label+value",
            hovertemplate="%{label}<br><b>%{value} resources</b><extra></extra>",
            marker=dict(colorscale="Teal"),
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=380)

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("🖥️ Resource Inventory")
st.caption("Azure resources across all subscriptions, synced via Resource Graph")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────────────
params: dict = {"limit": limit}
if type_filter:     params["type"]            = type_filter
if rg_filter:       params["resource_group"]  = rg_filter
if location_filter: params["location"]        = location_filter
if sub_filter:      params["subscription_id"] = sub_filter

resources  = get("/resources",       params)
types_resp = get("/resources/types")

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
total_resources = 0
df_all = pd.DataFrame()

if resources and resources.get("data"):
    total_resources = resources.get("count", len(resources["data"]))
    df_all = pd.DataFrame(resources["data"])

total_types = 0
df_types = pd.DataFrame()
if types_resp and types_resp.get("data"):
    df_types = pd.DataFrame(types_resp["data"])
    total_types = len(df_types)

untagged_count = 0
if not df_all.empty and "tags" in df_all.columns:
    untagged_count = int(df_all["tags"].apply(lambda t: not t).sum())

idle_count = 0
if not df_all.empty and "type" in df_all.columns:
    idle_count = int(df_all["type"].str.lower().isin(_IDLE_TYPES).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Resources", total_resources)
c2.metric("Resource Types",  total_types)
c3.metric("Untagged",        untagged_count,
          help="Resources with no tags applied")
c4.metric("Watch List",      idle_count,
          help="Resources of types commonly found idle or orphaned")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_overview, tab_types, tab_locations, tab_issues = st.tabs([
    "📋 All Resources", "📊 By Type", "🗺️ By Location", "⚠️ Watch List"
])

# ── Tab 1: All Resources ─────────────────────────────────────────────────────
with tab_overview:
    if not df_all.empty:
        display_cols = ["name", "type", "location", "resource_group", "subscription_id", "sku"]
        available    = [c for c in display_cols if c in df_all.columns]
        df_display   = df_all[available].copy()
        if "type" in df_display.columns:
            df_display["type"] = df_display["type"].str.split("/").str[-1]
        df_display.columns = [c.replace("_", " ").title() for c in df_display.columns]
        _dl_header("All Resources", df_display, "resources_all")
        st.dataframe(df_display, use_container_width=True, height=480)
        st.caption(f"Showing {len(df_display)} of {total_resources} resources")
    else:
        st.info("No resources found. Run a sync from the Home page.")

# ── Tab 2: By Type ────────────────────────────────────────────────────────────
with tab_types:
    if not df_types.empty:
        chart_type = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="type_chart")
        top_n = st.slider("Show top N types", 5, min(30, len(df_types)), 15, key="type_topn")
        df_plot = df_types.head(top_n).copy()
        df_plot["short_type"] = df_plot["type"].str.split("/").str[-1]

        _render_type_chart(df_plot, chart_type)

        df_types_display = df_types.copy()
        df_types_display["short_type"] = df_types_display["type"].str.split("/").str[-1]
        df_types_display = df_types_display[["short_type", "type", "count"]].rename(
            columns={"short_type": "Short Name", "type": "Full Type", "count": "Count"}
        )
        _dl_header("Full Type Breakdown", df_types_display, "resources_by_type")
        st.dataframe(df_types_display, use_container_width=True, height=320)
    else:
        st.info("No type data available.")

# ── Tab 3: By Location ────────────────────────────────────────────────────────
with tab_locations:
    if not df_all.empty and "location" in df_all.columns:
        chart_type_loc = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="loc_chart")
        loc_counts = df_all["location"].value_counts().reset_index()
        loc_counts.columns = ["Location", "Count"]

        _render_location_chart(loc_counts, chart_type_loc)

        _dl_header("Location Table", loc_counts, "resources_by_location")
        st.dataframe(loc_counts, use_container_width=True, height=280)

        # Resource group breakdown per location
        if "resource_group" in df_all.columns:
            st.divider()
            st.subheader("Resource Groups by Location")
            rg_loc = df_all.groupby(["location", "resource_group"]).size().reset_index(name="count")
            rg_loc.columns = ["Location", "Resource Group", "Count"]
            rg_loc = rg_loc.sort_values(["Location", "Count"], ascending=[True, False])
            st.dataframe(rg_loc, use_container_width=True, height=280)
    else:
        st.info("No location data available.")

# ── Tab 4: Watch List (potential idle / orphaned) ────────────────────────────
with tab_issues:
    st.caption(
        "Resources of types commonly found idle or orphaned. "
        "Review in Azure Portal to confirm before deleting."
    )

    if not df_all.empty and "type" in df_all.columns:
        # Section A: Untagged resources
        st.subheader("🏷️ Untagged Resources")
        if "tags" in df_all.columns:
            df_untagged = df_all[df_all["tags"].apply(lambda t: not t)].copy()
            if not df_untagged.empty:
                cols_show = [c for c in ["name", "type", "location", "resource_group"] if c in df_untagged.columns]
                df_ut_disp = df_untagged[cols_show].copy()
                if "type" in df_ut_disp.columns:
                    df_ut_disp["type"] = df_ut_disp["type"].str.split("/").str[-1]
                df_ut_disp.columns = [c.replace("_", " ").title() for c in df_ut_disp.columns]
                _dl_header("Untagged Resources", df_ut_disp, "resources_untagged")
                st.dataframe(df_ut_disp, use_container_width=True, height=240)
            else:
                st.success("All resources have tags applied.")
        else:
            st.info("Tag data not available in the current dataset.")

        st.divider()

        # Section B: Watch-list resource types
        st.subheader("🔍 Watch-List Resource Types")
        st.caption("Disks, Public IPs, NICs, NSGs, Snapshots, Images — review for orphaned state.")
        df_idle = df_all[df_all["type"].str.lower().isin(_IDLE_TYPES)].copy()
        if not df_idle.empty:
            # Count by type
            type_counts = df_idle["type"].str.split("/").str[-1].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]

            col_chart, col_table = st.columns([1, 2])
            with col_chart:
                fig_idle = go.Figure(go.Bar(
                    x=type_counts["Count"],
                    y=type_counts["Type"],
                    orientation="h",
                    marker_color=COLORS["amber"],
                    hovertemplate="%{y}<br><b>%{x} resources</b><extra></extra>",
                ))
                apply_plotly_theme(fig_idle)
                fig_idle.update_layout(
                    height=max(260, len(type_counts) * 32),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title="Count",
                    yaxis_title=None,
                    showlegend=False,
                )
                st.plotly_chart(fig_idle, use_container_width=True, config=PLOTLY_CONFIG)

            with col_table:
                cols_idle = [c for c in ["name", "type", "location", "resource_group"] if c in df_idle.columns]
                df_idle_disp = df_idle[cols_idle].copy()
                if "type" in df_idle_disp.columns:
                    df_idle_disp["type"] = df_idle_disp["type"].str.split("/").str[-1]
                df_idle_disp.columns = [c.replace("_", " ").title() for c in df_idle_disp.columns]
                st.dataframe(df_idle_disp, use_container_width=True, height=260)

            _dl_header("Watch-List Resources", df_idle_disp, "resources_watchlist")
        else:
            st.success("No watch-list resource types found in current results.")
    else:
        st.info("No resource data. Run a sync from the Home page.")
