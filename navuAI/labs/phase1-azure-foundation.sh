#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 1: Azure Infrastructure Foundation
#
#  What this script builds:
#    1. Resource Group
#    2. Virtual Network + Subnets + NSGs
#    3. Azure Container Registry (ACR)
#    4. Azure Key Vault
#    5. AKS Cluster (with 2 node pools: system + app)
#    6. GPU Virtual Machine (for self-hosted LLMs)
#    7. Connects AKS to ACR
#    8. Gets AKS credentials (so kubectl works)
#
#  Run from: WSL or Azure Cloud Shell
#  Time:     ~25 minutes
# =============================================================================

set -euo pipefail   # exit on error, undefined var, or pipe failure

# ── Colors for readable output ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color (reset)

# ── Helper functions ──────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${CYAN}${BOLD}──────────────────────────────────────────${NC}"; \
            echo -e "${CYAN}${BOLD}  STEP $*${NC}"; \
            echo -e "${CYAN}${BOLD}──────────────────────────────────────────${NC}"; }

banner() {
  echo -e "${BOLD}"
  echo "=============================================="
  echo "  navuAI — Phase 1: Azure Infrastructure"
  echo "=============================================="
  echo -e "${NC}"
}

# ── Load configuration ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/navuai.env"

if [[ ! -f "$ENV_FILE" ]]; then
  error "Config file not found: $ENV_FILE\n  Run: cp navuai.env.template navuai.env\n  Then fill in your values."
fi

source "$ENV_FILE"
success "Configuration loaded from navuai.env"

# ── Check prerequisites ───────────────────────────────────────────────────────
check_prereqs() {
  step "0 — Checking Prerequisites"
  local missing=0

  for tool in az kubectl helm jq; do
    if command -v "$tool" &>/dev/null; then
      success "$tool is installed ($(command -v $tool))"
    else
      warn "$tool is NOT installed"
      missing=$((missing + 1))
    fi
  done

  if [[ $missing -gt 0 ]]; then
    error "$missing required tool(s) missing. See labs.md Prerequisites section."
  fi

  success "All prerequisites satisfied"
}

# ── Azure login ───────────────────────────────────────────────────────────────
azure_login() {
  step "0b — Azure Login"
  info "Checking if you are already logged into Azure..."

  if az account show &>/dev/null; then
    CURRENT_SUB=$(az account show --query name -o tsv)
    success "Already logged in. Current subscription: $CURRENT_SUB"
  else
    info "Not logged in. Opening browser for Azure login..."
    az login
  fi

  info "Setting subscription to: $AZURE_SUBSCRIPTION_ID"
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
  success "Subscription set"
}

# ── Step 1: Resource Group ────────────────────────────────────────────────────
create_resource_group() {
  step "1 — Create Resource Group"
  info "Resource Group : $RESOURCE_GROUP"
  info "Location       : $AZURE_LOCATION"

  if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    warn "Resource group '$RESOURCE_GROUP' already exists — skipping creation"
  else
    az group create \
      --name "$RESOURCE_GROUP" \
      --location "$AZURE_LOCATION" \
      --output table
    success "Resource group created: $RESOURCE_GROUP"
  fi
}

# ── Step 2: Virtual Network ───────────────────────────────────────────────────
create_networking() {
  step "2 — Create Virtual Network, Subnets, and NSGs"

  # VNet
  info "Creating VNet: $VNET_NAME ($VNET_CIDR)"
  az network vnet create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VNET_NAME" \
    --address-prefixes "$VNET_CIDR" \
    --location "$AZURE_LOCATION" \
    --output table 2>/dev/null || warn "VNet already exists — skipping"

  # AKS Subnet
  info "Creating AKS subnet ($AKS_SUBNET_CIDR)"
  az network vnet subnet create \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "aks-subnet" \
    --address-prefixes "$AKS_SUBNET_CIDR" \
    --output table 2>/dev/null || warn "AKS subnet already exists — skipping"

  # GPU Subnet
  info "Creating GPU subnet ($GPU_SUBNET_CIDR)"
  az network vnet subnet create \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "gpu-subnet" \
    --address-prefixes "$GPU_SUBNET_CIDR" \
    --output table 2>/dev/null || warn "GPU subnet already exists — skipping"

  # Private Endpoint Subnet
  info "Creating private endpoint subnet ($PE_SUBNET_CIDR)"
  az network vnet subnet create \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "pe-subnet" \
    --address-prefixes "$PE_SUBNET_CIDR" \
    --private-endpoint-network-policies Disabled \
    --output table 2>/dev/null || warn "PE subnet already exists — skipping"

  # NSG for AKS
  info "Creating Network Security Group for AKS"
  az network nsg create \
    --resource-group "$RESOURCE_GROUP" \
    --name "navuai-aks-nsg" \
    --output table 2>/dev/null || warn "NSG already exists — skipping"

  info "Adding NSG rule: allow HTTPS inbound"
  az network nsg rule create \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "navuai-aks-nsg" \
    --name "AllowHTTPS" \
    --priority 100 \
    --protocol Tcp \
    --destination-port-ranges 443 \
    --access Allow \
    --direction Inbound \
    --output table 2>/dev/null || warn "HTTPS rule already exists"

  info "Adding NSG rule: deny all other inbound"
  az network nsg rule create \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "navuai-aks-nsg" \
    --name "DenyAllInbound" \
    --priority 4096 \
    --protocol "*" \
    --destination-port-ranges "*" \
    --access Deny \
    --direction Inbound \
    --output table 2>/dev/null || warn "DenyAll rule already exists"

  success "Networking created"
}

# ── Step 3: Azure Container Registry ─────────────────────────────────────────
create_acr() {
  step "3 — Create Azure Container Registry (ACR)"
  info "ACR Name: $ACR_NAME (must be globally unique)"

  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Standard \
    --location "$AZURE_LOCATION" \
    --output table 2>/dev/null || warn "ACR already exists — skipping"

  success "ACR ready: $ACR_NAME.azurecr.io"
}

# ── Step 4: Key Vault ─────────────────────────────────────────────────────────
create_keyvault() {
  step "4 — Create Azure Key Vault"
  info "Key Vault: $KEYVAULT_NAME"

  az keyvault create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$KEYVAULT_NAME" \
    --location "$AZURE_LOCATION" \
    --enable-rbac-authorization false \
    --output table 2>/dev/null || warn "Key Vault already exists — skipping"

  success "Key Vault ready: $KEYVAULT_NAME"

  # Store placeholder secrets (filled in Phase 2)
  info "Pre-creating secret slots in Key Vault..."
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "openai-api-key"        --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "azure-openai-key"      --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "azure-openai-endpoint" --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "aws-access-key-id"     --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "aws-secret-key"        --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "vertex-project"        --value "PLACEHOLDER" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "postgres-password"     --value "pg-$(openssl rand -hex 16)" --output none 2>/dev/null || true
  az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "litellm-master-key"    --value "sk-navuai-$(openssl rand -hex 16)" --output none 2>/dev/null || true

  success "Secret slots created in Key Vault"
}

# ── Step 5: AKS Cluster ───────────────────────────────────────────────────────
create_aks() {
  step "5 — Create AKS Cluster"
  info "Cluster Name : $AKS_CLUSTER_NAME"
  info "Node VM Size : $AKS_NODE_VM_SIZE"
  info "Node Count   : $AKS_NODE_COUNT_MIN – $AKS_NODE_COUNT_MAX"
  warn "This takes 10–15 minutes. Do not close the terminal."

  AKS_SUBNET_ID=$(az network vnet subnet show \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "aks-subnet" \
    --query id -o tsv)

  if az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" &>/dev/null; then
    warn "AKS cluster '$AKS_CLUSTER_NAME' already exists — skipping creation"
  else
    az aks create \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AKS_CLUSTER_NAME" \
      --location "$AZURE_LOCATION" \
      --tier free \
      --node-count 1 \
      --min-count 1 \
      --max-count "$AKS_NODE_COUNT_MAX" \
      --node-vm-size "$AKS_NODE_VM_SIZE" \
      --enable-cluster-autoscaler \
      --network-plugin azure \
      --vnet-subnet-id "$AKS_SUBNET_ID" \
      --service-cidr "$AKS_SERVICE_CIDR" \
      --dns-service-ip "$AKS_DNS_SERVICE_IP" \
      --enable-managed-identity \
      --enable-oidc-issuer \
      --enable-workload-identity \
      --generate-ssh-keys \
      --output table || error "AKS cluster creation failed."
    success "AKS cluster created: $AKS_CLUSTER_NAME"
  fi

  # Add app node pool — minimal size for cost
  if az aks nodepool show --resource-group "$RESOURCE_GROUP" --cluster-name "$AKS_CLUSTER_NAME" --name "app" &>/dev/null; then
    warn "'app' node pool already exists — skipping"
  else
    info "Adding 'app' node pool (1 node, minimal VM)..."
    az aks nodepool add \
      --resource-group "$RESOURCE_GROUP" \
      --cluster-name "$AKS_CLUSTER_NAME" \
      --name "app" \
      --node-count 1 \
      --min-count 1 \
      --max-count "$AKS_NODE_COUNT_MAX" \
      --node-vm-size "$AKS_NODE_VM_SIZE" \
      --enable-cluster-autoscaler \
      --output table || error "'app' node pool creation failed."
    success "App node pool added"
  fi
}

# ── Step 6: GPU Virtual Machine ───────────────────────────────────────────────
create_gpu_vm() {
  step "6 — Create GPU Virtual Machine (self-hosted LLMs)"

  if [[ "${SKIP_GPU_VM:-true}" == "true" ]]; then
    warn "SKIP_GPU_VM=true — skipping GPU VM. Set SKIP_GPU_VM=false in navuai.env after GPU quota is approved."
    warn "To approve quota: Azure Portal → Subscriptions → Usage + Quotas → filter '$GPU_VM_SIZE' → Request increase"
    return
  fi

  info "VM Name  : $GPU_VM_NAME"
  info "VM Size  : $GPU_VM_SIZE"
  warn "GPU quota must be approved in your Azure subscription first."
  warn "Check: Azure Portal → Subscriptions → Usage + Quotas"

  GPU_SUBNET_ID=$(az network vnet subnet show \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "gpu-subnet" \
    --query id -o tsv)

  # Generate SSH key if it doesn't exist
  if [[ ! -f "${GPU_VM_SSH_KEY_PATH}" ]]; then
    info "Generating SSH key at $GPU_VM_SSH_KEY_PATH"
    ssh-keygen -t rsa -b 4096 -f "${GPU_VM_SSH_KEY_PATH}" -N "" -q
    success "SSH key generated"
  else
    info "SSH key already exists at $GPU_VM_SSH_KEY_PATH"
  fi

  if az vm show --resource-group "$RESOURCE_GROUP" --name "$GPU_VM_NAME" &>/dev/null; then
    warn "GPU VM '$GPU_VM_NAME' already exists — skipping creation"
  else
    az vm create \
      --resource-group "$RESOURCE_GROUP" \
      --name "$GPU_VM_NAME" \
      --size "$GPU_VM_SIZE" \
      --image "Canonical:ubuntu-24_04-lts:server:latest" \
      --admin-username "$GPU_VM_ADMIN_USER" \
      --ssh-key-values "${GPU_VM_SSH_KEY_PATH}.pub" \
      --vnet-name "$VNET_NAME" \
      --subnet "gpu-subnet" \
      --public-ip-address "" \
      --nsg "" \
      --output table || error "GPU VM creation failed. Check GPU quota: Azure Portal → Subscriptions → Usage + Quotas → filter '$GPU_VM_SIZE'"
    success "GPU VM created: $GPU_VM_NAME"
  fi

  # Guard: confirm VM exists before running anything on it
  if ! az vm show --resource-group "$RESOURCE_GROUP" --name "$GPU_VM_NAME" &>/dev/null; then
    warn "GPU VM does not exist — skipping Ollama install. Approve GPU quota and re-run."
    return
  fi

  GPU_VM_IP=$(az vm show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$GPU_VM_NAME" \
    --query privateIps -d -o tsv)

  info "GPU VM private IP: $GPU_VM_IP"
  info "To SSH into it: ssh -i $GPU_VM_SSH_KEY_PATH $GPU_VM_ADMIN_USER@$GPU_VM_IP"

  info "Installing Ollama (LLM server) on GPU VM — this takes ~5 minutes..."
  az vm run-command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$GPU_VM_NAME" \
    --command-id RunShellScript \
    --scripts "
      apt-get update -qq
      curl -fsSL https://ollama.ai/install.sh | sh
      systemctl enable ollama
      systemctl start ollama
      echo 'Ollama installed and started'
      ollama serve &
      sleep 5
      ollama pull nomic-embed-text
      echo 'Embed model pulled'
    " \
    --output table 2>/dev/null || warn "Could not run install script on GPU VM (check SSH access)"

  success "GPU VM ready at private IP: $GPU_VM_IP"
}

# ── Step 7: Attach ACR to AKS ────────────────────────────────────────────────
attach_acr_to_aks() {
  step "7 — Attach ACR to AKS (so AKS can pull images from your registry)"

  az aks update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER_NAME" \
    --attach-acr "$ACR_NAME" \
    --output table

  success "AKS can now pull images from $ACR_NAME.azurecr.io"
}

# ── Step 8: Get AKS credentials ───────────────────────────────────────────────
get_aks_credentials() {
  step "8 — Configure kubectl to connect to your AKS cluster"

  az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER_NAME" \
    --overwrite-existing

  info "Verifying connection to AKS..."
  kubectl get nodes -o wide

  success "kubectl is connected to $AKS_CLUSTER_NAME"
}

# ── Install NGINX ingress controller ──────────────────────────────────────────
install_ingress() {
  step "8b — Install NGINX Ingress Controller on AKS"

  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx --force-update
  helm repo update

  kubectl create namespace ingress-nginx --dry-run=client -o yaml | kubectl apply -f -

  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --set controller.replicaCount=1 \
    --set controller.nodeSelector."kubernetes\.io/os"=linux \
    --set controller.service.externalTrafficPolicy=Local \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-sku"=standard \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
    --wait

  success "NGINX ingress controller installed"

  info "Waiting for external IP assignment (may take 2–3 minutes)..."
  for i in {1..20}; do
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$INGRESS_IP" ]]; then
      success "Ingress External IP: $INGRESS_IP"
      echo ""
      warn "ACTION REQUIRED: Point your DNS records to this IP:"
      warn "  chat.$DOMAIN  →  $INGRESS_IP"
      warn "  api.$DOMAIN   →  $INGRESS_IP"
      break
    fi
    info "Still waiting... ($i/20)"
    sleep 15
  done
}

# ── Install cert-manager (TLS certificates) ───────────────────────────────────
install_cert_manager() {
  step "8c — Install cert-manager (automatic TLS certificates)"

  helm repo add jetstack https://charts.jetstack.io --force-update
  helm repo update

  kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -

  helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --set installCRDs=true \
    --wait

  # ClusterIssuer for Let's Encrypt
  cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

  success "cert-manager installed — TLS certificates will be auto-provisioned"
}

# ── Phase summary ─────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 1 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ Resource Group    : $RESOURCE_GROUP"
  echo "  ✓ VNet + Subnets    : $VNET_NAME"
  echo "  ✓ ACR               : $ACR_NAME.azurecr.io"
  echo "  ✓ Key Vault         : $KEYVAULT_NAME"
  echo "  ✓ AKS Cluster       : $AKS_CLUSTER_NAME"
  if [[ "${SKIP_GPU_VM:-true}" == "true" ]]; then
    echo "  ⚠ GPU VM            : skipped (SKIP_GPU_VM=true)"
  else
    echo "  ✓ GPU VM            : $GPU_VM_NAME"
  fi
  echo "  ✓ NGINX Ingress     : installed"
  echo "  ✓ cert-manager      : installed"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  Fill in your LLM API keys in navuai.env, then run:"
  echo "  ./phase2-litellm-gateway.sh"
  echo ""
}

# ── Main execution ────────────────────────────────────────────────────────────
main() {
  banner
  check_prereqs
  azure_login
  create_resource_group
  create_networking
  create_acr
  create_keyvault
  create_aks
  create_gpu_vm
  attach_acr_to_aks
  get_aks_credentials
  install_ingress
  install_cert_manager
  print_summary
}

main "$@"
