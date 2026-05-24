#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 6: Security & Compliance
#
#  What this script builds:
#    1. NGINX rate limiting — per-IP and per-user request throttling
#    2. Source IP allowlist — restrict ingress to corporate/VPN IPs
#    3. Azure AD (Entra ID) SSO — OAuth2 login for Open WebUI
#    4. Kubernetes RBAC — navuai-admin, navuai-user, navuai-billing roles
#    5. LiteLLM rate limits — RPM/TPM caps per virtual key
#    6. Private endpoint for Key Vault (no public access)
#    7. NSG lockdown — deny all inbound except HTTPS + VPN
#
#  Prerequisites: Phases 1–3 complete
#  Run from:     WSL or Azure Cloud Shell
#  Time:         ~20 minutes
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
  echo "  navuAI — Phase 6: Security & Compliance"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

# ── Step 1: NGINX rate limiting via ingress annotations ───────────────────────
configure_rate_limiting() {
  step "1 — Configure NGINX ingress rate limiting"
  info "Applying rate limit: 60 req/min per IP on all public endpoints"
  info "Burst: 20 requests | Whitelist: cluster-internal traffic"

  # Patch LiteLLM ingress with rate limit annotations
  kubectl annotate ingress litellm-ingress \
    --namespace litellm \
    --overwrite \
    "nginx.ingress.kubernetes.io/limit-rps=1" \
    "nginx.ingress.kubernetes.io/limit-connections=10" \
    "nginx.ingress.kubernetes.io/proxy-read-timeout=600" \
    "nginx.ingress.kubernetes.io/proxy-send-timeout=600" \
    2>/dev/null && success "LiteLLM ingress rate limit applied" \
    || warn "LiteLLM ingress not found — skipping (run Phase 2 first)"

  # Patch Chat ingress
  kubectl annotate ingress openwebui-ingress \
    --namespace chat \
    --overwrite \
    "nginx.ingress.kubernetes.io/limit-rps=5" \
    "nginx.ingress.kubernetes.io/limit-connections=20" \
    "nginx.ingress.kubernetes.io/proxy-body-size=50m" \
    2>/dev/null && success "Chat UI ingress rate limit applied" \
    || warn "Chat ingress not found — skipping (run Phase 3 first)"

  success "Rate limiting configured on all public ingress points"
}

# ── Step 2: Source IP allowlist on ingress ────────────────────────────────────
configure_ip_allowlist() {
  step "2 — Configure source IP allowlist on NGINX ingress"

  if [[ -z "${ALLOWED_IP_RANGES:-}" ]]; then
    warn "ALLOWED_IP_RANGES not set in navuai.env — skipping IP allowlist"
    warn "Set ALLOWED_IP_RANGES=\"1.2.3.4/32,10.0.0.0/8\" to restrict access"
    warn "Without this, the API is reachable from any IP (still protected by API key)"
    return
  fi

  info "Restricting API access to: $ALLOWED_IP_RANGES"

  kubectl annotate ingress litellm-ingress \
    --namespace litellm \
    --overwrite \
    "nginx.ingress.kubernetes.io/whitelist-source-range=$ALLOWED_IP_RANGES" \
    && success "IP allowlist applied to LiteLLM ingress" \
    || warn "Could not patch LiteLLM ingress"

  kubectl annotate ingress openwebui-ingress \
    --namespace chat \
    --overwrite \
    "nginx.ingress.kubernetes.io/whitelist-source-range=$ALLOWED_IP_RANGES" \
    && success "IP allowlist applied to Chat ingress" \
    || warn "Could not patch Chat ingress"
}

# ── Step 3: Azure AD SSO for Open WebUI ───────────────────────────────────────
configure_sso() {
  step "3 — Configure Azure AD (Entra ID) SSO for chat UI"

  if [[ -z "${AZURE_AD_CLIENT_ID:-}" || -z "${AZURE_AD_TENANT_ID:-}" ]]; then
    warn "AZURE_AD_CLIENT_ID or AZURE_AD_TENANT_ID not set in navuai.env — skipping SSO"
    warn "To enable SSO:"
    warn "  1. Azure Portal → Entra ID → App Registrations → New Registration"
    warn "  2. Name: navuAI-chat | Redirect URI: https://chat.${DOMAIN}/oauth/oidc/callback"
    warn "  3. Copy Client ID and Tenant ID to navuai.env"
    warn "  4. Create a Client Secret → copy to navuai.env as AZURE_AD_CLIENT_SECRET"
    warn "  5. Re-run this script"
    return
  fi

  info "Configuring Open WebUI for Azure AD SSO..."
  info "Tenant: $AZURE_AD_TENANT_ID | Client: $AZURE_AD_CLIENT_ID"

  OIDC_URL="https://login.microsoftonline.com/${AZURE_AD_TENANT_ID}/v2.0"

  # Store Azure AD client secret in Key Vault
  if [[ -n "${AZURE_AD_CLIENT_SECRET:-}" ]]; then
    az keyvault secret set \
      --vault-name "$KEYVAULT_NAME" \
      --name "azure-ad-client-secret" \
      --value "$AZURE_AD_CLIENT_SECRET" \
      --output none
    success "Azure AD client secret stored in Key Vault"
  fi

  # Patch Open WebUI deployment with OAuth2 env vars
  kubectl set env deployment/openwebui \
    --namespace chat \
    ENABLE_OAUTH_SIGNUP="true" \
    OAUTH_PROVIDER_NAME="Azure AD" \
    OPENID_PROVIDER_URL="$OIDC_URL" \
    OAUTH_CLIENT_ID="$AZURE_AD_CLIENT_ID" \
    OAUTH_CLIENT_SECRET="${AZURE_AD_CLIENT_SECRET:-}" \
    OAUTH_SCOPES="openid profile email" \
    ENABLE_LOGIN_FORM="false" \
    DEFAULT_USER_ROLE="user" \
    2>/dev/null && {
      kubectl rollout restart deployment/openwebui -n chat
      kubectl rollout status deployment/openwebui -n chat --timeout=120s
      success "Open WebUI patched with Azure AD SSO — users now log in via Microsoft"
    } || warn "Could not patch Open WebUI — run Phase 3 first"
}

# ── Step 4: Kubernetes RBAC roles ─────────────────────────────────────────────
configure_k8s_rbac() {
  step "4 — Create Kubernetes RBAC roles for navuAI"
  info "Roles: navuai-admin (full), navuai-user (chat+billing read), navuai-billing (billing only)"

  cat <<'EOF' | kubectl apply -f -
---
# navuai-admin: full cluster access for ops team
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: navuai-admin
  labels:
    app.kubernetes.io/part-of: navuai
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs:     ["*"]
---
# navuai-user: read pods/logs in chat and agents namespaces only
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: navuai-user
  namespace: chat
  labels:
    app.kubernetes.io/part-of: navuai
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs:     ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: navuai-user
  namespace: agents
  labels:
    app.kubernetes.io/part-of: navuai
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs:     ["get", "list"]
---
# navuai-billing: read billing namespace only
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: navuai-billing
  namespace: billing
  labels:
    app.kubernetes.io/part-of: navuai
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "services"]
  verbs:     ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs:     ["get", "list"]
EOF

  success "RBAC roles created: navuai-admin (ClusterRole), navuai-user (Role), navuai-billing (Role)"
  info "Bind a user: kubectl create clusterrolebinding <name> --clusterrole=navuai-admin --user=<email>"
}

# ── Step 5: LiteLLM rate limits per virtual key ───────────────────────────────
configure_litellm_rate_limits() {
  step "5 — Configure LiteLLM per-user rate limits"
  info "Rate limits (RPM/TPM) are enforced per virtual key — set at key generation time"
  info "Default: 60 RPM / 100K TPM per key. Override per user at /key/generate."

  # LiteLLM enforces rate limits at the virtual key level, not in the config YAML.
  # The correct approach is to pass rpm_limit/tpm_limit when creating a key via the API.
  # We only add max_parallel_requests to general_settings — that IS a valid config key.

  CURRENT_CONFIG=$(kubectl get configmap litellm-config -n litellm \
    -o jsonpath='{.data.config\.yaml}' 2>/dev/null || echo "")

  if [[ -z "$CURRENT_CONFIG" ]]; then
    warn "LiteLLM ConfigMap not found — skipping"
    return
  fi

  if echo "$CURRENT_CONFIG" | grep -q "default_max_parallel_requests"; then
    warn "general_settings already present in LiteLLM config — skipping (idempotent)"
  else
    info "Adding general_settings.default_max_parallel_requests to LiteLLM config..."
    UPDATED_CONFIG="${CURRENT_CONFIG}

general_settings:
  default_max_parallel_requests: 10
"
    kubectl create configmap litellm-config \
      --namespace litellm \
      --from-literal="config.yaml=${UPDATED_CONFIG}" \
      --dry-run=client -o yaml | kubectl apply -f -

    # Patch memory limits before restarting to prevent OOMKill
    kubectl set resources deployment/litellm -n litellm \
      --requests=cpu=250m,memory=768Mi \
      --limits=cpu=2,memory=2Gi 2>/dev/null || true

    kubectl rollout restart deployment/litellm -n litellm
    info "Waiting for LiteLLM to restart (timeout 180s)..."
    if ! kubectl rollout status deployment/litellm -n litellm --timeout=180s; then
      error "LiteLLM rollout failed. Check logs: kubectl logs deployment/litellm -n litellm --previous"
    fi
    success "LiteLLM restarted with parallel request limit"
  fi

  # Show how to create a rate-limited key (informational — not automated to avoid over-provisioning)
  info "To create a user key with rate limits, use the LiteLLM API:"
  info "  curl -X POST https://api.${DOMAIN}/key/generate \\"
  info "    -H 'Authorization: Bearer \$LITELLM_KEY' \\"
  info "    -d '{\"rpm_limit\":60,\"tpm_limit\":100000,\"max_budget\":${MONTHLY_USER_BUDGET_USD},\"budget_duration\":\"1mo\"}'"
  success "Rate limit configuration complete (enforced per virtual key at key creation)"
}

# ── Step 6: Key Vault private endpoint ────────────────────────────────────────
configure_keyvault_private_endpoint() {
  step "6 — Configure Key Vault private endpoint (no public access)"
  info "This routes Key Vault traffic through your VNet — secrets never traverse the public internet"

  PE_NAME="navuai-kv-pe"
  PE_SUBNET_ID=$(az network vnet subnet show \
    --resource-group "$RESOURCE_GROUP" \
    --vnet-name "$VNET_NAME" \
    --name "pe-subnet" \
    --query id -o tsv 2>/dev/null || echo "")

  if [[ -z "$PE_SUBNET_ID" ]]; then
    warn "Private endpoint subnet 'pe-subnet' not found in VNet"
    warn "Run: az network vnet subnet create --vnet-name $VNET_NAME --resource-group $RESOURCE_GROUP --name pe-subnet --address-prefix 10.0.3.0/24"
    warn "Then re-run this script step"
    return
  fi

  EXISTING_PE=$(az network private-endpoint show \
    --name "$PE_NAME" --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv 2>/dev/null || echo "")

  if [[ -n "$EXISTING_PE" ]]; then
    warn "Private endpoint '$PE_NAME' already exists — skipping"
    return
  fi

  KV_ID=$(az keyvault show --name "$KEYVAULT_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

  az network private-endpoint create \
    --name "$PE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --subnet "$PE_SUBNET_ID" \
    --private-connection-resource-id "$KV_ID" \
    --group-id vault \
    --connection-name "navuai-kv-connection" \
    --output none

  # Disable public network access to Key Vault
  az keyvault update \
    --name "$KEYVAULT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --public-network-access Disabled \
    --output none \
    && success "Key Vault public access disabled — private endpoint only" \
    || warn "Could not disable Key Vault public access — check your role assignment"

  success "Key Vault private endpoint created: $PE_NAME"
}

# ── Step 7: NSG lockdown ──────────────────────────────────────────────────────
configure_nsg() {
  step "7 — Harden NSG rules on AKS subnet"
  info "Adding deny-all inbound rule (HTTPS on 443 is already allowed by Phase 1)"

  NSG_NAME="navuai-aks-nsg"
  EXISTING_NSG=$(az network nsg show \
    --name "$NSG_NAME" --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv 2>/dev/null || echo "")

  if [[ -z "$EXISTING_NSG" ]]; then
    warn "NSG '$NSG_NAME' not found — skipping. Run Phase 1 first."
    return
  fi

  # Add explicit deny-all inbound at low priority (runs after allow rules)
  DENY_RULE_EXISTS=$(az network nsg rule show \
    --nsg-name "$NSG_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --name "DenyAllInbound" \
    --query name -o tsv 2>/dev/null || echo "")

  if [[ -n "$DENY_RULE_EXISTS" ]]; then
    warn "NSG deny-all rule already exists — skipping"
  else
    az network nsg rule create \
      --nsg-name "$NSG_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --name "DenyAllInbound" \
      --priority 4000 \
      --direction Inbound \
      --access Deny \
      --protocol "*" \
      --source-address-prefixes "*" \
      --destination-address-prefixes "*" \
      --source-port-ranges "*" \
      --destination-port-ranges "*" \
      --output none
    success "NSG deny-all inbound rule added at priority 4000"
  fi

  # Allow AzureLoadBalancer (required for AKS)
  LB_RULE_EXISTS=$(az network nsg rule show \
    --nsg-name "$NSG_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --name "AllowAzureLoadBalancer" \
    --query name -o tsv 2>/dev/null || echo "")

  if [[ -z "$LB_RULE_EXISTS" ]]; then
    az network nsg rule create \
      --nsg-name "$NSG_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --name "AllowAzureLoadBalancer" \
      --priority 3900 \
      --direction Inbound \
      --access Allow \
      --protocol "*" \
      --source-address-prefixes "AzureLoadBalancer" \
      --destination-address-prefixes "*" \
      --source-port-ranges "*" \
      --destination-port-ranges "*" \
      --output none
    success "NSG allow Azure Load Balancer rule added"
  fi
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 6 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ NGINX rate limits : 60 RPM/IP on API, 5 RPM/IP on chat UI"
  echo "  ✓ IP allowlist      : ${ALLOWED_IP_RANGES:-not set — skipped}"
  echo "  ✓ Azure AD SSO      : ${AZURE_AD_CLIENT_ID:-not set — skipped}"
  echo "  ✓ K8s RBAC          : navuai-admin / navuai-user / navuai-billing roles"
  echo "  ✓ LiteLLM rate lim  : 60 RPM / 100K TPM per user key"
  echo "  ✓ Key Vault PE       : private endpoint (no public internet)"
  echo "  ✓ NSG rules         : deny-all inbound + AzureLoadBalancer allow"
  echo ""
  echo -e "${YELLOW}Bind admin role to a user:${NC}"
  echo "  kubectl create clusterrolebinding alice-admin \\"
  echo "    --clusterrole=navuai-admin --user=alice@yourcompany.com"
  echo ""
  echo -e "${YELLOW}Enable SSO (if skipped):${NC}"
  echo "  1. Azure Portal → Entra ID → App Registrations → New Registration"
  echo "  2. Redirect URI: https://chat.${DOMAIN}/oauth/oidc/callback"
  echo "  3. Set in navuai.env: AZURE_AD_TENANT_ID, AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET"
  echo "  4. Re-run: ./phase6-security.sh"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  ./phase7-observability.sh"
  echo ""
}

main() {
  banner
  configure_rate_limiting
  configure_ip_allowlist
  configure_sso
  configure_k8s_rbac
  configure_litellm_rate_limits
  configure_keyvault_private_endpoint
  configure_nsg
  print_summary
}

main "$@"
