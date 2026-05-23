#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 1.1: Azure AI Foundry (Azure OpenAI)
#
#  What this script builds:
#    1. Azure OpenAI resource (Cognitive Services)
#    2. GPT-4o model deployment
#    3. Saves endpoint + key into Key Vault (auto-used by Phase 2)
#
#  Run AFTER: phase1-azure-foundation.sh
#  Run BEFORE: phase2-litellm-gateway.sh
#
#  Run from: WSL or Azure Cloud Shell
#  Time:     ~5 minutes
#
#  NOTE: Azure OpenAI is not available in all regions.
#        FOUNDRY_LOCATION in navuai.env defaults to eastus.
#        Your AKS stays in centralindia — only the Foundry resource is in eastus.
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

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
  echo "  navuAI — Phase 1.1: Azure AI Foundry"
  echo "=============================================="
  echo -e "${NC}"
}

# ── Load configuration ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/navuai.env"

if [[ ! -f "$ENV_FILE" ]]; then
  error "Config file not found: $ENV_FILE\n  Run: cp navuai.env.template navuai.env"
fi

source "$ENV_FILE"
success "Configuration loaded from navuai.env"

# ── Step 1: Create Azure OpenAI resource ─────────────────────────────────────
create_foundry_resource() {
  step "1 — Create Azure OpenAI Resource"
  info "Resource Name : $FOUNDRY_RESOURCE_NAME"
  info "Resource Group: $RESOURCE_GROUP"
  info "Location      : $FOUNDRY_LOCATION"
  warn "Note: Azure OpenAI is hosted in $FOUNDRY_LOCATION — your AKS stays in $AZURE_LOCATION"

  if az cognitiveservices account show \
      --name "$FOUNDRY_RESOURCE_NAME" \
      --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    warn "Azure OpenAI resource '$FOUNDRY_RESOURCE_NAME' already exists — skipping creation"
  else
    az cognitiveservices account create \
      --name "$FOUNDRY_RESOURCE_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --kind OpenAI \
      --sku S0 \
      --location "$FOUNDRY_LOCATION" \
      --yes \
      --output table || error "Failed to create Azure OpenAI resource. Check that your subscription has Azure OpenAI access approved."
    success "Azure OpenAI resource created: $FOUNDRY_RESOURCE_NAME"
  fi
}

# ── Step 2: Deploy model (auto-detects latest non-deprecated version) ─────────
deploy_model() {
  step "2 — Deploy $FOUNDRY_MODEL_NAME model"
  info "Deployment : $FOUNDRY_DEPLOYMENT_NAME"
  info "Capacity   : ${FOUNDRY_CAPACITY}K tokens/min"
  info "Location   : $FOUNDRY_LOCATION"

  if az cognitiveservices account deployment show \
      --name "$FOUNDRY_RESOURCE_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --deployment-name "$FOUNDRY_DEPLOYMENT_NAME" &>/dev/null; then
    warn "Deployment '$FOUNDRY_DEPLOYMENT_NAME' already exists — skipping"
    return
  fi

  # Use known working version; fallback to auto-detect if not found in region
  MODEL_VERSION="${FOUNDRY_MODEL_VERSION:-2025-04-14}"

  info "Checking '$FOUNDRY_MODEL_NAME' version $MODEL_VERSION availability in $FOUNDRY_LOCATION..."
  VERSION_EXISTS=$(az cognitiveservices model list \
    --location "$FOUNDRY_LOCATION" \
    --query "[?kind=='OpenAI' && model.name=='$FOUNDRY_MODEL_NAME' && model.version=='$MODEL_VERSION'].model.version" \
    -o tsv 2>/dev/null || echo "")

  if [[ -z "$VERSION_EXISTS" ]]; then
    warn "Version $MODEL_VERSION not found — auto-detecting latest available version..."
    MODEL_VERSION=$(az cognitiveservices model list \
      --location "$FOUNDRY_LOCATION" \
      --query "sort_by([?kind=='OpenAI' && model.name=='$FOUNDRY_MODEL_NAME'], &model.version)[-1].model.version" \
      -o tsv 2>/dev/null || echo "")
  fi

  if [[ -z "$MODEL_VERSION" ]]; then
    warn "Model '$FOUNDRY_MODEL_NAME' not found in $FOUNDRY_LOCATION"
    info "Available OpenAI models in $FOUNDRY_LOCATION:"
    az cognitiveservices model list --location "$FOUNDRY_LOCATION" \
      --query "[?kind=='OpenAI'].{name:model.name,version:model.version}" -o table 2>/dev/null || true
    error "Set FOUNDRY_LOCATION or FOUNDRY_MODEL_NAME in navuai.env to a supported combination and re-run."
  fi

  info "Deploying $FOUNDRY_MODEL_NAME version $MODEL_VERSION"

  az cognitiveservices account deployment create \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$FOUNDRY_DEPLOYMENT_NAME" \
    --model-name "$FOUNDRY_MODEL_NAME" \
    --model-version "$MODEL_VERSION" \
    --model-format OpenAI \
    --sku-capacity "$FOUNDRY_CAPACITY" \
    --sku-name GlobalStandard \
    --query id -o tsv || error "Deployment failed for $FOUNDRY_MODEL_NAME $MODEL_VERSION in $FOUNDRY_LOCATION"

  success "Model deployed: $FOUNDRY_DEPLOYMENT_NAME ($FOUNDRY_MODEL_NAME $MODEL_VERSION)"
}

# ── Step 3: Save endpoint + key to Key Vault ──────────────────────────────────
save_to_keyvault() {
  step "3 — Save Foundry credentials to Key Vault"
  info "Key Vault: $KEYVAULT_NAME"

  # Retrieve endpoint
  FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" -o tsv)

  # Retrieve key
  FOUNDRY_KEY=$(az cognitiveservices account keys list \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "key1" -o tsv)

  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "azure-openai-endpoint" \
    --value "$FOUNDRY_ENDPOINT" \
    --output none
  success "Saved azure-openai-endpoint → Key Vault"

  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "azure-openai-key" \
    --value "$FOUNDRY_KEY" \
    --output none
  success "Saved azure-openai-key → Key Vault"

  # Write back into navuai.env so Phase 2 picks them up without manual editing
  sed -i "s|^AZURE_OPENAI_ENDPOINT=.*|AZURE_OPENAI_ENDPOINT=\"$FOUNDRY_ENDPOINT\"|" "$ENV_FILE"
  sed -i "s|^AZURE_OPENAI_KEY=.*|AZURE_OPENAI_KEY=\"$FOUNDRY_KEY\"|" "$ENV_FILE"
  success "Updated navuai.env with endpoint and key"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" -o tsv 2>/dev/null || echo "unknown")

  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 1.1 Complete"
  echo "=============================================="
  echo -e "${NC}"
  echo "  Resource  : $FOUNDRY_RESOURCE_NAME"
  echo "  Location  : $FOUNDRY_LOCATION"
  echo "  Model     : $FOUNDRY_DEPLOYMENT_NAME ($FOUNDRY_MODEL_NAME $FOUNDRY_MODEL_VERSION)"
  echo "  Endpoint  : $FOUNDRY_ENDPOINT"
  echo "  Key Vault : credentials saved as 'azure-openai-key' + 'azure-openai-endpoint'"
  echo "  navuai.env: AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_KEY auto-filled"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  Run Phase 2:  bash phase2-litellm-gateway.sh"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  banner
  create_foundry_resource
  deploy_model
  save_to_keyvault
  print_summary
}

main "$@"
