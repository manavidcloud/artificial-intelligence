"""Shared dark theme CSS and Plotly template."""
import plotly.graph_objects as go
import streamlit as st

DARK_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stApp"] {
    font-family: 'Inter', sans-serif !important;
    background: #0a0f1e !important;
    color: #e2e8f0 !important;
}
[data-testid="stApp"] { background: linear-gradient(135deg, #0a0f1e 0%, #0c1528 100%) !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1526 0%, #0a1020 100%) !important;
    border-right: 1px solid rgba(0,120,212,0.2) !important;
}
[data-testid="stSidebar"] .stMarkdown p { color: #94a3b8 !important; font-size: 12px; }
[data-testid="stSidebarNav"] a { color: #cbd5e1 !important; border-radius: 6px; }
[data-testid="stSidebarNav"] a:hover { background: rgba(0,120,212,0.12) !important; color: #60a5fa !important; }
[data-testid="stSidebarNav"] a[aria-current] { background: rgba(0,120,212,0.2) !important; color: #60a5fa !important; border-left: 3px solid #0078D4; }
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color: rgba(0,120,212,0.4) !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 12px !important; font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 28px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] svg { display: none; }
h1 { color: #f1f5f9 !important; font-size: 26px !important; font-weight: 700 !important; letter-spacing: -0.02em; }
h2 { color: #e2e8f0 !important; font-size: 18px !important; font-weight: 600 !important; }
h3 { color: #cbd5e1 !important; font-size: 15px !important; font-weight: 600 !important; }
hr { border-color: rgba(255,255,255,0.06) !important; }
.stButton > button {
    background: linear-gradient(135deg, #0078D4 0%, #005a9e 100%) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; letter-spacing: 0.02em;
    transition: opacity 0.2s, transform 0.1s;
}
.stButton > button:hover { opacity: 0.85 !important; transform: translateY(-1px); }
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #94a3b8 !important;
}
.stSelectbox > div > div, .stTextInput > div > div > input, .stNumberInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] thead tr th {
    background: rgba(0,120,212,0.15) !important;
    color: #94a3b8 !important; font-size: 11px !important;
    letter-spacing: 0.06em; text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stDataFrame"] tbody tr { border-bottom: 1px solid rgba(255,255,255,0.04) !important; }
[data-testid="stDataFrame"] tbody tr:hover { background: rgba(0,120,212,0.07) !important; }
[data-testid="stInfo"] { background: rgba(0,120,212,0.1) !important; border: 1px solid rgba(0,120,212,0.3) !important; border-radius: 8px !important; color: #93c5fd !important; }
[data-testid="stWarning"] { background: rgba(234,179,8,0.1) !important; border: 1px solid rgba(234,179,8,0.3) !important; border-radius: 8px !important; }
[data-testid="stError"] { background: rgba(239,68,68,0.1) !important; border: 1px solid rgba(239,68,68,0.3) !important; border-radius: 8px !important; }
[data-testid="stSuccess"] { background: rgba(34,197,94,0.1) !important; border: 1px solid rgba(34,197,94,0.3) !important; border-radius: 8px !important; }
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.03) !important; border-radius: 10px; border: 1px solid rgba(255,255,255,0.07); }
.stTabs [data-baseweb="tab"] { color: #94a3b8 !important; font-weight: 500; border-radius: 8px; }
.stTabs [aria-selected="true"] { background: rgba(0,120,212,0.2) !important; color: #60a5fa !important; }
.stProgress > div > div { background: linear-gradient(90deg, #0078D4, #60a5fa) !important; border-radius: 4px; }
.stProgress > div { background: rgba(255,255,255,0.06) !important; border-radius: 4px; }
.streamlit-expanderHeader { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.07) !important; border-radius: 8px !important; color: #e2e8f0 !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
/* Compact download buttons — Azure-portal style */
.stDownloadButton > button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #94a3b8 !important;
    border-radius: 6px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 5px 10px !important;
    letter-spacing: 0.04em;
    transition: all 0.15s;
    white-space: nowrap;
}
.stDownloadButton > button:hover {
    background: rgba(0,120,212,0.15) !important;
    border-color: rgba(0,120,212,0.4) !important;
    color: #60a5fa !important;
    transform: none !important;
}
.chat-user {
    background: linear-gradient(135deg, #0078D4 0%, #005a9e 100%);
    border-radius: 16px 16px 4px 16px; padding: 10px 14px;
    display: inline-block; max-width: 80%; color: white; margin: 4px 0;
}
.chat-ai {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 4px 16px 16px 16px; padding: 12px 16px;
    display: block; max-width: 85%; color: #e2e8f0;
    backdrop-filter: blur(10px);
}
</style>"""

PLOTLY_DARK = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter", "color": "#94a3b8", "size": 12},
    "xaxis": {
        "gridcolor": "#1e2d4a",
        "linecolor": "#1e2d4a",
        "tickcolor": "#94a3b8",
        "zerolinecolor": "#1e2d4a",
    },
    "yaxis": {
        "gridcolor": "#1e2d4a",
        "linecolor": "#1e2d4a",
        "tickcolor": "#94a3b8",
        "zerolinecolor": "#1e2d4a",
    },
    "colorway": [
        "#0078D4",
        "#60a5fa",
        "#38bdf8",
        "#a78bfa",
        "#f472b6",
        "#34d399",
        "#fbbf24",
        "#f87171",
    ],
    "margin": {"l": 40, "r": 20, "t": 30, "b": 40},
    "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"color": "#94a3b8"}},
    "hoverlabel": {
        "bgcolor": "#0d1526",
        "bordercolor": "#1e2d4a",
        "font": {"color": "#e2e8f0", "family": "Inter"},
    },
}


def apply_theme():
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def apply_plotly_theme(fig):
    fig.update_layout(**PLOTLY_DARK)
    return fig


COLORS = {
    "blue":   "#0078D4",
    "blue2":  "#60a5fa",
    "purple": "#a78bfa",
    "green":  "#34d399",
    "amber":  "#fbbf24",
    "red":    "#f87171",
    "teal":   "#38bdf8",
    "pink":   "#f472b6",
    "text":   "#E2E8F0",
    "slate":  "#64748B",
}

# Plotly modebar config — keep zoom/pan/save-PNG, remove clutter
PLOTLY_CONFIG: dict = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d",
        "toggleSpikelines", "hoverClosestCartesian",
        "hoverCompareCartesian", "resetScale2d",
    ],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}
