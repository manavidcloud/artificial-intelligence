"""FinOps Dashboard — AI Assistant Chat Page with Context Awareness."""
import streamlit as st

from auth import require_auth, sidebar_user
from utils.api import ai_chat, ai_health, get
from utils.theme import apply_theme, COLORS
from utils.currency import convert, fmt

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
        st.success("AI Agent: Online")
        st.caption(f"Model: {health.get('model', 'unknown')}")
    else:
        st.error("AI Agent: Offline")
        st.caption("Check that the AI agent pod is running.")

    st.markdown("---")
    days = st.selectbox("Context Period", [7, 14, 30, 60], index=2,
                        format_func=lambda d: f"Last {d} days",
                        help="Time window sent as context to the AI")
    context_on = st.toggle("Dashboard Context", value=True,
                           help="Send current spend data as context to each message")

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["_messages"] = []
        st.rerun()

    with st.expander("How it works"):
        st.caption(
            "Powered by **Azure OpenAI** (gpt-4.1-nano) and **LangGraph ReAct**. "
            "The agent calls Platform API tools to fetch live cost, resource, and "
            "Advisor data, then synthesises an answer. With Dashboard Context on, "
            "it automatically knows your current spend, top services, and currency."
        )
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Build dashboard context snapshot (fetched once per page load)
# ─────────────────────────────────────────────────────────────────────────────
disp_currency = st.session_state.get("_currency", "USD")
_dashboard_context: str | None = None

if context_on:
    _summ  = get("/costs/summary",    {"days": days})
    _svc   = get("/costs/by-service", {"days": days, "limit": 5})
    _adv   = get("/advisor/summary")

    ctx_lines = [f"Time range: Last {days} days", f"Currency: {disp_currency}"]

    if _summ and _summ.get("data"):
        d = _summ["data"]
        src = d.get("currency", "USD")
        total = convert(d.get("total_cost", 0), src, disp_currency)
        prev  = convert(d.get("prev_period_cost", 0), src, disp_currency)
        ctx_lines.append(f"Total spend: {fmt(total, disp_currency)} {disp_currency}")
        if d.get("change_pct") is not None:
            ctx_lines.append(f"Period change vs previous: {d['change_pct']:+.1f}%")
        ctx_lines.append(f"Previous period spend: {fmt(prev, disp_currency)} {disp_currency}")

    if _svc and _svc.get("data"):
        svc_lines = []
        src2 = _svc["data"][0].get("currency", "USD") if _svc["data"] else "USD"
        for r in _svc["data"][:5]:
            cost = convert(r.get("total_cost", 0), src2, disp_currency)
            svc_lines.append(f"  - {r['service_name']}: {fmt(cost, disp_currency)}")
        if svc_lines:
            ctx_lines.append("Top 5 services by spend:")
            ctx_lines.extend(svc_lines)

    if _adv and _adv.get("data"):
        cost_rows = [r for r in _adv["data"] if r.get("category") == "Cost"]
        total_sav = sum(convert(r.get("total_savings", 0), "USD", disp_currency)
                        for r in cost_rows)
        total_cnt = sum(r.get("count", 0) for r in cost_rows)
        if total_cnt > 0:
            ctx_lines.append(
                f"Azure Advisor: {total_cnt} cost recommendations, "
                f"{fmt(total_sav, disp_currency)} {disp_currency} savings potential"
            )

    _dashboard_context = "\n".join(ctx_lines)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.title("🤖 FinOps AI Assistant")
st.caption(
    "Ask about your Azure spend in plain English. "
    "The AI fetches live data from your Platform API to answer with real numbers."
)

if context_on and _dashboard_context:
    with st.expander("📡 Context being sent to AI (click to inspect)", expanded=False):
        st.code(_dashboard_context, language="text")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
if "_messages" not in st.session_state:
    st.session_state["_messages"] = []

# ─────────────────────────────────────────────────────────────────────────────
# Call AI when last message is from user
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["_messages"] and st.session_state["_messages"][-1]["role"] == "user":
    with st.spinner("FinOps AI is thinking…"):
        resp = ai_chat(
            st.session_state["_messages"],
            context=_dashboard_context if context_on else None,
        )

    if resp:
        ai_msg = {
            "role":       "assistant",
            "content":    resp.get("response", "No response."),
            "tool_calls": resp.get("tool_calls", []),
        }
    else:
        ai_msg = {
            "role":    "assistant",
            "content": (
                "I couldn't reach the AI agent. "
                "Verify the pod is running: `kubectl get pods -n ai`"
            ),
            "tool_calls": [],
        }

    st.session_state["_messages"].append(ai_msg)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Chat history
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
            f'<div style="margin:8px 0;"><div class="chat-ai">{content}</div></div>',
            unsafe_allow_html=True,
        )
        if msg.get("tool_calls"):
            st.caption(f"🔧 Tools used: {', '.join(msg['tool_calls'])}")

# ─────────────────────────────────────────────────────────────────────────────
# Suggested prompts — shown when chat is empty, organised by category
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state["_messages"]:
    tab_cost, tab_bill, tab_opt = st.tabs(
        ["💰 Cost Analysis", "🧾 Explain the Bill", "🔧 Optimization"]
    )

    with tab_cost:
        prompts = [
            "What are my top 5 spending services this month?",
            "Show me the cost trend for the last 30 days",
            "How much have I spent on compute vs storage vs network?",
            "Which resource group is driving the most spend?",
            "How does my current spend compare to last month?",
            "Are there any unusual cost spikes in the past 30 days?",
        ]
        c1, c2 = st.columns(2)
        for i, p in enumerate(prompts):
            if (c1 if i % 2 == 0 else c2).button(p, key=f"cost_{i}", use_container_width=True):
                st.session_state["_messages"].append({"role": "user", "content": p})
                st.rerun()

    with tab_bill:
        st.caption(
            "These prompts help you understand confusing Azure billing line items "
            "in plain business language — useful for finance reviews."
        )
        prompts_bill = [
            "Explain what 'Bandwidth' charges mean on my Azure bill",
            "What is Azure Monitor charging me for and can I reduce it?",
            "Why does 'Azure Storage' appear as multiple line items?",
            "What is the difference between compute and AKS costs?",
            "Explain what Reserved Instance savings plans are and if I should use them",
            "Why did my bill jump on the 1st of the month?",
        ]
        c1b, c2b = st.columns(2)
        for i, p in enumerate(prompts_bill):
            if (c1b if i % 2 == 0 else c2b).button(p, key=f"bill_{i}", use_container_width=True):
                st.session_state["_messages"].append({"role": "user", "content": p})
                st.rerun()

    with tab_opt:
        prompts_opt = [
            "What are the highest-impact Advisor recommendations I should act on?",
            "How can I reduce my compute costs?",
            "Which resources look idle or orphaned and should I review them?",
            "What would my savings be if I bought Reserved Instances?",
            "How can I reduce my network/bandwidth costs?",
            "Give me a cost optimisation action plan for this month",
        ]
        c1o, c2o = st.columns(2)
        for i, p in enumerate(prompts_opt):
            if (c1o if i % 2 == 0 else c2o).button(p, key=f"opt_{i}", use_container_width=True):
                st.session_state["_messages"].append({"role": "user", "content": p})
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask about your Azure costs, explain a bill line item, or request optimisation tips…"
)
if prompt:
    st.session_state["_messages"].append({"role": "user", "content": prompt})
    st.rerun()
