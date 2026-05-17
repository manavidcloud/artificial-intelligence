"""FinOps Dashboard — Settings / Admin Page."""
import streamlit as st

from auth import require_auth, sidebar_user, is_admin
from utils.api import get, post
from utils.theme import apply_theme

st.set_page_config(page_title="Settings · FinOps", page_icon="⚙️", layout="wide")
require_auth()
apply_theme()

with st.sidebar:
    sidebar_user()
    st.markdown("---")
    st.caption("FinOps Platform v1.0")

st.title("⚙️ Settings")

if not is_admin():
    st.warning("You need **admin** role to access this page.")
    st.caption("Contact your FinOps administrator to request elevated access.")
    st.stop()

tab_sync, tab_alerts, tab_health = st.tabs(["Data Sync", "Email Alerts", "System Health"])

# ─────────────────────────────────────────────────────────────────────────────
# DATA SYNC
# ─────────────────────────────────────────────────────────────────────────────
with tab_sync:
    st.subheader("Manual Data Sync")
    st.caption(
        "Trigger individual or full sync operations from Azure. "
        "Use this after infrastructure changes or to refresh data on demand."
    )

    days = st.number_input(
        "Cost history (days)", min_value=1, max_value=365, value=30, step=1,
        help="Number of historical days to pull when syncing costs.",
    )
    st.divider()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("**Subscriptions**")
        st.caption("Sync Azure subscription list from environment.")
        if st.button("Sync Subscriptions", use_container_width=True):
            with st.spinner("Syncing…"):
                resp = post("/sync/subscriptions")
            if resp:
                st.success(f"{resp.get('rows', 0)} rows upserted")
            else:
                st.error("Failed — check API logs.")

    with c2:
        st.markdown("**Costs**")
        st.caption("Pull cost data from Azure Cost Management.")
        if st.button("Sync Costs", use_container_width=True):
            with st.spinner("Syncing…"):
                resp = post("/sync/costs", params={"days": days})
            if resp:
                st.success(f"{resp.get('rows', 0)} rows upserted")
            else:
                st.error("Failed — check API logs.")

    with c3:
        st.markdown("**Resources**")
        st.caption("Query Azure Resource Graph for inventory.")
        if st.button("Sync Resources", use_container_width=True):
            with st.spinner("Syncing…"):
                resp = post("/sync/resources")
            if resp:
                st.success(f"{resp.get('rows', 0)} rows upserted")
            else:
                st.error("Failed — check API logs.")

    with c4:
        st.markdown("**Advisor**")
        st.caption("Pull Azure Advisor Cost recommendations.")
        if st.button("Sync Advisor", use_container_width=True):
            with st.spinner("Syncing…"):
                resp = post("/sync/advisor")
            if resp:
                st.success(f"{resp.get('rows', 0)} rows upserted")
            else:
                st.error("Failed — check API logs.")

    st.divider()
    st.markdown("#### Full Sync")
    st.caption("Runs all four sync operations in sequence: subscriptions → costs → resources → advisor.")
    if st.button("Run Full Sync", type="primary"):
        with st.spinner("Running full sync — this may take a minute…"):
            resp = post("/sync/all", params={"days": days})
        if resp:
            st.success("Full sync complete!")
            results = resp.get("results", {})
            for key, val in results.items():
                if isinstance(val, int):
                    st.markdown(f"- **{key.title()}**: {val} rows")
                else:
                    st.error(f"- **{key.title()}**: {val}")
        else:
            st.error("Full sync failed — check Platform API connection and logs.")

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL ALERTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_alerts:
    st.subheader("Email Notification Testing")
    st.caption(
        "Test your SMTP configuration and trigger manual alert emails. "
        "SMTP settings are configured via `secrets.env` → Kubernetes secret."
    )

    col_test, col_digest = st.columns(2)

    with col_test:
        st.markdown("**Test Email**")
        st.caption("Sends a simple test message to all configured recipients.")
        if st.button("Send Test Email", use_container_width=True):
            with st.spinner("Sending…"):
                resp = post("/alerts/test")
            if resp:
                if resp.get("sent"):
                    st.success("Test email sent!")
                elif not resp.get("configured"):
                    st.warning(
                        "Email not configured. Set SMTP_HOST, SMTP_USER, "
                        "SMTP_PASSWORD, and ALERT_RECIPIENTS in secrets.env."
                    )
                else:
                    st.error("SMTP config present but send failed — check API logs.")
            else:
                st.error("API request failed.")

    with col_digest:
        st.markdown("**Daily Cost Digest**")
        st.caption("Builds and sends a digest from today's cost data.")
        digest_days = st.number_input("Digest period (days)", min_value=1, max_value=30, value=1)
        if st.button("Send Daily Digest", use_container_width=True):
            with st.spinner("Building digest…"):
                resp = post("/alerts/digest", params={"days": digest_days})
            if resp:
                if resp.get("sent"):
                    st.success(
                        f"Digest sent! Total: ${resp.get('total_cost', 0):,.2f} "
                        f"({resp.get('advisor_count', 0)} Advisor recommendations)"
                    )
                else:
                    st.warning("Digest built but email not sent — check SMTP config.")
            else:
                st.error("Failed to generate digest.")

    st.divider()
    st.markdown("#### Manual Alert Triggers")

    col_spike, col_budget = st.columns(2)

    with col_spike:
        st.markdown("**Cost Spike Alert**")
        spike_svc  = st.text_input("Service name", value="Virtual Machines")
        spike_prev = st.number_input("Previous cost ($)", value=1000.0, step=100.0)
        spike_curr = st.number_input("Current cost ($)",  value=2500.0, step=100.0)
        if st.button("Send Spike Alert", use_container_width=True):
            with st.spinner("Sending…"):
                resp = post("/alerts/cost-spike", params={
                    "service": spike_svc,
                    "prev":    spike_prev,
                    "curr":    spike_curr,
                    "currency": "USD",
                })
            if resp:
                st.success(f"Spike alert sent! Change: {resp.get('pct_change', 0):+.1f}%")
            else:
                st.error("Send failed.")

    with col_budget:
        st.markdown("**Budget Alert**")
        b_spent   = st.number_input("Amount spent ($)",  value=4500.0, step=100.0)
        b_budget  = st.number_input("Budget ($)",        value=5000.0, step=100.0)
        b_days    = st.number_input("Days remaining",    value=5, min_value=0)
        if st.button("Send Budget Alert", use_container_width=True):
            with st.spinner("Sending…"):
                resp = post("/alerts/budget", params={
                    "spent":           b_spent,
                    "budget":          b_budget,
                    "currency":        "USD",
                    "days_remaining":  b_days,
                })
            if resp:
                st.success(f"Budget alert sent! Consumed: {resp.get('pct_consumed', 0):.1f}%")
            else:
                st.error("Send failed.")

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM HEALTH
# ─────────────────────────────────────────────────────────────────────────────
with tab_health:
    st.subheader("System Health")

    col_api, col_subs = st.columns(2)

    with col_api:
        st.markdown("**Platform API**")
        health_resp = get("/health")
        if health_resp:
            status = health_resp.get("status", "unknown")
            db_status = health_resp.get("db", "unknown")
            ts = health_resp.get("timestamp", "—")
            if status == "healthy":
                st.success(f"Status: {status.upper()}")
            else:
                st.error(f"Status: {status.upper()}")
            st.caption(f"Database: {db_status}")
            st.caption(f"Checked at: {ts}")
        else:
            st.error("Platform API is unreachable.")
            st.caption("Verify the service is running: `kubectl get svc -n platform`")

    with col_subs:
        st.markdown("**Synced Subscriptions**")
        subs_resp = get("/subscriptions")
        if subs_resp:
            count = subs_resp.get("count", 0)
            st.info(f"{count} subscription(s) synced")
            for s in subs_resp.get("data", []):
                st.markdown(
                    f"- **{s.get('name', s.get('id', '—'))}**  "
                    f"State: `{s.get('state', '—')}`  "
                    f"Synced: {s.get('synced_at', '—')}"
                )
        else:
            st.warning("Could not fetch subscription list.")

    st.divider()
    st.markdown("**Useful kubectl Commands**")
    st.code(
        "# Check pod status\n"
        "kubectl get pods -A\n\n"
        "# Platform API logs\n"
        "kubectl logs -n platform -l app=finops-platform-api --tail=50\n\n"
        "# AI Agent logs\n"
        "kubectl logs -n ai -l app=finops-ai-agent --tail=50\n\n"
        "# Dashboard logs\n"
        "kubectl logs -n frontend -l app=finops-dashboard --tail=50\n\n"
        "# Port-forward Platform API locally\n"
        "kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80\n\n"
        "# Port-forward Dashboard locally\n"
        "kubectl port-forward -n frontend svc/finops-dashboard-svc 8501:80",
        language="bash",
    )
