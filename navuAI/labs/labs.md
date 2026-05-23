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

## Architecture Reminder

```
You (WSL/Cloud Shell)
       │
       ▼
  Azure Portal / CLI
       │
       ▼
  ┌─────────────────────────────────────────────┐
  │  Azure AKS Cluster (navuai-aks)             │
  │                                             │
  │  ┌──────────────┐  ┌──────────────────────┐ │
  │  │  LiteLLM GW  │  │  Chat + Agents       │ │
  │  │  (Phase 2)   │  │  (Phase 3)           │ │
  │  └──────┬───────┘  └──────────────────────┘ │
  │         │                                   │
  │    routes to:                               │
  │    ├── Azure AI Foundry (private endpoint)  │
  │    ├── AWS Bedrock                          │
  │    ├── Google Vertex AI                     │
  │    ├── OpenAI                               │
  │    └── GPU VM (self-hosted)                 │
  └─────────────────────────────────────────────┘
```
