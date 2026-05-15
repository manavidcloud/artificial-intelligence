import os
import requests
import streamlit as st
import plotly.express as px 
import plotly.graph_objects as go 
import pandas as pd

AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://finops-ai-agent-svc.ai.svc.cluster.local")

st.set_page_config(
    page_title="FinOps AI Platform",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-header { font-size: 2rem; font-weight: 700; color: #0078D4; }
.status-ok   { color: #28a745; font-weight: bold; }
.status-warn { color: #fd7e14; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def call_agent(message: str) -> str:
    try:
        resp = requests.post(
            f"{AI_AGENT_URL}/chat",
            json={"message": message},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.exceptions.ConnectionError:
        return "Cannot connect to AI agent. Make sure finops-ai-agent pod is running in the ai namespace."
    except Exception as e:
        return f"Error: {str(e)}"


def check_agent_health() -> bool:
    try:
        resp = requests.get(f"{AI_AGENT_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## FinOps AI Platform")
    st.markdown("---")

    agent_ok = check_agent_health()
    if agent_ok:
        st.markdown('<span class="status-ok">AI Agent Online</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-warn">AI Agent Offline</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Quick Actions")

    if st.button("7-Day Cost Summary", use_container_width=True):
        st.session_state.quick_query = "Give me a detailed cost summary for the last 7 days broken down by service."

    if st.button("Detect Cost Spikes", use_container_width=True):
        st.session_state.quick_query = "Detect any cost spikes in the last 14 days and explain what might have caused them."

    if st.button("This Month's Spend", use_container_width=True):
        st.session_state.quick_query = "What is our total Azure spend this month? Is it on track?"

    if st.button("List Subscriptions", use_container_width=True):
        st.session_state.quick_query = "List all Azure subscriptions we are tracking and their sync status."

    if st.button("Cost by Subscription", use_container_width=True):
        st.session_state.quick_query = "Break down our Azure costs by subscription for the last 30 days."

    if st.button("Optimization Tips", use_container_width=True):
        st.session_state.quick_query = "Based on the cost data, give me the top 3 actionable recommendations to reduce Azure spend."

    if st.button("CTO Summary", use_container_width=True):
        st.session_state.quick_query = "Generate an executive summary of our Azure cloud spend suitable for a CTO briefing."

    st.markdown("---")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Main Area ─────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">Azure FinOps Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown("Ask questions about your Azure costs in plain English.")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle quick action buttons
query = None
if "quick_query" in st.session_state:
    query = st.session_state.pop("quick_query")

# Handle typed input
typed = st.chat_input("Ask about your Azure costs... e.g. 'Why did costs spike last Tuesday?'")
if typed:
    query = typed

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your Azure data..."):
            answer = call_agent(query)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
