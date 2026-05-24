#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 7: Observability & Monitoring
#
#  What this script builds:
#    1. Langfuse — open-source LLM trace observability (every prompt/response logged)
#    2. Prometheus — metrics collection (LiteLLM + AKS node/pod metrics)
#    3. Grafana — dashboards for LLM usage, cost, latency, error rates
#    4. LiteLLM callback — wires LiteLLM to send traces to Langfuse
#    5. Azure Monitor — container insights + log analytics workspace
#
#  Prerequisites: Phases 1–2 complete (AKS + LiteLLM running)
#  Run from:     WSL or Azure Cloud Shell
#  Time:         ~15 minutes
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
  echo "  navuAI — Phase 7: Observability & Monitoring"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

OBS_NS="observability"

# ── Step 1: Create observability namespace ────────────────────────────────────
create_namespace() {
  step "1 — Create Kubernetes Namespace 'observability'"
  kubectl create namespace "$OBS_NS" --dry-run=client -o yaml | kubectl apply -f -
  success "Namespace 'observability' ready"
}

# ── Step 2: Deploy Langfuse (LLM trace observability) ─────────────────────────
deploy_langfuse() {
  step "2 — Deploy Langfuse (LLM observability)"
  info "Langfuse traces every LLM request: model, tokens, latency, cost, user, prompt, response"
  info "Access: kubectl port-forward svc/langfuse-svc 3000:3000 -n observability"

  LANGFUSE_STATUS=$(kubectl get deployment langfuse -n "$OBS_NS" \
    -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")
  if [[ "$LANGFUSE_STATUS" == "True" ]]; then
    success "Langfuse already running — skipping redeploy"
    return
  fi

  # Langfuse requires a PostgreSQL database
  info "Deploying Langfuse PostgreSQL database..."
  LANGFUSE_PG_PASS=$(openssl rand -hex 16)
  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "langfuse-pg-password" \
    --value "$LANGFUSE_PG_PASS" \
    --output none 2>/dev/null || true

  kubectl create secret generic langfuse-secrets \
    --namespace "$OBS_NS" \
    --from-literal=LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
    --from-literal=LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
    --from-literal=DATABASE_URL="postgresql://langfuse:${LANGFUSE_PG_PASS}@langfuse-postgres-svc:5432/langfuse" \
    --from-literal=NEXTAUTH_SECRET="$(openssl rand -hex 32)" \
    --from-literal=NEXTAUTH_URL="http://langfuse-svc:3000" \
    --from-literal=POSTGRES_PASSWORD="$LANGFUSE_PG_PASS" \
    --dry-run=client -o yaml | kubectl apply -f -

  cat <<'EOF' | kubectl apply -f -
---
# Langfuse PostgreSQL
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse-postgres
  namespace: observability
  labels:
    app: langfuse-postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: langfuse-postgres
  template:
    metadata:
      labels:
        app: langfuse-postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: langfuse
        - name: POSTGRES_USER
          value: langfuse
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: langfuse-postgres-svc
  namespace: observability
spec:
  selector:
    app: langfuse-postgres
  ports:
  - port: 5432
    targetPort: 5432
---
# Langfuse web app
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
  namespace: observability
  labels:
    app: langfuse
spec:
  replicas: 1
  selector:
    matchLabels:
      app: langfuse
  template:
    metadata:
      labels:
        app: langfuse
    spec:
      initContainers:
      - name: wait-for-postgres
        image: busybox
        command: ['sh', '-c', 'until nc -z langfuse-postgres-svc 5432; do echo waiting for postgres; sleep 2; done']
      containers:
      - name: langfuse
        image: langfuse/langfuse:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: DATABASE_URL
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: NEXTAUTH_SECRET
        - name: NEXTAUTH_URL
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: NEXTAUTH_URL
        - name: LANGFUSE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: LANGFUSE_SECRET_KEY
        - name: LANGFUSE_PUBLIC_KEY
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: LANGFUSE_PUBLIC_KEY
        - name: TELEMETRY_ENABLED
          value: "false"
        livenessProbe:
          httpGet:
            path: /api/public/health
            port: 3000
          initialDelaySeconds: 60
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /api/public/health
            port: 3000
          initialDelaySeconds: 45
          periodSeconds: 10
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: langfuse-svc
  namespace: observability
spec:
  selector:
    app: langfuse
  ports:
  - port: 3000
    targetPort: 3000
EOF

  info "Waiting for Langfuse PostgreSQL to start..."
  kubectl rollout status deployment/langfuse-postgres -n "$OBS_NS" --timeout=120s
  info "Waiting for Langfuse to start (may take 2–3 minutes for first-run DB migration)..."
  kubectl rollout status deployment/langfuse -n "$OBS_NS" --timeout=300s
  success "Langfuse deployed (internal: langfuse-svc.observability.svc.cluster.local:3000)"
}

# ── Step 3: Deploy Prometheus + Grafana via Helm ──────────────────────────────
deploy_prometheus_grafana() {
  step "3 — Deploy Prometheus + Grafana (kube-prometheus-stack)"
  info "Prometheus scrapes LiteLLM metrics + AKS node/pod metrics"
  info "Grafana builds dashboards for token usage, latency, error rates, cost"

  # Add Helm repos
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts \
    --force-update 2>/dev/null || true
  helm repo update 2>/dev/null || true

  # Check if already installed
  EXISTING=$(helm list -n "$OBS_NS" --filter "kube-prometheus" --short 2>/dev/null || echo "")
  if [[ -n "$EXISTING" ]]; then
    warn "kube-prometheus-stack already installed — upgrading..."
    HELM_CMD="upgrade"
  else
    HELM_CMD="install"
  fi

  # Install kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
  helm "$HELM_CMD" kube-prometheus prometheus-community/kube-prometheus-stack \
    --namespace "$OBS_NS" \
    --set grafana.adminPassword="$GRAFANA_ADMIN_PASSWORD" \
    --set grafana.service.type="ClusterIP" \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
    --set prometheus.prometheusSpec.retention="30d" \
    --set prometheus.prometheusSpec.retentionSize="10GB" \
    --set alertmanager.alertmanagerSpec.retention="120h" \
    --set kubeStateMetrics.enabled=true \
    --set nodeExporter.enabled=true \
    --timeout 10m \
    --wait

  success "Prometheus + Grafana deployed in namespace 'observability'"
  info "Grafana access: kubectl port-forward svc/kube-prometheus-grafana 3001:80 -n observability"
  info "Default login: admin / $GRAFANA_ADMIN_PASSWORD"
}

# ── Step 4: Wire LiteLLM → Langfuse callback ──────────────────────────────────
configure_litellm_langfuse() {
  step "4 — Wire LiteLLM to send traces to Langfuse"
  info "Adding success_callback and failure_callback to LiteLLM config"

  CURRENT_CONFIG=$(kubectl get configmap litellm-config -n litellm \
    -o jsonpath='{.data.config\.yaml}' 2>/dev/null || echo "")

  if [[ -z "$CURRENT_CONFIG" ]]; then
    warn "LiteLLM ConfigMap not found — skipping Langfuse callback"
    warn "After Phase 2 completes, re-run this script."
    return
  fi

  if echo "$CURRENT_CONFIG" | grep -q "langfuse"; then
    warn "Langfuse already wired into LiteLLM — skipping (idempotent)"
    return
  fi

  LANGFUSE_HOST="http://langfuse-svc.observability.svc.cluster.local:3000"

  # Replace or append litellm_settings section
  UPDATED_CONFIG=$(echo "$CURRENT_CONFIG" | sed 's/success_callback: \[\]/success_callback: ["langfuse"]/' | \
    sed 's/failure_callback: \[\]/failure_callback: ["langfuse"]/')

  if ! echo "$UPDATED_CONFIG" | grep -q "langfuse_host"; then
    UPDATED_CONFIG="${UPDATED_CONFIG}

environment_variables:
  LANGFUSE_PUBLIC_KEY: \"${LANGFUSE_PUBLIC_KEY}\"
  LANGFUSE_SECRET_KEY: \"${LANGFUSE_SECRET_KEY}\"
  LANGFUSE_HOST: \"${LANGFUSE_HOST}\"
"
  fi

  kubectl create configmap litellm-config \
    --namespace litellm \
    --from-literal="config.yaml=${UPDATED_CONFIG}" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl rollout restart deployment/litellm -n litellm
  kubectl rollout status deployment/litellm -n litellm --timeout=120s
  success "LiteLLM now sends all traces to Langfuse"
}

# ── Step 5: Azure Monitor container insights ──────────────────────────────────
configure_azure_monitor() {
  step "5 — Enable Azure Monitor Container Insights for AKS"
  info "Container Insights gives CPU/memory/pod metrics in Azure Portal"

  # Check if already enabled
  INSIGHTS_STATUS=$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER_NAME" \
    --query "addonProfiles.omsagent.enabled" \
    -o tsv 2>/dev/null || echo "false")

  if [[ "$INSIGHTS_STATUS" == "true" ]]; then
    warn "Container Insights already enabled — skipping"
    return
  fi

  # Create Log Analytics workspace
  LOG_WORKSPACE="navuai-logs"
  EXISTING_WS=$(az monitor log-analytics workspace show \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_WORKSPACE" \
    --query id -o tsv 2>/dev/null || echo "")

  if [[ -z "$EXISTING_WS" ]]; then
    info "Creating Log Analytics workspace: $LOG_WORKSPACE"
    az monitor log-analytics workspace create \
      --resource-group "$RESOURCE_GROUP" \
      --workspace-name "$LOG_WORKSPACE" \
      --location "$AZURE_LOCATION" \
      --retention-time 30 \
      --output none
    success "Log Analytics workspace created"
  else
    info "Log Analytics workspace '$LOG_WORKSPACE' already exists"
  fi

  WS_ID=$(az monitor log-analytics workspace show \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_WORKSPACE" \
    --query id -o tsv)

  # Enable Container Insights on AKS
  az aks enable-addons \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER_NAME" \
    --addons monitoring \
    --workspace-resource-id "$WS_ID" \
    --output none \
    && success "Container Insights enabled on AKS — visible in Azure Portal → AKS → Insights" \
    || warn "Failed to enable Container Insights — check Azure role permissions"
}

# ── Step 6: Create LiteLLM dashboard in Grafana ───────────────────────────────
create_grafana_dashboard() {
  step "6 — Import LiteLLM dashboard into Grafana"
  info "Checking if Grafana is ready to accept dashboard imports..."

  # Wait for Grafana to be ready
  GRAFANA_READY=false
  for i in {1..12}; do
    GF_STATUS=$(kubectl get deployment kube-prometheus-grafana -n "$OBS_NS" \
      -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")
    if [[ "$GF_STATUS" == "True" ]]; then
      GRAFANA_READY=true
      break
    fi
    info "[$i/12] Waiting for Grafana to be ready... (10s)"
    sleep 10
  done

  if [[ "$GRAFANA_READY" != "true" ]]; then
    warn "Grafana not ready yet — skipping dashboard import"
    warn "Import manually after Grafana is up: kubectl port-forward svc/kube-prometheus-grafana 3001:80 -n observability"
    return
  fi

  # Port-forward Grafana in background, import dashboard, then kill
  kubectl port-forward svc/kube-prometheus-grafana 3001:80 -n "$OBS_NS" &
  PF_PID=$!
  sleep 5

  # Import LiteLLM community dashboard (ID 20842) from Grafana.com
  IMPORT_RESPONSE=$(curl -s -X POST "http://localhost:3001/api/dashboards/import" \
    -u "admin:$GRAFANA_ADMIN_PASSWORD" \
    -H "Content-Type: application/json" \
    -d '{
      "dashboard": {
        "id": null,
        "title": "navuAI — LLM Usage",
        "tags": ["navuai", "litellm"],
        "timezone": "browser",
        "panels": [
          {"id": 1, "title": "Total Requests", "type": "stat",
           "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
           "targets": [{"expr": "sum(litellm_requests_total)"}]},
          {"id": 2, "title": "Total Tokens Used", "type": "stat",
           "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
           "targets": [{"expr": "sum(litellm_total_tokens_total)"}]},
          {"id": 3, "title": "Requests / Min", "type": "timeseries",
           "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
           "targets": [{"expr": "rate(litellm_requests_total[1m])"}]}
        ],
        "schemaVersion": 38, "version": 1
      },
      "overwrite": true,
      "folderId": 0
    }' 2>/dev/null || echo "{}")

  kill $PF_PID 2>/dev/null || true

  if echo "$IMPORT_RESPONSE" | grep -q '"status":"success"'; then
    success "navuAI LLM Usage dashboard imported into Grafana"
  else
    warn "Dashboard import response: $IMPORT_RESPONSE"
    warn "Import manually via Grafana UI → Dashboards → Import → paste panel JSON"
  fi
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 7 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ Langfuse      : LLM trace observability — every prompt/response logged"
  echo "  ✓ Prometheus    : metrics scraping (LiteLLM + AKS nodes)"
  echo "  ✓ Grafana       : dashboards for usage, cost, latency"
  echo "  ✓ LiteLLM → LF : all requests now traced to Langfuse"
  echo "  ✓ Azure Monitor : Container Insights on AKS"
  echo ""
  echo -e "${YELLOW}Access Langfuse (LLM traces):${NC}"
  echo "  kubectl port-forward svc/langfuse-svc 3000:3000 -n observability"
  echo "  Open: http://localhost:3000"
  echo "  Login: create admin account on first visit"
  echo ""
  echo -e "${YELLOW}Access Grafana (metrics dashboards):${NC}"
  echo "  kubectl port-forward svc/kube-prometheus-grafana 3001:80 -n observability"
  echo "  Open: http://localhost:3001"
  echo "  Login: admin / $GRAFANA_ADMIN_PASSWORD"
  echo ""
  echo -e "${YELLOW}Access Prometheus (raw metrics):${NC}"
  echo "  kubectl port-forward svc/kube-prometheus-kube-prome-prometheus 9090:9090 -n observability"
  echo "  Open: http://localhost:9090"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  ./phase8-cicd.sh"
  echo ""
}

main() {
  banner
  create_namespace
  deploy_langfuse
  deploy_prometheus_grafana
  configure_litellm_langfuse
  configure_azure_monitor
  create_grafana_dashboard
  print_summary
}

main "$@"
