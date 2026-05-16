"""FinOps Dashboard — Azure Advisor Intelligence Center."""
import io
import math
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import get
from utils.theme import apply_theme, apply_plotly_theme, COLORS, PLOTLY_CONFIG
from utils.currency import convert, fmt

st.set_page_config(page_title="Advisor · FinOps", page_icon="💡", layout="wide")
require_auth()
apply_theme()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _dl_header(title: str, df: pd.DataFrame, prefix: str) -> None:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:30])
    col_t, col_c, col_x = st.columns([7, 1, 1])
    with col_t:
        st.subheader(title)
    with col_c:
        st.download_button("⬇ CSV", data=df.to_csv(index=False).encode(),
                           file_name=f"{prefix}.csv", mime="text/csv",
                           use_container_width=True, key=f"csv_{prefix}")
    with col_x:
        st.download_button("⬇ Excel", data=buf.getvalue(),
                           file_name=f"{prefix}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, key=f"xlsx_{prefix}")


_IMPACT_ORDER  = {"High": 0, "Medium": 1, "Low": 2}
_IMPACT_COLORS = {"High": COLORS["red"], "Medium": COLORS["amber"], "Low": COLORS["green"]}

_COMPLEXITY_KW = {
    1: ["delete", "remove", "turn off", "deallocat", "shutdown", "unused", "idle", "orphan"],
    2: ["resize", "rightsize", "downgrade", "scale down", "sku", "tier", "underutil"],
    3: ["reserved instance", "savings plan", "reservation", "commitment", "purchase"],
    4: ["migrate", "redesign", "architecture", "refactor", "redeploy"],
}
_COMPLEXITY_LABELS = {1: "⚡ Quick Fix", 2: "🔧 Moderate", 3: "💰 Investment", 4: "🏗️ Project"}
_COMPLEXITY_COLORS = {1: COLORS["green"], 2: COLORS["teal"], 3: COLORS["amber"], 4: COLORS["red"]}
_COMPLEXITY_JITTER = {1: -0.12, 2: 0.0, 3: 0.12, 4: 0.0}

_RIGHTSIZE_KW = [
    "right", "resize", "scale", "underutil", "virtual machine", " vm ",
    "compute", "size", "sku", "tier", "downsize", "shutdown", "deallocat",
    "reserved instance", "savings plan",
]

_ALL_CATS = ["Cost", "Security", "Performance", "HighAvailability", "OperationalExcellence"]
_CAT_COLORS = {
    "Cost": COLORS["green"],
    "Security": COLORS["red"],
    "Performance": COLORS["blue"],
    "HighAvailability": COLORS["amber"],
    "OperationalExcellence": "#a78bfa",
}
_CAT_ICONS = {
    "Cost": "💰",
    "Security": "🔒",
    "Performance": "⚡",
    "HighAvailability": "🛡️",
    "OperationalExcellence": "⚙️",
}


def _complexity(rec: dict) -> int:
    text = (rec.get("short_description", "") + " " + rec.get("resource_name", "")).lower()
    for score in [1, 2, 3, 4]:
        if any(kw in text for kw in _COMPLEXITY_KW[score]):
            return score
    return 2


def _rg_from_id(resource_id: str) -> str:
    if not resource_id:
        return "Unknown"
    parts = resource_id.lower().split("/")
    try:
        idx = parts.index("resourcegroups")
        return resource_id.split("/")[idx + 1]
    except (ValueError, IndexError):
        return "Unknown"


def _is_rightsize(rec: dict) -> bool:
    text = " ".join([rec.get("short_description", ""), rec.get("resource_name", "")]).lower()
    return any(kw in text for kw in _RIGHTSIZE_KW)


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _clean_resource_name(name: str, sub_id: str, sid_map: dict,
                         resource_id: str = "",
                         res_lookup: dict | None = None) -> str:
    """Return the best human-readable resource name.

    Priority:
    1. Resource inventory name (from Azure Resource Graph via /resources endpoint)
    2. Last segment of the ARM resource_id path
    3. resource_name field if it is a plain string (not a UUID)
    4. Subscription display name if either field is the subscription UUID
    5. "Subscription-level" as final fallback
    """
    rid = (resource_id or "").strip()
    nm  = (name or "").strip()

    # 1. Direct lookup in resource inventory (most accurate — actual Azure name)
    if res_lookup and rid:
        inv_name = res_lookup.get(rid.lower())
        if inv_name:
            return inv_name

    # 2. ARM resource_id last segment  (e.g. /…/virtualMachines/my-vm → "my-vm")
    if rid and "/" in rid:
        last = rid.rstrip("/").split("/")[-1]
        if last and not _UUID_RE.match(last):
            return last

    # 3. resource_name plain string
    if nm and not _UUID_RE.match(nm):
        return nm.rstrip("/").split("/")[-1] if "/" in nm else nm

    # 4. UUID → subscription display name
    for candidate in [nm, rid, sub_id or ""]:
        if candidate and _UUID_RE.match(candidate.strip()):
            display = sid_map.get(candidate.strip())
            if display:
                return f"Subscription: {display}"

    return "Subscription-level"


def _clean_rg(resource_id: str, sub_id: str, sid_map: dict) -> str:
    """Return the resource group, or the subscription name for sub-level recs."""
    rg = _rg_from_id(resource_id or "")
    if rg != "Unknown":
        return rg
    display = sid_map.get(sub_id or "")
    return f"Sub: {display}" if display else "Subscription-level"


# ─── Sidebar ──────────────────────────────────────────────────────────────────
sub_id_to_name: dict = {}

with st.sidebar:
    sidebar_user()
    st.markdown("---")
    impact_filter = st.selectbox("Impact Level", ["All", "High", "Medium", "Low"])
    sub_filter = None
    subs_resp = get("/subscriptions")
    if subs_resp and subs_resp.get("data"):
        sub_map = {"All": None}
        for s in subs_resp["data"]:
            sub_map[s.get("name", s["id"])] = s["id"]
        sub_id_to_name = {v: k for k, v in sub_map.items() if v is not None}
        selected = st.selectbox("Subscription", list(sub_map.keys()))
        sub_filter = sub_map[selected]
    st.markdown("---")
    st.caption("FinOps Platform v1.0")


# ─── Fetch ────────────────────────────────────────────────────────────────────
disp_currency = st.session_state.get("_currency", "USD")

advisor_params: dict = {"category": "Cost"}
if impact_filter != "All":
    advisor_params["impact"] = impact_filter
if sub_filter:
    advisor_params["subscription_id"] = sub_filter

advisor_resp  = get("/advisor", advisor_params)
# all_cost_resp is used by every tab — respect subscription filter but not impact filter
_all_params: dict = {"category": "Cost"}
if sub_filter:
    _all_params["subscription_id"] = sub_filter
all_cost_resp = get("/advisor", _all_params)
summary_resp  = get("/advisor/summary")

# Resource inventory: id (ARM path) → name — used to resolve advisor resource_ids
_res_params: dict = {"limit": 2000}
if sub_filter:
    _res_params["subscription_id"] = sub_filter
_res_resp   = get("/resources", _res_params)
# Keyed by lowercase ARM ID for case-insensitive matching
_res_lookup: dict[str, str] = {
    r["id"].lower(): r["name"]
    for r in (_res_resp or {}).get("data", [])
    if r.get("id") and r.get("name")
}

all_data  = (all_cost_resp or {}).get("data", [])
filt_data = (advisor_resp  or {}).get("data", [])
summ_rows = (summary_resp  or {}).get("data", [])

cost_summ    = [r for r in summ_rows if r.get("category") == "Cost"]
total_savings = sum(convert(r.get("total_savings", 0), "USD", disp_currency) for r in cost_summ)
total_count   = sum(r.get("count", 0) for r in cost_summ)
high_rows     = [r for r in cost_summ if r.get("impact") == "High"]
high_savings  = sum(convert(r.get("total_savings", 0), "USD", disp_currency) for r in high_rows)
high_count    = sum(r.get("count", 0) for r in high_rows)

cat_scores: dict[str, float] = {}
for _cat in _ALL_CATS:
    _cat_recs = [r for r in summ_rows if r.get("category") == _cat]
    _deduction = sum(
        r.get("count", 0) * (15 if r.get("impact") == "High" else 8 if r.get("impact") == "Medium" else 3)
        for r in _cat_recs
    )
    cat_scores[_cat] = max(0.0, 100.0 - _deduction)

overall_score = sum(cat_scores.values()) / len(_ALL_CATS)


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("💡 Azure Advisor Intelligence Center")
st.caption("Cost optimization · security posture · performance · reliability — all in one view")

score_color = COLORS["green"] if overall_score >= 75 else COLORS["amber"] if overall_score >= 50 else COLORS["red"]

hdr_score, kpi1, kpi2, kpi3, kpi4 = st.columns([1.8, 1, 1, 1, 1])
with hdr_score:
    st.markdown(
        f"<div style='background:rgba(255,255,255,0.03); border:1px solid {score_color}33; "
        f"border-radius:14px; padding:18px 22px; text-align:center;'>"
        f"<div style='color:#94a3b8; font-size:11px; text-transform:uppercase; "
        f"letter-spacing:0.1em; margin-bottom:4px;'>Advisor Health Score</div>"
        f"<div style='font-size:54px; font-weight:900; color:{score_color}; line-height:1.05;'>"
        f"{overall_score:.0f}</div>"
        f"<div style='color:#64748b; font-size:11px; margin-top:4px;'>/ 100 across all pillars</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
kpi1.metric("Total Recommendations", total_count)
kpi2.metric(f"Total Savings ({disp_currency})", fmt(total_savings, disp_currency))
kpi3.metric("High Impact", high_count)
kpi4.metric(f"High-Impact Savings", fmt(high_savings, disp_currency))

st.markdown("---")

# 5-pillar score tiles
cat_cols = st.columns(5)
for _i, _cat in enumerate(_ALL_CATS):
    _sc = cat_scores[_cat]
    _c  = COLORS["green"] if _sc >= 75 else COLORS["amber"] if _sc >= 50 else COLORS["red"]
    _cnt = sum(r.get("count", 0) for r in summ_rows if r.get("category") == _cat)
    with cat_cols[_i]:
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.02); border:1px solid {_c}33; "
            f"border-radius:12px; padding:12px 14px; text-align:center; min-height:100px;'>"
            f"<div style='font-size:18px;'>{_CAT_ICONS[_cat]}</div>"
            f"<div style='color:#94a3b8; font-size:10px; margin:2px 0;'>{_cat}</div>"
            f"<div style='font-size:28px; font-weight:800; color:{_c};'>{_sc:.0f}</div>"
            f"<div style='color:#64748b; font-size:10px;'>{_cnt} open</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.divider()


# ─── Tabs ─────────────────────────────────────────────────────────────────────
(tab_matrix, tab_all, tab_leaderboard,
 tab_rg, tab_rightsize, tab_radar, tab_roi) = st.tabs([
    "🎯 Priority Matrix",
    "📋 All Recommendations",
    "🏆 Top Savings",
    "🏢 By Resource Group",
    "⚙️ Rightsizing",
    "📊 Advisor Score",
    "📈 12-Month ROI",
])


# ── Tab 1: Priority Matrix ─────────────────────────────────────────────────────
with tab_matrix:
    st.caption(
        "Position each recommendation by **effort vs savings**. "
        "Top-left = high savings, low effort = **act on these first**."
    )
    if all_data:
        rows_pm = []
        for rec in all_data:
            s    = convert(rec.get("potential_savings") or 0, rec.get("currency", "USD"), disp_currency)
            cx   = _complexity(rec)
            _sid = rec.get("subscription_id") or ""
            rows_pm.append({
                "desc":     (rec.get("short_description") or "")[:72],
                "resource": _clean_resource_name(rec.get("resource_name") or "", _sid, sub_id_to_name,
                                                  rec.get("resource_id") or "", _res_lookup),
                "impact":   (rec.get("impact") or "Low"),
                "savings":  s,
                "cx":       cx,
                "cx_label": _COMPLEXITY_LABELS[cx],
                "rg":       _clean_rg(rec.get("resource_id") or "", _sid, sub_id_to_name),
            })
        df_pm = pd.DataFrame(rows_pm)

        med_s   = df_pm["savings"].median() if len(df_pm) > 1 else df_pm["savings"].mean()
        y_max   = max(df_pm["savings"].max() * 1.18, med_s * 2)

        fig_pm = go.Figure()

        # Quadrant shading
        for (x0, x1, y0, y1, rgba) in [
            (0.5, 2.5, med_s, y_max,   "rgba(16,185,129,0.07)"),
            (2.5, 4.5, med_s, y_max,   "rgba(99,102,241,0.06)"),
            (0.5, 2.5, 0,    med_s,    "rgba(245,158,11,0.05)"),
            (2.5, 4.5, 0,    med_s,    "rgba(239,68,68,0.04)"),
        ]:
            fig_pm.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                             fillcolor=rgba, line_width=0)

        fig_pm.add_shape(type="line", x0=2.5, x1=2.5, y0=0, y1=y_max,
                         line=dict(color="#334155", width=1, dash="dash"))
        fig_pm.add_shape(type="line", x0=0.5, x1=4.5, y0=med_s, y1=med_s,
                         line=dict(color="#334155", width=1, dash="dash"))

        for label, x, y in [
            ("⚡ QUICK WINS",        1.5, y_max * 0.96),
            ("🏗️ MAJOR PROJECTS",   3.5, y_max * 0.96),
            ("🍃 LOW HANGING FRUIT", 1.5, med_s * 0.05 + 0.5),
            ("⚠️ QUESTIONABLE",      3.5, med_s * 0.05 + 0.5),
        ]:
            fig_pm.add_annotation(x=x, y=y, text=f"<b>{label}</b>",
                                  showarrow=False, font=dict(size=10, color="#475569"))

        for impact in ["High", "Medium", "Low"]:
            sub = df_pm[df_pm["impact"] == impact]
            if sub.empty:
                continue
            jit = _COMPLEXITY_JITTER.get(impact, 0)
            sizes = sub["savings"].apply(lambda v: max(10, min(55, math.sqrt(max(v, 1)) * 1.8)))
            fig_pm.add_trace(go.Scatter(
                x=sub["cx"] + jit,
                y=sub["savings"],
                mode="markers",
                name=impact,
                marker=dict(size=sizes, color=_IMPACT_COLORS[impact],
                            opacity=0.82, line=dict(width=1, color="rgba(255,255,255,0.15)")),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Resource: %{customdata[1]}<br>"
                    f"Savings: {disp_currency} %{{y:,.0f}}/yr<br>"
                    "Effort: %{customdata[2]}<br>"
                    "RG: %{customdata[3]}"
                    "<extra></extra>"
                ),
                customdata=list(zip(sub["desc"], sub["resource"], sub["cx_label"], sub["rg"])),
            ))

        apply_plotly_theme(fig_pm)
        fig_pm.update_layout(
            height=520,
            xaxis=dict(title="Implementation Effort",
                       tickvals=[1, 2, 3, 4],
                       ticktext=["⚡ Quick Fix", "🔧 Moderate", "💰 Investment", "🏗️ Project"],
                       range=[0.3, 4.7]),
            yaxis=dict(title=f"Annual Savings ({disp_currency})", tickformat=",.0f"),
            legend=dict(title="Impact"),
        )
        st.plotly_chart(fig_pm, use_container_width=True, config=PLOTLY_CONFIG)

        quick_wins = df_pm[(df_pm["cx"] <= 2) & (df_pm["savings"] >= med_s)].sort_values("savings", ascending=False)
        if not quick_wins.empty:
            st.markdown(
                f"#### ⚡ Quick Wins — {len(quick_wins)} opportunities · "
                f"{fmt(quick_wins['savings'].sum(), disp_currency)} total potential"
            )
            _green = COLORS["green"]
            for _, row in quick_wins.head(6).iterrows():
                c = _IMPACT_COLORS.get(row["impact"], "#94a3b8")
                st.markdown(
                    f"<div style='border-left:3px solid {c}; padding:8px 12px; margin:4px 0; "
                    f"background:rgba(255,255,255,0.02); border-radius:0 8px 8px 0;'>"
                    f"<b style='color:#e2e8f0;'>{row['desc']}</b> "
                    f"<span style='color:#94a3b8; font-size:12px;'>— {row['resource']}</span><br>"
                    f"<span style='color:{_green}; font-size:13px; font-weight:700;'>"
                    f"Save {fmt(row['savings'], disp_currency)}/yr</span> "
                    f"<span style='color:#64748b; font-size:11px;'>{row['cx_label']} · {row['rg']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No recommendations. Run a sync from the Home page.")


# ── Tab 2: All Recommendations ─────────────────────────────────────────────────
with tab_all:
    if filt_data:
        data = sorted(filt_data, key=lambda r: _IMPACT_ORDER.get(r.get("impact", "Low"), 3))
        st.caption(f"{len(data)} recommendations — use Impact Level in sidebar to filter")

        for rec in data:
            impact   = rec.get("impact", "")
            color    = _IMPACT_COLORS.get(impact, "#94a3b8")
            savings  = convert(rec.get("potential_savings") or 0, rec.get("currency", "USD"), disp_currency)
            desc     = rec.get("short_description") or "No description"
            cx       = _complexity(rec)
            cx_lbl   = _COMPLEXITY_LABELS[cx]
            cx_color = _COMPLEXITY_COLORS[cx]
            _sub_id  = rec.get("subscription_id") or ""
            _rid     = rec.get("resource_id") or ""
            rg       = _clean_rg(_rid, _sub_id, sub_id_to_name)
            res_name = _clean_resource_name(rec.get("resource_name") or "", _sub_id, sub_id_to_name, _rid, _res_lookup)
            sub_name = sub_id_to_name.get(_sub_id, _sub_id) if _sub_id else "N/A"

            with st.expander(f"{desc[:88]}{'…' if len(desc) > 88 else ''}"):
                col_info, col_sav = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f"<span style='background:{color}22; color:{color}; font-size:10px; "
                        f"padding:2px 8px; border-radius:999px; font-weight:700; "
                        f"border:1px solid {color}44;'>{impact}</span> "
                        f"<span style='background:{cx_color}22; color:{cx_color}; font-size:10px; "
                        f"padding:2px 8px; border-radius:999px; "
                        f"border:1px solid {cx_color}44;'>{cx_lbl}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Resource:** `{res_name}`")
                    st.markdown(f"**Description:** {desc}")
                    st.caption(f"Resource Group: {rg}  ·  Subscription: {sub_name}")
                    if rec.get("resource_id") and not _UUID_RE.match(rec.get("resource_id", "")):
                        st.caption(f"ARM ID: {rec['resource_id']}")
                with col_sav:
                    savings_str = fmt(savings, disp_currency) if savings else "N/A"
                    st.markdown(
                        f"<div style='text-align:center; padding:14px 10px; "
                        f"background:{color}0d; border:1px solid {color}44; border-radius:10px;'>"
                        f"<div style='color:#94a3b8; font-size:10px; font-weight:700; "
                        f"text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;'>Save / yr</div>"
                        f"<div style='color:{color}; font-size:20px; font-weight:700;'>{savings_str}</div>"
                        f"<div style='color:#64748b; font-size:10px; margin-top:4px;'>{cx_lbl}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()
        df_ex = pd.DataFrame(filt_data)
        # Resolve human-readable values before export
        df_ex["Resource Name"] = df_ex.apply(
            lambda r: _clean_resource_name(
                str(r.get("resource_name") or ""),
                str(r.get("subscription_id") or ""),
                sub_id_to_name,
                str(r.get("resource_id") or ""),
                _res_lookup,
            ), axis=1
        )
        df_ex["Resource Group"] = df_ex.apply(
            lambda r: _clean_rg(
                str(r.get("resource_id") or ""),
                str(r.get("subscription_id") or ""),
                sub_id_to_name,
            ), axis=1
        )
        df_ex["Subscription"] = df_ex["subscription_id"].apply(
            lambda x: sub_id_to_name.get(str(x), str(x)) if x else "N/A"
        )
        df_ex["Savings/yr"] = df_ex.apply(
            lambda r: fmt(convert(r.get("potential_savings") or 0,
                                  r.get("currency", "USD"), disp_currency), disp_currency), axis=1
        )
        df_show = df_ex[[
            "impact", "short_description", "Resource Name",
            "Resource Group", "Savings/yr", "Subscription",
        ]].copy()
        df_show = df_show.rename(columns={"impact": "Impact", "short_description": "Recommendation"})
        _dl_header("Export Recommendations", df_show, "advisor_all")
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.info("No recommendations found. Adjust the Impact filter or run a sync from the Home page.")


# ── Tab 3: Top Savings Leaderboard ────────────────────────────────────────────
with tab_leaderboard:
    if all_data:
        sorted_data = sorted(all_data, key=lambda r: r.get("potential_savings") or 0, reverse=True)
        top20 = sorted_data[:20]
        max_s = max(
            (convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency) for r in top20),
            default=1,
        ) or 1

        total_achievable = sum(
            convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
            for r in all_data
        )
        top_achievable = sum(
            convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
            for r in top20
        )
        cov_pct = top_achievable / total_achievable * 100 if total_achievable else 0

        lb1, lb2, lb3 = st.columns(3)
        lb1.metric(f"Total Achievable ({disp_currency})", fmt(total_achievable, disp_currency))
        lb2.metric(f"Top-20 Value ({disp_currency})", fmt(top_achievable, disp_currency))
        lb3.metric("Top-20 Coverage", f"{cov_pct:.0f}%",
                   help="Fraction of total savings potential captured by the top 20")

        st.divider()

        for rank, rec in enumerate(top20, 1):
            s       = convert(rec.get("potential_savings") or 0, rec.get("currency", "USD"), disp_currency)
            pct_bar = min(100, int(s / max_s * 100))
            impact  = rec.get("impact") or "Low"
            _sub_id  = rec.get("subscription_id") or ""
            color    = _IMPACT_COLORS.get(impact, "#94a3b8")
            cx       = _complexity(rec)
            _rid     = rec.get("resource_id") or ""
            rg       = _clean_rg(_rid, _sub_id, sub_id_to_name)
            res_name = _clean_resource_name(rec.get("resource_name") or "", _sub_id, sub_id_to_name, _rid, _res_lookup)
            sub_name = sub_id_to_name.get(_sub_id, _sub_id[:8] + "…" if _sub_id else "N/A")

            st.markdown(
                f"<div style='display:flex; align-items:center; gap:14px; "
                f"padding:10px 16px; background:rgba(255,255,255,0.02); "
                f"border-radius:10px; margin-bottom:6px; border:1px solid rgba(255,255,255,0.05);'>"
                f"<div style='font-size:20px; font-weight:900; color:#334155; "
                f"min-width:28px; text-align:right;'>#{rank}</div>"
                f"<div style='flex:1; min-width:0;'>"
                f"<div style='color:#e2e8f0; font-size:13px; font-weight:600; "
                f"white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                f"{(rec.get('short_description') or '')[:78]}</div>"
                f"<div style='color:#64748b; font-size:11px; margin-top:1px;'>"
                f"{res_name} · {rg} · {sub_name} · {_COMPLEXITY_LABELS[cx]}</div>"
                f"<div style='margin-top:6px; background:rgba(255,255,255,0.06); "
                f"border-radius:3px; height:5px;'>"
                f"<div style='background:{color}; height:5px; width:{pct_bar}%; "
                f"border-radius:3px;'></div></div>"
                f"</div>"
                f"<div style='text-align:right; min-width:90px;'>"
                f"<div style='color:{color}; font-size:16px; font-weight:700;'>{fmt(s, disp_currency)}</div>"
                f"<div style='color:#64748b; font-size:10px;'>/year</div>"
                f"<span style='color:{color}; font-size:10px; background:{color}22; "
                f"padding:1px 7px; border-radius:999px;'>{impact}</span>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No recommendations found. Run a sync from the Home page.")


# ── Tab 4: By Resource Group ──────────────────────────────────────────────────
with tab_rg:
    if all_data:
        rg_map: dict = {}
        for rec in all_data:
            _sid = rec.get("subscription_id") or ""
            rg = _clean_rg(rec.get("resource_id") or "", _sid, sub_id_to_name)
            if rg not in rg_map:
                rg_map[rg] = {"count": 0, "savings": 0.0, "high": 0, "recs": []}
            s = convert(rec.get("potential_savings") or 0, rec.get("currency", "USD"), disp_currency)
            rg_map[rg]["count"]   += 1
            rg_map[rg]["savings"] += s
            if rec.get("impact") == "High":
                rg_map[rg]["high"] += 1
            rg_map[rg]["recs"].append(rec)

        df_rg = pd.DataFrame([
            {"resource_group": rg, "count": v["count"],
             "savings": v["savings"], "high": v["high"]}
            for rg, v in rg_map.items()
        ]).sort_values("savings", ascending=False)

        st.caption(f"{len(df_rg)} resource groups with open cost recommendations")

        bar_colors = [COLORS["red"] if h > 0 else COLORS["amber"]
                      for h in df_rg["high"]]
        fig_rg = go.Figure(go.Bar(
            x=df_rg["resource_group"],
            y=df_rg["savings"],
            marker_color=bar_colors,
            text=df_rg["count"].apply(lambda n: f"{n} recs"),
            textposition="outside",
            hovertemplate="%{x}<br><b>" + disp_currency + " %{y:,.0f}</b><extra></extra>",
        ))
        apply_plotly_theme(fig_rg)
        fig_rg.update_layout(
            height=320,
            xaxis_title="Resource Group",
            yaxis_title=f"Savings Potential ({disp_currency})",
            showlegend=False,
        )
        st.subheader("Waste by Resource Group")
        st.plotly_chart(fig_rg, use_container_width=True, config=PLOTLY_CONFIG)

        st.divider()
        _green = COLORS["green"]
        for _, row in df_rg.iterrows():
            rg   = row["resource_group"]
            recs = sorted(rg_map[rg]["recs"],
                          key=lambda r: _IMPACT_ORDER.get(r.get("impact", "Low"), 3))
            c = COLORS["red"] if row["high"] > 0 else COLORS["amber"]
            with st.expander(
                f"**{rg}** — {row['count']} recs · "
                f"{fmt(row['savings'], disp_currency)}/yr · "
                f"{int(row['high'])} high-impact"
            ):
                for rec in recs:
                    imp  = rec.get("impact") or "Low"
                    ic   = _IMPACT_COLORS.get(imp, "#94a3b8")
                    s    = convert(rec.get("potential_savings") or 0,
                                   rec.get("currency", "USD"), disp_currency)
                    _rsid = rec.get("subscription_id") or ""
                    _rrid = rec.get("resource_id") or ""
                    _rn   = _clean_resource_name(rec.get("resource_name") or "", _rsid, sub_id_to_name, _rrid, _res_lookup)
                    st.markdown(
                        f"<div style='border-left:3px solid {ic}; padding:6px 10px; "
                        f"margin:3px 0; background:rgba(255,255,255,0.02); border-radius:0 6px 6px 0;'>"
                        f"<b style='color:#e2e8f0; font-size:13px;'>"
                        f"{(rec.get('short_description') or '')[:80]}</b><br>"
                        f"<span style='color:#94a3b8; font-size:11px;'>"
                        f"{_rn} · "
                        f"<span style='color:{ic};'>{imp}</span></span>"
                        f"<span style='float:right; color:{_green}; "
                        f"font-weight:700; font-size:13px;'>{fmt(s, disp_currency)}/yr</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()
        df_rg_ex = df_rg.copy()
        df_rg_ex.columns = ["Resource Group", "Recommendations",
                             f"Total Savings ({disp_currency})", "High Impact"]
        _dl_header("Export by Resource Group", df_rg_ex, "advisor_by_rg")
        st.dataframe(df_rg_ex, use_container_width=True)
    else:
        st.info("No recommendations found. Run a sync from the Home page.")


# ── Tab 5: Rightsizing Panel ───────────────────────────────────────────────────
with tab_rightsize:
    st.caption("VM sizing, Reserved Instances, and compute optimisation recommendations.")
    rs_data = [r for r in all_data if _is_rightsize(r)]

    if rs_data:
        rs_data.sort(key=lambda r: _IMPACT_ORDER.get(r.get("impact", "Low"), 3))
        total_rs = sum(
            convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
            for r in rs_data
        )
        rs1, rs2, rs3 = st.columns(3)
        rs1.metric("Rightsizing Recommendations", len(rs_data))
        rs2.metric(f"Total Savings ({disp_currency})", fmt(total_rs, disp_currency))
        rs3.metric("High-Impact", sum(1 for r in rs_data if r.get("impact") == "High"))

        st.divider()

        df_rs = pd.DataFrame(rs_data)
        df_rs["disp_savings"] = df_rs.apply(
            lambda row: convert(row.get("potential_savings") or 0,
                                row.get("currency", "USD"), disp_currency), axis=1
        )
        df_rs["label"]  = df_rs["resource_name"].fillna("Unknown").str[:40]
        df_rs["impact"] = df_rs["impact"].fillna("Low")
        df_rs = df_rs.sort_values("disp_savings", ascending=False).head(20)
        bar_colors = [_IMPACT_COLORS.get(i, COLORS["blue"]) for i in df_rs["impact"]]

        fig_rs = go.Figure(go.Bar(
            x=df_rs["disp_savings"], y=df_rs["label"], orientation="h",
            marker_color=bar_colors,
            hovertemplate=f"%{{y}}<br><b>Save: {disp_currency} %{{x:,.2f}}</b><extra></extra>",
            text=df_rs["impact"], textposition="outside",
        ))
        apply_plotly_theme(fig_rs)
        fig_rs.update_layout(
            height=max(320, len(df_rs) * 30),
            yaxis=dict(autorange="reversed"),
            xaxis_title=f"Potential Savings ({disp_currency})",
            yaxis_title=None, showlegend=False, margin=dict(r=80),
        )
        st.subheader(f"Top Rightsizing Opportunities ({disp_currency})")
        st.plotly_chart(fig_rs, use_container_width=True, config=PLOTLY_CONFIG)

        st.divider()
        st.subheader("Details")
        for rec in rs_data:
            imp   = rec.get("impact") or ""
            color = _IMPACT_COLORS.get(imp, "#94a3b8")
            s     = convert(rec.get("potential_savings") or 0, rec.get("currency", "USD"), disp_currency)
            cx    = _complexity(rec)
            _sid  = rec.get("subscription_id") or ""
            _rid  = rec.get("resource_id") or ""
            with st.expander(f"**[{imp}]** {(rec.get('short_description') or '')[:88]}"):
                ci, cs = st.columns([3, 1])
                with ci:
                    st.markdown(f"**Resource:** `{_clean_resource_name(rec.get('resource_name') or '', _sid, sub_id_to_name, _rid, _res_lookup)}`")
                    st.markdown(f"**RG:** {_clean_rg(_rid, _sid, sub_id_to_name)}")
                    st.markdown(f"**Subscription:** {sub_id_to_name.get(_sid, _sid) if _sid else 'N/A'}")
                    st.markdown(f"**Effort:** {_COMPLEXITY_LABELS[cx]}")
                    st.markdown(rec.get("short_description") or "")
                with cs:
                    st.markdown(
                        f"<div style='text-align:center; padding:14px 10px; "
                        f"background:{color}0d; border:1px solid {color}44; border-radius:10px;'>"
                        f"<div style='color:#94a3b8; font-size:10px; font-weight:700; "
                        f"text-transform:uppercase; margin-bottom:4px;'>Save / yr</div>"
                        f"<div style='color:{color}; font-size:18px; font-weight:700;'>"
                        f"{fmt(s, disp_currency)}</div></div>",
                        unsafe_allow_html=True,
                    )

        st.divider()
        df_rs_ex = df_rs[["label", "impact", "disp_savings"]].copy()
        df_rs_ex.columns = ["Resource", "Impact", f"Savings ({disp_currency})"]
        _dl_header("Export Rightsizing", df_rs_ex, "advisor_rightsizing")
        st.dataframe(df_rs_ex, use_container_width=True)
    else:
        st.info(
            "No rightsizing recommendations found. "
            "These appear when Azure Advisor identifies VM resize, Reserved Instance, "
            "or underutilised compute opportunities."
        )


# ── Tab 6: Advisor Score Radar ────────────────────────────────────────────────
with tab_radar:
    st.caption(
        "Advisor health score across all 5 pillars. "
        "Score = 100 − (High×15 + Medium×8 + Low×3). Target: ≥ 80."
    )

    scores_vals = [cat_scores[c] for c in _ALL_CATS]
    cat_labels  = ["Cost", "Security", "Performance", "High\nAvailability", "Operational\nExcellence"]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=scores_vals + [scores_vals[0]],
        theta=cat_labels + [cat_labels[0]],
        fill="toself",
        name="Current Score",
        fillcolor="rgba(99,102,241,0.15)",
        line=dict(color=COLORS["blue"], width=2),
        hovertemplate="%{theta}: <b>%{r:.0f}/100</b><extra></extra>",
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=[80] * len(_ALL_CATS) + [80],
        theta=cat_labels + [cat_labels[0]],
        fill="none",
        name="Target (80)",
        line=dict(color=COLORS["green"], width=1, dash="dot"),
        hoverinfo="skip",
    ))
    apply_plotly_theme(fig_radar)
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=9, color="#64748b"),
                            gridcolor="rgba(255,255,255,0.06)"),
            angularaxis=dict(tickfont=dict(size=11, color="#94a3b8")),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=440,
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    col_rad, col_detail = st.columns([2, 1])
    with col_rad:
        st.plotly_chart(fig_radar, use_container_width=True, config=PLOTLY_CONFIG)
    with col_detail:
        st.markdown("#### Pillar Scores")
        for cat in _ALL_CATS:
            sc    = cat_scores[cat]
            cnt   = sum(r.get("count", 0) for r in summ_rows if r.get("category") == cat)
            c     = COLORS["green"] if sc >= 75 else COLORS["amber"] if sc >= 50 else COLORS["red"]
            grade = "A" if sc >= 90 else "B" if sc >= 75 else "C" if sc >= 60 else "D" if sc >= 40 else "F"
            st.markdown(
                f"<div style='margin-bottom:12px;'>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:3px;'>"
                f"<span style='color:#94a3b8; font-size:12px;'>{_CAT_ICONS[cat]} {cat}</span>"
                f"<span style='color:{c}; font-size:13px; font-weight:700;'>{sc:.0f} "
                f"<span style='font-size:10px; background:{c}22; padding:1px 6px; "
                f"border-radius:999px;'>{grade}</span></span>"
                f"</div>"
                f"<div style='background:rgba(255,255,255,0.06); border-radius:3px; height:6px;'>"
                f"<div style='background:{c}; border-radius:3px; height:6px; "
                f"width:{sc:.0f}%;'></div></div>"
                f"<div style='color:#64748b; font-size:10px; margin-top:2px;'>"
                f"{cnt} open recommendations</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        other_recs = [r for r in summ_rows if r.get("category") != "Cost"]
        if other_recs:
            st.markdown("---")
            st.markdown("#### Non-Cost Detail")
            df_other = pd.DataFrame(other_recs)[["category", "impact", "count"]].copy()
            df_other.columns = ["Category", "Impact", "Count"]
            st.dataframe(df_other, use_container_width=True, hide_index=True)


# ── Tab 7: 12-Month ROI Projection ────────────────────────────────────────────
with tab_roi:
    st.caption(
        "Projected cumulative savings over 12 months under three scenarios. "
        "Quick fixes in month 1 · investments in month 2 · projects in month 4."
    )
    if all_data:
        quick_s   = sum(convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
                        for r in all_data if _complexity(r) <= 2)
        invest_s  = sum(convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
                        for r in all_data if _complexity(r) == 3)
        project_s = sum(convert(r.get("potential_savings") or 0, r.get("currency", "USD"), disp_currency)
                        for r in all_data if _complexity(r) == 4)

        months = list(range(1, 13))

        # Full implementation (phased): quick m1, invest m2, projects m4
        cum_a = []
        for m in months:
            v = quick_s * m / 12
            if m >= 2: v += invest_s * (m - 1) / 12
            if m >= 4: v += project_s * (m - 3) / 12
            cum_a.append(v)

        cum_b = [quick_s * m / 12 for m in months]

        fig_roi = go.Figure()
        fig_roi.add_trace(go.Scatter(
            x=months, y=cum_a, mode="lines+markers",
            name="🚀 Full Implementation (phased)",
            line=dict(color=COLORS["green"], width=3),
            fill="tozeroy", fillcolor="rgba(16,185,129,0.07)",
            hovertemplate=f"Month %{{x}}<br><b>{disp_currency} %{{y:,.0f}} cumulative</b><extra></extra>",
        ))
        fig_roi.add_trace(go.Scatter(
            x=months, y=cum_b, mode="lines+markers",
            name="⚡ Quick Wins Only",
            line=dict(color=COLORS["blue"], width=2, dash="dot"),
            hovertemplate=f"Month %{{x}}<br><b>{disp_currency} %{{y:,.0f}} cumulative</b><extra></extra>",
        ))
        fig_roi.add_trace(go.Scatter(
            x=months, y=[0] * 12, mode="lines", name="❌ Do Nothing",
            line=dict(color="#475569", width=1, dash="dash"), hoverinfo="skip",
        ))
        fig_roi.add_annotation(
            x=12, y=cum_a[-1], xanchor="left",
            text=f"<b>{fmt(cum_a[-1], disp_currency)}</b>",
            showarrow=True, arrowhead=2, arrowcolor=COLORS["green"],
            font=dict(color=COLORS["green"], size=12),
        )
        apply_plotly_theme(fig_roi)
        fig_roi.update_layout(
            height=400,
            xaxis=dict(title="Month", tickvals=months, ticktext=[f"M{m}" for m in months]),
            yaxis=dict(title=f"Cumulative Savings ({disp_currency})", tickformat=",.0f"),
            legend=dict(orientation="h", y=-0.18),
        )
        st.plotly_chart(fig_roi, use_container_width=True, config=PLOTLY_CONFIG)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric(f"Year-1 Full ({disp_currency})", fmt(cum_a[-1], disp_currency))
        r2.metric(f"Quick Wins ({disp_currency})", fmt(quick_s, disp_currency),
                  help="Can be actioned in days — delete, rightsize, shutdown")
        r3.metric(f"Investments ({disp_currency})", fmt(invest_s, disp_currency),
                  help="Reserved Instances, Savings Plans — needs budget approval")
        r4.metric(f"Projects ({disp_currency})", fmt(project_s, disp_currency),
                  help="Migration / redesign work — 1-3 months of engineering")

        st.divider()
        st.markdown("#### 📅 Recommended Roadmap")

        n_quick   = sum(1 for r in all_data if _complexity(r) <= 2)
        n_invest  = sum(1 for r in all_data if _complexity(r) == 3)
        n_project = sum(1 for r in all_data if _complexity(r) == 4)

        for (timeline, label, count, savings_val, action, c) in [
            ("Month 1",  "⚡ Quick Wins",   n_quick,   quick_s,
             "Delete orphaned resources · rightsize VMs · turn off idle services", COLORS["green"]),
            ("Month 2–3", "💰 Investments", n_invest,  invest_s,
             "Purchase Reserved Instances · commit to Savings Plans",               COLORS["amber"]),
            ("Month 4+", "🏗️ Projects",    n_project, project_s,
             "Architecture migrations · service redesigns",                         COLORS["red"]),
        ]:
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:16px; "
                f"padding:12px 16px; background:rgba(255,255,255,0.02); "
                f"border-left:4px solid {c}; border-radius:0 10px 10px 0; margin-bottom:6px;'>"
                f"<div style='min-width:80px; color:#64748b; font-size:12px;'>{timeline}</div>"
                f"<div style='flex:1;'>"
                f"<div style='color:#e2e8f0; font-weight:700;'>{label} — {count} recs</div>"
                f"<div style='color:#64748b; font-size:12px;'>{action}</div>"
                f"</div>"
                f"<div style='text-align:right; min-width:90px;'>"
                f"<div style='color:{c}; font-size:16px; font-weight:700;'>"
                f"{fmt(savings_val, disp_currency)}/yr</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No recommendations found. Run a sync from the Home page.")
