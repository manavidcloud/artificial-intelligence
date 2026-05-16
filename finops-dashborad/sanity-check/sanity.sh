#!/usr/bin/env bash
# =============================================================================
# FinOps Platform — Sanity Check Script
# =============================================================================
# Usage:
#   chmod +x sanity-check/sanity.sh
#   ./sanity-check/sanity.sh
#
# What it checks:
#   1. kubectl connectivity
#   2. Pod health across all namespaces
#   3. Ingress and TLS certificate status
#   4. Platform API health (/health endpoint)
#   5. AI Agent health (/health endpoint)
#   6. Dashboard reachability (external URL)
#   7. Database connectivity (via platform-api logs)
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS="${GREEN}[PASS]${NC}"
FAIL="${RED}[FAIL]${NC}"
WARN="${YELLOW}[WARN]${NC}"
INFO="${BLUE}[INFO]${NC}"

DASHBOARD_URL="${DASHBOARD_URL:-https://app.manmas.online}"
API_URL="${API_URL:-https://api.manmas.online}"
AI_URL="${AI_URL:-https://ai.manmas.online}"

errors=0

echo ""
echo "============================================================"
echo "  FinOps Platform — Sanity Check"
echo "  $(date)"
echo "============================================================"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. kubectl connectivity
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [1/7] kubectl connectivity"
if kubectl cluster-info --request-timeout=5s &>/dev/null; then
    echo -e "${PASS} kubectl can reach the cluster"
    SERVER=$(kubectl cluster-info 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
    echo "       API server: $SERVER"
else
    echo -e "${FAIL} kubectl cannot reach the cluster — check your kubeconfig"
    echo "       Run: az aks get-credentials --name finops-aks --resource-group rg-finops-prod-core"
    ((errors++))
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 2. Pod health
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [2/7] Pod health"

check_pod() {
    local ns="$1" label="$2" name="$3"
    local status
    status=$(kubectl get pods -n "$ns" -l "app=$label" \
        -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    local ready
    ready=$(kubectl get pods -n "$ns" -l "app=$label" \
        -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
    if [[ "$status" == "Running" && "$ready" == "true" ]]; then
        echo -e "${PASS} $name  (namespace: $ns, status: $status)"
    elif [[ "$status" == "NotFound" ]]; then
        echo -e "${FAIL} $name  — no pod found in namespace $ns"
        ((errors++))
    else
        echo -e "${FAIL} $name  — status: $status, ready: $ready"
        echo "       Debug: kubectl describe pod -n $ns -l app=$label"
        echo "       Logs:  kubectl logs -n $ns -l app=$label --tail=30"
        ((errors++))
    fi
}

check_pod "platform" "finops-platform-api" "Platform API"
check_pod "ai"       "finops-ai-agent"     "AI Agent"
check_pod "frontend" "finops-dashboard"    "Dashboard"

# Check for any CrashLoopBackOff across all namespaces
CRASH_PODS=$(kubectl get pods -A 2>/dev/null | grep -i 'CrashLoopBackOff\|Error\|OOMKilled' || true)
if [[ -n "$CRASH_PODS" ]]; then
    echo -e "${WARN} Pods in error state:"
    echo "$CRASH_PODS" | sed 's/^/       /'
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 3. Ingress + TLS certificates
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [3/7] Ingress + TLS certificates"

# Ingress objects
for ns_ing in "frontend/finops-dashboard-ingress" "platform/finops-platform-api-ingress" "ai/finops-ai-agent-ingress"; do
    ns="${ns_ing%%/*}"
    ing="${ns_ing##*/}"
    if kubectl get ingress "$ing" -n "$ns" &>/dev/null; then
        echo -e "${PASS} Ingress $ing (ns: $ns) exists"
    else
        echo -e "${FAIL} Ingress $ing missing in namespace $ns"
        ((errors++))
    fi
done

# TLS certificates (cert-manager)
for cert_ns in "finops-dashboard-tls/frontend" "finops-platform-api-tls/platform" "finops-ai-agent-tls/ai"; do
    secret="${cert_ns%%/*}"
    ns="${cert_ns##*/}"
    ready=$(kubectl get certificate "$secret" -n "$ns" \
        -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "NotFound")
    if [[ "$ready" == "True" ]]; then
        expiry=$(kubectl get certificate "$secret" -n "$ns" \
            -o jsonpath='{.status.notAfter}' 2>/dev/null || echo "unknown")
        echo -e "${PASS} TLS cert $secret (ns: $ns) — Ready, expires: $expiry"
    elif [[ "$ready" == "NotFound" ]]; then
        echo -e "${WARN} TLS cert $secret not found in namespace $ns (may not use cert-manager)"
    else
        echo -e "${FAIL} TLS cert $secret (ns: $ns) — Not Ready (status: $ready)"
        echo "       Debug: kubectl describe certificate $secret -n $ns"
        ((errors++))
    fi
done
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 4. Platform API health
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [4/7] Platform API health"

# Try external URL first, then fall back to port-forward
API_HEALTH_URL="$API_URL/health"
response=$(curl -sf --max-time 8 "$API_HEALTH_URL" 2>/dev/null || true)
if [[ -n "$response" ]]; then
    echo -e "${PASS} Platform API health OK via $API_HEALTH_URL"
    echo "       Response: $response"
else
    echo -e "${WARN} External URL unreachable — testing via kubectl exec"
    POD=$(kubectl get pod -n platform -l app=finops-platform-api \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [[ -n "$POD" ]]; then
        exec_resp=$(kubectl exec -n platform "$POD" -- \
            curl -sf http://localhost:8080/health 2>/dev/null || echo "FAILED")
        if [[ "$exec_resp" != "FAILED" ]]; then
            echo -e "${PASS} Platform API health OK (in-cluster): $exec_resp"
        else
            echo -e "${FAIL} Platform API /health returned error inside pod"
            ((errors++))
        fi
    else
        echo -e "${FAIL} No platform-api pod found"
        ((errors++))
    fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 5. AI Agent health
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [5/7] AI Agent health"

AI_HEALTH_URL="$AI_URL/health"
ai_response=$(curl -sf --max-time 8 "$AI_HEALTH_URL" 2>/dev/null || true)
if [[ -n "$ai_response" ]]; then
    echo -e "${PASS} AI Agent health OK via $AI_HEALTH_URL"
    echo "       Response: $ai_response"
else
    echo -e "${WARN} External URL unreachable — testing via kubectl exec"
    AI_POD=$(kubectl get pod -n ai -l app=finops-ai-agent \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [[ -n "$AI_POD" ]]; then
        ai_exec=$(kubectl exec -n ai "$AI_POD" -- \
            curl -sf http://localhost:8000/health 2>/dev/null || echo "FAILED")
        if [[ "$ai_exec" != "FAILED" ]]; then
            echo -e "${PASS} AI Agent health OK (in-cluster): $ai_exec"
        else
            echo -e "${FAIL} AI Agent /health returned error inside pod"
            ((errors++))
        fi
    else
        echo -e "${FAIL} No ai-agent pod found"
        ((errors++))
    fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 6. Dashboard reachability
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [6/7] Dashboard reachability"

http_code=$(curl -so /dev/null -w "%{http_code}" --max-time 10 "$DASHBOARD_URL" 2>/dev/null || echo "000")
if [[ "$http_code" == "200" ]]; then
    echo -e "${PASS} Dashboard reachable at $DASHBOARD_URL (HTTP $http_code)"
elif [[ "$http_code" == "302" || "$http_code" == "301" ]]; then
    echo -e "${PASS} Dashboard reachable at $DASHBOARD_URL (HTTP $http_code — redirect, normal for HTTPS)"
elif [[ "$http_code" == "000" ]]; then
    echo -e "${FAIL} Dashboard not reachable at $DASHBOARD_URL (connection refused or timeout)"
    ((errors++))
else
    echo -e "${WARN} Dashboard returned HTTP $http_code at $DASHBOARD_URL"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 7. Recent platform-api logs (database + sync status)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${INFO} [7/7] Platform API recent logs (last 20 lines)"

API_POD=$(kubectl get pod -n platform -l app=finops-platform-api \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [[ -n "$API_POD" ]]; then
    echo "       Pod: $API_POD"
    kubectl logs -n platform "$API_POD" --tail=20 2>/dev/null | sed 's/^/       /'

    # Flag common error patterns
    recent_logs=$(kubectl logs -n platform "$API_POD" --tail=50 2>/dev/null || true)
    if echo "$recent_logs" | grep -qi "password authentication failed"; then
        echo -e "${FAIL} DB password auth failure detected in logs"
        echo "       Fix: update secrets.env and re-run apply-secrets.sh, then rollout restart"
        ((errors++))
    fi
    if echo "$recent_logs" | grep -qi "no pg_hba"; then
        echo -e "${FAIL} PostgreSQL SSL rejection detected — sslmode=require must be set"
        ((errors++))
    fi
    if echo "$recent_logs" | grep -qi "error\|exception\|fatal" ; then
        echo -e "${WARN} Errors found in recent platform-api logs — review above"
    fi
else
    echo -e "${WARN} No platform-api pod found — skipping log check"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo "============================================================"
if [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}  All checks passed.${NC}"
else
    echo -e "${RED}  $errors check(s) failed. Review the output above.${NC}"
fi
echo "============================================================"
echo ""

exit $errors
