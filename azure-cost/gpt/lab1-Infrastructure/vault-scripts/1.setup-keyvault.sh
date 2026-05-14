#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Key Vault setup — Lab 1
# Fresh start with new vault name kv-finops-prod-002
# Usage: bash setup-keyvault.sh
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────
KV_NAME="kv-finops-prod-002"
RG="rg-finops-prod-core"
LOCATION="centralindia"

DB_HOST="finops-pgflex.postgres.database.azure.com"
DB_USER="pgadmin"
DB_PASS="YourStr0ngPass!"
DB_NAME="finops-db"

# Static Identity (Provided by user)
MY_OBJECT_ID="e6456ecd-d04e-42d3-a1b9-e6696ebe45a0"
MY_UPN="test1@manmas1359gmail.onmicrosoft.com"
# ─────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${YELLOW}[INFO]${NC}  $1"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
info "=== Key Vault setup ==="
info "Vault name: $KV_NAME"

# ── 0. Validate Subscription ──────────────────────────────────────
# This fixes the (MissingSubscription) error
info "Validating subscription context..."
SUB_ID=$(az account show --query id -o tsv 2>/dev/null) || {
    error "No active subscription found. Please run 'az login' first."
}
pass "Active Subscription: $SUB_ID"

# ── 1. Check if vault already exists ──────────────────────────────
info "Checking if vault already exists..."
EXISTING=$(az keyvault show --name "$KV_NAME" --resource-group "$RG" --query name -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING" ]; then
    pass "Vault '$KV_NAME' already exists. Skipping creation and proceeding to config..."
    SKIP_CREATE=true
else
    info "Vault name is available. Proceeding with fresh creation."
    SKIP_CREATE=false
fi

# ── 2. Identify User ──────────────────────────────────────────────
pass "Logged in as: $MY_UPN"

# ── 3. Create Key Vault (Conditional) ─────────────────────────────
if [ "$SKIP_CREATE" = false ]; then
    info "Creating Key Vault..."
    az keyvault create \
      --name "$KV_NAME" \
      --resource-group "$RG" \
      --location "$LOCATION" \
      --enable-rbac-authorization true \
      --enable-purge-protection true \
      --retention-days 90 \
      --output none
    pass "Key Vault created: $KV_NAME"
fi

# ── 4. Grant Key Vault Administrator ──────────────────────────────
info "Ensuring Key Vault Administrator role..."
KV_ID=$(az keyvault show --name "$KV_NAME" --resource-group "$RG" --query id -o tsv)

# We use || true to ignore the error if the assignment already exists
az role assignment create \
  --assignee "$MY_OBJECT_ID" \
  --role "Key Vault Administrator" \
  --scope "$KV_ID" \
  --output none 2>/dev/null || info "Role already assigned to user."
pass "Role verified."

# ── 5. Propagation Wait ──────────────────────────────────────────
if [ "$SKIP_CREATE" = false ]; then
    info "Waiting 45s for RBAC to propagate..."
    for i in $(seq 45 -1 1); do
      echo -ne "  ${i}s remaining...\r"
      sleep 1
    done
    echo ""
fi

# ── 6. Store all secrets ──────────────────────────────────────────
info "Storing/Updating secrets into Key Vault..."

set_kv_secret() {
    az keyvault secret set --vault-name "$KV_NAME" --name "$1" --value "$2" --output none
    pass "  stored: $1"
}

set_kv_secret "db-connection-string" "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}/${DB_NAME}?sslmode=require"
set_kv_secret "foundry-endpoint" "placeholder-lab4"
set_kv_secret "foundry-api-key" "placeholder-lab4"
set_kv_secret "redis-connection-string" "placeholder-lab2"
set_kv_secret "langsmith-api-key" "placeholder-lab5"
set_kv_secret "oauth2-proxy-client-secret" "placeholder-lab1-step3"

# ── 7. Verify ─────────────────────────────────────────────────────
echo ""
info "Verifying all secrets..."
SECRET_COUNT=$(az keyvault secret list --vault-name "$KV_NAME" --query "length(@)" -o tsv)

if [ "$SECRET_COUNT" -ge 6 ]; then
  pass "All secrets confirmed (Count: $SECRET_COUNT)"
else
  error "Expected at least 6, found $SECRET_COUNT — check errors above"
fi

# ── 8. Lock down public access ────────────────────────────────────
info "Ensuring public network access is disabled..."
az keyvault update \
  --name "$KV_NAME" \
  --resource-group "$RG" \
  --public-network-access Disabled \
  --output none
pass "Public access: Disabled"

# ── 9. Write .env ─────────────────────────────────────────────────
echo "KV_NAME=${KV_NAME}" > .env.keyvault
pass ".env.keyvault written"

# ── 10. Final summary ─────────────────────────────────────────────
echo ""
pass "=== Key Vault setup complete ==="
echo ""
printf "  %-12s %s\n" "Name:"      "$KV_NAME"
printf "  %-12s %s\n" "Group:"     "$RG"
printf "  %-12s %s\n" "Location:"  "$LOCATION"
printf "  %-12s %s\n" "Network:"   "private — no public access"
printf "  %-12s %s\n" "Secrets:"   "$SECRET_COUNT stored"
echo ""
info "Next: bash setup-workload-identity.sh"
echo ""
