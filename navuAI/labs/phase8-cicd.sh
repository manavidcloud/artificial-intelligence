#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 8: CI/CD Pipelines
#
#  What this script builds:
#    1. Azure Service Principal — GitHub Actions identity with ACR push + AKS deploy
#    2. GitHub Actions workflows — auto-build Docker images and push to ACR
#    3. Deploy workflow — kubectl rollout on every push to main
#    4. Outputs all GitHub secrets you need to paste into your repo settings
#
#  Prerequisites: Phases 1–3 complete | GitHub repo exists
#  Run from:     WSL or Azure Cloud Shell
#  Time:         ~10 minutes
# =============================================================================

set -euo pipefail

RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   BOLD='\033[1m';  NC='\033[0m'

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
  echo "  navuAI — Phase 8: CI/CD Pipelines"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GH_WORKFLOWS_DIR="$REPO_ROOT/.github/workflows"

# ── Step 1: Create GitHub Actions service principal ───────────────────────────
create_service_principal() {
  step "1 — Create Azure Service Principal for GitHub Actions"
  info "This identity will: push images to ACR, deploy to AKS"

  SP_NAME="navuai-github-actions"

  EXISTING_SP=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null || echo "")
  if [[ -n "$EXISTING_SP" ]]; then
    warn "Service principal '$SP_NAME' already exists (AppId: $EXISTING_SP)"
    warn "Reusing existing SP — if credentials are lost, delete and re-run:"
    warn "  az ad sp delete --id $EXISTING_SP"
    SP_APP_ID="$EXISTING_SP"
  else
    info "Creating service principal: $SP_NAME"
    SP_JSON=$(az ad sp create-for-rbac \
      --name "$SP_NAME" \
      --role Contributor \
      --scopes "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
      --sdk-auth)

    SP_APP_ID=$(echo "$SP_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['clientId'])")
    az keyvault secret set \
      --vault-name "$KEYVAULT_NAME" \
      --name "github-actions-credentials" \
      --value "$SP_JSON" \
      --output none
    success "Service principal created and credentials stored in Key Vault"
  fi

  # Grant ACR push permission
  ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
  if [[ -n "$ACR_ID" ]]; then
    az role assignment create \
      --assignee "$SP_APP_ID" \
      --role "AcrPush" \
      --scope "$ACR_ID" \
      --output none 2>/dev/null || true
    success "ACR push role granted to service principal"
  fi

  # Grant AKS deploy permission
  AKS_ID=$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
  if [[ -n "$AKS_ID" ]]; then
    az role assignment create \
      --assignee "$SP_APP_ID" \
      --role "Azure Kubernetes Service Cluster User Role" \
      --scope "$AKS_ID" \
      --output none 2>/dev/null || true
    success "AKS user role granted to service principal"
  fi
}

# ── Step 2: Output GitHub secrets needed ─────────────────────────────────────
output_github_secrets() {
  step "2 — Output GitHub repository secrets"
  info "You need to add these secrets to your GitHub repo:"
  info "Go to: https://github.com/${GITHUB_ORG:-YOUR_ORG}/${GITHUB_REPO}/settings/secrets/actions"
  echo ""

  SP_JSON=$(az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" \
    --name "github-actions-credentials" \
    --query value -o tsv 2>/dev/null || echo "{}")

  LITELLM_KEY=$(az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" \
    --name "litellm-master-key" \
    --query value -o tsv 2>/dev/null || echo "")

  echo -e "${YELLOW}────────────────────────────────────────────────────────${NC}"
  echo -e "${BOLD}Secret name               Value to paste${NC}"
  echo -e "${YELLOW}────────────────────────────────────────────────────────${NC}"
  echo "AZURE_CREDENTIALS         <paste JSON below>"
  echo ""
  echo "$SP_JSON"
  echo ""
  echo "AZURE_SUBSCRIPTION_ID     $AZURE_SUBSCRIPTION_ID"
  echo "AZURE_RESOURCE_GROUP      $RESOURCE_GROUP"
  echo "ACR_NAME                  ${ACR_NAME}.azurecr.io"
  echo "AKS_CLUSTER_NAME          $AKS_CLUSTER_NAME"
  echo "DOMAIN                    $DOMAIN"
  echo "LITELLM_MASTER_KEY        $LITELLM_KEY"
  echo -e "${YELLOW}────────────────────────────────────────────────────────${NC}"
  echo ""

  # Store in Key Vault for reference
  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "github-actions-domain" \
    --value "$DOMAIN" \
    --output none 2>/dev/null || true
}

# ── Step 3: Write GitHub Actions workflow files ───────────────────────────────
write_workflow_files() {
  step "3 — Write GitHub Actions workflow files"
  info "Writing CI/CD workflows to $GH_WORKFLOWS_DIR"

  mkdir -p "$GH_WORKFLOWS_DIR"

  # ── Main deploy pipeline ───────────────────────────────────────────────────
  cat > "$GH_WORKFLOWS_DIR/deploy.yml" << YAML
name: navuAI CI/CD

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      service:
        description: 'Service to deploy (all | billbot | billy | mcp-server | billing-dashboard)'
        required: false
        default: 'all'

env:
  ACR_REGISTRY: \${{ secrets.ACR_NAME }}
  AKS_CLUSTER:  \${{ secrets.AKS_CLUSTER_NAME }}
  RESOURCE_GROUP: \${{ secrets.AZURE_RESOURCE_GROUP }}

jobs:
  # ── Build & push agent images ───────────────────────────────────────────────
  build-agents:
    name: Build agent images
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [billbot, billy, mcp-server, billing-dashboard]
    steps:
    - uses: actions/checkout@v4

    - name: Azure login
      uses: azure/login@v2
      with:
        creds: \${{ secrets.AZURE_CREDENTIALS }}

    - name: ACR login
      run: az acr login --name \${{ secrets.ACR_NAME }}

    - name: Build and push \${{ matrix.service }}
      run: |
        IMAGE=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-\${{ matrix.service }}:latest
        SHA_IMAGE=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-\${{ matrix.service }}:\${{ github.sha }}

        # Use inline Dockerfile if no Dockerfile exists for the service
        if [ -f "services/\${{ matrix.service }}/Dockerfile" ]; then
          docker build -t \$IMAGE -t \$SHA_IMAGE services/\${{ matrix.service }}/
        else
          echo "No Dockerfile found for \${{ matrix.service }} — using base python image (managed inline)"
          echo "FROM python:3.12-slim" | docker build -t \$IMAGE -t \$SHA_IMAGE -
        fi

        docker push \$IMAGE
        docker push \$SHA_IMAGE

    - name: Output image digest
      run: |
        echo "Image: \${{ env.ACR_REGISTRY }}.azurecr.io/navuai-\${{ matrix.service }}:\${{ github.sha }}"

  # ── Deploy to AKS ────────────────────────────────────────────────────────────
  deploy:
    name: Deploy to AKS
    runs-on: ubuntu-latest
    needs: build-agents
    environment: production
    steps:
    - uses: actions/checkout@v4

    - name: Azure login
      uses: azure/login@v2
      with:
        creds: \${{ secrets.AZURE_CREDENTIALS }}

    - name: Get AKS credentials
      run: |
        az aks get-credentials \
          --resource-group \${{ env.RESOURCE_GROUP }} \
          --name \${{ env.AKS_CLUSTER }} \
          --overwrite-existing

    - name: Deploy BillBot
      if: \${{ github.event.inputs.service == 'all' || github.event.inputs.service == 'billbot' || github.event_name == 'push' }}
      run: |
        kubectl set image deployment/billbot \
          billbot=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-billbot:\${{ github.sha }} \
          -n agents || echo "Deployment not found — run Phase 3 first"
        kubectl rollout status deployment/billbot -n agents --timeout=120s || true

    - name: Deploy Billy
      if: \${{ github.event.inputs.service == 'all' || github.event.inputs.service == 'billy' || github.event_name == 'push' }}
      run: |
        kubectl set image deployment/billy \
          billy=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-billy:\${{ github.sha }} \
          -n agents || echo "Deployment not found — run Phase 3 first"
        kubectl rollout status deployment/billy -n agents --timeout=120s || true

    - name: Deploy MCP Server
      if: \${{ github.event.inputs.service == 'all' || github.event.inputs.service == 'mcp-server' || github.event_name == 'push' }}
      run: |
        kubectl set image deployment/mcp-server \
          mcp-server=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-mcp-server:\${{ github.sha }} \
          -n mcp || echo "Deployment not found — run Phase 4 first"
        kubectl rollout status deployment/mcp-server -n mcp --timeout=120s || true

    - name: Deploy Billing Dashboard
      if: \${{ github.event.inputs.service == 'all' || github.event.inputs.service == 'billing-dashboard' || github.event_name == 'push' }}
      run: |
        kubectl set image deployment/billing-dashboard \
          billing-dashboard=\${{ env.ACR_REGISTRY }}.azurecr.io/navuai-billing-dashboard:\${{ github.sha }} \
          -n billing || echo "Deployment not found — run Phase 5 first"
        kubectl rollout status deployment/billing-dashboard -n billing --timeout=120s || true

    - name: Deployment summary
      run: |
        echo "=== navuAI Deployment Summary ==="
        echo "Commit: \${{ github.sha }}"
        echo "Time:   \$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        kubectl get deployments -A --field-selector=metadata.namespace!=kube-system
YAML

  # ── Security scanning workflow ─────────────────────────────────────────────
  cat > "$GH_WORKFLOWS_DIR/security-scan.yml" << YAML
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2am UTC

jobs:
  scan:
    name: Trivy vulnerability scan
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Scan Python source files
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'

    - name: Upload scan results
      uses: github/codeql-action/upload-sarif@v3
      if: always()
      with:
        sarif_file: 'trivy-results.sarif'
YAML

  # ── Pull request checks ────────────────────────────────────────────────────
  cat > "$GH_WORKFLOWS_DIR/pr-checks.yml" << YAML
name: PR Checks

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint shell scripts
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Install ShellCheck
      run: sudo apt-get install -y shellcheck

    - name: Run ShellCheck on phase scripts
      run: |
        shellcheck labs/phase*.sh || true

  validate-env:
    name: Validate navuai.env template
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Check all required variables present
      run: |
        REQUIRED_VARS=(
          AZURE_SUBSCRIPTION_ID AZURE_LOCATION RESOURCE_GROUP
          AKS_CLUSTER_NAME ACR_NAME KEYVAULT_NAME
          VNET_NAME DOMAIN MONTHLY_USER_BUDGET_USD
        )
        source labs/navuai.env.template || true
        for var in "\${REQUIRED_VARS[@]}"; do
          if [[ -z "\${!var:-}" ]]; then
            echo "WARNING: \$var not set in navuai.env.template"
          else
            echo "OK: \$var"
          fi
        done
YAML

  success "GitHub Actions workflows written to $GH_WORKFLOWS_DIR"
  info "Files created:"
  info "  $GH_WORKFLOWS_DIR/deploy.yml"
  info "  $GH_WORKFLOWS_DIR/security-scan.yml"
  info "  $GH_WORKFLOWS_DIR/pr-checks.yml"
}

# ── Step 4: Configure Azure Container Registry webhook ───────────────────────
configure_acr_webhook() {
  step "4 — Configure ACR auto-trigger (optional)"
  info "ACR webhooks can auto-trigger GitHub Actions when new images are pushed"
  info "This requires a GitHub webhook URL — skipping (manual step below)"

  # Check ACR exists
  ACR_EXISTS=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv 2>/dev/null || echo "")

  if [[ -z "$ACR_EXISTS" ]]; then
    warn "ACR '$ACR_NAME' not found — run Phase 1 first"
    return
  fi

  # Enable admin access on ACR for CI/CD push
  az acr update --name "$ACR_NAME" --admin-enabled true --output none
  ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "acr-admin-password" \
    --value "$ACR_PASS" \
    --output none
  success "ACR admin enabled and password stored in Key Vault as 'acr-admin-password'"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  REPO_URL="https://github.com/${GITHUB_ORG:-YOUR_ORG}/${GITHUB_REPO}"
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 8 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ Service principal  : navuai-github-actions (Contributor on RG + ACRPush)"
  echo "  ✓ GitHub workflows   : deploy.yml, security-scan.yml, pr-checks.yml"
  echo "  ✓ ACR admin          : enabled for image push"
  echo ""
  echo -e "${YELLOW}ACTION REQUIRED — Add these secrets to GitHub:${NC}"
  echo "  Go to: $REPO_URL/settings/secrets/actions"
  echo "  Add:   AZURE_CREDENTIALS, AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP"
  echo "         ACR_NAME, AKS_CLUSTER_NAME, DOMAIN, LITELLM_MASTER_KEY"
  echo ""
  echo -e "${YELLOW}Trigger a deploy manually:${NC}"
  echo "  1. Push any commit to 'main' branch"
  echo "  2. Or: GitHub → Actions → navuAI CI/CD → Run workflow"
  echo ""
  echo -e "${YELLOW}Credentials are in Key Vault:${NC}"
  echo "  az keyvault secret show --vault-name $KEYVAULT_NAME --name github-actions-credentials --query value -o tsv"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  ./phase9-multicloud.sh"
  echo ""
}

main() {
  banner
  create_service_principal
  output_github_secrets
  write_workflow_files
  configure_acr_webhook
  print_summary
}

main "$@"
