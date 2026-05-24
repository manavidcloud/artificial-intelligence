#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 4: MCP Server (Tool Integrations)
#
#  What this script builds:
#    1. MCP Server — Model Context Protocol server in the 'mcp' namespace
#       Exposes tools to Billy agent: Jira (get/create/update/search), Bass (stub)
#    2. Updates Billy Agent — injects MCP_SERVER_URL so Billy can call tools
#
#  Prerequisites: Phase 1 + Phase 2 + Phase 3 must be complete
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
  echo "  navuAI — Phase 4: MCP Server"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

MCP_NS="mcp"
AGENTS_NS="agents"

# ── Step 1: Create mcp namespace ──────────────────────────────────────────────
create_namespace() {
  step "1 — Create Kubernetes Namespace 'mcp'"
  kubectl create namespace "$MCP_NS" --dry-run=client -o yaml | kubectl apply -f -
  success "Namespace 'mcp' ready"
}

# ── Step 2: Store Jira credentials in Key Vault and create K8s secret ─────────
create_mcp_secrets() {
  step "2 — Store MCP / Jira credentials"
  info "Pushing Jira credentials to Azure Key Vault..."

  if [[ -n "${JIRA_API_TOKEN:-}" ]]; then
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "jira-api-token"  --value "$JIRA_API_TOKEN"  --output none
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "jira-email"      --value "$JIRA_EMAIL"      --output none
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "jira-url"        --value "$JIRA_URL"        --output none
    success "Jira credentials stored in Key Vault"
  else
    warn "JIRA_API_TOKEN not set in navuai.env — deploying MCP server with stub Jira tools"
    warn "Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in navuai.env and re-run to enable live Jira"
  fi

  kubectl create secret generic mcp-secrets \
    --namespace "$MCP_NS" \
    --from-literal=JIRA_URL="${JIRA_URL:-}" \
    --from-literal=JIRA_EMAIL="${JIRA_EMAIL:-}" \
    --from-literal=JIRA_API_TOKEN="${JIRA_API_TOKEN:-}" \
    --from-literal=JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY:-PROJ}" \
    --dry-run=client -o yaml | kubectl apply -f -

  success "K8s secret 'mcp-secrets' created in namespace '$MCP_NS'"
}

# ── Step 3: Deploy MCP Server ─────────────────────────────────────────────────
deploy_mcp_server() {
  step "3 — Deploy MCP Server (JSON-RPC over HTTP)"
  info "MCP server exposes Jira tools via the Model Context Protocol"
  info "Billy agent will call this server to execute actions on your behalf"

  MCP_STATUS=$(kubectl get deployment mcp-server -n "$MCP_NS" \
    -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "")
  if [[ "$MCP_STATUS" == "True" ]]; then
    success "MCP server already running and healthy — skipping redeploy"
    return
  fi

  cat <<'EOF' | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: mcp
  labels:
    app: mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: python:3.12-slim
        command: ["/bin/sh", "-c"]
        args:
        - |
          pip install fastapi uvicorn httpx --quiet
          mkdir -p /app
          cat > /app/main.py << 'PYEOF'
          import os, json
          import httpx
          from fastapi import FastAPI, Request

          app = FastAPI(title="navuAI MCP Server", description="Model Context Protocol server — Jira + Bass tools")

          JIRA_URL        = os.environ.get("JIRA_URL", "")
          JIRA_EMAIL      = os.environ.get("JIRA_EMAIL", "")
          JIRA_API_TOKEN  = os.environ.get("JIRA_API_TOKEN", "")
          JIRA_PROJECT    = os.environ.get("JIRA_PROJECT_KEY", "PROJ")
          JIRA_CONFIGURED = bool(JIRA_URL and JIRA_EMAIL and JIRA_API_TOKEN)

          TOOLS = [
              {
                  "name": "jira_get_issue",
                  "description": "Get a Jira issue by key (e.g. PROJ-123). Returns summary, status, assignee, description.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {
                          "issue_key": {"type": "string", "description": "Jira issue key e.g. PROJ-123"}
                      },
                      "required": ["issue_key"]
                  }
              },
              {
                  "name": "jira_create_issue",
                  "description": "Create a new Jira issue in the project.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {
                          "summary":     {"type": "string", "description": "Issue title"},
                          "description": {"type": "string", "description": "Issue details"},
                          "issue_type":  {"type": "string", "description": "Task | Bug | Story", "default": "Task"},
                          "project_key": {"type": "string", "description": "Jira project key"}
                      },
                      "required": ["summary"]
                  }
              },
              {
                  "name": "jira_update_issue",
                  "description": "Update status or add a comment on a Jira issue.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {
                          "issue_key": {"type": "string"},
                          "status":    {"type": "string", "description": "New status e.g. In Progress, Done"},
                          "comment":   {"type": "string", "description": "Comment text to add"}
                      },
                      "required": ["issue_key"]
                  }
              },
              {
                  "name": "jira_search",
                  "description": "Search Jira issues using JQL. Returns up to 10 matching issues.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {
                          "jql": {"type": "string", "description": "JQL query e.g. project=PROJ AND status=Open"}
                      },
                      "required": ["jql"]
                  }
              },
              {
                  "name": "bass_get_record",
                  "description": "Retrieve a record from Bass (internal system). Stub — wire up your Bass API endpoint.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {
                          "record_id": {"type": "string", "description": "Bass record identifier"}
                      },
                      "required": ["record_id"]
                  }
              }
          ]

          async def call_jira(method: str, path: str, payload: dict = None):
              if not JIRA_CONFIGURED:
                  return {"error": "Jira not configured. Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in navuai.env."}
              async with httpx.AsyncClient(timeout=15) as c:
                  r = await c.request(
                      method,
                      f"{JIRA_URL}/rest/api/3{path}",
                      auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                      headers={"Accept": "application/json", "Content-Type": "application/json"},
                      json=payload
                  )
                  try:
                      return r.json()
                  except Exception:
                      return {"status_code": r.status_code, "text": r.text}

          async def execute_tool(name: str, args: dict) -> dict:
              if name == "jira_get_issue":
                  raw = await call_jira("GET", f"/issue/{args['issue_key']}")
                  if "fields" in raw:
                      f = raw["fields"]
                      return {
                          "key":         raw.get("key"),
                          "summary":     f.get("summary"),
                          "status":      f.get("status", {}).get("name"),
                          "assignee":    (f.get("assignee") or {}).get("displayName"),
                          "description": str(f.get("description") or ""),
                          "priority":    (f.get("priority") or {}).get("name")
                      }
                  return raw

              elif name == "jira_create_issue":
                  proj = args.get("project_key", JIRA_PROJECT)
                  desc_text = args.get("description", "")
                  return await call_jira("POST", "/issue", payload={
                      "fields": {
                          "project":     {"key": proj},
                          "summary":     args["summary"],
                          "issuetype":   {"name": args.get("issue_type", "Task")},
                          "description": {
                              "type": "doc", "version": 1,
                              "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc_text}]}]
                          }
                      }
                  })

              elif name == "jira_update_issue":
                  result = {}
                  if args.get("status"):
                      transitions = await call_jira("GET", f"/issue/{args['issue_key']}/transitions")
                      target = next(
                          (t for t in transitions.get("transitions", [])
                           if args["status"].lower() in t["name"].lower()), None
                      )
                      if target:
                          await call_jira("POST", f"/issue/{args['issue_key']}/transitions",
                                          payload={"transition": {"id": target["id"]}})
                          result["status_update"] = f"Moved to {target['name']}"
                      else:
                          result["status_update"] = f"Transition '{args['status']}' not found"
                  if args.get("comment"):
                      await call_jira("POST", f"/issue/{args['issue_key']}/comment", payload={
                          "body": {"type": "doc", "version": 1,
                                   "content": [{"type": "paragraph",
                                                "content": [{"type": "text", "text": args["comment"]}]}]}
                      })
                      result["comment"] = "Comment added"
                  return result

              elif name == "jira_search":
                  raw = await call_jira("GET", f"/search?jql={args['jql']}&maxResults=10")
                  issues = raw.get("issues", [])
                  return {"total": raw.get("total", 0), "issues": [
                      {"key": i["key"], "summary": i["fields"].get("summary"),
                       "status": i["fields"].get("status", {}).get("name")}
                      for i in issues
                  ]}

              elif name == "bass_get_record":
                  return {"record_id": args["record_id"], "status": "stub",
                          "message": "Wire up your Bass API endpoint in /app/main.py execute_tool()"}

              return {"error": f"Unknown tool: {name}"}

          # ── MCP Protocol Endpoints ────────────────────────────────────────────
          @app.get("/health")
          async def health():
              return {"status": "ok", "service": "navuAI MCP Server",
                      "jira_configured": JIRA_CONFIGURED, "tools": len(TOOLS)}

          @app.post("/mcp")
          async def mcp_endpoint(request: Request):
              body = await request.json()
              method  = body.get("method", "")
              params  = body.get("params", {})
              req_id  = body.get("id", 1)

              if method == "initialize":
                  return {"jsonrpc": "2.0", "id": req_id, "result": {
                      "protocolVersion": "2024-11-05",
                      "capabilities":    {"tools": {}},
                      "serverInfo":      {"name": "navuai-mcp", "version": "1.0.0"}
                  }}

              elif method == "tools/list":
                  return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

              elif method == "tools/call":
                  tool_name = params.get("name", "")
                  arguments = params.get("arguments", {})
                  result    = await execute_tool(tool_name, arguments)
                  return {"jsonrpc": "2.0", "id": req_id, "result": {
                      "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                  }}

              return {"jsonrpc": "2.0", "id": req_id,
                      "error": {"code": -32601, "message": f"Method not found: {method}"}}

          # ── Convenience REST endpoints (for testing outside MCP) ──────────────
          @app.get("/tools")
          async def list_tools():
              return {"tools": [t["name"] for t in TOOLS]}

          @app.post("/tools/{tool_name}")
          async def call_tool(tool_name: str, request: Request):
              args = await request.json()
              return await execute_tool(tool_name, args)
          PYEOF
          cd /app && uvicorn main:app --host 0.0.0.0 --port 8080
        workingDir: /
        ports:
        - containerPort: 8080
        envFrom:
        - secretRef:
            name: mcp-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 20
          periodSeconds: 10
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
  name: mcp-server-svc
  namespace: mcp
spec:
  selector:
    app: mcp-server
  ports:
  - port: 80
    targetPort: 8080
EOF

  info "Waiting for MCP server to start..."
  kubectl rollout status deployment/mcp-server -n "$MCP_NS" --timeout=180s
  success "MCP server deployed (internal: mcp-server-svc.mcp.svc.cluster.local)"
}

# ── Step 4: Patch Billy agent to use MCP server ───────────────────────────────
patch_billy_with_mcp() {
  step "4 — Wire MCP server into Billy agent"
  info "Updating Billy to call mcp-server-svc.mcp.svc.cluster.local for tool execution"

  MCP_INTERNAL_URL="http://mcp-server-svc.mcp.svc.cluster.local/mcp"

  # Patch Billy's secret to include MCP_SERVER_URL
  LITELLM_KEY=$(az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" --name "litellm-master-key" --query value -o tsv)

  kubectl create secret generic billy-secrets \
    --namespace "$AGENTS_NS" \
    --from-literal=LITELLM_API_KEY="$LITELLM_KEY" \
    --from-literal=LITELLM_API_URL="https://api.${DOMAIN}" \
    --from-literal=MCP_SERVER_URL="$MCP_INTERNAL_URL" \
    --dry-run=client -o yaml | kubectl apply -f -

  # Restart Billy so it picks up the new env var
  kubectl rollout restart deployment/billy -n "$AGENTS_NS"
  kubectl rollout status deployment/billy -n "$AGENTS_NS" --timeout=120s
  success "Billy agent patched and restarted with MCP_SERVER_URL"
}

# ── Step 5: Validate MCP server health ───────────────────────────────────────
validate_mcp() {
  step "5 — Validate MCP server"
  info "Testing /health and /tools endpoints from within the cluster..."

  kubectl run mcp-test --image=curlimages/curl --restart=Never --rm -i \
    --namespace "$MCP_NS" \
    -- curl -sf http://mcp-server-svc.mcp.svc.cluster.local/health 2>/dev/null \
    && success "MCP /health endpoint responding" \
    || warn "Could not reach MCP server — check: kubectl logs deployment/mcp-server -n $MCP_NS"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 4 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was built:${NC}"
  echo "  ✓ MCP Server  : mcp-server-svc.mcp.svc.cluster.local (internal)"
  echo "  ✓ Tools       : jira_get_issue, jira_create_issue, jira_update_issue, jira_search, bass_get_record"
  echo "  ✓ Billy agent : patched with MCP_SERVER_URL"
  echo ""
  echo -e "${YELLOW}Test MCP tools manually:${NC}"
  echo "  kubectl port-forward svc/mcp-server-svc 8080:80 -n mcp"
  echo "  curl http://localhost:8080/tools"
  echo "  curl -X POST http://localhost:8080/tools/jira_search -d '{\"jql\":\"project=PROJ\"}'"
  echo ""
  echo -e "${YELLOW}Enable Jira (if not done):${NC}"
  echo "  Edit navuai.env → set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN"
  echo "  Re-run: ./phase4-mcp-server.sh"
  echo ""
  echo -e "${YELLOW}Next step:${NC}"
  echo "  ./phase5-billing.sh"
  echo ""
}

main() {
  banner
  create_namespace
  create_mcp_secrets
  deploy_mcp_server
  patch_billy_with_mcp
  validate_mcp
  print_summary
}

main "$@"
