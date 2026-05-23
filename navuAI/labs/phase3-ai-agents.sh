#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 3: AI Chatbot & Agents
#
#  What this script builds:
#    1. Chat Frontend (Open WebUI) — user-facing chat interface
#    2. BillBot Agent — billing questions + usage reports
#    3. Billy Agent — general AI assistant with tool use
#
#  Prerequisites: Phase 1 + Phase 2 must be complete
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
  echo "  navuAI — Phase 3: AI Chatbot & Agents"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

AGENTS_NS="agents"
CHAT_NS="chat"

# ── Wait for TLS certificate to be Ready ─────────────────────────────────────
wait_for_certificate() {
  local cert_name=$1
  local namespace=$2
  local max_wait=30   # 30 x 10s = 5 minutes

  step "— Wait for TLS Certificate: $cert_name"
  info "cert-manager starts as READY: False, runs ACME HTTP-01 challenge, then flips to READY: True"

  for i in $(seq 1 $max_wait); do
    READY=$(kubectl get certificate "$cert_name" -n "$namespace" \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "NotFound")

    if [[ "$READY" == "True" ]]; then
      success "Certificate '$cert_name' is READY: True — TLS is active"
      return 0
    fi

    REASON=$(kubectl get certificate "$cert_name" -n "$namespace" \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null || echo "unknown")
    info "[$i/$max_wait] READY: $READY ($REASON) — waiting 10s..."
    sleep 10
  done

  warn "Certificate '$cert_name' did not become ready in time."
  warn "Debug: kubectl describe certificate $cert_name -n $namespace"
  warn "Common causes: DNS not pointing to ingress IP, or HTTP-01 challenge blocked"
}

# ── Step 1: Create namespaces ─────────────────────────────────────────────────
create_namespaces() {
  step "1 — Create Kubernetes Namespaces"
  kubectl create namespace "$CHAT_NS"   --dry-run=client -o yaml | kubectl apply -f -
  kubectl create namespace "$AGENTS_NS" --dry-run=client -o yaml | kubectl apply -f -
  success "Namespaces 'chat' and 'agents' ready"
}

# ── Step 2: Get LiteLLM master key ───────────────────────────────────────────
get_litellm_key() {
  step "2 — Fetching LiteLLM credentials from Key Vault"
  LITELLM_KEY=$(az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" \
    --name "litellm-master-key" \
    --query value -o tsv)
  LITELLM_URL="https://api.${DOMAIN}/v1"
  info "LiteLLM URL: $LITELLM_URL"
  success "Credentials fetched"
}

# ── Step 3: Deploy Open WebUI (Chat Frontend) ─────────────────────────────────
deploy_chat_frontend() {
  step "3 — Deploy Chat Frontend (Open WebUI)"
  info "Open WebUI is a ChatGPT-style interface that connects to your LiteLLM gateway"
  info "URL after deployment: https://${CHAT_SUBDOMAIN}.${DOMAIN}"

  kubectl create secret generic chat-secrets \
    --namespace "$CHAT_NS" \
    --from-literal=OPENAI_API_KEY="$LITELLM_KEY" \
    --from-literal=OPENAI_API_BASE_URL="$LITELLM_URL" \
    --dry-run=client -o yaml | kubectl apply -f -

  if kubectl get pvc openwebui-pvc -n "$CHAT_NS" &>/dev/null; then
    warn "PVC 'openwebui-pvc' already exists — skipping to preserve data"
  else
    kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: openwebui-pvc
  namespace: ${CHAT_NS}
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
EOF
  fi

  OWU_STATUS=$(kubectl get deployment openwebui -n "$CHAT_NS" \
    -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")
  if [[ "$OWU_STATUS" == "True" ]]; then
    success "Open WebUI already running and healthy — skipping redeploy"
  else
  cat <<EOF | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openwebui
  namespace: ${CHAT_NS}
  labels:
    app: openwebui
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: openwebui
  template:
    metadata:
      labels:
        app: openwebui
    spec:
      containers:
      - name: openwebui
        image: ghcr.io/open-webui/open-webui:main
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: chat-secrets
              key: OPENAI_API_KEY
        - name: OPENAI_API_BASE_URL
          valueFrom:
            secretKeyRef:
              name: chat-secrets
              key: OPENAI_API_BASE_URL
        - name: WEBUI_NAME
          value: "navuAI"
        - name: WEBUI_URL
          value: "https://${CHAT_SUBDOMAIN}.${DOMAIN}"
        - name: ENABLE_SIGNUP
          value: "true"
        - name: DEFAULT_USER_ROLE
          value: "user"
        volumeMounts:
        - name: data
          mountPath: /app/backend/data
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: openwebui-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: openwebui-svc
  namespace: ${CHAT_NS}
spec:
  selector:
    app: openwebui
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: openwebui-ingress
  namespace: ${CHAT_NS}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  tls:
  - hosts:
    - ${CHAT_SUBDOMAIN}.${DOMAIN}
    secretName: openwebui-tls
  rules:
  - host: ${CHAT_SUBDOMAIN}.${DOMAIN}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: openwebui-svc
            port:
              number: 80
EOF
  fi  # end: skip if already healthy

  info "Waiting for Open WebUI to start..."
  kubectl rollout status deployment/openwebui -n "$CHAT_NS" --timeout=180s
  success "Chat UI deployed at: https://${CHAT_SUBDOMAIN}.${DOMAIN}"

  # Wait for TLS certificate before curl validation
  wait_for_certificate "openwebui-tls" "$CHAT_NS"

  info "Validating HTTPS endpoint: https://${CHAT_SUBDOMAIN}.${DOMAIN}"
  for i in {1..6}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${CHAT_SUBDOMAIN}.${DOMAIN}" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
      success "HTTPS validation passed — ${CHAT_SUBDOMAIN}.${DOMAIN} is live (HTTP $HTTP_CODE)"
      break
    fi
    warn "[$i/6] Got HTTP $HTTP_CODE — retrying in 10s..."
    sleep 10
  done

  if [[ ! "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
    warn "HTTPS validation did not pass. Manual check:"
    warn "  curl -v https://${CHAT_SUBDOMAIN}.${DOMAIN}"
    warn "  kubectl describe certificate openwebui-tls -n $CHAT_NS"
  fi
}

# ── Step 4: Deploy BillBot Agent ──────────────────────────────────────────────
deploy_billbot() {
  step "4 — Deploy BillBot Agent (billing questions + usage reports)"
  info "BillBot answers billing questions and shows per-user/per-LLM cost data"

  # BillBot is a FastAPI app that queries LiteLLM's PostgreSQL database
  PG_PASS=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "postgres-password" --query value -o tsv)

  kubectl create secret generic billbot-secrets \
    --namespace "$AGENTS_NS" \
    --from-literal=LITELLM_API_KEY="$LITELLM_KEY" \
    --from-literal=LITELLM_API_URL="https://api.${DOMAIN}" \
    --from-literal=DATABASE_URL="postgresql://litellm:${PG_PASS}@postgres-svc.litellm.svc.cluster.local:5432/litellm" \
    --dry-run=client -o yaml | kubectl apply -f -

  cat <<EOF | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billbot
  namespace: ${AGENTS_NS}
  labels:
    app: billbot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: billbot
  template:
    metadata:
      labels:
        app: billbot
    spec:
      containers:
      - name: billbot
        image: python:3.12-slim
        command: ["/bin/sh", "-c"]
        args:
        - |
          pip install fastapi uvicorn httpx asyncpg psycopg2-binary openai --quiet
          mkdir -p /app
          cat > /app/main.py << 'PYEOF'
          import os, httpx
          from fastapi import FastAPI, HTTPException
          from openai import AsyncOpenAI

          app = FastAPI(title="BillBot", description="navuAI Billing Agent")
          client = AsyncOpenAI(
              api_key=os.environ["LITELLM_API_KEY"],
              base_url=os.environ["LITELLM_API_URL"] + "/v1"
          )

          SYSTEM_PROMPT = """You are BillBot, navuAI's billing assistant.
          You help users understand their LLM usage costs, view reports,
          and manage their \$40/month budget. Be concise and helpful."""

          @app.get("/health")
          async def health():
              return {"status": "ok", "agent": "BillBot"}

          @app.post("/chat")
          async def chat(message: str, user_id: str = "anonymous"):
              response = await client.chat.completions.create(
                  model="azure-gpt41-nano",
                  messages=[
                      {"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": message}
                  ],
                  user=user_id
              )
              return {"reply": response.choices[0].message.content}

          @app.get("/usage/{user_id}")
          async def get_usage(user_id: str):
              async with httpx.AsyncClient() as c:
                  r = await c.get(
                      os.environ["LITELLM_API_URL"] + f"/user/info?user_id={user_id}",
                      headers={"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
                  )
              return r.json()
          PYEOF
          cd /app && uvicorn main:app --host 0.0.0.0 --port 8001
        workingDir: /
        ports:
        - containerPort: 8001
        envFrom:
        - secretRef:
            name: billbot-secrets
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: billbot-svc
  namespace: ${AGENTS_NS}
spec:
  selector:
    app: billbot
  ports:
  - port: 80
    targetPort: 8001
EOF

  info "Waiting for BillBot to start..."
  kubectl rollout status deployment/billbot -n "$AGENTS_NS" --timeout=120s
  success "BillBot deployed (internal service: billbot-svc.agents.svc.cluster.local)"
}

# ── Step 5: Deploy Billy Agent ────────────────────────────────────────────────
deploy_billy() {
  step "5 — Deploy Billy Agent (general AI assistant with tool use)"
  info "Billy is a general-purpose AI assistant that can search, analyze files, and use tools"

  kubectl create secret generic billy-secrets \
    --namespace "$AGENTS_NS" \
    --from-literal=LITELLM_API_KEY="$LITELLM_KEY" \
    --from-literal=LITELLM_API_URL="https://api.${DOMAIN}" \
    --dry-run=client -o yaml | kubectl apply -f -

  cat <<EOF | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billy
  namespace: ${AGENTS_NS}
  labels:
    app: billy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: billy
  template:
    metadata:
      labels:
        app: billy
    spec:
      containers:
      - name: billy
        image: python:3.12-slim
        command: ["/bin/sh", "-c"]
        args:
        - |
          pip install fastapi uvicorn openai httpx --quiet
          mkdir -p /app
          cat > /app/main.py << 'PYEOF'
          import os, json
          from fastapi import FastAPI
          from openai import AsyncOpenAI

          app = FastAPI(title="Billy", description="navuAI General Assistant")
          client = AsyncOpenAI(
              api_key=os.environ["LITELLM_API_KEY"],
              base_url=os.environ["LITELLM_API_URL"] + "/v1"
          )

          TOOLS = [
              {
                  "type": "function",
                  "function": {
                      "name": "get_current_date",
                      "description": "Get today's date and time",
                      "parameters": {"type": "object", "properties": {}}
                  }
              }
          ]

          SYSTEM_PROMPT = """You are Billy, navuAI's general AI assistant.
          You help with questions, analysis, and tasks. You have access to tools
          and can be extended with Jira/Bass integration via MCP."""

          @app.get("/health")
          async def health():
              return {"status": "ok", "agent": "Billy"}

          @app.post("/chat")
          async def chat(message: str, model: str = "azure-gpt41-nano", user_id: str = "anonymous"):
              response = await client.chat.completions.create(
                  model=model,
                  messages=[
                      {"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": message}
                  ],
                  tools=TOOLS,
                  user=user_id
              )
              return {"reply": response.choices[0].message.content, "model": model}
          PYEOF
          cd /app && uvicorn main:app --host 0.0.0.0 --port 8002
        workingDir: /
        ports:
        - containerPort: 8002
        envFrom:
        - secretRef:
            name: billy-secrets
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: billy-svc
  namespace: ${AGENTS_NS}
spec:
  selector:
    app: billy
  ports:
  - port: 80
    targetPort: 8002
EOF

  info "Waiting for Billy to start..."
  kubectl rollout status deployment/billy -n "$AGENTS_NS" --timeout=120s
  success "Billy deployed (internal service: billy-svc.agents.svc.cluster.local)"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 3 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ Chat UI   : https://${CHAT_SUBDOMAIN}.${DOMAIN}"
  echo "  ✓ BillBot   : billbot-svc.agents (internal)"
  echo "  ✓ Billy     : billy-svc.agents (internal)"
  echo ""
  echo -e "${YELLOW}Test the chat UI:${NC}"
  echo "  Open https://${CHAT_SUBDOMAIN}.${DOMAIN} in your browser"
  echo "  Login → select a model → start chatting"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  ./phase4-mcp-server.sh"
  echo ""
}

main() {
  banner
  create_namespaces
  get_litellm_key
  deploy_chat_frontend
  deploy_billbot
  deploy_billy
  print_summary
}

main "$@"
