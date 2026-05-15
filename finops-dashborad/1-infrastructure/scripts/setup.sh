#!/usr/bin/env bash
# =============================================================================
# setup.sh — FinOps Platform Azure Infrastructure Provisioning
# =============================================================================
# Provisions all Azure resources required for the FinOps platform in order:
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
ACR_NAME="finopsacr"
POSTGRES_NAME="finops-pgflex"
KV_NAME="kv-finops-prod"
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
POSTGRES_SKU="Standard_B1ms"
K8S_VERSION="1.32"
SYSTEM_NODE_SIZE="Standard_B2als_v2"
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

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
banner "PRE-FLIGHT CHECKS"
command -v az      >/dev/null 2>&1 || err "azure-cli not found. Install it and re-run."
command -v kubectl >/dev/null 2>&1 || err "kubectl not found. Install it and re-run."
command -v python3 >/dev/null 2>&1 || err "python3 not found. Install it and re-run."

info "Checking Azure login..."
az account show >/dev/null 2>&1 || err "Not logged in to Azure. Run 'az login' first."

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
info "Using subscription: ${SUBSCRIPTION_ID}"

# ---------------------------------------------------------------------------
# STEP 1 — Resource Groups
# ---------------------------------------------------------------------------
banner "STEP 1 — Resource Groups"

for RG in "$RG_NETWORK" "$RG_CORE" "$RG_SECURITY" "$RG_DATA" "$RG_AI"; do
  info "Ensuring resource group: ${RG}"
  az group create \
    --name "$RG" \
    --location "$LOCATION" \
    --query id -o tsv || true
done

info "All resource groups ready."

# ---------------------------------------------------------------------------
# STEP 2 — Managed Identity
# ---------------------------------------------------------------------------
banner "STEP 2 — Managed Identity"

info "Creating managed identity: ${MI_NAME}"
az identity create \
  --name "$MI_NAME" \
  --resource-group "$RG_CORE" \
  --location "$LOCATION" \
  --query id -o tsv

MI_PRINCIPAL_ID=$(az identity show --name "$MI_NAME" --resource-group "$RG_CORE" --query principalId -o tsv)
MI_CLIENT_ID=$(az identity show     --name "$MI_NAME" --resource-group "$RG_CORE" --query clientId -o tsv)
MI_RESOURCE_ID=$(az identity show   --name "$MI_NAME" --resource-group "$RG_CORE" --query id -o tsv)

info "MI Principal ID : ${MI_PRINCIPAL_ID}"
info "MI Client ID    : ${MI_CLIENT_ID}"

# Allow time for AAD propagation before role assignments
info "Waiting 30 s for AAD principal propagation..."
sleep 30

info "Assigning 'Cost Management Reader' on subscription..."
az role assignment create \
  --role "Cost Management Reader" \
  --assignee-object-id "$MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/${SUBSCRIPTION_ID}" \
  --query id -o tsv

info "Assigning 'Reader' on subscription..."
az role assignment create \
  --role "Reader" \
  --assignee-object-id "$MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/${SUBSCRIPTION_ID}" \
  --query id -o tsv

# ---------------------------------------------------------------------------
# STEP 3 — VNet and Subnets
# ---------------------------------------------------------------------------
banner "STEP 3 — VNet and Subnets"

info "Creating VNet: ${VNET_NAME} (${VNET_CIDR})"
az network vnet create \
  --name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --location "$LOCATION" \
  --address-prefixes "$VNET_CIDR" \
  --query id -o tsv

info "Creating subnet: ${GENERAL_SUBNET_NAME} (${GENERAL_SUBNET_CIDR})"
az network vnet subnet create \
  --name "$GENERAL_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --address-prefix "$GENERAL_SUBNET_CIDR" \
  --query id -o tsv

info "Creating subnet: ${POSTGRES_SUBNET_NAME} (${POSTGRES_SUBNET_CIDR})"
az network vnet subnet create \
  --name "$POSTGRES_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --address-prefix "$POSTGRES_SUBNET_CIDR" \
  --query id -o tsv

info "Creating subnet: ${AKS_SUBNET_NAME} (${AKS_SUBNET_CIDR})"
az network vnet subnet create \
  --name "$AKS_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --address-prefix "$AKS_SUBNET_CIDR" \
  --query id -o tsv

info "Delegating postgres-subnet to Microsoft.DBforPostgreSQL/flexibleServers..."
az network vnet subnet update \
  --name "$POSTGRES_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --delegations Microsoft.DBforPostgreSQL/flexibleServers \
  --query id -o tsv

AKS_SUBNET_ID=$(az network vnet subnet show \
  --name "$AKS_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --query id -o tsv)

POSTGRES_SUBNET_ID=$(az network vnet subnet show \
  --name "$POSTGRES_SUBNET_NAME" \
  --vnet-name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --query id -o tsv)

VNET_ID=$(az network vnet show \
  --name "$VNET_NAME" \
  --resource-group "$RG_NETWORK" \
  --query id -o tsv)

info "AKS Subnet ID     : ${AKS_SUBNET_ID}"
info "Postgres Subnet ID: ${POSTGRES_SUBNET_ID}"
info "VNet ID           : ${VNET_ID}"

# ---------------------------------------------------------------------------
# STEP 4 — Private DNS Zone for PostgreSQL
# ---------------------------------------------------------------------------
banner "STEP 4 — Private DNS Zone for PostgreSQL"

POSTGRES_DNS_ZONE="${POSTGRES_NAME}.private.postgres.database.azure.com"
info "Creating private DNS zone: ${POSTGRES_DNS_ZONE}"

az network private-dns zone create \
  --name "$POSTGRES_DNS_ZONE" \
  --resource-group "$RG_NETWORK" \
  --query id -o tsv

info "Linking DNS zone to VNet..."
az network private-dns link vnet create \
  --name "finops-dns-link" \
  --resource-group "$RG_NETWORK" \
  --zone-name "$POSTGRES_DNS_ZONE" \
  --virtual-network "$VNET_ID" \
  --registration-enabled false \
  --query id -o tsv

POSTGRES_DNS_ZONE_ID=$(az network private-dns zone show \
  --name "$POSTGRES_DNS_ZONE" \
  --resource-group "$RG_NETWORK" \
  --query id -o tsv)

info "Postgres DNS Zone ID: ${POSTGRES_DNS_ZONE_ID}"

# ---------------------------------------------------------------------------
# STEP 5 — Azure Container Registry
# ---------------------------------------------------------------------------
banner "STEP 5 — Azure Container Registry"

info "Creating ACR: ${ACR_NAME}"
az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RG_CORE" \
  --location "$LOCATION" \
  --sku Basic \
  --admin-enabled false \
  --query id -o tsv

# ---------------------------------------------------------------------------
# STEP 6 — AKS Cluster
# ---------------------------------------------------------------------------
banner "STEP 6 — AKS Cluster"

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
  --generate-ssh-keys \
  --query id -o tsv

# ---------------------------------------------------------------------------
# STEP 7 — ACR ↔ AKS Integration
# ---------------------------------------------------------------------------
banner "STEP 7 — ACR <-> AKS Integration"

info "Attaching ACR ${ACR_NAME} to AKS ${AKS_NAME}..."
az aks update \
  --name "$AKS_NAME" \
  --resource-group "$RG_CORE" \
  --attach-acr "$ACR_NAME" \
  --query id -o tsv

# ---------------------------------------------------------------------------
# STEP 8 — Key Vault
# ---------------------------------------------------------------------------
banner "STEP 8 — Key Vault"

info "Creating Key Vault: ${KV_NAME}"
az keyvault create \
  --name "$KV_NAME" \
  --resource-group "$RG_SECURITY" \
  --location "$LOCATION" \
  --enable-rbac-authorization true \
  --retention-days 7 \
  --bypass AzureServices \
  --query id -o tsv

KV_ID=$(az keyvault show --name "$KV_NAME" --resource-group "$RG_SECURITY" --query id -o tsv)

info "Assigning 'Key Vault Secrets User' to managed identity on vault..."
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "$MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$KV_ID" \
  --query id -o tsv

# ---------------------------------------------------------------------------
# STEP 9 — PostgreSQL Flexible Server
# ---------------------------------------------------------------------------
banner "STEP 9 — PostgreSQL Flexible Server"

info "Generating random DB password..."
DB_PASSWORD=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#') for _ in range(20)))")

info "Creating PostgreSQL Flexible Server: ${POSTGRES_NAME}"
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

info "Creating database: ${POSTGRES_DB}"
az postgres flexible-server db create \
  --server-name "$POSTGRES_NAME" \
  --resource-group "$RG_DATA" \
  --database-name "$POSTGRES_DB" \
  --query id -o tsv

info "Enabling pgvector extension..."
az postgres flexible-server parameter set \
  --server-name "$POSTGRES_NAME" \
  --resource-group "$RG_DATA" \
  --name azure.extensions \
  --value VECTOR \
  --query value -o tsv

# ---------------------------------------------------------------------------
# STEP 10 — Azure OpenAI
# ---------------------------------------------------------------------------
banner "STEP 10 — Azure OpenAI"

info "Creating Azure OpenAI account: ${OPENAI_NAME} in ${AI_LOCATION}"
az cognitiveservices account create \
  --name "$OPENAI_NAME" \
  --resource-group "$RG_AI" \
  --location "$AI_LOCATION" \
  --kind OpenAI \
  --sku S0 \
  --yes \
  --query id -o tsv

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

OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" \
  --resource-group "$RG_AI" \
  --query properties.endpoint -o tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "$OPENAI_NAME" \
  --resource-group "$RG_AI" \
  --query key1 -o tsv)

OPENAI_ID=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" \
  --resource-group "$RG_AI" \
  --query id -o tsv)

info "Assigning 'Cognitive Services OpenAI User' to managed identity on OpenAI resource..."
az role assignment create \
  --role "Cognitive Services OpenAI User" \
  --assignee-object-id "$MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$OPENAI_ID" \
  --query id -o tsv

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
  --name "$AKS_NAME" \
  --resource-group "$RG_CORE" \
  --query oidcIssuerProfile.issuerUrl -o tsv)

info "OIDC Issuer URL: ${OIDC_ISSUER}"

# ---------------------------------------------------------------------------
# STEP 13 — Workload Identity Federated Credentials
# ---------------------------------------------------------------------------
banner "STEP 13 — Workload Identity Federated Credentials"

# platform namespace / cost-platform-sa
PLATFORM_NAMESPACE="platform"
info "Creating federated credential for ${PLATFORM_NAMESPACE}/${PLATFORM_SA}..."
az identity federated-credential create \
  --name "finops-${PLATFORM_SA}" \
  --identity-name "$MI_NAME" \
  --resource-group "$RG_CORE" \
  --issuer "$OIDC_ISSUER" \
  --subject "system:serviceaccount:${PLATFORM_NAMESPACE}:${PLATFORM_SA}" \
  --audiences api://AzureADTokenExchange \
  --query id -o tsv

# ai namespace / cost-ai-sa
AI_NAMESPACE="ai"
info "Creating federated credential for ${AI_NAMESPACE}/${AI_SA}..."
az identity federated-credential create \
  --name "finops-${AI_SA}" \
  --identity-name "$MI_NAME" \
  --resource-group "$RG_CORE" \
  --issuer "$OIDC_ISSUER" \
  --subject "system:serviceaccount:${AI_NAMESPACE}:${AI_SA}" \
  --audiences api://AzureADTokenExchange \
  --query id -o tsv

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
