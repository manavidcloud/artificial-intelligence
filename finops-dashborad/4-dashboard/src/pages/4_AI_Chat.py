"""FinOps Dashboard — AI Assistant Chat Page."""
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import ai_chat, ai_health
from utils.theme import apply_theme

st.set_page_config(page_title="AI Chat · FinOps", page_icon="🤖", layout="wide")
require_auth()
apply_theme()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_user()
    st.markdown("---")

    health = ai_health()
    if health:
        model = health.get("model", "unknown")
        st.success(f"AI Agent: Online")
        st.caption(f"Model: {model}")
    else:
        st.error("AI Agent: Offline")
        st.caption("Check that the AI agent pod is running.")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["_messages"] = []
        st.rerun()

    with st.expander("About"):
        st.caption(
            "Powered by **Azure OpenAI** (gpt-4.1-nano) and **LangGraph ReAct**. "
            "The agent has access to cost, resource, and Advisor data from the "
            "Platform API and reasons step-by-step before answering."
        )
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("🤖 FinOps AI Assistant")
st.caption(
    "Ask about your Azure spend, identify anomalies, and get actionable "
    "optimization recommendations — powered by Azure OpenAI."
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
if "_messages" not in st.session_state:
    st.session_state["_messages"] = []

# ─────────────────────────────────────────────────────────────────────────────
# Call AI if the last message is from the user (handles both chat_input and
# suggestion buttons — both paths end with a user message in state then rerun)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["_messages"] and st.session_state["_messages"][-1]["role"] == "user":
    with st.spinner("FinOps AI is thinking…"):
        resp = ai_chat(st.session_state["_messages"])

    if resp:
        ai_msg = {
            "role":       "assistant",
            "content":    resp.get("response", "No response."),
            "tool_calls": resp.get("tool_calls", []),
        }
    else:
        ai_msg = {
            "role":       "assistant",
            "content":    (
                "I couldn't reach the AI agent. Please verify that the AI agent "
                "service is running (`kubectl get pods -n ai`) and try again."
            ),
            "tool_calls": [],
        }

    st.session_state["_messages"].append(ai_msg)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Chat history display
# ─────────────────────────────────────────────────────────────────────────────
for msg in st.session_state["_messages"]:
    role    = msg["role"]
    content = msg["content"]
    if role == "user":
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin:8px 0;">'
            f'<div class="chat-user">{content}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="margin:8px 0;">'
            f'<div class="chat-ai">{content}</div></div>',
            unsafe_allow_html=True,
        )
        if msg.get("tool_calls"):
            tools_used = ", ".join(msg["tool_calls"])
            st.caption(f"🔧 Tools used: {tools_used}")

# ─────────────────────────────────────────────────────────────────────────────
# Suggested prompts (shown when chat is empty)
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state["_messages"]:
    st.markdown("#### Suggested questions")
    suggestions = [
        "What are my top 5 spending services this month?",
        "Show me the cost trend for the last 30 days",
        "What Advisor recommendations can save me the most money?",
        "How much have I spent on compute vs storage?",
        "Are there any high-impact cost optimization opportunities?",
        "Which resource group is driving the most spend?",
    ]
    col1, col2 = st.columns(2)
    for i, s in enumerate(suggestions):
        if (col1 if i % 2 == 0 else col2).button(s, key=f"suggest_{i}", use_container_width=True):
            st.session_state["_messages"].append({"role": "user", "content": s})
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Chat input — append user message and rerun; AI is called at top of next render
# ─────────────────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask about your Azure costs, resources, or optimization opportunities…")

if prompt:
    st.session_state["_messages"].append({"role": "user", "content": prompt})
    st.rerun()
