#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 2: LiteLLM API Gateway
#
#  What this script builds:
#    1. Pushes real API keys from navuai.env into Azure Key Vault
#    2. Creates Kubernetes namespace + secrets for LiteLLM
#    3. Deploys PostgreSQL (for usage tracking)
#    4. Deploys LiteLLM with full multi-provider config
#    5. Exposes LiteLLM via Ingress (HTTPS)
#    6. Validates HTTPS endpoint end-to-end
#
#  Self-healing: detects pod failures, reads logs, fixes known issues, retries.
#  Prerequisites: Phase 1 must be complete
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
  echo "  navuAI — Phase 2: LiteLLM API Gateway"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

LITELLM_NS="litellm"

# Read stable passwords from Key Vault (set once by phase1, never regenerated)
POSTGRES_PASSWORD=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "postgres-password"  --query value -o tsv 2>/dev/null || echo "")
LITELLM_MASTER_KEY=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "litellm-master-key" --query value -o tsv 2>/dev/null || echo "")

if [[ -z "$POSTGRES_PASSWORD" || -z "$LITELLM_MASTER_KEY" ]]; then
  error "Key Vault secrets not found. Did Phase 1 complete successfully?\n  Expected: 'postgres-password' and 'litellm-master-key' in $KEYVAULT_NAME"
fi

# ── Generic: wait for a deployment to become ready, with self-diagnosis ────────
wait_for_deployment() {
  local deploy=$1
  local ns=$2
  local timeout=${3:-180}
  local max_checks=36  # check every 5s for up to 3 minutes

  info "Waiting for deployment/$deploy to be ready..."

  for i in $(seq 1 $max_checks); do
    STATUS=$(kubectl get deployment "$deploy" -n "$ns" \
      -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")

    if [[ "$STATUS" == "True" ]]; then
      success "deployment/$deploy is Ready"
      return 0
    fi

    # Detect CrashLoopBackOff or Error state early
    POD_STATUS=$(kubectl get pods -n "$ns" -l "app=$deploy" \
      --no-headers 2>/dev/null | awk '{print $3}' | head -1 || echo "")

    if [[ "$POD_STATUS" == "CrashLoopBackOff" || "$POD_STATUS" == "Error" ]]; then
      warn "Pod is in $POD_STATUS — reading logs for diagnosis..."
      echo -e "${YELLOW}── Pod logs (last 30 lines) ──────────────────${NC}"
      kubectl logs -n "$ns" -l "app=$deploy" --tail=30 2>/dev/null || true
      echo -e "${YELLOW}──────────────────────────────────────────────${NC}"
      return 1
    fi

    info "[$i/$max_checks] Status: ${POD_STATUS:-Pending} — waiting 5s..."
    sleep 5
  done

  warn "Timeout waiting for deployment/$deploy. Current state:"
  kubectl get pods -n "$ns" -l "app=$deploy" 2>/dev/null || true
  kubectl logs -n "$ns" -l "app=$deploy" --tail=30 2>/dev/null || true
  return 1
}

# ── Step 1: Push real secrets to Key Vault ───────────────────────────────────
push_secrets_to_keyvault() {
  step "1 — Storing API Keys in Azure Key Vault"
  info "Keys are stored in Key Vault — never in code or config files"

  [[ -n "$OPENAI_API_KEY" ]]        && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "openai-api-key"    --value "$OPENAI_API_KEY"        --output none && success "OpenAI key stored"
  [[ -n "$AZURE_OPENAI_KEY" ]]      && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "azure-openai-key"  --value "$AZURE_OPENAI_KEY"      --output none && success "Azure OpenAI key stored"
  [[ -n "$AZURE_OPENAI_ENDPOINT" ]] && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "azure-openai-endpoint" --value "$AZURE_OPENAI_ENDPOINT" --output none && success "Azure OpenAI endpoint stored"
  [[ -n "$AWS_ACCESS_KEY_ID" ]]     && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "aws-access-key-id" --value "$AWS_ACCESS_KEY_ID"     --output none && success "AWS key ID stored"
  [[ -n "$AWS_SECRET_ACCESS_KEY" ]] && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "aws-secret-key"    --value "$AWS_SECRET_ACCESS_KEY" --output none && success "AWS secret key stored"
  [[ -n "$VERTEX_PROJECT" ]]        && az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "vertex-project"    --value "$VERTEX_PROJECT"        --output none && success "Vertex project stored"

  success "All secrets stored in Key Vault: $KEYVAULT_NAME"
}

# ── Step 2: Create Namespace ──────────────────────────────────────────────────
create_namespace() {
  step "2 — Create Kubernetes Namespace: $LITELLM_NS"
  kubectl create namespace "$LITELLM_NS" --dry-run=client -o yaml | kubectl apply -f -
  success "Namespace '$LITELLM_NS' ready"
}

# ── Step 3: Create Kubernetes Secrets ────────────────────────────────────────
create_k8s_secrets() {
  step "3 — Create Kubernetes Secrets (pulled from Key Vault)"

  OPENAI_KEY_VAL=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "openai-api-key"       --query value -o tsv 2>/dev/null || echo "")
  AZ_OAI_KEY_VAL=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "azure-openai-key"     --query value -o tsv 2>/dev/null || echo "")
  AZ_OAI_EP_VAL=$(az keyvault secret show  --vault-name "$KEYVAULT_NAME" --name "azure-openai-endpoint" --query value -o tsv 2>/dev/null || echo "$AZURE_OPENAI_ENDPOINT")
  AWS_KEY_VAL=$(az keyvault secret show    --vault-name "$KEYVAULT_NAME" --name "aws-access-key-id"    --query value -o tsv 2>/dev/null || echo "")
  AWS_SEC_VAL=$(az keyvault secret show    --vault-name "$KEYVAULT_NAME" --name "aws-secret-key"       --query value -o tsv 2>/dev/null || echo "")
  VERTEX_VAL=$(az keyvault secret show     --vault-name "$KEYVAULT_NAME" --name "vertex-project"       --query value -o tsv 2>/dev/null || echo "")

  kubectl create secret generic litellm-secrets \
    --namespace "$LITELLM_NS" \
    --from-literal=OPENAI_API_KEY="$OPENAI_KEY_VAL" \
    --from-literal=AZURE_API_KEY="$AZ_OAI_KEY_VAL" \
    --from-literal=AZURE_API_BASE="$AZ_OAI_EP_VAL" \
    --from-literal=AZURE_API_VERSION="$AZURE_OPENAI_API_VERSION" \
    --from-literal=AWS_ACCESS_KEY_ID="$AWS_KEY_VAL" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SEC_VAL" \
    --from-literal=AWS_REGION_NAME="$AWS_REGION" \
    --from-literal=VERTEX_PROJECT="$VERTEX_VAL" \
    --from-literal=VERTEX_LOCATION="$VERTEX_LOCATION" \
    --from-literal=LITELLM_MASTER_KEY="$LITELLM_MASTER_KEY" \
    --from-literal=DATABASE_URL="postgresql://litellm:${POSTGRES_PASSWORD}@postgres-svc:5432/litellm" \
    --dry-run=client -o yaml | kubectl apply -f -

  success "Kubernetes secret 'litellm-secrets' ready in namespace '$LITELLM_NS'"
}

# ── Step 4: Deploy PostgreSQL (self-healing) ──────────────────────────────────
deploy_postgres() {
  step "4 — Deploy PostgreSQL (usage tracking database)"

  # PVC: skip if exists — Kubernetes forbids reducing size, and Azure may have provisioned larger
  if kubectl get pvc postgres-pvc -n "$LITELLM_NS" &>/dev/null; then
    warn "PVC 'postgres-pvc' already exists — skipping to preserve data"
  else
    kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: ${LITELLM_NS}
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
EOF
  fi

  # Skip full redeploy if postgres is already healthy
  PG_STATUS=$(kubectl get deployment postgres -n "$LITELLM_NS" \
    -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")
  if [[ "$PG_STATUS" == "True" ]]; then
    success "PostgreSQL already running and healthy — skipping redeploy"
  else
  kubectl apply -f - <<EOF
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: ${LITELLM_NS}
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: litellm
        - name: POSTGRES_USER
          value: litellm
        - name: POSTGRES_PASSWORD
          value: "${POSTGRES_PASSWORD}"
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: ["pg_isready", "-U", "litellm"]
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: pgdata
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-svc
  namespace: ${LITELLM_NS}
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
EOF
  fi  # end: skip if already healthy

  # Self-healing: retry once if postgres crashes (e.g. lost+found on fresh PVC)
  if ! wait_for_deployment "postgres" "$LITELLM_NS" 120; then
    warn "PostgreSQL failed — checking for known issues..."
    LOGS=$(kubectl logs -n "$LITELLM_NS" -l app=postgres --tail=10 2>/dev/null || echo "")

    if echo "$LOGS" | grep -q "lost+found\|not empty\|is not empty"; then
      warn "Detected: Azure disk lost+found issue. PGDATA is already set to subdirectory — forcing pod restart..."
      kubectl rollout restart deployment/postgres -n "$LITELLM_NS"
      wait_for_deployment "postgres" "$LITELLM_NS" 120 || error "PostgreSQL failed to recover. Logs above show the cause."
    else
      error "PostgreSQL failed for unknown reason. Check logs above."
    fi
  fi

  success "PostgreSQL is running"
}

# ── Step 5: Build LiteLLM config ─────────────────────────────────────────────
create_litellm_config() {
  step "5 — Create LiteLLM Configuration (model routing)"

  # Only include GPU models if the VM exists
  GPU_MODELS=""
  if [[ "${SKIP_GPU_VM:-true}" != "true" ]]; then
    GPU_VM_IP=$(az vm show \
      --resource-group "$RESOURCE_GROUP" \
      --name "${GPU_VM_NAME:-navuai-gpu-vm}" \
      --query privateIps -d -o tsv 2>/dev/null || echo "")
    if [[ -n "$GPU_VM_IP" ]]; then
      GPU_MODELS="
      # ── Self-Hosted GPU VM (Ollama) ──────────────────────
      - model_name: local-llama3
        litellm_params:
          model: openai/llama3
          api_base: http://${GPU_VM_IP}:11434/v1
          api_key: none

      - model_name: local-embed
        litellm_params:
          model: openai/nomic-embed-text
          api_base: http://${GPU_VM_IP}:11434/v1
          api_key: none"
    fi
  fi

  # Build model list — only include providers with actual credentials
  OPENAI_MODELS=""
  if [[ -n "$OPENAI_API_KEY" ]]; then
    OPENAI_MODELS="
      # ── OpenAI ───────────────────────────────────────────
      - model_name: gpt-4o
        litellm_params:
          model: openai/gpt-4o
          api_key: os.environ/OPENAI_API_KEY

      - model_name: gpt-4o-mini
        litellm_params:
          model: openai/gpt-4o-mini
          api_key: os.environ/OPENAI_API_KEY"
  fi

  BEDROCK_MODELS=""
  if [[ -n "$AWS_ACCESS_KEY_ID" ]]; then
    BEDROCK_MODELS="
      # ── AWS Bedrock ──────────────────────────────────────
      - model_name: claude-3-5-sonnet
        litellm_params:
          model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
          aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
          aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
          aws_region_name: os.environ/AWS_REGION_NAME"
  fi

  VERTEX_MODELS=""
  if [[ -n "$VERTEX_PROJECT" ]]; then
    VERTEX_MODELS="
      # ── Google Vertex AI ─────────────────────────────────
      - model_name: gemini-2-0-flash
        litellm_params:
          model: vertex_ai/gemini-2.0-flash-001
          vertex_project: os.environ/VERTEX_PROJECT
          vertex_location: os.environ/VERTEX_LOCATION"
  fi

  kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: litellm-config
  namespace: ${LITELLM_NS}
data:
  config.yaml: |
    model_list:

      # ── Azure AI Foundry (always present) ────────────────
      - model_name: azure-gpt41-nano
        litellm_params:
          model: azure/gpt-4.1-nano
          api_base: os.environ/AZURE_API_BASE
          api_key: os.environ/AZURE_API_KEY
          api_version: os.environ/AZURE_API_VERSION
${OPENAI_MODELS}
${BEDROCK_MODELS}
${VERTEX_MODELS}
${GPU_MODELS}

    router_settings:
      enable_pre_call_check: false
      routing_strategy: least-busy

    litellm_settings:
      drop_params: true
      request_timeout: 600
      # langfuse callbacks enabled in phase7
      # success_callback: ["langfuse"]
      # failure_callback: ["langfuse"]

    general_settings:
      master_key: os.environ/LITELLM_MASTER_KEY
      database_url: os.environ/DATABASE_URL
      store_model_in_db: true
EOF

  success "LiteLLM config ready"
}

# ── Step 6: Deploy LiteLLM (self-healing) ────────────────────────────────────
deploy_litellm() {
  step "6 — Deploy LiteLLM API Gateway"

  kubectl apply -f - <<EOF
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litellm
  namespace: ${LITELLM_NS}
  labels:
    app: litellm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: litellm
  template:
    metadata:
      labels:
        app: litellm
    spec:
      containers:
      - name: litellm
        image: ghcr.io/berriai/litellm:main-latest
        args: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "1"]
        ports:
        - containerPort: 4000
        envFrom:
        - secretRef:
            name: litellm-secrets
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health/liveliness
            port: 4000
          initialDelaySeconds: 90
          periodSeconds: 15
          failureThreshold: 5
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 4000
          initialDelaySeconds: 60
          periodSeconds: 10
          failureThreshold: 10
      volumes:
      - name: config
        configMap:
          name: litellm-config
---
apiVersion: v1
kind: Service
metadata:
  name: litellm-svc
  namespace: ${LITELLM_NS}
spec:
  selector:
    app: litellm
  ports:
  - port: 80
    targetPort: 4000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: litellm-ingress
  namespace: ${LITELLM_NS}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
spec:
  tls:
  - hosts:
    - ${API_SUBDOMAIN}.${DOMAIN}
    secretName: litellm-tls
  rules:
  - host: ${API_SUBDOMAIN}.${DOMAIN}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: litellm-svc
            port:
              number: 80
EOF

  # Restart to pick up any configmap changes (safe — probes give 90s grace)
  kubectl rollout restart deployment/litellm -n "$LITELLM_NS"

  # Self-healing: if litellm crashes, show logs and diagnose
  if ! wait_for_deployment "litellm" "$LITELLM_NS" 180; then
    warn "LiteLLM failed — checking for known issues..."
    LOGS=$(kubectl logs -n "$LITELLM_NS" -l app=litellm --tail=30 2>/dev/null || echo "")

    if echo "$LOGS" | grep -q "prisma\|database\|connection refused\|ECONNREFUSED"; then
      warn "Detected: database connection issue — verifying PostgreSQL is healthy..."
      PG_READY=$(kubectl get pods -n "$LITELLM_NS" -l app=postgres --no-headers | awk '{print $3}')
      if [[ "$PG_READY" != "Running" ]]; then
        error "PostgreSQL is not Running ($PG_READY). Fix postgres first, then re-run this script."
      fi
      warn "PostgreSQL is running but LiteLLM can't connect — restarting LiteLLM to retry migration..."
      kubectl rollout restart deployment/litellm -n "$LITELLM_NS"
      wait_for_deployment "litellm" "$LITELLM_NS" 180 || error "LiteLLM still failing. Run: kubectl logs deployment/litellm -n litellm"
    elif echo "$LOGS" | grep -q "config\|yaml\|parse"; then
      error "LiteLLM config parse error. Run: kubectl logs deployment/litellm -n $LITELLM_NS"
    else
      error "LiteLLM failed. Run: kubectl logs deployment/litellm -n $LITELLM_NS"
    fi
  fi

  success "LiteLLM is running"
}

# ── Step 7: Wait for TLS cert + validate HTTPS ───────────────────────────────
wait_for_certificate() {
  local cert_name=$1
  local namespace=$2
  local max_wait=30

  step "7a — Wait for TLS Certificate: $cert_name"
  info "cert-manager: READY=False (issuing) → READY=True (active)"

  for i in $(seq 1 $max_wait); do
    READY=$(kubectl get certificate "$cert_name" -n "$namespace" \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "NotFound")

    if [[ "$READY" == "True" ]]; then
      success "Certificate '$cert_name' READY: True — TLS active"
      return 0
    fi

    REASON=$(kubectl get certificate "$cert_name" -n "$namespace" \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null || echo "unknown")
    info "[$i/$max_wait] READY: $READY ($REASON) — waiting 10s..."
    sleep 10
  done

  warn "Certificate did not become ready in time."
  warn "Debug: kubectl describe certificate $cert_name -n $namespace"
  warn "Common causes: DNS A record not pointing to ingress IP, or port 80 blocked"
}

verify_providers() {
  step "7 — Validate HTTPS endpoint"

  wait_for_certificate "litellm-tls" "$LITELLM_NS"

  info "Curling https://${API_SUBDOMAIN}.${DOMAIN}/health..."
  for i in {1..6}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      "https://${API_SUBDOMAIN}.${DOMAIN}/health" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
      success "HTTPS validation passed — ${API_SUBDOMAIN}.${DOMAIN} is live (HTTP $HTTP_CODE)"
      return 0
    fi
    warn "[$i/6] HTTP $HTTP_CODE — retrying in 10s..."
    sleep 10
  done

  warn "HTTPS validation did not return 200. Debug:"
  warn "  curl -v https://${API_SUBDOMAIN}.${DOMAIN}/health"
  warn "  kubectl logs deployment/litellm -n $LITELLM_NS --tail=20"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  LTM_KEY=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "litellm-master-key" --query value -o tsv 2>/dev/null || echo "check Key Vault")
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 2 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ API keys stored in Key Vault"
  echo "  ✓ PostgreSQL (usage tracking)"
  echo "  ✓ LiteLLM gateway"
  echo "  ✓ Ingress: https://${API_SUBDOMAIN}.${DOMAIN}"
  echo ""
  echo -e "${YELLOW}LiteLLM master key (save this):${NC}"
  echo "  $LTM_KEY"
  echo ""
  echo -e "${YELLOW}Test:${NC}"
  echo "  curl https://${API_SUBDOMAIN}.${DOMAIN}/v1/models \\"
  echo "    -H 'Authorization: Bearer $LTM_KEY'"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  bash phase3-ai-agents.sh"
  echo ""
}

main() {
  banner
  push_secrets_to_keyvault
  create_namespace
  create_k8s_secrets
  deploy_postgres
  create_litellm_config
  deploy_litellm
  verify_providers
  print_summary
}

main "$@"
