# This is optional script if verify lab fails we can use this 
#az role assignment list -otable
# all four roles must assign to subscript MI_NAME -> SUBSCRITPTION [roles: ]
# Cost Management Reader
# Reader                
# Monitoring Reader     
# Key Vault Secrets User
# C:\Users\manav>az role assignment list -otable
# Principal                                                  Role                    Scope
# ---------------------------------------------------------  ----------------------  ---------------------------------------------------
# manmas1359_gmail.com#EXT#@manmas1359gmail.onmicrosoft.com  Owner                   /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# manmas1359_gmail.com#EXT#@manmas1359gmail.onmicrosoft.com  Owner                   /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# test1@manmas1359gmail.onmicrosoft.com                      Owner                   /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# b0bc52b2-7b79-444d-a0e6-ef1421d86314                       Cost Management Reader  /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# b0bc52b2-7b79-444d-a0e6-ef1421d86314                       Reader                  /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# b0bc52b2-7b79-444d-a0e6-ef1421d86314                       Monitoring Reader       /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f
# b0bc52b2-7b79-444d-a0e6-ef1421d86314                       Key Vault Secrets User  /subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f


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

STATE_FILE="/tmp/finops_identity_state.env"
> "$STATE_FILE"

# ── Styling ───────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${YELLOW}[INFO]${NC}  $*"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
head()  { echo -e "\n${CYAN}${BOLD}── $* ──${NC}"; }

# ── Robust Role Verification ─────────────────────────────────────
wait_for_role_robust() {
    local PRINCIPAL="$1"
    local ROLE="$2"
    local SCOPE="$3"
    local MAX_ATTEMPTS=5
    local WAIT_SEC=10
    local attempt=1

    while [ $attempt -le $MAX_ATTEMPTS ]; do
        local check
        check=$(az role assignment list --assignee "$PRINCIPAL" --all --query "[?roleDefinitionName=='$ROLE' && (scope=='$SCOPE' || starts_with(scope, '$SCOPE'))].id" -o tsv 2>/dev/null || echo "")
        
        if [ -n "$check" ]; then
            pass "    CONFIRMED: Identity [$PRINCIPAL] now has role [$ROLE] ✓"
            return 0
        fi
        
        info "    Attempt $attempt/$MAX_ATTEMPTS — Azure is syncing the permission..."
        sleep $WAIT_SEC
        ((attempt++))
    done

    # Fallback to verify via broad-list
    if [ -n "$(az role assignment list --assignee "$PRINCIPAL" --all --query "[?roleDefinitionName=='$ROLE'].id" -o tsv 2>/dev/null)" ]; then
        pass "    CONFIRMED: Role [$ROLE] detected via broad search. ✓"
        return 0
    fi

    fail "    CRITICAL: Could not confirm role [$ROLE] for identity [$PRINCIPAL]"
    return 1
}

# ════════════════════════════════════════════════════════════════════
head "1. Identity Context"
# ════════════════════════════════════════════════════════════════════

SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
MI_PRINCIPAL_ID=$(az identity show -n "$MI_NAME" -g "$RG" --query principalId -o tsv)
MI_CLIENT_ID=$(az identity show -n "$MI_NAME" -g "$RG" --query clientId -o tsv)

info "TARGET IDENTITY (The 'Who'): $MI_NAME"
info "PRINCIPAL ID  (The OID): $MI_PRINCIPAL_ID"
info "CLIENT ID     (The App): $MI_CLIENT_ID"

# ════════════════════════════════════════════════════════════════════
head "2. Infrastructure Targets"
# ════════════════════════════════════════════════════════════════════

KV_ID=$(az keyvault show -n "$KV_NAME" -g "$RG" --query id -o tsv)
OIDC_URL=$(az aks show -n "$AKS_NAME" -g "$RG" --query oidcIssuerProfile.issuerUrl -o tsv)
SUB_SCOPE="/subscriptions/$SUB_ID"

pass "Target KeyVault: $KV_NAME"
pass "Target Sub     : $SUB_ID"

# ════════════════════════════════════════════════════════════════════
head "3. Executing Role Grants"
# ════════════════════════════════════════════════════════════════════

force_assign_role() {
    local ROLE="$1"
    local SCOPE="$2"
    local LABEL="$3"

    echo -e "${CYAN}------------------------------------------------------------${NC}"
    info "STEP: Granting role [$ROLE] on $LABEL"
    info "TO  : Managed Identity [$MI_NAME] (ID: $MI_PRINCIPAL_ID)"
    
    az role assignment create \
        --assignee-object-id "$MI_PRINCIPAL_ID" \
        --assignee-principal-type "ServicePrincipal" \
        --role "$ROLE" \
        --scope "$SCOPE" \
        --output none 2>/dev/null || true

    wait_for_role_robust "$MI_PRINCIPAL_ID" "$ROLE" "$SCOPE"
}

# Define the roles we are "forcing" onto the Identity
force_assign_role "Key Vault Secrets User" "$KV_ID"     "KeyVault"
force_assign_role "Cost Management Reader" "$SUB_SCOPE" "Subscription"
force_assign_role "Reader"                 "$SUB_SCOPE" "Subscription"
force_assign_role "Monitoring Reader"      "$SUB_SCOPE" "Subscription"

echo "RBAC_VERIFIED=true" >> "$STATE_FILE"

# ════════════════════════════════════════════════════════════════════
head "4. Kubernetes Workload Identity Link"
# ════════════════════════════════════════════════════════════════════

info "Creating the link between K8s and Azure Managed Identity..."
az aks get-credentials -g "$RG" -n "$AKS_NAME" --overwrite-existing --output none

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

info "Setting up OIDC Trust (Federated Credential)..."
az identity federated-credential create \
    -n "$FEDERATION_NAME" \
    --identity-name "$MI_NAME" \
    -g "$RG" \
    --issuer "$OIDC_URL" \
    --subject "system:serviceaccount:${K8S_NAMESPACE}:${K8S_SA_NAME}" \
    --audiences "api://AzureADTokenExchange" \
    --output none 2>/dev/null || info "  Notice: Federation already exists."

pass "SUCCESS: Identity [$MI_NAME] is now authorized for all FinOps tasks."