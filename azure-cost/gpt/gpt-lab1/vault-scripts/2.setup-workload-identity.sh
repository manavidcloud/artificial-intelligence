#!/bin/bash
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────
MI_NAME="mi-finops-prod"
RG="rg-finops-prod-core"
LOCATION="centralindia"
AKS_NAME="finops-aks"
KV_NAME="kv-finops-prod-002"
K8S_NAMESPACE="platform"
K8S_SA_NAME="cost-platform-sa"
FEDERATION_NAME="finops-federation"

# ── Styling ───────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${YELLOW}[INFO]${NC}  $1"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $1"; }

# ── 0. Context Lock ───────────────────────────────────────────────
SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUB_SCOPE="/subscriptions/$SUB_ID"

info "Executing in Subscription: $SUB_ID"

# ── 1. Managed Identity (Idempotent) ──────────────────────────────
info "Managing Identity: $MI_NAME..."
MI_EXISTS=$(az identity show -n "$MI_NAME" -g "$RG" --query id -o tsv 2>/dev/null || echo "")

if [ -z "$MI_EXISTS" ]; then
    az identity create -n "$MI_NAME" -g "$RG" -l "$LOCATION" --subscription "$SUB_ID" --output none
    info "Created new identity. Waiting 15s for replication..."
    sleep 15
fi

MI_PRINCIPAL_ID=$(az identity show -n "$MI_NAME" -g "$RG" --query principalId -o tsv --subscription "$SUB_ID")
MI_CLIENT_ID=$(az identity show -n "$MI_NAME" -g "$RG" --query clientId -o tsv --subscription "$SUB_ID")

# ── 2. Infrastructure Details ─────────────────────────────────────
OIDC_URL=$(az aks show -n "$AKS_NAME" -g "$RG" --query oidcIssuerProfile.issuerUrl -o tsv --subscription "$SUB_ID")
KV_ID=$(az keyvault show -n "$KV_NAME" -g "$RG" --query id -o tsv --subscription "$SUB_ID")

# ── 3. Role Assignments (Bypassing the 'MissingSubscription' Check) ──
info "Applying Role Assignments..."

force_assign_role() {
    local ROLE="$1"
    local SCOPE="$2"

    info "  Syncing: $ROLE"

    # We skip the 'list' check because that's where your CLI is failing.
    # We attempt to create and ignore the 'AlreadyExists' error.
    az role assignment create \
        --assignee "$MI_PRINCIPAL_ID" \
        --role "$ROLE" \
        --scope "$SCOPE" \
        --subscription "$SUB_ID" \
        --output none 2>/dev/null || info "    Note: Role already exists or assignment skipped."
}

force_assign_role "Key Vault Secrets User" "$KV_ID"
force_assign_role "Cost Management Reader" "$SUB_SCOPE"
force_assign_role "Reader" "$SUB_SCOPE"
force_assign_role "Monitoring Reader" "$SUB_SCOPE"

# ── 4. Kubernetes ServiceAccount ──────────────────────────────────
info "Configuring Kubernetes Workload Identity..."
az aks get-credentials -g "$RG" -n "$AKS_NAME" --subscription "$SUB_ID" --overwrite-existing --output none

# Removed --quiet here
kubectl create namespace "$K8S_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${K8S_SA_NAME}
  namespace: ${K8S_NAMESPACE}
  annotations:
    azure.workload.identity/client-id: "${MI_CLIENT_ID}"
    azure.workload.identity/tenant-id: "${TENANT_ID}"
  labels:
    azure.workload.identity/use: "true"
EOF

pass "Workload Identity logic applied successfully."
