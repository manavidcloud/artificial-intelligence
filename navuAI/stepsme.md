# navuAI Build Plan

Primary platform: **Azure (AKS)**  
Multi-cloud LLM support: AWS Bedrock, Google Vertex AI, OpenAI Platform, Azure AI Foundry  
Architecture reference: navuAI architecture diagram (LiteLLM gateway + AI Agents + GPU LLMs)

---

## Architecture Overview

```
On-Premise / Customer
  └── B2B VPN
        └── AKS Cluster (Azure)
              ├── LiteLLM API Gateway  ──►  Azure AI Foundry (private endpoint)
              │                        ──►  AWS Bedrock
              │                        ──►  Google Vertex AI
              │                        ──►  OpenAI Platform
              ├── AI Chatbot / Agents (chat UI, BillBot, Billy)
              ├── GPU VM (self-hosted LLMs: Kimi, OSS, Embedded, Reranker)
              ├── MCP Server (Jira / Bass integration)
              └── Billing Service (per user / per LLM / per token)
```

---

## Phase 1 — Azure Infrastructure Foundation

**Goal:** AKS cluster, networking, VPN, and core Azure services provisioned via Terraform.

### Step 1 — Azure Prerequisites
- [ ] Create Azure subscription and Resource Group: `navuai-rg`
- [ ] Enable required providers: `Microsoft.ContainerService`, `Microsoft.Compute`, `Microsoft.Network`, `Microsoft.KeyVault`
- [ ] Create Service Principal with contributor role (or use Managed Identity)
- [ ] Store credentials in Azure Key Vault: `navuai-kv`
- [ ] Set up Terraform backend: Azure Storage Account + container for remote state

### Step 2 — Virtual Network & Security
- [ ] Create VNet: `navuai-vnet` (address space: `10.0.0.0/16`)
  - Subnet: `aks-subnet` (10.0.1.0/24)
  - Subnet: `gpu-subnet` (10.0.2.0/24)
  - Subnet: `private-endpoint-subnet` (10.0.3.0/24)
- [ ] Create NSGs with rules:
  - Allow HTTPS (443) inbound from VPN/corporate IPs only
  - Deny all other inbound by default
  - Allow internal AKS pod-to-pod traffic
- [ ] Create VPN Gateway for B2B VPN (on-premise + customer connectivity)
  - SKU: `VpnGw1` (can upgrade to `VpnGw2` for higher throughput)
  - Configure Local Network Gateway for on-premise IP ranges
- [ ] Set up Azure Firewall or Application Gateway for NC FW equivalent (public API endpoint control)

### Step 3 — AKS Cluster
- [ ] Provision AKS cluster: `navuai-aks`
  - Node pool: `system` (Standard_D4s_v3, min 2 / max 5 nodes)
  - Node pool: `app` (Standard_D8s_v3, min 2 / max 10 nodes, for AI workloads)
  - Enable Cluster Autoscaler
  - Enable Azure CNI networking (for VNet integration)
  - Enable Managed Identity
  - Enable OIDC issuer + Workload Identity
- [ ] Attach Azure Container Registry (ACR): `navuairegistry`
- [ ] Install ingress controller: NGINX or Azure Application Gateway Ingress Controller (AGIC)
- [ ] Install cert-manager for TLS certificates (Let's Encrypt or Azure-managed certs)

### Step 4 — GPU VM for Self-Hosted LLMs
- [ ] Provision GPU VM: `navuai-gpu-vm`
  - Size: `Standard_NC24ads_A100_v4` (or `Standard_NC6s_v3` for dev/test)
  - OS: Ubuntu 22.04
  - Install NVIDIA drivers + CUDA
  - Install Ollama or vLLM serving framework
- [ ] Deploy self-hosted models:
  - Embedded model (e.g., `nomic-embed-text` or `bge-m3`)
  - Reranker model (e.g., `bge-reranker-v2-m3`)
  - OSS LLM (e.g., `llama3`, `mistral`, or `kimi` when available)
- [ ] Expose via internal private endpoint only (not public)
- [ ] Register GPU VM models in LiteLLM config

---

## Phase 2 — LiteLLM API Gateway

**Goal:** Central LLM routing layer that abstracts all providers behind one API.

### Step 5 — LiteLLM Deployment on AKS
- [ ] Create namespace: `litellm`
- [ ] Write Helm chart / Kubernetes manifests for LiteLLM:
  - Deployment with `litellm/litellm` container image
  - ConfigMap for `config.yaml` (model routing config)
  - Secret for all provider API keys (pull from Azure Key Vault via CSI driver)
  - Service (ClusterIP) + Ingress for public API endpoint
- [ ] Configure LiteLLM `config.yaml` with model list:
  ```yaml
  model_list:
    - model_name: gpt-4o          # OpenAI
      litellm_params:
        model: openai/gpt-4o
        api_key: os.environ/OPENAI_API_KEY

    - model_name: claude-3-5      # AWS Bedrock
      litellm_params:
        model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
        aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
        aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
        aws_region_name: us-east-1

    - model_name: gemini-pro      # Google Vertex AI
      litellm_params:
        model: vertex_ai/gemini-1.5-pro
        vertex_project: os.environ/VERTEX_PROJECT
        vertex_location: us-central1

    - model_name: azure-gpt4      # Azure AI Foundry
      litellm_params:
        model: azure/gpt-4o
        api_base: os.environ/AZURE_API_BASE
        api_key: os.environ/AZURE_API_KEY
        api_version: "2024-02-01"

    - model_name: local-llm       # Self-hosted GPU VM
      litellm_params:
        model: openai/llama3
        api_base: http://navuai-gpu-vm:11434/v1
        api_key: none
  ```
- [ ] Enable LiteLLM database (PostgreSQL on Azure) for usage tracking
- [ ] Configure rate limits per API key
- [ ] Configure budget limits per user/team

### Step 6 — API Key Management
- [ ] Set up LiteLLM virtual API keys (per user / per app)
- [ ] Integrate with Azure AD for SSO-based key provisioning
- [ ] Configure key scopes: which models each key can access
- [ ] Set per-key token budgets and rate limits

---

## Phase 3 — AI Chatbot & Agents

**Goal:** Deploy AI-powered chat interface and agent applications.

### Step 7 — Chat Frontend (chat.ai.navuai.cloud)
- [ ] Choose frontend framework: Next.js + shadcn/ui (recommended) or Open WebUI
- [ ] Features:
  - Multi-model selector (user picks which LLM to use)
  - Conversation history (stored in PostgreSQL or CosmosDB)
  - File upload + RAG (connect to vector DB)
  - Streaming responses
  - User authentication via Azure AD SSO
- [ ] Containerize and push to ACR
- [ ] Deploy to AKS namespace: `chat`
- [ ] Configure Ingress with TLS: `chat.ai.navuai.cloud`

### Step 8 — BillBot Agent
- [ ] Billing-focused AI agent that:
  - Answers billing questions
  - Shows usage reports per user / per LLM
  - Sends alerts when budget thresholds are hit
- [ ] Connect to billing database (LiteLLM PostgreSQL)
- [ ] Expose as API + integrate into chat UI as a "BillBot" persona
- [ ] Deploy to AKS namespace: `agents`

### Step 9 — Billy Agent (General AI Assistant)
- [ ] General-purpose AI agent (Billy):
  - Tool use: web search, file analysis, code execution
  - MCP protocol support for Jira/Bass integration
  - Memory (short-term via context, long-term via vector DB)
- [ ] Build with LangChain, LlamaIndex, or direct Anthropic/OpenAI SDK
- [ ] Deploy to AKS namespace: `agents`

---

## Phase 4 — MCP Server (Tool Integrations)

**Goal:** MCP protocol server to give AI agents access to internal tools.

### Step 10 — MCP Server Setup
- [ ] Build MCP server (Python or Node.js)
- [ ] Implement tools:
  - **Jira**: create/read/update tickets
  - **Bass**: internal system integration
  - **Azure DevOps**: pipeline triggers (optional)
- [ ] Secure with API key auth (internal only, not exposed publicly)
- [ ] Deploy to AKS namespace: `mcp`
- [ ] Connect to Billy agent via MCP protocol

---

## Phase 5 — Billing & Usage Reporting

**Goal:** Per-user, per-LLM cost tracking and reporting.

### Step 11 — Billing Service
- [ ] LiteLLM built-in billing (PostgreSQL):
  - Track tokens per user per model
  - Track cost per 1M tokens (configure pricing table per model)
- [ ] Build billing dashboard (or integrate into chat UI):
  - Usage $ per User report
  - Usage $ per LLM report
  - Online billing: $40/User/Mo cap
- [ ] Set up automated alerts:
  - Alert when user approaches budget limit
  - Alert when monthly spend exceeds threshold
- [ ] Export billing data to Azure Cost Management or custom reporting

### Step 12 — LLM Pricing Config in LiteLLM
- [ ] Set per-model pricing:
  ```yaml
  # config.yaml additions
  router_settings:
    enable_pre_call_check: true

  litellm_settings:
    success_callback: ["langfuse"]  # observability
    failure_callback: ["langfuse"]
  ```
- [ ] Configure `$40/User/Mo` hard budget cap in LiteLLM virtual keys

---

## Phase 6 — Security & Compliance

**Goal:** Implement all Infra Security requirements from the architecture.

### Step 13 — Network Security
- [ ] SourceIP allowlist on Application Gateway / Azure Firewall
  - Only corporate/VPN IPs can reach internal endpoints
  - Public endpoint only for approved external users
- [ ] HTTP Referrer policies on App Gateway
- [ ] Enable Azure DDoS Protection Standard on VNet
- [ ] Enable Private Endpoints for:
  - Azure AI Foundry (private API endpoint)
  - PostgreSQL (no public access)
  - Azure Key Vault
  - ACR

### Step 14 — SSO & MFA
- [ ] Integrate Azure AD (Entra ID) as identity provider
- [ ] Require MFA for all UI access
- [ ] GSO team approval workflow:
  - New user requests access → approval ticket → Azure AD group assignment
- [ ] Role-Based Access Control (RBAC):
  - `navuai-admin`: full access
  - `navuai-user`: chat + own usage reports only
  - `navuai-billing`: billing reports only

### Step 15 — API Key Security (PoLP)
- [ ] LiteLLM virtual API keys scoped to minimum required models
- [ ] Rotate provider API keys on a schedule (Azure Key Vault rotation policy)
- [ ] No API keys in code or environment variables directly — all via Key Vault CSI driver
- [ ] Audit log all API key usage

### Step 16 — Rate Limits & Budget Alerts
- [ ] LiteLLM rate limits: requests per minute per user
- [ ] Azure API Management rate limiting (if APIM used as front door)
- [ ] Azure Monitor budget alerts:
  - Alert at 80% and 100% of monthly LLM spend
- [ ] Automatic key suspension when budget exceeded

---

## Phase 7 — Observability & Monitoring

**Goal:** Full visibility into LLM usage, errors, latency, and costs.

### Step 17 — Observability Stack
- [ ] Deploy Langfuse (open-source LLM observability) on AKS:
  - Trace every LLM call (model, tokens, latency, cost, user)
  - View prompt/response history
  - Track error rates per model
- [ ] Deploy Prometheus + Grafana on AKS:
  - AKS node and pod metrics
  - LiteLLM custom metrics (requests/sec, token usage, errors)
- [ ] Configure Azure Monitor:
  - Container insights for AKS
  - Log Analytics workspace
  - Alerts for pod failures, high latency

### Step 18 — Logging
- [ ] Centralized logging: Azure Log Analytics or ELK stack
- [ ] Log all API requests (sanitized — no PII in logs)
- [ ] Set retention policy (90 days hot, 1 year cold/archive)

---

## Phase 8 — CI/CD Pipeline

**Goal:** Automated build, test, and deploy pipeline.

### Step 19 — CI/CD Setup
- [ ] Use Azure DevOps Pipelines or GitHub Actions
- [ ] Pipeline per service:
  1. Build Docker image
  2. Push to ACR
  3. Update Helm chart image tag
  4. Deploy to AKS (kubectl apply / helm upgrade)
- [ ] Environments: `dev` → `staging` → `prod`
- [ ] GitOps option: ArgoCD watching the Helm chart repo

---

## Phase 9 — Multi-Cloud Expansion

**Goal:** Ensure architecture is cloud-agnostic beyond Azure.

### Step 20 — Provider Abstraction Layer
- [ ] LiteLLM already handles LLM provider abstraction
- [ ] Infrastructure abstraction via Terraform modules:
  - `modules/kubernetes` — works with AKS, EKS, GKE
  - `modules/gpu-vm` — Azure, AWS, GCP GPU VM provisioning
  - `modules/vpn` — cloud-agnostic VPN setup
- [ ] For AWS deployment:
  - Replace AKS → EKS
  - Replace Azure AI Foundry → AWS Bedrock (already in LiteLLM config)
  - Replace Azure Key Vault → AWS Secrets Manager
- [ ] For GCP deployment:
  - Replace AKS → GKE
  - Replace Azure AI Foundry → Google Vertex AI
  - Replace Azure Key Vault → GCP Secret Manager
- [ ] Document provider-specific swap guide in each module

---

## Build Order (Recommended Sequence)

| Phase | Steps | Deliverable |
|-------|-------|-------------|
| 1 | 1–4 | Azure infra running (AKS + GPU VM + VPN + VNet) |
| 2 | 5–6 | LiteLLM gateway live, all providers connected |
| 3 | 7 | Chat UI live at chat.ai.navuai.cloud |
| 4 | 8–9 | BillBot + Billy agents deployed |
| 5 | 10 | MCP server + Jira integration live |
| 6 | 11–12 | Billing tracking + $40/user cap enforced |
| 7 | 13–16 | Full security hardening |
| 8 | 17–18 | Observability stack live |
| 9 | 19 | CI/CD pipelines automated |
| 10 | 20 | Multi-cloud Terraform modules ready |

---

## Folder Structure (to be built)

```
navuAI/
├── stepsme.md                  ← this file
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── aks/
│   │   │   ├── gpu-vm/
│   │   │   ├── networking/
│   │   │   ├── keyvault/
│   │   │   └── vpn/
│   └── helm/
│       ├── litellm/
│       ├── chat/
│       ├── agents/
│       ├── mcp-server/
│       └── observability/
├── services/
│   ├── litellm-config/
│   │   └── config.yaml
│   ├── chat-frontend/
│   ├── billbot-agent/
│   ├── billy-agent/
│   └── mcp-server/
├── billing/
│   └── pricing-config.yaml
├── security/
│   └── rbac/
└── docs/
    └── multi-cloud-swap-guide.md
```

---

## Current Status

- [x] navuAI folder created
- [x] Architecture defined (stepsme.md written)
- [ ] Phase 1 — Step 1: Azure prerequisites (START HERE)
