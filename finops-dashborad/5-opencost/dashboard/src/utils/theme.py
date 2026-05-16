"""Shared theme utilities for the K8s Cost Dashboard."""
import plotly.graph_objects as go
import streamlit as st

COLORS = {
    "blue":    "#2563EB",
    "blue2":   "#3B82F6",
    "teal":    "#0D9488",
    "green":   "#16A34A",
    "amber":   "#D97706",
    "red":     "#DC2626",
    "purple":  "#7C3AED",
    "pink":    "#DB2777",
    "cyan":    "#0891B2",
    "slate":   "#475569",
    "bg":      "#0F1117",
    "card":    "#1E2130",
    "border":  "#2D3748",
    "text":    "#E2E8F0",
    "muted":   "#94A3B8",
}

PALETTE = [
    COLORS["blue"], COLORS["teal"], COLORS["green"], COLORS["purple"],
    COLORS["amber"], COLORS["pink"], COLORS["cyan"], COLORS["red"],
    "#8B5CF6", "#F59E0B", "#10B981", "#EF4444",
]

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {COLORS["bg"]};
            color: {COLORS["text"]};
        }}
        [data-testid="stSidebar"] {{
            background-color: {COLORS["card"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        [data-testid="metric-container"] {{
            background: {COLORS["card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 12px 16px;
        }}
        div[data-testid="stExpander"] {{
            background: {COLORS["card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
        }}
        .stDataFrame {{ background: {COLORS["card"]}; }}
        div[data-testid="stTab"] button[aria-selected="true"] {{
            border-bottom: 2px solid {COLORS["blue"]};
            color: {COLORS["blue"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_plotly_theme(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["card"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif", size=12),
        xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        margin=dict(l=10, r=10, t=30, b=10),
        colorway=PALETTE,
    )
