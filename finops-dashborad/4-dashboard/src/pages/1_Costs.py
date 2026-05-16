"""FinOps Dashboard — Cost Analysis Page."""
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PLOTLY_CONFIG
from utils.currency import convert, fmt

st.set_page_config(page_title="Costs · FinOps", page_icon="💰", layout="wide")
require_auth()
apply_theme()

STORAGE_KW = ["storage", "blob", "disk", "files", "backup", "archive",
              "data lake", "netapp", "site recovery", "recovery"]
NETWORK_KW = ["bandwidth", "virtual network", "vnet", "dns", "cdn", "content delivery",
              "vpn", "application gateway", "load balancer", "front door",
              "bastion", "expressroute", "public ip", "ip address", "ddos",
              "azure firewall", "firewall", "nat gateway", "traffic manager"]


def _matches(service: str, keywords: list) -> bool:
    s = service.lower()
    return any(k in s for k in keywords)


def _dl_header(title: str, df: pd.DataFrame, prefix: str, level: str = "subheader") -> None:
    """Section title on the left, CSV + Excel download buttons on the right — Azure portal style."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:30])

    col_title, col_csv, col_xlsx = st.columns([7, 1, 1])
    with col_title:
        if level == "subheader":
            st.subheader(title)
        else:
            st.markdown(f"**{title}**")
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


def _render_chart(df: pd.DataFrame, x_col: str, y_col: str, label_col: str,
                  chart_type: str, currency: str, height: int = 400) -> None:
    sym = currency
    if chart_type == "Bar":
        fig = go.Figure(go.Bar(
            x=df[x_col] if x_col != "h" else df[y_col],
            y=df[y_col] if x_col != "h" else df[label_col],
            orientation="v" if x_col != "h" else "h",
            marker=dict(
                color=df[y_col],
                colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                showscale=False,
            ),
            hovertemplate=(
                f"%{{x}}<br><b>{sym} %{{y:,.2f}}</b><extra></extra>"
                if x_col != "h" else
                f"%{{y}}<br><b>{sym} %{{x:,.2f}}</b><extra></extra>"
            ),
        ))
        apply_plotly_theme(fig)
        if x_col == "h":
            fig.update_layout(height=height, yaxis=dict(autorange="reversed"),
                              xaxis_title=f"Cost ({currency})", yaxis_title=None)
        else:
            fig.update_layout(height=height, xaxis_title=None,
                              yaxis_title=f"Cost ({currency})")

    elif chart_type == "Line":
        fig = go.Figure(go.Scatter(
            x=df[x_col], y=df[y_col], mode="lines+markers",
            line=dict(color=COLORS["blue"], width=2.5),
            marker=dict(size=6, color=COLORS["blue"]),
            fill="tozeroy", fillcolor="rgba(0,120,212,0.07)",
            hovertemplate=f"%{{x}}<br><b>{sym} %{{y:,.2f}}</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=height, xaxis_title=None, yaxis_title=f"Cost ({currency})")

    elif chart_type == "Area":
        fig = go.Figure(go.Scatter(
            x=df[x_col], y=df[y_col], mode="lines",
            line=dict(color=COLORS["teal"], width=2),
            fill="tozeroy", fillcolor="rgba(0,200,180,0.12)",
            hovertemplate=f"%{{x}}<br><b>{sym} %{{y:,.2f}}</b><extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=height, xaxis_title=None, yaxis_title=f"Cost ({currency})")

    elif chart_type == "Pie":
        fig = go.Figure(go.Pie(
            labels=df[label_col], values=df[y_col], hole=0.4,
            hovertemplate=f"%{{label}}<br><b>{sym} %{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=height)

    elif chart_type == "Treemap":
        fig = go.Figure(go.Treemap(
            labels=df[label_col],
            parents=[""] * len(df),
            values=df[y_col],
            textinfo="label+percent parent",
            hovertemplate=f"%{{label}}<br><b>{sym} %{{value:,.2f}}</b><extra></extra>",
            marker=dict(colorscale="Blues"),
        ))
        apply_plotly_theme(fig)
        fig.update_layout(height=height, margin=dict(t=30, l=0, r=0, b=0))

    else:
        return

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")
    days = st.selectbox(
        "Period", [7, 14, 30, 60, 90], index=2,
        format_func=lambda d: f"Last {d} days",
    )
    sub_filter = None
    sub_id_to_name: dict = {}
    subs_resp = get("/subscriptions")
    if subs_resp and subs_resp.get("data"):
        sub_map = {"All Subscriptions": None}
        for s in subs_resp["data"]:
            sub_map[s.get("name", s["id"])] = s["id"]
        sub_id_to_name = {v: k for k, v in sub_map.items() if v}
        selected = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]
    limit = st.selectbox("Top N Services", [10, 20, 30, 50], index=1)
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

disp_currency = st.session_state.get("_currency", "USD")

# ─────────────────────────────────────────────────────────────────────────────
# Header + Fetch
# ─────────────────────────────────────────────────────────────────────────────
st.title("💰 Cost Analysis")
st.caption(f"Last {days} days · {disp_currency}")

base = {"days": days}
if sub_filter:
    base["subscription_id"] = sub_filter

summary      = get("/costs/summary",           base)
daily        = get("/costs/daily",             base)
by_svc       = get("/costs/by-service",        {**base, "limit": limit})
by_sub       = get("/costs/by-subscription",   {"days": days})
by_rg        = get("/costs/by-resource-group", {**base, "limit": 15})
base_long    = {"days": days * 2, **({"subscription_id": sub_filter} if sub_filter else {})}
by_svc_long  = get("/costs/by-service",        {**base_long, "limit": limit})

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
if summary and summary.get("data"):
    d       = summary["data"]
    src_cur = d.get("currency", "USD")
    total   = convert(d.get("total_cost", 0),       src_cur, disp_currency)
    prev    = convert(d.get("prev_period_cost", 0), src_cur, disp_currency)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        f"Total Spend ({disp_currency})", fmt(total, disp_currency),
        delta=f"{d['change_pct']:+.1f}% vs prev" if d.get("change_pct") is not None else None,
        delta_color="inverse",
    )
    c2.metric("Previous Period", fmt(prev, disp_currency))
    c3.metric("Period Start",    d.get("period_start", "—"))
    c4.metric("Period End",      d.get("period_end",   "—"))

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_daily, tab_svc, tab_sub, tab_rg, tab_storage, tab_network, tab_leaderboard, tab_mom = st.tabs([
    "📅 Daily Trend", "🏷️ By Service", "🔑 By Subscription",
    "📁 By Resource Group", "💾 Storage", "🌐 Network", "🏆 Savings Leaderboard", "📊 MoM Comparison",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Daily Trend
# ══════════════════════════════════════════════════════════════════════════════
with tab_daily:
    chart_type = st.radio("Chart type", ["Line", "Bar", "Area"], horizontal=True, key="ct_daily")
    if daily and daily.get("data"):
        df = pd.DataFrame(daily["data"])
        df["date"] = pd.to_datetime(df["date"])
        sc = df["currency"].iloc[0] if "currency" in df.columns else "USD"
        df["disp_cost"] = df["total_cost"].apply(lambda x: convert(x, sc, disp_currency))
        df["rolling_avg"] = df["disp_cost"].rolling(7, min_periods=1).mean()

        mean_c = df["disp_cost"].mean()
        std_c  = df["disp_cost"].std(ddof=0)
        thresh = mean_c + 2 * std_c
        df["is_anomaly"] = df["disp_cost"] > thresh
        anomalies = df[df["is_anomaly"]]

        if chart_type == "Bar":
            fig = go.Figure(go.Bar(
                x=df["date"], y=df["disp_cost"],
                name="Daily Cost", marker_color=COLORS["blue"], opacity=0.75,
                hovertemplate=f"%{{x|%b %d}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
            ))
        elif chart_type == "Line":
            fig = go.Figure(go.Scatter(
                x=df["date"], y=df["disp_cost"],
                mode="lines+markers", name="Daily Cost",
                line=dict(color=COLORS["blue"], width=2.5),
                fill="tozeroy", fillcolor="rgba(0,120,212,0.07)",
                hovertemplate=f"%{{x|%b %d}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
            ))
        else:
            fig = go.Figure(go.Scatter(
                x=df["date"], y=df["disp_cost"],
                mode="lines", name="Daily Cost",
                line=dict(color=COLORS["teal"], width=2),
                fill="tozeroy", fillcolor="rgba(0,200,180,0.12)",
                hovertemplate=f"%{{x|%b %d}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
            ))

        fig.add_trace(go.Scatter(
            x=df["date"], y=df["rolling_avg"],
            mode="lines", name="7-Day Avg",
            line=dict(color=COLORS["amber"], width=1.5, dash="dot"),
            hovertemplate=f"%{{x|%b %d}}<br>Avg: {disp_currency} %{{y:,.2f}}<extra></extra>",
        ))
        if len(anomalies):
            fig.add_trace(go.Scatter(
                x=anomalies["date"], y=anomalies["disp_cost"],
                mode="markers", name="⚠ Spike",
                marker=dict(color=COLORS["red"], size=12, symbol="circle",
                            line=dict(color="white", width=1.5)),
                hovertemplate=f"⚠ Spike: {disp_currency} %{{y:,.2f}}<extra></extra>",
            ))

        apply_plotly_theme(fig)
        fig.update_layout(
            height=420, xaxis_title=None,
            yaxis_title=f"Cost ({disp_currency})",
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        if len(anomalies):
            st.warning(f"⚠ {len(anomalies)} spike(s) detected (> {disp_currency} {thresh:,.2f}, mean + 2σ)")

        export_df = df[["date", "disp_cost"]].copy()
        export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
        export_df.columns = ["Date", f"Cost ({disp_currency})"]
        _dl_header("Daily Cost Data", export_df, "daily_cost")
        st.dataframe(export_df, use_container_width=True)
    else:
        st.info("No daily cost data. Run a sync from the Home page.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — By Service
# ══════════════════════════════════════════════════════════════════════════════
with tab_svc:
    chart_type = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="ct_svc")
    if by_svc and by_svc.get("data"):
        df_svc = pd.DataFrame(by_svc["data"])
        sc2 = df_svc["currency"].iloc[0] if "currency" in df_svc.columns else "USD"
        df_svc["disp_cost"] = df_svc["total_cost"].apply(lambda x: convert(x, sc2, disp_currency))
        total_svc = df_svc["disp_cost"].sum()
        df_svc["share_pct"] = (df_svc["disp_cost"] / total_svc * 100).round(1)

        if chart_type == "Bar":
            col_bar, col_pie = st.columns([3, 2])
            with col_bar:
                fig = go.Figure(go.Bar(
                    x=df_svc["disp_cost"],
                    y=df_svc["service_name"],
                    orientation="h",
                    marker=dict(
                        color=df_svc["disp_cost"],
                        colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                        showscale=False,
                    ),
                    text=df_svc["share_pct"].apply(lambda p: f"{p:.1f}%"),
                    textposition="outside",
                    hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig)
                fig.update_layout(
                    height=max(350, len(df_svc) * 30),
                    yaxis=dict(autorange="reversed"),
                    xaxis_title=f"Cost ({disp_currency})",
                    yaxis_title=None, showlegend=False, margin=dict(r=60),
                )
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            with col_pie:
                top8 = df_svc.head(8)
                fig2 = go.Figure(go.Pie(
                    labels=top8["service_name"], values=top8["disp_cost"], hole=0.45,
                    hovertemplate=f"%{{label}}<br><b>{disp_currency} %{{value:,.2f}}</b> (%{{percent}})<extra></extra>",
                ))
                apply_plotly_theme(fig2)
                fig2.update_layout(height=380, showlegend=False)
                st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            _render_chart(df_svc, "", "disp_cost", "service_name", chart_type, disp_currency, height=480)

        export_df = df_svc[["service_name", "disp_cost", "share_pct"]].copy()
        export_df.columns = ["Service", f"Cost ({disp_currency})", "Share %"]
        _dl_header("Service Cost Breakdown", export_df, "cost_by_service")
        st.dataframe(export_df, use_container_width=True)
    else:
        st.info("No service cost data. Run a sync from the Home page.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — By Subscription
# ══════════════════════════════════════════════════════════════════════════════
with tab_sub:
    chart_type = st.radio("Chart type", ["Pie", "Bar", "Treemap"], horizontal=True, key="ct_sub")
    if by_sub and by_sub.get("data"):
        df_sub = pd.DataFrame(by_sub["data"])
        sc3 = df_sub["currency"].iloc[0] if "currency" in df_sub.columns else "USD"
        df_sub["disp_cost"] = df_sub["total_cost"].apply(lambda x: convert(x, sc3, disp_currency))
        df_sub["sub_name"]  = df_sub["subscription_id"].apply(lambda x: sub_id_to_name.get(x, x))

        if chart_type == "Pie":
            _render_chart(df_sub, "", "disp_cost", "sub_name", "Pie", disp_currency)
        elif chart_type == "Bar":
            fig = go.Figure(go.Bar(
                x=df_sub["sub_name"], y=df_sub["disp_cost"],
                marker=dict(
                    color=df_sub["disp_cost"],
                    colorscale=[[0, COLORS["blue2"]], [1, COLORS["blue"]]],
                    showscale=False,
                ),
                hovertemplate=f"%{{x}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(height=380, xaxis_title=None, yaxis_title=f"Cost ({disp_currency})")
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            _render_chart(df_sub, "", "disp_cost", "sub_name", "Treemap", disp_currency)

        export_df = df_sub[["sub_name", "disp_cost"]].copy()
        export_df.columns = ["Subscription", f"Cost ({disp_currency})"]
        _dl_header("Subscription Cost Breakdown", export_df, "cost_by_subscription")
        st.dataframe(export_df, use_container_width=True)
    else:
        st.info("No subscription cost data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — By Resource Group
# ══════════════════════════════════════════════════════════════════════════════
with tab_rg:
    chart_type = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="ct_rg")
    if by_rg and by_rg.get("data"):
        df_rg = pd.DataFrame(by_rg["data"])
        sc4 = df_rg["currency"].iloc[0] if "currency" in df_rg.columns else "USD"
        df_rg["disp_cost"] = df_rg["total_cost"].apply(lambda x: convert(x, sc4, disp_currency))

        if chart_type == "Bar":
            fig = go.Figure(go.Bar(
                x=df_rg["resource_group"], y=df_rg["disp_cost"],
                marker=dict(
                    color=df_rg["disp_cost"],
                    colorscale=[[0, COLORS["teal"]], [1, COLORS["blue"]]],
                    showscale=False,
                ),
                hovertemplate=f"%{{x}}<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
            ))
            apply_plotly_theme(fig)
            fig.update_layout(height=380, xaxis_title=None,
                              yaxis_title=f"Cost ({disp_currency})", xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            _render_chart(df_rg, "", "disp_cost", "resource_group", chart_type, disp_currency)

        export_df = df_rg[["resource_group", "disp_cost"]].copy()
        export_df.columns = ["Resource Group", f"Cost ({disp_currency})"]
        _dl_header("Resource Group Cost Breakdown", export_df, "cost_by_resource_group")
        st.dataframe(export_df, use_container_width=True)
    else:
        st.info("No resource group cost data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Storage Analysis
# ══════════════════════════════════════════════════════════════════════════════
with tab_storage:
    if by_svc and by_svc.get("data"):
        df_all = pd.DataFrame(by_svc["data"])
        sc5 = df_all["currency"].iloc[0] if "currency" in df_all.columns else "USD"
        df_all["disp_cost"] = df_all["total_cost"].apply(lambda x: convert(x, sc5, disp_currency))
        df_stor = df_all[df_all["service_name"].apply(lambda s: _matches(s, STORAGE_KW))].copy()

        if not df_stor.empty:
            total_stor = df_stor["disp_cost"].sum()
            total_all  = df_all["disp_cost"].sum()
            stor_pct   = total_stor / total_all * 100 if total_all > 0 else 0

            s1, s2, s3 = st.columns(3)
            s1.metric(f"Storage Total ({disp_currency})", fmt(total_stor, disp_currency))
            s2.metric("% of Total Spend",                 f"{stor_pct:.1f}%")
            s3.metric("Storage Services",                 len(df_stor))

            st.divider()
            chart_type = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="ct_stor")
            df_stor_s = df_stor.sort_values("disp_cost", ascending=False)

            if chart_type == "Bar":
                fig = go.Figure(go.Bar(
                    x=df_stor_s["disp_cost"], y=df_stor_s["service_name"],
                    orientation="h",
                    marker=dict(
                        color=df_stor_s["disp_cost"],
                        colorscale=[[0, "#0d3b66"], [1, "#60a5fa"]], showscale=False,
                    ),
                    hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig)
                fig.update_layout(height=max(280, len(df_stor) * 40),
                                  yaxis=dict(autorange="reversed"),
                                  xaxis_title=f"Cost ({disp_currency})", yaxis_title=None)
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                _render_chart(df_stor_s, "", "disp_cost", "service_name", chart_type, disp_currency, 380)

            df_stor_s["share_pct"] = (df_stor_s["disp_cost"] / total_stor * 100).round(1)
            export_df = df_stor_s[["service_name", "disp_cost", "share_pct"]].copy()
            export_df.columns = ["Storage Service", f"Cost ({disp_currency})", "% of Storage"]
            _dl_header("Storage Cost Breakdown", export_df, "storage_cost")
            st.dataframe(export_df, use_container_width=True)
        else:
            st.info("No storage services in the current period. Common: Azure Storage, Blob, Managed Disks, Azure Backup.")
    else:
        st.info("No cost data. Run a sync first.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Network Cost
# ══════════════════════════════════════════════════════════════════════════════
with tab_network:
    if by_svc and by_svc.get("data"):
        df_all_n = pd.DataFrame(by_svc["data"])
        sc6 = df_all_n["currency"].iloc[0] if "currency" in df_all_n.columns else "USD"
        df_all_n["disp_cost"] = df_all_n["total_cost"].apply(lambda x: convert(x, sc6, disp_currency))
        df_net = df_all_n[df_all_n["service_name"].apply(lambda s: _matches(s, NETWORK_KW))].copy()

        if not df_net.empty:
            total_net   = df_net["disp_cost"].sum()
            total_all_n = df_all_n["disp_cost"].sum()
            net_pct     = total_net / total_all_n * 100 if total_all_n > 0 else 0

            n1, n2, n3 = st.columns(3)
            n1.metric(f"Network Total ({disp_currency})", fmt(total_net, disp_currency))
            n2.metric("% of Total Spend",                 f"{net_pct:.1f}%")
            n3.metric("Network Services",                 len(df_net))

            st.divider()
            chart_type = st.radio("Chart type", ["Bar", "Pie", "Treemap"], horizontal=True, key="ct_net")
            df_net_s = df_net.sort_values("disp_cost", ascending=False)

            if chart_type == "Bar":
                fig = go.Figure(go.Bar(
                    x=df_net_s["disp_cost"], y=df_net_s["service_name"],
                    orientation="h",
                    marker=dict(
                        color=df_net_s["disp_cost"],
                        colorscale=[[0, "#0d3b2e"], [1, COLORS["teal"]]], showscale=False,
                    ),
                    hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b><extra></extra>",
                ))
                apply_plotly_theme(fig)
                fig.update_layout(height=max(280, len(df_net) * 40),
                                  yaxis=dict(autorange="reversed"),
                                  xaxis_title=f"Cost ({disp_currency})", yaxis_title=None)
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                _render_chart(df_net_s, "", "disp_cost", "service_name", chart_type, disp_currency, 380)

            df_net_s["share_pct"] = (df_net_s["disp_cost"] / total_net * 100).round(1)
            export_df = df_net_s[["service_name", "disp_cost", "share_pct"]].copy()
            export_df.columns = ["Network Service", f"Cost ({disp_currency})", "% of Network"]
            _dl_header("Network Cost Breakdown", export_df, "network_cost")
            st.dataframe(export_df, use_container_width=True)
        else:
            st.info("No network services in the current period. Common: Bandwidth, VNet, VPN Gateway, Azure DNS, CDN.")
    else:
        st.info("No cost data. Run a sync first.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — Savings Leaderboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_leaderboard:
    st.caption(
        "All services ranked by spend for the selected period. "
        "Use this to find your biggest cost drivers at a glance."
    )
    if by_svc and by_svc.get("data"):
        df_lb = pd.DataFrame(by_svc["data"])
        sc7 = df_lb["currency"].iloc[0] if "currency" in df_lb.columns else "USD"
        df_lb["disp_cost"] = df_lb["total_cost"].apply(lambda x: convert(x, sc7, disp_currency))
        total_lb = df_lb["disp_cost"].sum()
        df_lb["share_pct"]  = (df_lb["disp_cost"] / total_lb * 100).round(2)
        df_lb["cumul_pct"]  = df_lb["share_pct"].cumsum().round(1)
        df_lb = df_lb.sort_values("disp_cost", ascending=False).reset_index(drop=True)
        df_lb.index += 1

        # KPIs
        top1 = df_lb.iloc[0]
        top3_cost = df_lb.head(3)["disp_cost"].sum()
        lb1, lb2, lb3 = st.columns(3)
        lb1.metric("Top Service",        top1["service_name"])
        lb2.metric(f"Top Service Cost ({disp_currency})", fmt(top1["disp_cost"], disp_currency))
        lb3.metric("Top 3 Services Share", f"{df_lb.head(3)['share_pct'].sum():.1f}%")

        st.divider()

        # Waterfall-style bar
        fig_lb = go.Figure(go.Bar(
            x=df_lb["disp_cost"],
            y=df_lb["service_name"],
            orientation="h",
            marker=dict(
                color=df_lb["disp_cost"],
                colorscale=[[0, COLORS["blue2"]], [0.5, COLORS["blue"]], [1, COLORS["purple"]]],
                showscale=False,
            ),
            text=df_lb["share_pct"].apply(lambda p: f"{p:.1f}%"),
            textposition="outside",
            hovertemplate=f"%{{y}}<br><b>{disp_currency} %{{x:,.2f}}</b> (%{{text}})<extra></extra>",
        ))
        apply_plotly_theme(fig_lb)
        fig_lb.update_layout(
            height=max(400, len(df_lb) * 28),
            yaxis=dict(autorange="reversed"),
            xaxis_title=f"Cost ({disp_currency})",
            yaxis_title=None, showlegend=False, margin=dict(r=70),
        )
        st.subheader("Cost Leaderboard")
        st.plotly_chart(fig_lb, use_container_width=True, config=PLOTLY_CONFIG)

        # Full ranked table
        df_lb_export = df_lb[["service_name", "disp_cost", "share_pct", "cumul_pct"]].copy()
        df_lb_export.columns = ["Service", f"Cost ({disp_currency})", "Share %", "Cumulative %"]
        _dl_header("Full Ranked Table", df_lb_export, "cost_leaderboard")
        st.dataframe(df_lb_export, use_container_width=True)
    else:
        st.info("No service cost data. Run a sync from the Home page.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — Month-over-Month Category Comparison
# ══════════════════════════════════════════════════════════════════════════════
_CAT_KW_MOM = {
    "Compute":            ["virtual machine", "compute", "aks", "kubernetes", "container",
                           "function", "app service", "batch", "spring"],
    "Storage":            ["storage", "blob", "disk", "backup", "archive", "files", "data lake"],
    "Network":            ["bandwidth", "vnet", "virtual network", "dns", "cdn", "vpn",
                           "gateway", "load balancer", "front door", "bastion",
                           "expressroute", "public ip", "firewall", "nat", "traffic manager"],
    "Database":           ["sql", "mysql", "postgresql", "cosmos", "redis", "mariadb",
                           "synapse", "database", "data factory", "databricks"],
    "Monitor & Security": ["monitor", "log analytics", "application insights", "sentinel",
                           "defender", "security", "key vault"],
}


def _cat_mom(name: str) -> str:
    s = name.lower()
    for cat, kws in _CAT_KW_MOM.items():
        if any(k in s for k in kws):
            return cat
    return "Other"


with tab_mom:
    st.caption(
        f"Current {days}d vs previous {days}d by service category. "
        f"Computed from {days * 2} days of data, split into two equal halves."
    )
    if by_svc and by_svc.get("data") and by_svc_long and by_svc_long.get("data"):
        df_curr = pd.DataFrame(by_svc["data"])
        sc_m    = df_curr["currency"].iloc[0] if "currency" in df_curr.columns else "USD"
        df_curr["curr_cost"] = df_curr["total_cost"].apply(lambda x: convert(x, sc_m, disp_currency))

        df_long = pd.DataFrame(by_svc_long["data"])
        df_long["long_cost"] = df_long["total_cost"].apply(lambda x: convert(x, sc_m, disp_currency))

        # Previous period = long_period_total - current_period_total per service
        df_mom = df_curr[["service_name", "curr_cost"]].merge(
            df_long[["service_name", "long_cost"]], on="service_name", how="outer"
        ).fillna(0)
        df_mom["prev_cost"] = (df_mom["long_cost"] - df_mom["curr_cost"]).clip(lower=0)
        df_mom["category"]  = df_mom["service_name"].apply(_cat_mom)

        cat_curr_s = df_mom.groupby("category")["curr_cost"].sum()
        cat_prev_s = df_mom.groupby("category")["prev_cost"].sum()
        all_cats   = sorted(set(cat_curr_s.index) | set(cat_prev_s.index))

        df_cat = pd.DataFrame({
            "Category": all_cats,
            "Current":  [cat_curr_s.get(c, 0) for c in all_cats],
            "Previous": [cat_prev_s.get(c, 0) for c in all_cats],
        })
        df_cat["Change %"] = df_cat.apply(
            lambda r: round((r["Current"] - r["Previous"]) / r["Previous"] * 100, 1)
            if r["Previous"] > 0 else None,
            axis=1,
        )
        df_cat = df_cat.sort_values("Current", ascending=False)

        curr_total  = df_mom["curr_cost"].sum()
        prev_total  = df_mom["prev_cost"].sum()
        overall_chg = round((curr_total - prev_total) / prev_total * 100, 1) if prev_total > 0 else None

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Current {days}d ({disp_currency})", fmt(curr_total, disp_currency),
                  delta=f"{overall_chg:+.1f}%" if overall_chg is not None else None,
                  delta_color="inverse")
        m2.metric(f"Previous {days}d ({disp_currency})", fmt(prev_total, disp_currency))
        growing   = df_cat[df_cat["Change %"].notna() & (df_cat["Change %"] > 0)]
        shrinking = df_cat[df_cat["Change %"].notna() & (df_cat["Change %"] < 0)]
        if not growing.empty:
            top_g = growing.nlargest(1, "Change %").iloc[0]
            m3.metric("Fastest Growing", top_g["Category"],
                      delta=f"+{top_g['Change %']:.1f}%", delta_color="inverse")
        if not shrinking.empty:
            top_s = shrinking.nsmallest(1, "Change %").iloc[0]
            m4.metric("Biggest Reduction", top_s["Category"],
                      delta=f"{top_s['Change %']:.1f}%", delta_color="normal")

        st.divider()

        fig_mom = go.Figure()
        fig_mom.add_trace(go.Bar(
            name=f"Previous {days}d",
            x=df_cat["Category"], y=df_cat["Previous"],
            marker_color=COLORS["blue2"], opacity=0.75,
            hovertemplate=f"Previous {days}d<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
        ))
        fig_mom.add_trace(go.Bar(
            name=f"Current {days}d",
            x=df_cat["Category"], y=df_cat["Current"],
            marker_color=COLORS["blue"],
            hovertemplate=f"Current {days}d<br><b>{disp_currency} %{{y:,.2f}}</b><extra></extra>",
        ))
        apply_plotly_theme(fig_mom)
        fig_mom.update_layout(
            height=340, barmode="group",
            xaxis_title=None, yaxis_title=f"Cost ({disp_currency})",
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
        )
        st.subheader(f"Category Comparison — Current {days}d vs Previous {days}d")
        st.plotly_chart(fig_mom, use_container_width=True, config=PLOTLY_CONFIG)

        cat_cols = st.columns(min(len(df_cat), 6))
        for i, (_, row) in enumerate(df_cat.iterrows()):
            if i >= 6:
                break
            chg = row["Change %"]
            with cat_cols[i]:
                st.metric(row["Category"], fmt(row["Current"], disp_currency),
                          delta=f"{chg:+.1f}%" if chg is not None else "N/A",
                          delta_color="inverse" if chg and chg > 0 else "normal")

        st.divider()
        df_cat_exp = df_cat.rename(columns={
            "Current":   f"Current {days}d ({disp_currency})",
            "Previous":  f"Previous {days}d ({disp_currency})",
        })
        _dl_header(f"MoM Category Comparison ({days}d)", df_cat_exp, "costs_mom_comparison")
        st.dataframe(df_cat_exp, use_container_width=True)
    else:
        st.info("No cost data. Run a sync first.")
