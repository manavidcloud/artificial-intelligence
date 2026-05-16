#!/usr/bin/env bash
# =============================================================================
# apply-secrets.sh — FinOps Platform Kubernetes Secrets & Workload Identity
# =============================================================================
# Reads secrets.env from the project root and applies them to the AKS cluster:
#   - Creates namespaces
#   - Creates Kubernetes secrets (never written to YAML files)
#   - Creates service accounts annotated for Workload Identity
#
# Usage:
#   chmod +x apply-secrets.sh
#   ./apply-secrets.sh
#
# Requirements: azure-cli, kubectl
# secrets.env must exist two levels up from this script (project root)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SECRETS_FILE="${PROJECT_ROOT}/secrets.env"

# ---------------------------------------------------------------------------
# Log helpers (colored output)
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
# STEP 0 — Source secrets.env
# ---------------------------------------------------------------------------
banner "STEP 0 — Loading secrets.env"

if [[ ! -f "$SECRETS_FILE" ]]; then
  err "secrets.env not found at: ${SECRETS_FILE}
  Copy secrets.env.template to secrets.env and populate it, then re-run."
fi

info "Sourcing: ${SECRETS_FILE}"
# shellcheck source=/dev/null
set -a
# shellcheck disable=SC1090
source "$SECRETS_FILE"
set +a
ok "secrets.env loaded."

# ---------------------------------------------------------------------------
# STEP 1 — Validate required variables
# ---------------------------------------------------------------------------
banner "STEP 1 — Validating Required Variables"

REQUIRED_VARS=(
  DB_HOST
  DB_NAME
  DB_USER
  DB_PASSWORD
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT
  MI_CLIENT_ID
  AZURE_SUBSCRIPTION_IDS
)

MISSING=0
for VAR in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!VAR:-}" ]]; then
    warn "Required variable not set or empty: ${VAR}"
    (( MISSING++ )) || true
  else
    ok "${VAR} is set."
  fi
done

if (( MISSING > 0 )); then
  err "${MISSING} required variable(s) are missing. Populate secrets.env and re-run."
fi

# AZURE_OPENAI_API_KEY is optional (Workload Identity preferred)
if [[ -z "${AZURE_OPENAI_API_KEY:-}" ]]; then
  warn "AZURE_OPENAI_API_KEY is not set — using Workload Identity (managed identity) for OpenAI auth."
else
  ok "AZURE_OPENAI_API_KEY is set (will be included in secrets)."
fi

# LANGSMITH_API_KEY is optional
if [[ -z "${LANGSMITH_API_KEY:-}" ]]; then
  warn "LANGSMITH_API_KEY is not set — LangSmith tracing will be disabled."
else
  ok "LANGSMITH_API_KEY is set (will be included in secrets)."
fi

# ---------------------------------------------------------------------------
# STEP 2 — Get AKS Kubeconfig
# ---------------------------------------------------------------------------
banner "STEP 2 — AKS Kubeconfig"

AKS_NAME="finops-aks"
RG_CORE="rg-finops-prod-core"

info "Fetching credentials for cluster: ${AKS_NAME}"
az aks get-credentials \
  --name "$AKS_NAME" \
  --resource-group "$RG_CORE" \
  --overwrite-existing

CURRENT_CTX=$(kubectl config current-context)
ok "kubectl context: ${CURRENT_CTX}"

# Quick connectivity check
info "Verifying cluster connectivity..."
kubectl get nodes --no-headers 2>/dev/null | awk '{print "[INFO]  Node: " $1 "  Status: " $2}' \
  || warn "Could not list nodes — cluster may still be starting."

# ---------------------------------------------------------------------------
# STEP 3 — Create Namespaces
# ---------------------------------------------------------------------------
banner "STEP 3 — Namespaces"

NAMESPACES=(platform ai frontend security monitoring)

for NS in "${NAMESPACES[@]}"; do
  info "Ensuring namespace: ${NS}"
  kubectl create namespace "$NS" \
    --dry-run=client -o yaml \
  | kubectl apply -f -
done

ok "All namespaces are ready."

# ---------------------------------------------------------------------------
# STEP 4 — Kubernetes Secrets
# ---------------------------------------------------------------------------
banner "STEP 4 — Kubernetes Secrets"

# Helper: build --from-literal flags only for variables that are set and non-empty.
# Usage: optional_literal VAR_NAME secret-key
optional_literal() {
  local var_name="$1"
  local secret_key="$2"
  local val="${!var_name:-}"
  if [[ -n "$val" ]]; then
    printf ' --from-literal=%s=%s' "$secret_key" "$val"
  fi
}

# ---- 4a. finops-platform-secret (platform namespace) ---------------------
info "Creating secret: finops-platform-secret in namespace: platform"

PLATFORM_ARGS=(
  --from-literal=DB_HOST="${DB_HOST}"
  --from-literal=DB_NAME="${DB_NAME}"
  --from-literal=DB_USER="${DB_USER}"
  --from-literal=DB_PASSWORD="${DB_PASSWORD}"
  --from-literal=AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}"
  --from-literal=AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT}"
  --from-literal=MI_CLIENT_ID="${MI_CLIENT_ID}"
  --from-literal=AZURE_SUBSCRIPTION_IDS="${AZURE_SUBSCRIPTION_IDS}"
)

# Optional fields
[[ -n "${AZURE_OPENAI_API_KEY:-}" ]]  && PLATFORM_ARGS+=(--from-literal=AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}")
[[ -n "${LANGSMITH_API_KEY:-}" ]]     && PLATFORM_ARGS+=(--from-literal=LANGSMITH_API_KEY="${LANGSMITH_API_KEY}")
[[ -n "${SMTP_HOST:-}" ]]             && PLATFORM_ARGS+=(--from-literal=SMTP_HOST="${SMTP_HOST}")
[[ -n "${SMTP_PORT:-}" ]]             && PLATFORM_ARGS+=(--from-literal=SMTP_PORT="${SMTP_PORT}")
[[ -n "${SMTP_USER:-}" ]]             && PLATFORM_ARGS+=(--from-literal=SMTP_USER="${SMTP_USER}")
[[ -n "${SMTP_PASSWORD:-}" ]]         && PLATFORM_ARGS+=(--from-literal=SMTP_PASSWORD="${SMTP_PASSWORD}")
[[ -n "${SMTP_FROM:-}" ]]             && PLATFORM_ARGS+=(--from-literal=SMTP_FROM="${SMTP_FROM}")
[[ -n "${ALERT_RECIPIENTS:-}" ]]      && PLATFORM_ARGS+=(--from-literal=ALERT_RECIPIENTS="${ALERT_RECIPIENTS}")

kubectl create secret generic finops-platform-secret \
  -n platform \
  "${PLATFORM_ARGS[@]}" \
  --dry-run=client -o yaml \
| kubectl apply -f -

ok "finops-platform-secret applied."

# ---- 4b. finops-ai-secret (ai namespace) ---------------------------------
info "Creating secret: finops-ai-secret in namespace: ai"

AI_ARGS=(
  --from-literal=AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}"
  --from-literal=AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT}"
  --from-literal=MI_CLIENT_ID="${MI_CLIENT_ID}"
)

# Optional fields
[[ -n "${AZURE_OPENAI_API_KEY:-}" ]] && AI_ARGS+=(--from-literal=AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}")
[[ -n "${LANGSMITH_API_KEY:-}" ]]    && AI_ARGS+=(--from-literal=LANGSMITH_API_KEY="${LANGSMITH_API_KEY}")

kubectl create secret generic finops-ai-secret \
  -n ai \
  "${AI_ARGS[@]}" \
  --dry-run=client -o yaml \
| kubectl apply -f -

ok "finops-ai-secret applied."

# ---- 4c. finops-frontend-secret (frontend namespace) --------------------
info "Creating secret: finops-frontend-secret in namespace: frontend"

kubectl create secret generic finops-frontend-secret \
  -n frontend \
  --from-literal=PLATFORM_API_URL="http://finops-platform-api-svc.platform.svc.cluster.local" \
  --from-literal=PLATFORM_AI_URL="http://finops-ai-agent-svc.ai.svc.cluster.local" \
  --dry-run=client -o yaml \
| kubectl apply -f -

ok "finops-frontend-secret applied."

# ---------------------------------------------------------------------------
# STEP 5 — Service Accounts with Workload Identity Annotation
# ---------------------------------------------------------------------------
banner "STEP 5 — Workload Identity Service Accounts"

for NS_SA in "platform/cost-platform-sa" "ai/cost-ai-sa"; do
  NS=$(echo "$NS_SA" | cut -d/ -f1)
  SA=$(echo "$NS_SA" | cut -d/ -f2)

  info "Ensuring service account: ${SA} in namespace: ${NS}"

  kubectl create serviceaccount "$SA" \
    -n "$NS" \
    --dry-run=client -o yaml \
  | kubectl apply -f -

  info "Annotating ${SA} with MI_CLIENT_ID: ${MI_CLIENT_ID}"
  kubectl annotate serviceaccount "$SA" \
    -n "$NS" \
    azure.workload.identity/client-id="${MI_CLIENT_ID}" \
    --overwrite

  ok "Service account ${NS}/${SA} ready."
done

# ---------------------------------------------------------------------------
# STEP 6 — Store secrets in Azure Key Vault (canonical source of truth)
# ---------------------------------------------------------------------------
banner "STEP 6 — Azure Key Vault Secret Storage"

KV_NAME="kv-finops-prod00"
KV_RG="rg-finops-prod-security"

info "Checking Key Vault: ${KV_NAME}"
KV_ID=$(az keyvault show --name "$KV_NAME" --resource-group "$KV_RG" \
  --query id -o tsv 2>/dev/null) \
  || err "Cannot reach Key Vault '${KV_NAME}'. Ensure setup.sh ran successfully."

# Auto-assign Key Vault Secrets Officer to the current caller if missing.
# The caller needs this to write secrets — it is NOT the same as the MI's Secrets User role.
CALLER_OID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
if [[ -z "$CALLER_OID" ]]; then
  CALLER_APP=$(az account show --query user.name -o tsv 2>/dev/null || echo "")
  [[ -n "$CALLER_APP" ]] && \
    CALLER_OID=$(az ad sp show --id "$CALLER_APP" --query id -o tsv 2>/dev/null || echo "")
fi

if [[ -n "$CALLER_OID" ]]; then
  role_count=$(az role assignment list \
    --assignee "$CALLER_OID" \
    --role "Key Vault Secrets Officer" \
    --scope "$KV_ID" \
    --query "length(@)" -o tsv 2>/dev/null || echo 0)
  if [[ "${role_count:-0}" -gt 0 ]]; then
    ok "Caller already has 'Key Vault Secrets Officer' on ${KV_NAME}"
  else
    info "Assigning 'Key Vault Secrets Officer' to caller on ${KV_NAME}..."
    az role assignment create \
      --role "Key Vault Secrets Officer" \
      --assignee-object-id "$CALLER_OID" \
      --scope "$KV_ID" \
      --query id -o tsv
    info "Waiting 20 s for RBAC propagation..."
    sleep 20
  fi
else
  warn "Could not determine caller OID — skipping Secrets Officer check. If writes fail, run manually:
  az role assignment create --role 'Key Vault Secrets Officer' --assignee <your-object-id> --scope ${KV_ID}"
fi

kv_set() {
  local name="$1"
  local value="$2"
  if [[ -n "$value" ]]; then
    existing=$(az keyvault secret show \
      --vault-name "$KV_NAME" --name "$name" \
      --query value -o tsv 2>/dev/null || echo "")
    if [[ "$existing" == "$value" ]]; then
      echo -e "${CYAN}[SKIP]  KV secret already up-to-date: ${name}${RESET}"
    else
      az keyvault secret set \
        --vault-name "$KV_NAME" \
        --name        "$name" \
        --value       "$value" \
        --query       "id" -o tsv
      ok "KV secret stored: ${name}"
    fi
  else
    warn "Skipping empty secret: ${name}"
  fi
}

# Required secrets
kv_set "db-host"                  "${DB_HOST}"
kv_set "db-name"                  "${DB_NAME}"
kv_set "db-user"                  "${DB_USER}"
kv_set "db-password"              "${DB_PASSWORD}"
kv_set "azure-openai-endpoint"    "${AZURE_OPENAI_ENDPOINT}"
kv_set "azure-openai-deployment"  "${AZURE_OPENAI_DEPLOYMENT}"
kv_set "mi-client-id"             "${MI_CLIENT_ID}"
kv_set "azure-subscription-ids"   "${AZURE_SUBSCRIPTION_IDS}"

# Optional secrets — only stored if set
[[ -n "${AZURE_OPENAI_API_KEY:-}" ]] && kv_set "azure-openai-api-key" "${AZURE_OPENAI_API_KEY}"
[[ -n "${LANGSMITH_API_KEY:-}" ]]    && kv_set "langsmith-api-key"    "${LANGSMITH_API_KEY}"
[[ -n "${SMTP_HOST:-}" ]]            && kv_set "smtp-host"            "${SMTP_HOST}"
[[ -n "${SMTP_PORT:-}" ]]            && kv_set "smtp-port"            "${SMTP_PORT}"
[[ -n "${SMTP_USER:-}" ]]            && kv_set "smtp-user"            "${SMTP_USER}"
[[ -n "${SMTP_PASSWORD:-}" ]]        && kv_set "smtp-password"        "${SMTP_PASSWORD}"
[[ -n "${SMTP_FROM:-}" ]]            && kv_set "smtp-from"            "${SMTP_FROM}"
[[ -n "${ALERT_RECIPIENTS:-}" ]]     && kv_set "alert-recipients"     "${ALERT_RECIPIENTS}"
[[ -n "${OAUTH_CLIENT_ID:-}" ]]      && kv_set "oauth-client-id"      "${OAUTH_CLIENT_ID}"
[[ -n "${OAUTH_CLIENT_SECRET:-}" ]]  && kv_set "oauth-client-secret"  "${OAUTH_CLIENT_SECRET}"

ok "All secrets stored in Key Vault: ${KV_NAME}"

# ---------------------------------------------------------------------------
# STEP 7 — Apply SecretProviderClass (CSI driver pulls KV → K8s secrets)
# ---------------------------------------------------------------------------
banner "STEP 7 — SecretProviderClass (Key Vault CSI)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SPC_TEMPLATE="${PROJECT_ROOT}/k8s/secret-provider-class.yaml"

if [[ -f "$SPC_TEMPLATE" ]]; then
  TENANT_ID=$(az account show --query tenantId -o tsv)
  info "Rendering and applying SecretProviderClass from: ${SPC_TEMPLATE}"
  # Substitute MI_CLIENT_ID and TENANT_ID placeholders
  MI_CLIENT_ID="${MI_CLIENT_ID}" TENANT_ID="${TENANT_ID}" \
    envsubst '${MI_CLIENT_ID} ${TENANT_ID}' < "$SPC_TEMPLATE" \
    | kubectl apply -f -
  ok "SecretProviderClass applied."
else
  warn "k8s/secret-provider-class.yaml not found — skipping CSI sync. Kubernetes secrets are still usable."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
banner "ALL DONE"

cat <<EOF

${GREEN}============================================================${RESET}
  Secrets and workload identity applied successfully.
${GREEN}============================================================${RESET}

Namespaces created : ${NAMESPACES[*]}

Kubernetes secrets (direct):
  platform/finops-platform-secret
  ai/finops-ai-secret
  frontend/finops-frontend-secret

Key Vault secrets (canonical):
  https://${KV_NAME}.vault.azure.net/secrets/db-password
  https://${KV_NAME}.vault.azure.net/secrets/azure-openai-api-key
  ... (view all: az keyvault secret list --vault-name ${KV_NAME})

Workload Identity service accounts:
  platform/cost-platform-sa  → MI_CLIENT_ID=${MI_CLIENT_ID}
  ai/cost-ai-sa              → MI_CLIENT_ID=${MI_CLIENT_ID}

Next steps:
  kubectl get secrets -A
  kubectl get secretproviderclass -A
  kubectl get serviceaccounts -A

EOF
