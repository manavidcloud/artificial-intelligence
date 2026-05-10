#!/bin/bash
# Lab 1 verification script
# Run AFTER terraform apply completes
# Usage: ./scripts/verify.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

echo ""
info "=== Lab 1 verification ==="
echo ""

# ── 1. Collect Terraform outputs ─────────────────────────────────────────────
info "Reading Terraform outputs..."
cd "$(dirname "$0")/../terraform"

AKS_NAME=$(terraform output -raw aks_cluster_name)
RG=$(terraform output -raw resource_group_name)
MI_CLIENT_ID=$(terraform output -raw managed_identity_client_id)
KV_NAME=$(terraform output -raw key_vault_name)
NAMESPACE=$(terraform output -raw k8s_namespace)
SA_NAME=$(terraform output -raw k8s_service_account_name)
OIDC_URL=$(terraform output -raw aks_oidc_issuer_url)

pass "Terraform outputs read"

# ── 2. Configure kubectl ──────────────────────────────────────────────────────
info "Fetching AKS credentials..."
az aks get-credentials --resource-group "$RG" --name "$AKS_NAME" --overwrite-existing --only-show-errors
pass "kubectl configured for cluster: $AKS_NAME"

# ── 3. Check nodes are Ready ──────────────────────────────────────────────────
info "Checking node readiness..."
NOT_READY=$(kubectl get nodes --no-headers | grep -v "Ready" | grep -v "SchedulingDisabled" | wc -l)
if [ "$NOT_READY" -eq 0 ]; then
  NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
  pass "All $NODE_COUNT nodes are Ready"
else
  fail "$NOT_READY node(s) are not Ready"
fi

# ── 4. Check Workload Identity webhook is running ─────────────────────────────
info "Checking Workload Identity webhook..."
WI_PODS=$(kubectl get pods -n kube-system -l app.kubernetes.io/name=workload-identity-webhook --no-headers 2>/dev/null | grep "Running" | wc -l)
if [ "$WI_PODS" -gt 0 ]; then
  pass "Workload Identity webhook running ($WI_PODS pod(s))"
else
  fail "Workload Identity webhook not found in kube-system"
fi

# ── 5. Check CSI secrets driver is running ────────────────────────────────────
info "Checking CSI Key Vault secrets provider..."
CSI_PODS=$(kubectl get pods -n kube-system -l app=secrets-store-csi-driver --no-headers 2>/dev/null | grep "Running" | wc -l)
if [ "$CSI_PODS" -gt 0 ]; then
  pass "CSI secrets driver running ($CSI_PODS pod(s))"
else
  fail "CSI secrets driver not found"
fi

# ── 6. Check namespace and ServiceAccount exist ───────────────────────────────
info "Checking namespace: $NAMESPACE..."
kubectl get namespace "$NAMESPACE" > /dev/null 2>&1 && pass "Namespace '$NAMESPACE' exists" || fail "Namespace '$NAMESPACE' missing"

info "Checking ServiceAccount: $SA_NAME..."
SA_CLIENT_ID=$(kubectl get serviceaccount "$SA_NAME" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.azure\.workload\.identity/client-id}' 2>/dev/null)
if [ "$SA_CLIENT_ID" = "$MI_CLIENT_ID" ]; then
  pass "ServiceAccount '$SA_NAME' annotated with correct MI client ID"
else
  fail "ServiceAccount client-id mismatch. Got: '$SA_CLIENT_ID', expected: '$MI_CLIENT_ID'"
fi

# ── 7. Deploy a debug pod and test Azure token acquisition ────────────────────
info "Deploying debug pod to test Workload Identity token..."

DEBUG_POD_NAME="wi-verify-$(date +%s)"

kubectl run "$DEBUG_POD_NAME" \
  --image=mcr.microsoft.com/azure-cli:latest \
  --restart=Never \
  --namespace="$NAMESPACE" \
  --serviceaccount="$SA_NAME" \
  --labels="azure.workload.identity/use=true" \
  --command -- sleep 120 \
  --overrides="{\"spec\":{\"nodeSelector\":{\"nodepool-type\":\"app\"}}}" \
  > /dev/null 2>&1

info "Waiting for debug pod to be Running..."
kubectl wait pod "$DEBUG_POD_NAME" -n "$NAMESPACE" --for=condition=Ready --timeout=90s > /dev/null 2>&1
pass "Debug pod is Running"

info "Testing az account get-access-token inside pod..."
TOKEN_OUTPUT=$(kubectl exec "$DEBUG_POD_NAME" -n "$NAMESPACE" -- \
  az account get-access-token \
    --resource "https://management.azure.com/" \
    --query "{tenant:tenant,expiresOn:expiresOn}" \
    -o json 2>/dev/null) || true

if echo "$TOKEN_OUTPUT" | grep -q "expiresOn"; then
  pass "Workload Identity token acquired successfully"
  echo "  Token details: $TOKEN_OUTPUT"
else
  fail "Could not acquire token inside pod — check federated credential and OIDC issuer"
fi

info "Testing Cost Management API access from pod..."
SUBS_OUTPUT=$(kubectl exec "$DEBUG_POD_NAME" -n "$NAMESPACE" -- \
  az rest \
    --method GET \
    --url "https://management.azure.com/subscriptions?api-version=2022-12-01" \
    --query "value[0].subscriptionId" \
    -o tsv 2>/dev/null) || true

if [ -n "$SUBS_OUTPUT" ]; then
  pass "Cost Management API reachable, first sub: $SUBS_OUTPUT"
else
  fail "Cannot reach Cost Management API — check MI RBAC assignments"
fi

info "Testing Key Vault access from pod..."
KV_TEST=$(kubectl exec "$DEBUG_POD_NAME" -n "$NAMESPACE" -- \
  az keyvault secret show \
    --vault-name "$KV_NAME" \
    --name "db-connection-string" \
    --query "value" -o tsv 2>/dev/null) || true

if [ -n "$KV_TEST" ]; then
  pass "Key Vault secret read successful"
else
  fail "Cannot read Key Vault secret — check MI 'Key Vault Secrets User' role"
fi

# ── 8. Cleanup debug pod ──────────────────────────────────────────────────────
info "Cleaning up debug pod..."
kubectl delete pod "$DEBUG_POD_NAME" -n "$NAMESPACE" --grace-period=0 > /dev/null 2>&1
pass "Debug pod deleted"

# ── 9. OIDC issuer URL sanity check ──────────────────────────────────────────
info "Checking OIDC issuer reachability..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${OIDC_URL}/.well-known/openid-configuration")
if [ "$HTTP_STATUS" = "200" ]; then
  pass "OIDC issuer endpoint reachable (HTTP $HTTP_STATUS)"
else
  fail "OIDC issuer returned HTTP $HTTP_STATUS — Workload Identity federation may fail"
fi

echo ""
pass "=== All Lab 1 checks passed. Ready for Lab 2. ==="
echo ""
info "Next step — Lab 2 (PostgreSQL + Redis):"
info "  Pass these outputs as variables to the Lab 2 terraform:"
echo ""
echo "  pe_subnet_id   = $(terraform output -raw pe_subnet_id)"
echo "  vnet_id        = $(terraform output -raw vnet_id)"
echo "  mi_client_id   = $MI_CLIENT_ID"
echo "  kv_name        = $KV_NAME"
echo "  namespace      = $NAMESPACE"
echo ""
