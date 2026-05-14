#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Lab 1 final verification
# Run AFTER all three setup scripts complete
# Usage: bash verify-lab1.sh
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

KV_NAME="kv-finops-prod-002"
MI_NAME="mi-finops-prod"
RG="rg-finops-prod-core"
AKS_NAME="finops-aks"
K8S_SA="cost-platform-sa"
K8S_NS="platform"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass()  { echo -e "${GREEN}[PASS]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; FAILED=1; }
info()  { echo -e "${YELLOW}[INFO]${NC} $1"; }
FAILED=0

echo ""
info "=== Lab 1 verification ==="
echo ""

# AKS
kubectl get nodes --no-headers | grep -q "Ready" \
  && pass "AKS nodes Ready" || fail "AKS nodes not Ready"

# Namespaces
kubectl get namespace platform  &>/dev/null && pass "Namespace: platform"  || fail "Namespace missing: platform"
kubectl get namespace security  &>/dev/null && pass "Namespace: security"  || fail "Namespace missing: security"

# ServiceAccount + Workload Identity annotation
SA_CLIENT=$(kubectl get sa $K8S_SA -n $K8S_NS \
  -o jsonpath='{.metadata.annotations.azure\.workload\.identity/client-id}' 2>/dev/null)
MI_CLIENT=$(az identity show --name $MI_NAME --resource-group $RG --query clientId -o tsv 2>/dev/null)
[ "$SA_CLIENT" = "$MI_CLIENT" ] \
  && pass "Workload Identity: ServiceAccount annotated correctly" \
  || fail "Workload Identity: annotation mismatch (got: $SA_CLIENT)"

# Key Vault secrets
SECRET_COUNT=$(az keyvault update --name $KV_NAME --resource-group $RG \
  --public-network-access Enabled --output none 2>/dev/null; sleep 5; \
  az keyvault secret list --vault-name $KV_NAME --query "length(@)" -o tsv 2>/dev/null; \
  az keyvault update --name $KV_NAME --resource-group $RG \
  --public-network-access Disabled --output none 2>/dev/null)
[ "$SECRET_COUNT" -ge 6 ] \
  && pass "Key Vault: $SECRET_COUNT secrets stored" \
  || fail "Key Vault: expected 6 secrets, found $SECRET_COUNT"

# nginx ingress
kubectl get svc ingress-nginx-controller -n ingress-nginx &>/dev/null \
  && pass "nginx ingress: service exists" || fail "nginx ingress: not found"

EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
[ -n "$EXTERNAL_IP" ] \
  && pass "nginx ingress: External IP = $EXTERNAL_IP" \
  || fail "nginx ingress: no External IP yet"

# cert-manager
kubectl get pods -n cert-manager --no-headers 2>/dev/null | grep -q "Running" \
  && pass "cert-manager: running" || fail "cert-manager: not running"

# oauth2-proxy
kubectl get pods -n security --no-headers 2>/dev/null | grep -q "Running" \
  && pass "oauth2-proxy: running" || fail "oauth2-proxy: not running"

# PostgreSQL reachability (DNS only — private subnet)
az postgres flexible-server show \
  --name finops-pgflex \
  --resource-group rg-finops-prod-data \
  --query state -o tsv 2>/dev/null | grep -q "Ready" \
  && pass "PostgreSQL: state = Ready" || fail "PostgreSQL: not Ready"

# RBAC on MI
RBAC_COUNT=$(az role assignment list \
  --assignee "$MI_CLIENT" \
  --query "length(@)" -o tsv 2>/dev/null)
[ "$RBAC_COUNT" -ge 4 ] \
  && pass "RBAC: $RBAC_COUNT roles on Managed Identity" \
  || fail "RBAC: expected 4+ roles, found $RBAC_COUNT"

# Final result
echo ""
if [ "$FAILED" -eq 0 ]; then
  pass "=== All Lab 1 checks passed — ready for Lab 2 ==="
else
  fail "=== Some checks failed — fix above before Lab 2 ==="
  exit 1
fi
echo ""
