#!/usr/bin/env bash
# =============================================================================
# setup.sh — FinOps Platform Azure Infrastructure Provisioning
# =============================================================================
# Idempotent: checks each resource before creating; skips if already correct,
# warns if it exists with unexpected settings.
#
# Provisions in order:
#   Resource Groups → Managed Identity → VNet → DNS → ACR → AKS → Key Vault
#   → PostgreSQL → Azure OpenAI → Workload Identity
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# Requirements: azure-cli, kubectl, python3
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config — hardcoded from config.yaml (do not read yaml dynamically)
# ---------------------------------------------------------------------------
LOCATION="centralindia"
AI_LOCATION="southindia"
RG_NETWORK="rg-finops-prod-network"
RG_CORE="rg-finops-prod-core"
RG_SECURITY="rg-finops-prod-security"
RG_DATA="rg-finops-prod-data"
RG_AI="rg-finops-prod-ai"
AKS_NAME="finops-aks"
ACR_NAME="finopsacrmanmas"
POSTGRES_NAME="finops-pgflex"
MI_NAME="mi-finops-prod"
OPENAI_NAME="finops-ai-brain"
OPENAI_DEPLOYMENT="gpt-4o-mini"
VNET_NAME="finops-prod-vnet"
VNET_CIDR="10.0.0.0/16"
AKS_SUBNET_NAME="aks-subnet"
AKS_SUBNET_CIDR="10.0.2.0/24"
POSTGRES_SUBNET_NAME="postgres-subnet"
POSTGRES_SUBNET_CIDR="10.0.1.0/24"
GENERAL_SUBNET_NAME="general-subnet"
GENERAL_SUBNET_CIDR="10.0.0.0/24"
SERVICE_CIDR="10.96.0.0/16"
DNS_SERVICE_IP="10.96.0.10"
POSTGRES_ADMIN="pgadmin"
POSTGRES_DB="finops-db"
POSTGRES_PASSWORD="AzFleX!admi9"
POSTGRES_SKU="Standard_B1ms"
K8S_VERSION="1.34"
SYSTEM_NODE_SIZE="Standard_B2als_v2"
APP_NODEPOOL_NAME="apppool"
APP_NODE_SIZE="Standard_D2pds_v6"
KV_NAME="kv-finops-prod00"
PLATFORM_SA="cost-platform-sa"
AI_SA="cost-ai-sa"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
banner() {
  local msg="$*"
  local line
  line=$(printf '%0.s─' $(seq 1 ${#msg}))
  echo ""
  echo "┌─${line}─┐"
  echo "│ ${msg} │"
  echo "└─${line}─┘"
}

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
err()   { echo "[ERROR] $*" >&2; exit 1; }
skip()  { echo "[SKIP]  $*"; }

# ---------------------------------------------------------------------------
# Existence checks — return 0 if resource exists, non-zero if not
# ---------------------------------------------------------------------------
exists_rg() {
  az group show --name "$1" --query id -o tsv >/dev/null 2>&1
}

exists_identity() {
  az identity show --name "$1" --resource-group "$2" --query id -o tsv >/dev/null 2>&1
}

# exists_role <assignee-object-id> <role-name> <scope>
exists_role() {
  local count
  count=$(az role assignment list \
    --assignee "$1" \
    --role     "$2" \
    --scope    "$3" \
    --query "length(@)" -o tsv 2>/dev/null || echo 0)
  [[ "${count:-0}" -gt 0 ]]
}

exists_vnet() {
  az network vnet show --name "$1" --resource-group "$2" --query id -o tsv >/dev/null 2>&1
}

exists_subnet() {
  az network vnet subnet show \
    --name "$1" --vnet-name "$2" --resource-group "$3" \
    --query id -o tsv >/dev/null 2>&1
}

exists_dns_zone() {
  az network private-dns zone show \
    --name "$1" --resource-group "$2" \
    --query id -o tsv >/dev/null 2>&1
}

exists_dns_link() {
  az network private-dns link vnet show \
    --name "$1" --zone-name "$2" --resource-group "$3" \
    --query id -o tsv >/dev/null 2>&1
}

exists_acr() {
  az acr show --name "$1" --resource-group "$2" --query id -o tsv >/dev/null 2>&1
}

exists_aks() {
  az aks show --name "$1" --resource-group "$2" --query id -o tsv >/dev/null 2>&1
}

exists_keyvault() {
  az keyvault show --name "$1" --resource-group "$2" --query id -o tsv >/dev/null 2>&1
}

exists_postgres() {
  az postgres flexible-server show \
    --name "$1" --resource-group "$2" \
    --query id -o tsv >/dev/null 2>&1
}

exists_postgres_db() {
  az postgres flexible-server db show \
    --server-name "$1" --resource-group "$2" --database-name "$3" \
    --query id -o tsv >/dev/null 2>&1
}

exists_openai() {
  az cognitiveservices account show \
    --name "$1" --resource-group "$2" \
    --query id -o tsv >/dev/null 2>&1
}

exists_openai_deploy() {
  az cognitiveservices account deployment show \
    --name "$1" --resource-group "$2" --deployment-name "$3" \
    --query id -o tsv >/dev/null 2>&1
}

exists_fed_cred() {
  az identity federated-credential show \
    --name "$1" --identity-name "$2" --resource-group "$3" \
    --query id -o tsv >/dev/null 2>&1
}

exists_nodepool() {
  az aks nodepool show \
    --name "$1" --cluster-name "$2" --resource-group "$3" \
    --query id -o tsv >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
banner "PRE-FLIGHT CHECKS"
command -v az      >/dev/null 2>&1 || err "azure-cli not found. Install it and re-run."
command -v kubectl >/dev/null 2>&1 || err "kubectl not found. Install it and re-run."
command -v python3 >/dev/null 2>&1 || err "python3 not found. Install it and re-run."

info "Checking Azure login..."
az account show >/dev/null 2>&1 || err "Not logged in to Azure. Run 'az login' first."

info "Checking Azure CLI module health..."
az postgres flexible-server --help >/dev/null 2>&1 || err "Azure CLI 'postgres' module failed to load (rdbms package missing or outdated).
  Fix: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
  Or:  sudo apt remove azure-cli && pip3 install azure-cli
  Or:  az upgrade"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
info "Using subscription: ${SUBSCRIPTION_ID}"

# ---------------------------------------------------------------------------
# STEP 1 — Resource Groups
# ---------------------------------------------------------------------------
banner "STEP 1 — Resource Groups"

for RG in "$RG_NETWORK" "$RG_CORE" "$RG_SECURITY" "$RG_DATA" "$RG_AI"; do
  if exists_rg "$RG"; then
    existing_loc=$(az group show --name "$RG" --query location -o tsv 2>/dev/null)
    if [[ "$existing_loc" == "$LOCATION" ]]; then
      skip "Resource group ${RG} already exists in ${LOCATION}"
    else
      warn "Resource group ${RG} exists in '${existing_loc}' (expected '${LOCATION}') — skipping, but verify this is intentional"
    fi
  else
    info "Creating resource group: ${RG}"
    az group create --name "$RG" --location "$LOCATION" --query id -o tsv
  fi
done

info "All resource groups ready."

# ---------------------------------------------------------------------------
# STEP 2 — Managed Identity
# ---------------------------------------------------------------------------
banner "STEP 2 — Managed Identity"

MI_CREATED=false

if exists_identity "$MI_NAME" "$RG_CORE"; then
  skip "Managed identity ${MI_NAME} already exists"
else
  info "Creating managed identity: ${MI_NAME}"
  az identity create \
    --name "$MI_NAME" \
    --resource-group "$RG_CORE" \
    --location "$LOCATION" \
    --query id -o tsv
  MI_CREATED=true
fi

MI_PRINCIPAL_ID=$(az identity show --name "$MI_NAME" --resource-group "$RG_CORE" --query principalId -o tsv)
MI_CLIENT_ID=$(az identity show     --name "$MI_NAME" --resource-group "$RG_CORE" --query clientId -o tsv)
MI_RESOURCE_ID=$(az identity show   --name "$MI_NAME" --resource-group "$RG_CORE" --query id -o tsv)

info "MI Principal ID : ${MI_PRINCIPAL_ID}"
info "MI Client ID    : ${MI_CLIENT_ID}"

if [[ "$MI_CREATED" == true ]]; then
  info "Waiting 30 s for AAD principal propagation..."
  sleep 30
else
  skip "AAD propagation wait (identity pre-existed)"
fi

SUB_SCOPE="/subscriptions/${SUBSCRIPTION_ID}"

if exists_role "$MI_PRINCIPAL_ID" "Cost Management Reader" "$SUB_SCOPE"; then
  skip "Role 'Cost Management Reader' already assigned on subscription"
else
  info "Assigning 'Cost Management Reader' on subscription..."
  az role assignment create \
    --role "Cost Management Reader" \
    --assignee-object-id "$MI_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$SUB_SCOPE" \
    --query id -o tsv
fi

if exists_role "$MI_PRINCIPAL_ID" "Reader" "$SUB_SCOPE"; then
  skip "Role 'Reader' already assigned on subscription"
else
  info "Assigning 'Reader' on subscription..."
  az role assignment create \
    --role "Reader" \
    --assignee-object-id "$MI_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$SUB_SCOPE" \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 3 — VNet and Subnets
# ---------------------------------------------------------------------------
banner "STEP 3 — VNet and Subnets"

if exists_vnet "$VNET_NAME" "$RG_NETWORK"; then
  existing_cidr=$(az network vnet show \
    --name "$VNET_NAME" --resource-group "$RG_NETWORK" \
    --query "addressSpace.addressPrefixes[0]" -o tsv 2>/dev/null)
  if [[ "$existing_cidr" == "$VNET_CIDR" ]]; then
    skip "VNet ${VNET_NAME} (${VNET_CIDR}) already exists"
  else
    warn "VNet ${VNET_NAME} exists with CIDR '${existing_cidr}' (expected '${VNET_CIDR}') — skipping; verify manually"
  fi
else
  info "Creating VNet: ${VNET_NAME} (${VNET_CIDR})"
  az network vnet create \
    --name "$VNET_NAME" \
    --resource-group "$RG_NETWORK" \
    --location "$LOCATION" \
    --address-prefixes "$VNET_CIDR" \
    --query id -o tsv
fi

# Subnet check helper: create if absent, validate CIDR if present
ensure_subnet() {
  local sname="$1" scidr="$2"
  if exists_subnet "$sname" "$VNET_NAME" "$RG_NETWORK"; then
    existing_prefix=$(az network vnet subnet show \
      --name "$sname" --vnet-name "$VNET_NAME" --resource-group "$RG_NETWORK" \
      --query addressPrefix -o tsv 2>/dev/null)
    if [[ "$existing_prefix" == "$scidr" ]]; then
      skip "Subnet ${sname} (${scidr}) already exists"
    else
      warn "Subnet ${sname} exists with prefix '${existing_prefix}' (expected '${scidr}') — skipping; verify manually"
    fi
  else
    info "Creating subnet: ${sname} (${scidr})"
    az network vnet subnet create \
      --name "$sname" \
      --vnet-name "$VNET_NAME" \
      --resource-group "$RG_NETWORK" \
      --address-prefix "$scidr" \
      --query id -o tsv
  fi
}

ensure_subnet "$GENERAL_SUBNET_NAME"  "$GENERAL_SUBNET_CIDR"
ensure_subnet "$POSTGRES_SUBNET_NAME" "$POSTGRES_SUBNET_CIDR"
ensure_subnet "$AKS_SUBNET_NAME"      "$AKS_SUBNET_CIDR"

# Delegate postgres subnet (idempotent — check before updating)
existing_delegation=$(az network vnet subnet show \
  --name "$POSTGRES_SUBNET_NAME" --vnet-name "$VNET_NAME" --resource-group "$RG_NETWORK" \
  --query "delegations[0].serviceName" -o tsv 2>/dev/null || echo "")
if [[ "$existing_delegation" == "Microsoft.DBforPostgreSQL/flexibleServers" ]]; then
  skip "Postgres subnet delegation already set"
else
  info "Delegating ${POSTGRES_SUBNET_NAME} to Microsoft.DBforPostgreSQL/flexibleServers..."
  az network vnet subnet update \
    --name "$POSTGRES_SUBNET_NAME" \
    --vnet-name "$VNET_NAME" \
    --resource-group "$RG_NETWORK" \
    --delegations Microsoft.DBforPostgreSQL/flexibleServers \
    --query id -o tsv
fi

AKS_SUBNET_ID=$(az network vnet subnet show \
  --name "$AKS_SUBNET_NAME" --vnet-name "$VNET_NAME" --resource-group "$RG_NETWORK" \
  --query id -o tsv)

POSTGRES_SUBNET_ID=$(az network vnet subnet show \
  --name "$POSTGRES_SUBNET_NAME" --vnet-name "$VNET_NAME" --resource-group "$RG_NETWORK" \
  --query id -o tsv)

VNET_ID=$(az network vnet show \
  --name "$VNET_NAME" --resource-group "$RG_NETWORK" \
  --query id -o tsv)

info "AKS Subnet ID     : ${AKS_SUBNET_ID}"
info "Postgres Subnet ID: ${POSTGRES_SUBNET_ID}"
info "VNet ID           : ${VNET_ID}"

# ---------------------------------------------------------------------------
# STEP 4 — Private DNS Zone for PostgreSQL
# ---------------------------------------------------------------------------
banner "STEP 4 — Private DNS Zone for PostgreSQL"

POSTGRES_DNS_ZONE="${POSTGRES_NAME}.private.postgres.database.azure.com"

if exists_dns_zone "$POSTGRES_DNS_ZONE" "$RG_NETWORK"; then
  skip "Private DNS zone ${POSTGRES_DNS_ZONE} already exists"
else
  info "Creating private DNS zone: ${POSTGRES_DNS_ZONE}"
  az network private-dns zone create \
    --name "$POSTGRES_DNS_ZONE" \
    --resource-group "$RG_NETWORK" \
    --query id -o tsv
fi

if exists_dns_link "finops-dns-link" "$POSTGRES_DNS_ZONE" "$RG_NETWORK"; then
  skip "DNS VNet link 'finops-dns-link' already exists"
else
  info "Linking DNS zone to VNet..."
  az network private-dns link vnet create \
    --name "finops-dns-link" \
    --resource-group "$RG_NETWORK" \
    --zone-name "$POSTGRES_DNS_ZONE" \
    --virtual-network "$VNET_ID" \
    --registration-enabled false \
    --query id -o tsv
fi

POSTGRES_DNS_ZONE_ID=$(az network private-dns zone show \
  --name "$POSTGRES_DNS_ZONE" --resource-group "$RG_NETWORK" \
  --query id -o tsv)

info "Postgres DNS Zone ID: ${POSTGRES_DNS_ZONE_ID}"

# ---------------------------------------------------------------------------
# STEP 5 — Azure Container Registry
# ---------------------------------------------------------------------------
banner "STEP 5 — Azure Container Registry"

if exists_acr "$ACR_NAME" "$RG_CORE"; then
  existing_sku=$(az acr show --name "$ACR_NAME" --resource-group "$RG_CORE" \
    --query sku.name -o tsv 2>/dev/null)
  skip "ACR ${ACR_NAME} already exists (SKU: ${existing_sku})"
else
  info "Creating ACR: ${ACR_NAME}"
  az acr create \
    --name "$ACR_NAME" \
    --resource-group "$RG_CORE" \
    --location "$LOCATION" \
    --sku Basic \
    --admin-enabled false \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 6 — AKS Cluster
# ---------------------------------------------------------------------------
banner "STEP 6 — AKS Cluster"

if exists_aks "$AKS_NAME" "$RG_CORE"; then
  existing_k8s=$(az aks show --name "$AKS_NAME" --resource-group "$RG_CORE" \
    --query kubernetesVersion -o tsv 2>/dev/null)
  skip "AKS cluster ${AKS_NAME} already exists (k8s: ${existing_k8s})"
else
  info "Creating AKS cluster: ${AKS_NAME} (kubernetes ${K8S_VERSION})"
  info "This step can take 5-10 minutes..."
  az aks create \
    --name "$AKS_NAME" \
    --resource-group "$RG_CORE" \
    --location "$LOCATION" \
    --kubernetes-version "$K8S_VERSION" \
    --node-count 1 \
    --node-vm-size "$SYSTEM_NODE_SIZE" \
    --vnet-subnet-id "$AKS_SUBNET_ID" \
    --network-plugin azure \
    --network-plugin-mode overlay \
    --service-cidr "$SERVICE_CIDR" \
    --dns-service-ip "$DNS_SERVICE_IP" \
    --enable-managed-identity \
    --assign-identity "$MI_RESOURCE_ID" \
    --tier free \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --enable-addons azure-keyvault-secrets-provider \
    --enable-keda \
    --generate-ssh-keys \
    --query id -o tsv
fi

# KEDA — enable on existing clusters that predate this flag
keda_enabled=$(az aks show --name "$AKS_NAME" --resource-group "$RG_CORE" \
  --query "workloadAutoScalerProfile.keda.enabled" -o tsv 2>/dev/null || echo "false")
if [[ "$keda_enabled" == "true" ]]; then
  skip "KEDA already enabled on ${AKS_NAME}"
else
  info "Enabling KEDA on existing cluster ${AKS_NAME}..."
  az aks update \
    --name "$AKS_NAME" \
    --resource-group "$RG_CORE" \
    --enable-keda \
    --query id -o tsv || warn "Could not enable KEDA via az aks update — enable manually: az aks update --enable-keda"
fi

# App node pool
if exists_nodepool "$APP_NODEPOOL_NAME" "$AKS_NAME" "$RG_CORE"; then
  existing_vm=$(az aks nodepool show \
    --name "$APP_NODEPOOL_NAME" --cluster-name "$AKS_NAME" --resource-group "$RG_CORE" \
    --query vmSize -o tsv 2>/dev/null)
  skip "Node pool '${APP_NODEPOOL_NAME}' already exists (VM: ${existing_vm})"
else
  info "Adding app node pool: ${APP_NODEPOOL_NAME} (${APP_NODE_SIZE})"
  az aks nodepool add \
    --name "$APP_NODEPOOL_NAME" \
    --cluster-name "$AKS_NAME" \
    --resource-group "$RG_CORE" \
    --kubernetes-version "$K8S_VERSION" \
    --node-vm-size "$APP_NODE_SIZE" \
    --node-count 1 \
    --vnet-subnet-id "$AKS_SUBNET_ID" \
    --mode User \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 7 — ACR ↔ AKS Integration
# ---------------------------------------------------------------------------
banner "STEP 7 — ACR <-> AKS Integration"

# Grant AcrPull directly via role assignment — avoids `az aks update` which
# triggers a K8s version compatibility check that fails on LTS versions with free tier.
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RG_CORE" --query id -o tsv)
AKS_KUBELET_OID=$(az aks show --name "$AKS_NAME" --resource-group "$RG_CORE" \
  --query "identityProfile.kubeletidentity.objectId" -o tsv 2>/dev/null || echo "")

if [[ -z "$AKS_KUBELET_OID" ]]; then
  warn "Could not retrieve AKS kubelet identity OID — skipping AcrPull role assignment"
elif exists_role "$AKS_KUBELET_OID" "AcrPull" "$ACR_ID"; then
  skip "AcrPull role for AKS kubelet identity already exists on ${ACR_NAME}"
else
  info "Granting AcrPull to AKS kubelet identity on ${ACR_NAME}..."
  az role assignment create \
    --role "AcrPull" \
    --assignee-object-id "$AKS_KUBELET_OID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$ACR_ID" \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 8 — Key Vault
# ---------------------------------------------------------------------------
banner "STEP 8 — Key Vault"

if exists_keyvault "$KV_NAME" "$RG_SECURITY"; then
  rbac_enabled=$(az keyvault show --name "$KV_NAME" --resource-group "$RG_SECURITY" \
    --query "properties.enableRbacAuthorization" -o tsv 2>/dev/null)
  if [[ "$rbac_enabled" == "true" ]]; then
    skip "Key Vault ${KV_NAME} already exists with RBAC enabled"
  else
    warn "Key Vault ${KV_NAME} exists but RBAC authorization is '${rbac_enabled}' (expected 'true') — skipping; verify manually"
  fi
else
  info "Creating Key Vault: ${KV_NAME}"
  az keyvault create \
    --name "$KV_NAME" \
    --resource-group "$RG_SECURITY" \
    --location "$LOCATION" \
    --enable-rbac-authorization true \
    --retention-days 7 \
    --bypass AzureServices \
    --query id -o tsv
fi

KV_ID=$(az keyvault show --name "$KV_NAME" --resource-group "$RG_SECURITY" --query id -o tsv)

if exists_role "$MI_PRINCIPAL_ID" "Key Vault Secrets User" "$KV_ID"; then
  skip "Role 'Key Vault Secrets User' already assigned to managed identity on Key Vault"
else
  info "Assigning 'Key Vault Secrets User' to managed identity on vault..."
  az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee-object-id "$MI_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$KV_ID" \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 9 — PostgreSQL Flexible Server
# ---------------------------------------------------------------------------
banner "STEP 9 — PostgreSQL Flexible Server"

DB_PASSWORD="$POSTGRES_PASSWORD"

if exists_postgres "$POSTGRES_NAME" "$RG_DATA"; then
  skip "PostgreSQL server ${POSTGRES_NAME} already exists"
  info "DB_PASSWORD: ${DB_PASSWORD}"
else
  info "Creating PostgreSQL Flexible Server: ${POSTGRES_NAME}"
  info "DB_PASSWORD: ${DB_PASSWORD}"
  info "This step can take 5-10 minutes..."
  az postgres flexible-server create \
    --name "$POSTGRES_NAME" \
    --resource-group "$RG_DATA" \
    --location "$LOCATION" \
    --tier Burstable \
    --sku-name "$POSTGRES_SKU" \
    --storage-size 32 \
    --version 16 \
    --admin-user "$POSTGRES_ADMIN" \
    --admin-password "$DB_PASSWORD" \
    --subnet "$POSTGRES_SUBNET_ID" \
    --private-dns-zone "$POSTGRES_DNS_ZONE_ID" \
    --yes \
    --query id -o tsv

  info "Storing DB password in Key Vault..."
  az keyvault secret set \
    --vault-name "$KV_NAME" \
    --name "db-password" \
    --value "$DB_PASSWORD" \
    --query id -o tsv
fi

if exists_postgres_db "$POSTGRES_NAME" "$RG_DATA" "$POSTGRES_DB"; then
  skip "Database ${POSTGRES_DB} already exists on ${POSTGRES_NAME}"
else
  info "Creating database: ${POSTGRES_DB}"
  az postgres flexible-server db create \
    --server-name "$POSTGRES_NAME" \
    --resource-group "$RG_DATA" \
    --database-name "$POSTGRES_DB" \
    --query id -o tsv
fi

existing_ext=$(az postgres flexible-server parameter show \
  --server-name "$POSTGRES_NAME" --resource-group "$RG_DATA" \
  --name azure.extensions --query value -o tsv 2>/dev/null || echo "")
if [[ "${existing_ext^^}" == *"VECTOR"* ]]; then
  skip "pgvector extension already enabled"
else
  info "Enabling pgvector extension..."
  az postgres flexible-server parameter set \
    --server-name "$POSTGRES_NAME" \
    --resource-group "$RG_DATA" \
    --name azure.extensions \
    --value VECTOR \
    --query value -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 10 — Azure OpenAI
# ---------------------------------------------------------------------------
banner "STEP 10 — Azure OpenAI"

if exists_openai "$OPENAI_NAME" "$RG_AI"; then
  skip "Azure OpenAI account ${OPENAI_NAME} already exists"
else
  info "Creating Azure OpenAI account: ${OPENAI_NAME} in ${AI_LOCATION}"
  az cognitiveservices account create \
    --name "$OPENAI_NAME" \
    --resource-group "$RG_AI" \
    --location "$AI_LOCATION" \
    --kind OpenAI \
    --sku S0 \
    --yes \
    --query id -o tsv
fi

if exists_openai_deploy "$OPENAI_NAME" "$RG_AI" "$OPENAI_DEPLOYMENT"; then
  existing_model=$(az cognitiveservices account deployment show \
    --name "$OPENAI_NAME" --resource-group "$RG_AI" --deployment-name "$OPENAI_DEPLOYMENT" \
    --query "properties.model.name" -o tsv 2>/dev/null)
  skip "OpenAI deployment '${OPENAI_DEPLOYMENT}' already exists (model: ${existing_model})"
else
  info "Deploying model: gpt-4.1-nano as '${OPENAI_DEPLOYMENT}'..."
  az cognitiveservices account deployment create \
    --name "$OPENAI_NAME" \
    --resource-group "$RG_AI" \
    --deployment-name "$OPENAI_DEPLOYMENT" \
    --model-name "gpt-4.1-nano" \
    --model-version "2025-04-14" \
    --model-format OpenAI \
    --sku-name "GlobalStandard" \
    --sku-capacity 10
fi

OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" --resource-group "$RG_AI" \
  --query properties.endpoint -o tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "$OPENAI_NAME" --resource-group "$RG_AI" \
  --query key1 -o tsv)

OPENAI_ID=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" --resource-group "$RG_AI" \
  --query id -o tsv)

if exists_role "$MI_PRINCIPAL_ID" "Cognitive Services OpenAI User" "$OPENAI_ID"; then
  skip "Role 'Cognitive Services OpenAI User' already assigned to managed identity on OpenAI"
else
  info "Assigning 'Cognitive Services OpenAI User' to managed identity on OpenAI resource..."
  az role assignment create \
    --role "Cognitive Services OpenAI User" \
    --assignee-object-id "$MI_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$OPENAI_ID" \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 11 — Get Kubeconfig
# ---------------------------------------------------------------------------
banner "STEP 11 — Get Kubeconfig"

info "Fetching credentials for AKS cluster: ${AKS_NAME}"
az aks get-credentials \
  --name "$AKS_NAME" \
  --resource-group "$RG_CORE" \
  --overwrite-existing

info "Kubectl context set to: $(kubectl config current-context)"

# ---------------------------------------------------------------------------
# STEP 12 — OIDC Issuer
# ---------------------------------------------------------------------------
banner "STEP 12 — OIDC Issuer"

OIDC_ISSUER=$(az aks show \
  --name "$AKS_NAME" --resource-group "$RG_CORE" \
  --query oidcIssuerProfile.issuerUrl -o tsv)

info "OIDC Issuer URL: ${OIDC_ISSUER}"

# ---------------------------------------------------------------------------
# STEP 13 — Workload Identity Federated Credentials
# ---------------------------------------------------------------------------
banner "STEP 13 — Workload Identity Federated Credentials"

PLATFORM_NAMESPACE="platform"
CRED_NAME_PLATFORM="finops-${PLATFORM_SA}"

if exists_fed_cred "$CRED_NAME_PLATFORM" "$MI_NAME" "$RG_CORE"; then
  existing_subject=$(az identity federated-credential show \
    --name "$CRED_NAME_PLATFORM" --identity-name "$MI_NAME" --resource-group "$RG_CORE" \
    --query subject -o tsv 2>/dev/null)
  expected_subject="system:serviceaccount:${PLATFORM_NAMESPACE}:${PLATFORM_SA}"
  if [[ "$existing_subject" == "$expected_subject" ]]; then
    skip "Federated credential ${CRED_NAME_PLATFORM} already exists and is correct"
  else
    warn "Federated credential ${CRED_NAME_PLATFORM} exists with subject '${existing_subject}' (expected '${expected_subject}') — skipping; verify manually"
  fi
else
  info "Creating federated credential for ${PLATFORM_NAMESPACE}/${PLATFORM_SA}..."
  az identity federated-credential create \
    --name "$CRED_NAME_PLATFORM" \
    --identity-name "$MI_NAME" \
    --resource-group "$RG_CORE" \
    --issuer "$OIDC_ISSUER" \
    --subject "system:serviceaccount:${PLATFORM_NAMESPACE}:${PLATFORM_SA}" \
    --audiences api://AzureADTokenExchange \
    --query id -o tsv
fi

AI_NAMESPACE="ai"
CRED_NAME_AI="finops-${AI_SA}"

if exists_fed_cred "$CRED_NAME_AI" "$MI_NAME" "$RG_CORE"; then
  existing_subject=$(az identity federated-credential show \
    --name "$CRED_NAME_AI" --identity-name "$MI_NAME" --resource-group "$RG_CORE" \
    --query subject -o tsv 2>/dev/null)
  expected_subject="system:serviceaccount:${AI_NAMESPACE}:${AI_SA}"
  if [[ "$existing_subject" == "$expected_subject" ]]; then
    skip "Federated credential ${CRED_NAME_AI} already exists and is correct"
  else
    warn "Federated credential ${CRED_NAME_AI} exists with subject '${existing_subject}' (expected '${expected_subject}') — skipping; verify manually"
  fi
else
  info "Creating federated credential for ${AI_NAMESPACE}/${AI_SA}..."
  az identity federated-credential create \
    --name "$CRED_NAME_AI" \
    --identity-name "$MI_NAME" \
    --resource-group "$RG_CORE" \
    --issuer "$OIDC_ISSUER" \
    --subject "system:serviceaccount:${AI_NAMESPACE}:${AI_SA}" \
    --audiences api://AzureADTokenExchange \
    --query id -o tsv
fi

# ---------------------------------------------------------------------------
# STEP 14 — Summary
# ---------------------------------------------------------------------------
banner "STEP 14 — Setup Complete"

cat <<EOF

============================================================
  SETUP COMPLETE — Copy these values into secrets.env
============================================================
DB_HOST=${POSTGRES_NAME}.postgres.database.azure.com
DB_NAME=${POSTGRES_DB}
DB_USER=${POSTGRES_ADMIN}
DB_PASSWORD=${DB_PASSWORD}
AZURE_OPENAI_ENDPOINT=${OPENAI_ENDPOINT}
AZURE_OPENAI_DEPLOYMENT=${OPENAI_DEPLOYMENT}
AZURE_OPENAI_API_KEY=${OPENAI_KEY}
MI_CLIENT_ID=${MI_CLIENT_ID}
AZURE_SUBSCRIPTION_IDS=${SUBSCRIPTION_ID}
============================================================

IMPORTANT: The DB_PASSWORD and AZURE_OPENAI_API_KEY above are
sensitive. Store them in Azure Key Vault or a secure secrets
manager. Do NOT commit secrets.env to version control.

Next step:
  1. Populate secrets.env at the project root with the values above
  2. Run: ./1-infrastructure/scripts/apply-secrets.sh

EOF
