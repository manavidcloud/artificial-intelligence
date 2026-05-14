#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# oauth2-proxy + Microsoft Entra ID setup (Idempotent)
# AKS + oauth2-proxy + NGINX Ingress
# ─────────────────────────────────────────────────────────────────
# Features:
#  - Idempotent App Registration
#  - Correct oauth2-proxy cookie secret
#  - Stores secrets in Azure Key Vault
#  - Stores local reference copy (.env.oauth2-proxy)
#  - Helm deployment
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────
APP_NAME="finops-platform"
KV_NAME="kv-finops-prod-002"
RG="rg-finops-prod-core"
DOMAIN="app.manmas.online"
K8S_NAMESPACE="security"

# ── Colors ────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${YELLOW}[INFO]${NC}  $1"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
info "=== oauth2-proxy + Entra ID setup starting ==="
echo ""

# ─────────────────────────────────────────────────────────────────
# 1. Validate prerequisites
# ─────────────────────────────────────────────────────────────────

for cmd in az kubectl helm openssl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    error "Required command not found: $cmd"
  fi
done

pass "All required tools are installed"

# ─────────────────────────────────────────────────────────────────
# 2. Get Tenant ID
# ─────────────────────────────────────────────────────────────────

TENANT_ID=$(az account show --query tenantId -o tsv)

if [[ -z "$TENANT_ID" ]]; then
  error "Unable to determine Tenant ID"
fi

pass "Tenant ID: $TENANT_ID"

# ─────────────────────────────────────────────────────────────────
# 3. Idempotent App Registration
# ─────────────────────────────────────────────────────────────────

info "Checking for existing App Registration..."

APP_ID=$(az ad app list \
  --display-name "$APP_NAME" \
  --query "[0].appId" \
  -o tsv)

if [[ -n "$APP_ID" ]]; then
  pass "Existing App Registration found: $APP_ID"
else
  info "Creating App Registration..."

  APP_ID=$(az ad app create \
    --display-name "$APP_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId \
    -o tsv)

  if [[ -z "$APP_ID" ]]; then
    error "Failed to create App Registration"
  fi

  pass "App Registration created: $APP_ID"
fi

# ─────────────────────────────────────────────────────────────────
# 4. Create / Reset Client Secret
# ─────────────────────────────────────────────────────────────────

info "Creating client secret..."

CLIENT_SECRET=$(az ad app credential reset \
  --id "$APP_ID" \
  --years 2 \
  --query password \
  -o tsv)

if [[ -z "$CLIENT_SECRET" ]]; then
  error "Failed to create client secret"
fi

pass "Client secret created"

# ─────────────────────────────────────────────────────────────────
# 5. Configure Redirect URI
# ─────────────────────────────────────────────────────────────────

REDIRECT_URI="https://${DOMAIN}/oauth2/callback"

info "Configuring redirect URI..."

az ad app update \
  --id "$APP_ID" \
  --web-redirect-uris "$REDIRECT_URI" \
  --output none

pass "Redirect URI configured"

# ─────────────────────────────────────────────────────────────────
# 6. Generate oauth2-proxy Cookie Secret
# ─────────────────────────────────────────────────────────────────

info "Generating oauth2-proxy cookie secret..."

COOKIE_SECRET=$(openssl rand -hex 16)

if [[ -z "$COOKIE_SECRET" ]]; then
  error "Failed to generate cookie secret"
fi

pass "Cookie secret generated"

# ─────────────────────────────────────────────────────────────────
# 7. Store Secrets in Azure Key Vault
# ─────────────────────────────────────────────────────────────────

info "Temporarily enabling public access on Key Vault..."

az keyvault update \
  --name "$KV_NAME" \
  --resource-group "$RG" \
  --public-network-access Enabled \
  --output none

sleep 10

info "Storing secrets in Azure Key Vault..."

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "oauth2-proxy-client-id" \
  --value "$APP_ID" \
  --output none

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "oauth2-proxy-client-secret" \
  --value "$CLIENT_SECRET" \
  --output none

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "oauth2-proxy-cookie-secret" \
  --value "$COOKIE_SECRET" \
  --output none

pass "Secrets stored in Azure Key Vault"

info "Disabling public access on Key Vault..."

az keyvault update \
  --name "$KV_NAME" \
  --resource-group "$RG" \
  --public-network-access Disabled \
  --output none

pass "Key Vault locked down"

# ─────────────────────────────────────────────────────────────────
# 8. Save Local Reference File
# ─────────────────────────────────────────────────────────────────

info "Saving local reference file..."

cat > .env.oauth2-proxy <<EOF
# ─────────────────────────────────────────────
# oauth2-proxy Local Reference
# Generated: $(date)
# ─────────────────────────────────────────────

APP_NAME=${APP_NAME}

APP_ID=${APP_ID}

CLIENT_SECRET=${CLIENT_SECRET}

COOKIE_SECRET=${COOKIE_SECRET}

TENANT_ID=${TENANT_ID}

DOMAIN=${DOMAIN}

REDIRECT_URI=${REDIRECT_URI}

KEYVAULT_NAME=${KV_NAME}

RESOURCE_GROUP=${RG}

K8S_NAMESPACE=${K8S_NAMESPACE}
EOF

chmod 600 .env.oauth2-proxy

pass "Local reference saved: .env.oauth2-proxy"

# ─────────────────────────────────────────────────────────────────
# 9. Create Namespace
# ─────────────────────────────────────────────────────────────────

info "Ensuring namespace exists..."

kubectl create namespace "$K8S_NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

pass "Namespace ready"

# ─────────────────────────────────────────────────────────────────
# 10. Prepare Helm Values
# ─────────────────────────────────────────────────────────────────

info "Preparing Helm values..."

cat > values-oauth2-proxy.yaml <<EOF
config:
  clientID: "${APP_ID}"
  clientSecret: "${CLIENT_SECRET}"
  cookieSecret: "${COOKIE_SECRET}"

extraArgs:
  provider: oidc

  oidc-issuer-url: "https://login.microsoftonline.com/${TENANT_ID}/v2.0"

  redirect-url: "${REDIRECT_URI}"

  upstream: "http://ingress-nginx-controller.ingress-nginx.svc.cluster.local:80"

  email-domain: "*"

  http-address: "0.0.0.0:4180"

  reverse-proxy: "true"

  set-xauthrequest: "true"

  pass-user-headers: "true"

  cookie-secure: "false"

  insecure-oidc-allow-unverified-email: "true"

ingress:
  enabled: false
EOF

pass "Helm values prepared"

# ─────────────────────────────────────────────────────────────────
# 11. Add / Update Helm Repo
# ─────────────────────────────────────────────────────────────────

info "Adding/updating Helm repo..."

helm repo add oauth2-proxy https://oauth2-proxy.github.io/manifests >/dev/null 2>&1 || true

helm repo update >/dev/null 2>&1

pass "Helm repo ready"

# ─────────────────────────────────────────────────────────────────
# 12. Deploy oauth2-proxy
# ─────────────────────────────────────────────────────────────────

info "Deploying oauth2-proxy..."

helm upgrade --install oauth2-proxy oauth2-proxy/oauth2-proxy \
  --namespace "$K8S_NAMESPACE" \
  -f values-oauth2-proxy.yaml \
  --wait \
  --timeout 300s

pass "oauth2-proxy deployed"

# ─────────────────────────────────────────────────────────────────
# 13. Verify Deployment
# ─────────────────────────────────────────────────────────────────

echo ""
info "Checking pod status..."

kubectl get pods -n "$K8S_NAMESPACE"

POD_STATUS=$(kubectl get pods -n "$K8S_NAMESPACE" \
  -l app.kubernetes.io/name=oauth2-proxy \
  -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")

if [[ "$POD_STATUS" == "Running" ]]; then
  pass "oauth2-proxy pod is Running"
else
  echo ""
  info "Fetching logs..."

  kubectl logs -n "$K8S_NAMESPACE" \
    deploy/oauth2-proxy \
    --tail=100 || true

  error "oauth2-proxy pod is not healthy"
fi

# ─────────────────────────────────────────────────────────────────
# 14. Summary
# ─────────────────────────────────────────────────────────────────

echo ""
pass "=== oauth2-proxy setup completed successfully ==="
echo ""
echo "App Name          : $APP_NAME"
echo "App ID            : $APP_ID"
echo "Tenant ID         : $TENANT_ID"
echo "Domain            : $DOMAIN"
echo "Namespace         : $K8S_NAMESPACE"
echo "Key Vault         : $KV_NAME"
echo ""
info "Local reference file:"
echo ".env.oauth2-proxy"
echo ""
info "Verify deployment:"
echo "kubectl get pods -n ${K8S_NAMESPACE}"
echo ""
info "View logs:"
echo "kubectl logs -n ${K8S_NAMESPACE} deploy/oauth2-proxy --tail=100"
echo ""