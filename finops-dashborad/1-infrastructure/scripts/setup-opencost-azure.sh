#!/usr/bin/env bash
# =============================================================================
# setup-opencost-azure.sh — OpenCost Azure Integration Setup
# =============================================================================
# Idempotent: checks each resource before creating; skips if already correct.
#
# Part A — Rate Card pricing (Service Principal → azure-service-key K8s secret)
# Part B — Cloud Cost billing export (Storage Account → cloud-costs K8s secret)
#
# Usage:
#   chmod +x setup-opencost-azure.sh
#   ./setup-opencost-azure.sh            # Part A + Part B
#   ./setup-opencost-azure.sh --part-a   # Rate Card only
#   ./setup-opencost-azure.sh --part-b   # Billing export only
#
# Requirements: azure-cli, kubectl (kubeconfig already set to finops-aks)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
LOCATION="centralindia"
RG_CORE="rg-finops-prod-core"
AKS_NAME="finops-aks"

OPENCOST_NAMESPACE="opencost"
OPENCOST_K8S_SECRET_RATECARD="azure-service-key"
OPENCOST_K8S_SECRET_CLOUDCOST="cloud-costs"

# Part A — Service Principal for Rate Card API
SP_NAME="opencost-ratecard-sp"
SP_ROLE_NAME="OpenCostRateCardRole"   # custom role — created here if absent

# Part B — Storage Account for Cost Management Export
STORAGE_RG="$RG_CORE"
STORAGE_ACCOUNT="finopsocexports"     # max 24 chars, lowercase alphanumeric only
EXPORT_CONTAINER="cost-exports"
EXPORT_NAME="finops-daily-export"

# Paths (relative to project root, resolved at run time)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
K8S_DIR="${PROJECT_ROOT}/4-dashboard/k8s"
SERVICE_KEY_FILE="${K8S_DIR}/opencost-service-key.json"
CLOUD_INTEGRATION_FILE="${K8S_DIR}/opencost-cloud-integration.json"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
RUN_PART_A=true
RUN_PART_B=true

for arg in "$@"; do
  case "$arg" in
    --part-a) RUN_PART_B=false ;;
    --part-b) RUN_PART_A=false ;;
    --help|-h)
      echo "Usage: $0 [--part-a | --part-b]"
      echo "  --part-a   Rate Card only (Service Principal + azure-service-key secret)"
      echo "  --part-b   Billing export only (Storage Account + Cost Export + cloud-costs secret)"
      echo "  (no flag)  Run both parts"
      exit 0
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

err()  { echo -e "${RED}[ERROR] $*${RESET}" >&2; exit 1; }
warn() { echo -e "${YELLOW}[WARN]  $*${RESET}" >&2; }
info() { echo -e "${CYAN}[INFO]  $*${RESET}"; }
ok()   { echo -e "${GREEN}[OK]    $*${RESET}"; }
skip() { echo -e "${CYAN}[SKIP]  $*${RESET}"; }

banner() {
  local msg="$*"
  local line
  line=$(printf '%0.s─' $(seq 1 ${#msg}))
  echo ""
  echo -e "${GREEN}┌─${line}─┐${RESET}"
  echo -e "${GREEN}│ ${msg} │${RESET}"
  echo -e "${GREEN}└─${line}─┘${RESET}"
}

# ---------------------------------------------------------------------------
# Existence helpers
# ---------------------------------------------------------------------------
exists_sp() {
  az ad sp list --display-name "$1" --query "[0].id" -o tsv 2>/dev/null | grep -q .
}

exists_role_def() {
  az role definition list --name "$1" --query "[0].id" -o tsv 2>/dev/null | grep -q .
}

exists_role_assignment() {
  local count
  count=$(az role assignment list \
    --assignee "$1" --role "$2" --scope "$3" \
    --query "length(@)" -o tsv 2>/dev/null || echo 0)
  [[ "${count:-0}" -gt 0 ]]
}

exists_storage() {
  az storage account show --name "$1" --resource-group "$2" \
    --query id -o tsv >/dev/null 2>&1
}

exists_container() {
  az storage container show \
    --name "$1" \
    --account-name "$2" \
    --account-key "$3" \
    --query name -o tsv >/dev/null 2>&1
}

exists_cost_export() {
  az costmanagement export show \
    --name "$1" \
    --scope "subscriptions/${SUBSCRIPTION_ID}" \
    --query name -o tsv >/dev/null 2>&1
}

k8s_secret_exists() {
  kubectl get secret "$1" -n "$2" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# PRE-FLIGHT
# ---------------------------------------------------------------------------
banner "PRE-FLIGHT CHECKS"

command -v az      >/dev/null 2>&1 || err "azure-cli not found. Install it and re-run."
command -v kubectl >/dev/null 2>&1 || err "kubectl not found. Install it and re-run."
command -v jq      >/dev/null 2>&1 || err "jq not found. Install it (apt/brew install jq) and re-run."

info "Checking Azure login..."
az account show >/dev/null 2>&1 || err "Not logged in to Azure. Run 'az login' first."

SUBSCRIPTION_ID=$(az account show --query id    -o tsv)
TENANT_ID=$(az       account show --query tenantId -o tsv)
info "Subscription : ${SUBSCRIPTION_ID}"
info "Tenant       : ${TENANT_ID}"

info "Checking kubectl connectivity to ${AKS_NAME}..."
if ! kubectl get nodes --no-headers >/dev/null 2>&1; then
  info "Fetching AKS credentials..."
  az aks get-credentials \
    --name "$AKS_NAME" --resource-group "$RG_CORE" \
    --overwrite-existing
fi
ok "kubectl connected: $(kubectl config current-context)"

info "Ensuring namespace: ${OPENCOST_NAMESPACE}"
kubectl create namespace "$OPENCOST_NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -
ok "Namespace ${OPENCOST_NAMESPACE} ready."

SUB_SCOPE="/subscriptions/${SUBSCRIPTION_ID}"

# ===========================================================================
# PART A — Rate Card Pricing via Service Principal
# ===========================================================================
if [[ "$RUN_PART_A" == true ]]; then

banner "PART A — Service Principal for Rate Card Pricing"

# ── A1: Custom role (OpenCostRateCardRole) ────────────────────────────────
banner "A1 — Custom Role: ${SP_ROLE_NAME}"

if exists_role_def "$SP_ROLE_NAME"; then
  skip "Custom role '${SP_ROLE_NAME}' already exists"
else
  info "Creating custom role '${SP_ROLE_NAME}'..."
  ROLE_DEF=$(jq -n \
    --arg name   "$SP_ROLE_NAME" \
    --arg sub    "$SUBSCRIPTION_ID" \
    '{
      Name: $name,
      Description: "Allows OpenCost to read Azure Rate Card pricing data",
      Actions: [
        "Microsoft.Compute/virtualMachines/vmSizes/read",
        "Microsoft.Resources/subscriptions/locations/read",
        "Microsoft.Resources/providers/read",
        "Microsoft.ContainerService/containerServices/read",
        "Microsoft.Commerce/RateCard/read"
      ],
      AssignableScopes: ["/subscriptions/\($sub)"]
    }')
  echo "$ROLE_DEF" > /tmp/opencost-role-def.json
  az role definition create --role-definition /tmp/opencost-role-def.json --query "id" -o tsv
  rm -f /tmp/opencost-role-def.json
  info "Waiting 30 s for role definition propagation..."
  sleep 30
  ok "Custom role created."
fi

# ── A2: Service Principal ─────────────────────────────────────────────────
banner "A2 — Service Principal: ${SP_NAME}"

if exists_sp "$SP_NAME"; then
  skip "Service principal '${SP_NAME}' already exists"
  SP_APP_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv)
  info "Existing SP appId: ${SP_APP_ID}"
  warn "Cannot retrieve existing password — if you need to regenerate it run:"
  warn "  az ad sp credential reset --id ${SP_APP_ID}"
  SP_PASSWORD="<existing-password-unknown>"
else
  info "Creating service principal '${SP_NAME}'..."
  SP_JSON=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role "$SP_ROLE_NAME" \
    --scopes "$SUB_SCOPE" \
    --output json)
  SP_APP_ID=$(echo "$SP_JSON" | jq -r '.appId')
  SP_PASSWORD=$(echo "$SP_JSON" | jq -r '.password')
  ok "Service principal created. appId: ${SP_APP_ID}"
fi

# ── A3: Role assignment (idempotent) ──────────────────────────────────────
if exists_role_assignment "$SP_APP_ID" "$SP_ROLE_NAME" "$SUB_SCOPE"; then
  skip "Role '${SP_ROLE_NAME}' already assigned to SP on subscription"
else
  info "Assigning '${SP_ROLE_NAME}' to service principal on subscription..."
  az role assignment create \
    --role "$SP_ROLE_NAME" \
    --assignee "$SP_APP_ID" \
    --scope "$SUB_SCOPE" \
    --query id -o tsv
  ok "Role assigned."
fi

# ── A4: Write service-key.json ────────────────────────────────────────────
banner "A4 — Write ${SERVICE_KEY_FILE}"

if [[ "$SP_PASSWORD" == "<existing-password-unknown>" ]]; then
  warn "Skipping service-key.json write — SP already existed and password is unavailable."
  warn "Either:"
  warn "  1. Populate ${SERVICE_KEY_FILE} manually from your records, OR"
  warn "  2. Reset the credential:  az ad sp credential reset --id ${SP_APP_ID}"
else
  info "Writing ${SERVICE_KEY_FILE}..."
  jq -n \
    --arg sub  "$SUBSCRIPTION_ID" \
    --arg app  "$SP_APP_ID" \
    --arg pass "$SP_PASSWORD" \
    --arg ten  "$TENANT_ID" \
    '{
      subscriptionId: $sub,
      serviceKey: {
        appId:       $app,
        displayName: "OpenCostAccess",
        password:    $pass,
        tenant:      $ten
      }
    }' > "$SERVICE_KEY_FILE"
  ok "Wrote ${SERVICE_KEY_FILE}"
  warn "This file contains a secret — it is in .gitignore and must NOT be committed."
fi

# ── A5: K8s secret azure-service-key ─────────────────────────────────────
banner "A5 — K8s Secret: ${OPENCOST_K8S_SECRET_RATECARD}"

if k8s_secret_exists "$OPENCOST_K8S_SECRET_RATECARD" "$OPENCOST_NAMESPACE"; then
  skip "K8s secret '${OPENCOST_K8S_SECRET_RATECARD}' already exists in ${OPENCOST_NAMESPACE}"
  warn "To update it: kubectl delete secret ${OPENCOST_K8S_SECRET_RATECARD} -n ${OPENCOST_NAMESPACE} && re-run this script"
else
  if [[ ! -f "$SERVICE_KEY_FILE" ]]; then
    err "${SERVICE_KEY_FILE} not found — populate it manually then re-run with --part-a"
  fi
  info "Creating K8s secret '${OPENCOST_K8S_SECRET_RATECARD}'..."
  kubectl create secret generic "$OPENCOST_K8S_SECRET_RATECARD" \
    --namespace "$OPENCOST_NAMESPACE" \
    --from-file=service-key.json="$SERVICE_KEY_FILE"
  ok "K8s secret '${OPENCOST_K8S_SECRET_RATECARD}' created."
fi

fi  # end PART A

# ===========================================================================
# PART B — Cloud Costs via Cost Management Export
# ===========================================================================
if [[ "$RUN_PART_B" == true ]]; then

banner "PART B — Azure Cost Management Export → Cloud Costs"

# ── B1: Storage Account ───────────────────────────────────────────────────
banner "B1 — Storage Account: ${STORAGE_ACCOUNT}"

if exists_storage "$STORAGE_ACCOUNT" "$STORAGE_RG"; then
  existing_sku=$(az storage account show \
    --name "$STORAGE_ACCOUNT" --resource-group "$STORAGE_RG" \
    --query "sku.name" -o tsv 2>/dev/null)
  skip "Storage account '${STORAGE_ACCOUNT}' already exists (SKU: ${existing_sku})"
else
  info "Creating storage account '${STORAGE_ACCOUNT}' in ${STORAGE_RG}..."
  az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$STORAGE_RG" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --access-tier Hot \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --query id -o tsv
  ok "Storage account created."
fi

STORAGE_KEY=$(az storage account keys list \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$STORAGE_RG" \
  --query "[0].value" -o tsv)
info "Storage access key retrieved."

# ── B2: Blob container ────────────────────────────────────────────────────
banner "B2 — Blob Container: ${EXPORT_CONTAINER}"

if exists_container "$EXPORT_CONTAINER" "$STORAGE_ACCOUNT" "$STORAGE_KEY"; then
  skip "Container '${EXPORT_CONTAINER}' already exists in storage account '${STORAGE_ACCOUNT}'"
else
  info "Creating container '${EXPORT_CONTAINER}'..."
  az storage container create \
    --name "$EXPORT_CONTAINER" \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --query created -o tsv
  ok "Container created."
fi

STORAGE_RESOURCE_ID=$(az storage account show \
  --name "$STORAGE_ACCOUNT" --resource-group "$STORAGE_RG" \
  --query id -o tsv)

# ── B2.5: Register resource provider ─────────────────────────────────────
banner "B2.5 — Register Microsoft.CostManagementExports RP"

RP_STATE=$(az provider show --namespace Microsoft.CostManagementExports \
  --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")

if [[ "$RP_STATE" == "Registered" ]]; then
  skip "Microsoft.CostManagementExports is already registered"
else
  info "Registering Microsoft.CostManagementExports (current state: ${RP_STATE})..."
  az provider register --namespace Microsoft.CostManagementExports
  info "Waiting for registration to complete (this can take ~60 s)..."
  for i in $(seq 1 20); do
    STATE=$(az provider show --namespace Microsoft.CostManagementExports \
      --query "registrationState" -o tsv 2>/dev/null || echo "Unknown")
    info "  attempt ${i}/20 — state: ${STATE}"
    [[ "$STATE" == "Registered" ]] && break
    sleep 10
  done
  STATE=$(az provider show --namespace Microsoft.CostManagementExports \
    --query "registrationState" -o tsv 2>/dev/null || echo "Unknown")
  if [[ "$STATE" != "Registered" ]]; then
    err "Microsoft.CostManagementExports did not reach Registered state (got: ${STATE}). Re-run the script once registration completes."
  fi
  ok "Microsoft.CostManagementExports registered."
fi

# ── B3: Cost Management Export ────────────────────────────────────────────
banner "B3 — Cost Management Export: ${EXPORT_NAME}"

# Compute today and +1y for the export recurrence end date
EXPORT_START=$(date -u +%Y-%m-%dT00:00:00Z 2>/dev/null || \
  python3 -c "from datetime import datetime; print(datetime.utcnow().strftime('%Y-%m-%dT00:00:00Z'))")
EXPORT_END=$(date -u -d "+1 year" +%Y-%m-%dT00:00:00Z 2>/dev/null || \
  python3 -c "from datetime import datetime, timedelta; print((datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%dT00:00:00Z'))")

if exists_cost_export "$EXPORT_NAME"; then
  skip "Cost Management Export '${EXPORT_NAME}' already exists"
else
  info "Creating daily actual-cost export '${EXPORT_NAME}'..."
  az costmanagement export create \
    --name "$EXPORT_NAME" \
    --scope "subscriptions/${SUBSCRIPTION_ID}" \
    --type ActualCost \
    --storage-account-id "$STORAGE_RESOURCE_ID" \
    --storage-container  "$EXPORT_CONTAINER" \
    --storage-directory  "exports" \
    --recurrence        "Daily" \
    --recurrence-period from="$EXPORT_START" to="$EXPORT_END" \
    --timeframe         "MonthToDate" \
    --query name -o tsv
  ok "Cost Management Export created."
fi

# Trigger an immediate run so data appears in the container without waiting 24 h
info "Triggering an immediate export run..."
az costmanagement export run \
  --name  "$EXPORT_NAME" \
  --scope "subscriptions/${SUBSCRIPTION_ID}" \
  && ok "Export run triggered — data will appear in the container within a few minutes." \
  || warn "Could not trigger immediate export run (this is non-fatal — the daily schedule will pick it up)."

# ── B4: Write cloud-integration.json ─────────────────────────────────────
banner "B4 — Write ${CLOUD_INTEGRATION_FILE}"

info "Writing ${CLOUD_INTEGRATION_FILE}..."
jq -n \
  --arg sub  "$SUBSCRIPTION_ID" \
  --arg acct "$STORAGE_ACCOUNT" \
  --arg cont "$EXPORT_CONTAINER" \
  --arg key  "$STORAGE_KEY" \
  '{
    azure: {
      storage: [
        {
          subscriptionID: $sub,
          account:        $acct,
          container:      $cont,
          path:           "exports",
          cloud:          "public",
          authorizer: {
            accessKey:     $key,
            account:       $acct,
            authorizerType: "AzureAccessKey"
          }
        }
      ]
    }
  }' > "$CLOUD_INTEGRATION_FILE"

ok "Wrote ${CLOUD_INTEGRATION_FILE}"
warn "This file contains a storage access key — it is in .gitignore and must NOT be committed."

# ── B5: K8s secret cloud-costs ────────────────────────────────────────────
banner "B5 — K8s Secret: ${OPENCOST_K8S_SECRET_CLOUDCOST}"

if k8s_secret_exists "$OPENCOST_K8S_SECRET_CLOUDCOST" "$OPENCOST_NAMESPACE"; then
  info "K8s secret '${OPENCOST_K8S_SECRET_CLOUDCOST}' already exists — updating it..."
  kubectl delete secret "$OPENCOST_K8S_SECRET_CLOUDCOST" -n "$OPENCOST_NAMESPACE"
fi

kubectl create secret generic "$OPENCOST_K8S_SECRET_CLOUDCOST" \
  --namespace "$OPENCOST_NAMESPACE" \
  --from-file=cloud-integration.json="$CLOUD_INTEGRATION_FILE"
ok "K8s secret '${OPENCOST_K8S_SECRET_CLOUDCOST}' created."

fi  # end PART B

# ===========================================================================
# SUMMARY
# ===========================================================================
banner "SETUP COMPLETE"

cat <<EOF

${GREEN}============================================================${RESET}
  OpenCost Azure Integration — Done
${GREEN}============================================================${RESET}

Subscription  : ${SUBSCRIPTION_ID}
Tenant        : ${TENANT_ID}
K8s namespace : ${OPENCOST_NAMESPACE}

EOF

if [[ "$RUN_PART_A" == true ]]; then
cat <<EOF
${GREEN}Part A — Rate Card Pricing${RESET}
  Service Principal : ${SP_NAME}  (appId: ${SP_APP_ID})
  Custom Role       : ${SP_ROLE_NAME}
  K8s Secret        : ${OPENCOST_NAMESPACE}/${OPENCOST_K8S_SECRET_RATECARD}
  Secret key file   : ${SERVICE_KEY_FILE}  ← in .gitignore, never commit

EOF
fi

if [[ "$RUN_PART_B" == true ]]; then
cat <<EOF
${GREEN}Part B — Cloud Cost Billing Export${RESET}
  Storage Account   : ${STORAGE_ACCOUNT}  (RG: ${STORAGE_RG})
  Container         : ${EXPORT_CONTAINER}/exports/
  Cost Export       : ${EXPORT_NAME}  (daily, ActualCost)
  K8s Secret        : ${OPENCOST_NAMESPACE}/${OPENCOST_K8S_SECRET_CLOUDCOST}
  Integration file  : ${CLOUD_INTEGRATION_FILE}  ← in .gitignore, never commit

EOF
fi

cat <<EOF
${YELLOW}Next steps:${RESET}
  1. If you haven't already, set AZURE_CLIENT_ID in opencost-helm-values.yaml:
       az identity show --name mi-finops-prod --resource-group rg-finops-prod-core --query clientId -o tsv
     Then paste it into 4-dashboard/k8s/opencost-helm-values.yaml → extraEnv[0].value

  2. Apply the updated Helm values:
       helm upgrade --install opencost opencost/opencost \\
         --namespace ${OPENCOST_NAMESPACE} \\
         -f 4-dashboard/k8s/opencost-helm-values.yaml

  3. Verify OpenCost picks up the secrets:
       kubectl rollout restart deployment/opencost -n ${OPENCOST_NAMESPACE}
       kubectl logs -n ${OPENCOST_NAMESPACE} -l app=opencost --tail=50 | grep -i cloud

  4. Cost export data lands in the storage container within a few minutes of the
     first export run.  OpenCost polls it periodically.  The ☁️ Cloud Costs tab
     in the dashboard will show data once the first export has been ingested.

${GREEN}============================================================${RESET}

EOF
