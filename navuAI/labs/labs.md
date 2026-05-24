# navuAI — Labs Guide
# Step-by-step. Zero assumptions. Start from nothing.

---

## What Is navuAI?

navuAI is an enterprise AI platform that:
- Routes AI requests to multiple LLM providers (Azure, AWS, Google, OpenAI) through ONE gateway
- Hosts your own private LLMs on a GPU server (no data leaves your network)
- Provides a chat interface for users
- Tracks cost per user, per model, per month
- Enforces security: SSO login, MFA, rate limits, budget caps

---

## How to Use This Lab

Every phase has its own script. Run them in order, one at a time.

```
Phase 1  →  phase1-azure-foundation.sh      Azure infra (AKS, VNet, GPU VM, Key Vault)
Phase 2  →  phase2-litellm-gateway.sh       LiteLLM API gateway (routes to all LLM providers)
Phase 3  →  phase3-ai-agents.sh             Chat UI + BillBot + Billy agents
Phase 4  →  phase4-mcp-server.sh            MCP server (Jira / Bass integration)
Phase 5  →  phase5-billing.sh               Billing tracker + budget caps
Phase 6  →  phase6-security.sh              SSO, MFA, private endpoints, rate limits
Phase 7  →  phase7-observability.sh         Langfuse + Prometheus + Grafana
Phase 8  →  phase8-cicd.sh                  CI/CD pipelines (GitHub Actions)
Phase 9  →  phase9-multicloud.sh            Multi-cloud Terraform modules
```

> **Run every script from WSL (Windows Subsystem for Linux) or Azure Cloud Shell.**
> Do NOT run from Windows CMD or regular PowerShell — bash commands will fail.

---

## Before You Start Anything — Prerequisites

You need these tools installed. The scripts will check and warn you if any are missing.

### 1. Open WSL on your Windows machine

Press `Windows key`, type `wsl`, press Enter. A Linux terminal opens.

### 2. Install Azure CLI

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az version
```
Expected output: something like `"azure-cli": "2.x.x"`

### 3. Install kubectl (Kubernetes CLI)

```bash
sudo az aks install-cli
kubectl version --client
```
Expected output: `Client Version: v1.xx.x`

### 4. Install Helm (Kubernetes package manager)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```
Expected output: `version.BuildInfo{Version:"v3.xx.x"...}`

### 5. Install Docker

```bash
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
docker --version
```
Expected output: `Docker version 24.x.x`

### 6. Install Terraform

```bash
sudo apt update && sudo apt install -y gnupg software-properties-common
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform
terraform version
```
Expected output: `Terraform v1.x.x`

### 7. Install jq (JSON processor — used in all scripts)

```bash
sudo apt install -y jq
jq --version
```
Expected output: `jq-1.x`

---

## Configuration — Set Your Values Once

Before running any script, open the file below and fill in your values.
Every script reads from this one file.

**File to edit:** `labs/navuai.env`

```bash
# ─────────────────────────────────────────────────────────────
# navuAI Global Configuration
# Fill in every value before running any phase script
# ─────────────────────────────────────────────────────────────

# Azure
AZURE_SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
AZURE_LOCATION="eastus"
RESOURCE_GROUP="navuai-rg"
AKS_CLUSTER_NAME="navuai-aks"
ACR_NAME="navuairegistry"          # must be globally unique, lowercase, no dashes
KEYVAULT_NAME="navuai-kv"          # must be globally unique

# Networking
VNET_NAME="navuai-vnet"
VNET_CIDR="10.0.0.0/16"
AKS_SUBNET_CIDR="10.0.1.0/24"
GPU_SUBNET_CIDR="10.0.2.0/24"

# DNS / Domain
DOMAIN="navuai.cloud"              # your domain, e.g. navuai.cloud
CHAT_SUBDOMAIN="chat"              # chat.navuai.cloud

# LLM Provider Keys (fill in only the ones you have)
OPENAI_API_KEY=""
AZURE_OPENAI_KEY=""
AZURE_OPENAI_ENDPOINT=""
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="us-east-1"
VERTEX_PROJECT=""
VERTEX_LOCATION="us-central1"

# Billing
MONTHLY_USER_BUDGET_USD="40"
ALERT_THRESHOLD_PERCENT="80"
```

To create this file, run:
```bash
cp labs/navuai.env.template labs/navuai.env
nano labs/navuai.env   # edit and fill in your values
```

---

## How to Run a Script

```bash
# 1. Go to the labs folder
cd /path/to/navuAI/labs

# 2. Make the script executable (first time only)
chmod +x phase1-azure-foundation.sh

# 3. Run it
./phase1-azure-foundation.sh
```

The script will:
- Show you what it's about to do
- Ask for confirmation before any destructive action
- Print GREEN for success, RED for errors, YELLOW for warnings
- Tell you exactly what to do next at the end

---

## Phase Summary

| Phase | Script | What It Builds | Time Estimate |
|-------|--------|----------------|---------------|
| 1 | phase1-azure-foundation.sh | Resource Group, VNet, AKS, GPU VM, ACR, Key Vault | ~25 min |
| 2 | phase2-litellm-gateway.sh | LiteLLM API Gateway + all LLM provider connections | ~10 min |
| 3 | phase3-ai-agents.sh | Chat UI, BillBot, Billy on AKS | ~15 min |
| 4 | phase4-mcp-server.sh | MCP server for Jira/Bass integration | ~10 min |
| 5 | phase5-billing.sh | Per-user billing, budget caps, cost reports | ~10 min |
| 6 | phase6-security.sh | SSO, MFA, private endpoints, rate limits, RBAC | ~20 min |
| 7 | phase7-observability.sh | Langfuse, Prometheus, Grafana dashboards | ~15 min |
| 8 | phase8-cicd.sh | GitHub Actions CI/CD pipelines | ~10 min |
| 9 | phase9-multicloud.sh | Terraform modules for AWS/GCP portability | ~10 min |

**Total estimated time:** ~2–2.5 hours for a full fresh deployment

---

---

## Phase 4 — MCP Server (Tool Integrations)

**Script:** `phase4-mcp-server.sh` | **Time:** ~10 min | **Prereqs:** Phases 1–3

**What it builds:**
- MCP (Model Context Protocol) server in the `mcp` K8s namespace
- Exposes Jira tools: `jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_search`
- Bass stub tool (wire up your own endpoint in the server code)
- Billy agent is patched to call the MCP server for tool execution

**Before running — optional Jira setup:**
```bash
# Edit navuai.env and fill in:
JIRA_URL="https://yourcompany.atlassian.net"
JIRA_EMAIL="you@yourcompany.com"
JIRA_API_TOKEN="your-atlassian-api-token"   # create at: id.atlassian.com/manage-profile/security/api-tokens
JIRA_PROJECT_KEY="PROJ"
```
If you leave these blank, the MCP server deploys with stub tools (returns mock data). You can fill them in later and re-run.

**Run it:**
```bash
chmod +x phase4-mcp-server.sh
./phase4-mcp-server.sh
```

**Test it manually:**
```bash
kubectl port-forward svc/mcp-server-svc 8080:80 -n mcp
curl http://localhost:8080/tools
curl -X POST http://localhost:8080/tools/jira_search \
     -H "Content-Type: application/json" \
     -d '{"jql": "project=PROJ AND status=Open"}'
```

---

## Phase 5 — Billing & Usage Reporting

**Script:** `phase5-billing.sh` | **Time:** ~10 min | **Prereqs:** Phases 1–2

**What it builds:**
- Model pricing table in LiteLLM (cost/token per model)
- $40/user/month hard budget cap enforced by LiteLLM virtual keys
- Billing dashboard service (FastAPI with usage reports + HTML dashboard)
- Azure Monitor budget alert (email at 80% threshold)

**No extra config needed** — values from navuai.env (`MONTHLY_USER_BUDGET_USD`, `ALERT_THRESHOLD_PERCENT`) are used automatically.

**Run it:**
```bash
chmod +x phase5-billing.sh
./phase5-billing.sh
```

**Access billing dashboard:**
```bash
kubectl port-forward svc/billing-dashboard-svc 8003:80 -n billing
# Open: http://localhost:8003/dashboard
```

**Create a user key with budget (manual):**
```bash
LITELLM_KEY=$(az keyvault secret show --vault-name navuai-kv --name litellm-master-key --query value -o tsv)
curl -X POST https://api.manmas.online/key/generate \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key_alias": "alice",
    "user_id": "alice@yourcompany.com",
    "max_budget": 40,
    "budget_duration": "1mo"
  }'
```

---

## Phase 6 — Security & Compliance

**Script:** `phase6-security.sh` | **Time:** ~20 min | **Prereqs:** Phases 1–3

**What it builds:**
- NGINX rate limiting: 60 RPM/IP on API, 5 RPM/IP on chat UI
- Source IP allowlist on ingress (if `ALLOWED_IP_RANGES` is set)
- Azure AD (Entra ID) SSO for Open WebUI (if `AZURE_AD_*` vars are set)
- Kubernetes RBAC roles: `navuai-admin`, `navuai-user`, `navuai-billing`
- LiteLLM rate limits: 60 RPM / 100K TPM per user key
- Key Vault private endpoint (no public internet access)
- NSG deny-all inbound rule (HTTPS already allowed by Phase 1)

**Before running — set up Azure AD app registration (for SSO):**
1. Go to Azure Portal → **Entra ID** → **App Registrations** → **New Registration**
2. Name: `navuAI-chat`
3. Redirect URI (Web): `https://chat.manmas.online/oauth/oidc/callback`
4. Copy the **Application (client) ID** → `AZURE_AD_CLIENT_ID` in navuai.env
5. Copy the **Directory (tenant) ID** → `AZURE_AD_TENANT_ID` in navuai.env
6. Go to **Certificates & Secrets** → **New client secret** → copy value → `AZURE_AD_CLIENT_SECRET` in navuai.env

**Before running — set IP allowlist (optional):**
```bash
# In navuai.env:
ALLOWED_IP_RANGES="203.0.113.0/24,10.0.0.0/8"  # your corporate/VPN CIDR ranges
```

**Run it:**
```bash
chmod +x phase6-security.sh
./phase6-security.sh
```

**Bind a user to admin role:**
```bash
kubectl create clusterrolebinding alice-admin \
  --clusterrole=navuai-admin \
  --user=alice@yourcompany.com
```

---

## Phase 7 — Observability & Monitoring

**Script:** `phase7-observability.sh` | **Time:** ~15 min | **Prereqs:** Phases 1–2

**What it builds:**
- **Langfuse** — open-source LLM trace observability (every prompt/response logged with tokens, cost, latency)
- **Prometheus** — metrics scraping (LiteLLM request metrics + AKS node/pod metrics)
- **Grafana** — dashboards for usage, cost, error rates, latency
- LiteLLM wired to send all traces to Langfuse via `success_callback`
- Azure Monitor Container Insights on AKS

**Before running:**
Check `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, and `GRAFANA_ADMIN_PASSWORD` in navuai.env.
The defaults (`changeme-*`) work for a non-public deployment. Change them before exposing publicly.

**Run it:**
```bash
chmod +x phase7-observability.sh
./phase7-observability.sh
```

**Access Langfuse (LLM traces):**
```bash
kubectl port-forward svc/langfuse-svc 3000:3000 -n observability
# Open: http://localhost:3000
# First visit: create admin account
# Navigate to Traces to see every LLM call
```

**Access Grafana (metrics dashboards):**
```bash
kubectl port-forward svc/kube-prometheus-grafana 3001:80 -n observability
# Open: http://localhost:3001
# Login: admin / <GRAFANA_ADMIN_PASSWORD from navuai.env>
```

**Access Prometheus (raw metrics):**
```bash
kubectl port-forward svc/kube-prometheus-kube-prome-prometheus 9090:9090 -n observability
# Open: http://localhost:9090
# Try query: litellm_requests_total
```

---

## Phase 8 — CI/CD Pipelines

**Script:** `phase8-cicd.sh` | **Time:** ~10 min | **Prereqs:** Phases 1–3, GitHub repo exists

**What it builds:**
- Azure Service Principal: `navuai-github-actions` (ACR push + AKS deploy permissions)
- GitHub Actions workflow files in `.github/workflows/`:
  - `deploy.yml` — build images → push to ACR → kubectl rollout on every push to main
  - `security-scan.yml` — Trivy vulnerability scan weekly + on every PR
  - `pr-checks.yml` — ShellCheck on phase scripts + env template validation
- ACR admin enabled for CI/CD image push

**Before running:**
```bash
# Fill in navuai.env:
GITHUB_ORG="your-github-org-or-username"
GITHUB_REPO="navuAI"
```

**Run it:**
```bash
chmod +x phase8-cicd.sh
./phase8-cicd.sh
```

**After running — ACTION REQUIRED:**
The script prints all GitHub secrets. You must manually add them to:
`https://github.com/YOUR_ORG/navuAI/settings/secrets/actions`

| Secret name | Value |
|-------------|-------|
| `AZURE_CREDENTIALS` | JSON block printed by script |
| `AZURE_SUBSCRIPTION_ID` | From navuai.env |
| `AZURE_RESOURCE_GROUP` | `navuai-rg` |
| `ACR_NAME` | `navuairegistry.azurecr.io` |
| `AKS_CLUSTER_NAME` | `navuai-aks` |
| `DOMAIN` | `manmas.online` |
| `LITELLM_MASTER_KEY` | From Key Vault |

**Trigger a deploy:**
```bash
git push origin main          # auto-triggers deploy
# OR: GitHub → Actions → navuAI CI/CD → Run workflow
```

---

## Phase 9 — Multi-Cloud Terraform Modules

**Script:** `phase9-multicloud.sh` | **Time:** ~10 min | **Prereqs:** terraform CLI installed

**What it builds (files written, nothing provisioned):**
- `infrastructure/terraform/main.tf` — root module wiring all sub-modules
- `infrastructure/terraform/variables.tf` — all config pre-filled from navuai.env
- `infrastructure/terraform/outputs.tf` — cluster name, ACR, Key Vault URI, etc.
- `modules/networking` — VNet, subnets, NSG
- `modules/aks` — AKS cluster, ACR, node pools
- `modules/keyvault` — Key Vault with private endpoint option
- `modules/gpu-vm` — GPU VM with Ollama bootstrap
- `modules/vpn` — VPN Gateway for B2B connectivity
- `docs/multi-cloud-swap-guide.md` — step-by-step Azure → AWS / GCP swap guide

**Run it:**
```bash
chmod +x phase9-multicloud.sh
./phase9-multicloud.sh
```

**To provision infrastructure from scratch using Terraform (instead of Phase 1 scripts):**
```bash
cd infrastructure/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**To swap to AWS or GCP:** read `docs/multi-cloud-swap-guide.md`

---

## Troubleshooting

### "az: command not found"
Azure CLI is not installed. Go back to Prerequisites → Step 2.

### "kubectl: command not found"
Run: `sudo az aks install-cli`

### "Error: insufficient quota"
Your Azure subscription doesn't have enough GPU quota.
Fix: Go to Azure Portal → Subscriptions → Your Sub → Usage + quotas → request increase for `Standard NCas T4 v3` or `Standard NCA100v4`.

### AKS creation times out
AKS takes 5–15 minutes. If the script times out, run:
```bash
az aks show --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME --query provisioningState
```
Wait until it says `Succeeded`.

### Pod stuck in `Pending` state
```bash
kubectl describe pod <pod-name> -n <namespace>
```
Look for "Insufficient CPU/memory" → your node pool is too small, scale up:
```bash
az aks nodepool scale --resource-group $RESOURCE_GROUP --cluster-name $AKS_CLUSTER_NAME \
  --name app --node-count 3
```

### LiteLLM can't reach a provider
```bash
kubectl logs deployment/litellm -n litellm
```
Usually means the API key is wrong or not set in Key Vault. Re-run phase 2.

---

### MCP server pod in CrashLoopBackOff
```bash
kubectl logs deployment/mcp-server -n mcp
```
Usually a pip install timeout. Re-run `./phase4-mcp-server.sh` — it is idempotent.

### Billing dashboard shows $0 spend
LiteLLM only tracks spend after Phase 5 pricing config is applied. Make a test request:
```bash
LITELLM_KEY=$(az keyvault secret show --vault-name navuai-kv --name litellm-master-key --query value -o tsv)
curl -X POST https://api.manmas.online/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"azure-gpt41-nano","messages":[{"role":"user","content":"hello"}]}'
```
Then refresh the billing dashboard.

### SSO login loop (Open WebUI)
If users are redirected in a loop after Azure AD login, check:
```bash
kubectl logs deployment/openwebui -n chat | grep -i oauth
```
Common fix: ensure the redirect URI in Azure App Registration exactly matches `https://chat.manmas.online/oauth/oidc/callback`.

### Langfuse not receiving traces
```bash
kubectl logs deployment/litellm -n litellm | grep -i langfuse
```
Check `LANGFUSE_HOST` is set to `http://langfuse-svc.observability.svc.cluster.local:3000` (internal cluster URL).

### Grafana "Data source not found"
The kube-prometheus-stack auto-configures Prometheus as a data source. If missing:
- Grafana → Configuration → Data Sources → Add Prometheus
- URL: `http://kube-prometheus-kube-prome-prometheus.observability.svc.cluster.local:9090`

### GitHub Actions workflow fails: "Unauthorized to ACR"
```bash
# Verify service principal has AcrPush role:
az role assignment list --assignee <SP_APP_ID> --scope /subscriptions/.../acr/navuairegistry
```
Re-run `./phase8-cicd.sh` to re-apply role assignments.

### Terraform plan fails: "Provider not found"
```bash
cd infrastructure/terraform
terraform init -upgrade
terraform providers
```
Ensure `terraform >= 1.5` is installed: `terraform version`.

---

## Architecture Reminder

```
You (WSL/Cloud Shell)
       │
       ▼
  Azure Portal / CLI
       │
       ▼
  ┌──────────────────────────────────────────────────────────┐
  │  Azure AKS Cluster (navuai-aks)                          │
  │                                                          │
  │  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐ │
  │  │  LiteLLM GW  │  │  Chat + Agents│  │  MCP Server   │ │
  │  │  (Phase 2)   │  │  (Phase 3)    │  │  (Phase 4)    │ │
  │  └──────┬───────┘  └───────────────┘  └───────────────┘ │
  │         │                                                │
  │    routes to:          ┌──────────────┐                 │
  │    ├── Azure AI Foundry│  Billing     │  (Phase 5)      │
  │    ├── AWS Bedrock     │  Dashboard   │                 │
  │    ├── Google Vertex AI└──────────────┘                 │
  │    ├── OpenAI                                           │
  │    └── GPU VM          ┌──────────────────────────────┐ │
  │                        │  Observability (Phase 7)     │ │
  │                        │  Langfuse │ Prometheus        │ │
  │                        │  Grafana  │ Azure Monitor     │ │
  │                        └──────────────────────────────┘ │
  └──────────────────────────────────────────────────────────┘

  GitHub Actions (Phase 8) → builds images → pushes to ACR → deploys to AKS
  Terraform modules (Phase 9) → reproducible infra on Azure / AWS / GCP
```
