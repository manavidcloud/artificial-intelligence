# LAB 3 — AI & Visualization Layer
# Step-by-Step Deployment Guide
# LLM: Azure AI Foundry + GPT-4o-mini via Workload Identity (no API keys)

## What We Are Building

```
Azure AI Foundry (finops-ai-hub)
  └── Azure OpenAI resource (finops-ai-brain)
        └── gpt-4o-mini deployment
                │
                │ Workload Identity (no keys)
                ▼
AKS — ai namespace
  └── finops-ai-agent   (LangGraph + AzureChatOpenAI + PostgreSQL tools)
                │
                │ internal cluster DNS
                ▼
AKS — frontend namespace
  └── finops-dashboard  (Streamlit chat UI + quick action buttons)
                │
                ▼
Ingress (TLS)
  ├── app.manmas.online  → Streamlit dashboard
  └── ai.manmas.online   → AI Agent API + Swagger docs
```

## Why Workload Identity (No API Keys)
- Managed Identity (mi-finops-prod) from Lab 1 authenticates to Azure OpenAI
- Zero secrets in the pod — fully enterprise compliant
- Same identity already used for Cost Management API in Lab 2
- If the key rotates, nothing breaks — no config change needed

---

## STEP 1 — Create Azure OpenAI Resource and Deploy Model

```bash
# Register the provider (run once per subscription)
az provider register --namespace Microsoft.CognitiveServices

# Create Azure OpenAI resource
az cognitiveservices account create \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --location southindia \
  --kind OpenAI \
  --sku S0 \
  --yes

# Deploy gpt-4o-mini model inside it
az cognitiveservices account deployment create \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

# Verify — note the endpoint URL from the output
az cognitiveservices account show \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --query properties.endpoint -o tsv
# Output example: https://finops-ai-brain.openai.azure.com/
```

---

## STEP 2 — Setup Workload Identity for AI Namespace

This script does 3 things:
- Creates a federated credential for the `ai` namespace service account
- Grants Managed Identity access to Azure OpenAI
- Prints the values you need for the deployment YAML

```bash
# Make executable and run
chmod +x azure-cost/gpt/lab3-ai_virtual/2.agent-deployment/workload-identity-setup.sh
bash azure-cost/gpt/lab3-ai_virtual/2.agent-deployment/workload-identity-setup.sh
```

Copy the output values — you need them in Step 4.

---

## STEP 3 — Build and Push the AI Agent Image

```bash
# Login to ACR (Docker Desktop must be running)
az acr login --name finopsacrmanmas

# Build from 1.langgraph-agent folder
cd azure-cost/gpt/lab3-ai_virtual/1.langgraph-agent

docker build -t finopsacrmanmas.azurecr.io/finops-ai-agent:v1 .
docker push finopsacrmanmas.azurecr.io/finops-ai-agent:v1

# Verify
az acr repository list --name finopsacrmanmas --output table
```

---

## STEP 4 — Update and Apply Agent Deployment

Edit `2.agent-deployment/agent-deployment.yaml` — replace the 3 placeholders:

| Placeholder | Replace with | How to get it |
|-------------|-------------|---------------|
| `REPLACE_WITH_MI_CLIENT_ID` | e.g. `a1b2c3d4-...` | Output of workload-identity-setup.sh |
| `REPLACE_WITH_AZURE_OPENAI_ENDPOINT` | e.g. `https://finops-ai-brain.openai.azure.com/` | Output of workload-identity-setup.sh |
| `REPLACE_WITH_DB_PASSWORD` | your PostgreSQL password | Same as Lab 1 & 2 |

Then apply:

```bash
kubectl apply -f azure-cost/gpt/lab3-ai_virtual/2.agent-deployment/agent-deployment.yaml

# Watch pod start
kubectl get pods -n ai -w

# Expected:
# NAME                               READY   STATUS    RESTARTS   AGE
# finops-ai-agent-xxxxxxxxxx-xxxxx   1/1     Running   0          45s
```

---

## STEP 5 — Test the AI Agent

```bash
kubectl port-forward svc/finops-ai-agent-svc 8001:80 -n ai

# Health check
curl http://localhost:8001/health
# Expected: {"status":"online","service":"finops-ai-agent","auth":"workload-identity",...}

# Chat test
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a cost summary for the last 7 days"}'

# Browse API docs
# Open: http://localhost:8001/docs
```

---

## STEP 6 — Build and Push Streamlit Dashboard

```bash
cd azure-cost/gpt/lab3-ai_virtual/3.streamlit-dashboard

docker build -t finopsacrmanmas.azurecr.io/finops-dashboard:v1 .
docker push finopsacrmanmas.azurecr.io/finops-dashboard:v1
```

---

## STEP 7 — Deploy Streamlit Dashboard

```bash
kubectl apply -f azure-cost/gpt/lab3-ai_virtual/4.dashboard-deployment/dashboard-deployment.yaml

kubectl get pods -n frontend -w

# Test locally
kubectl port-forward svc/finops-dashboard-svc 8502:80 -n frontend
# Open browser: http://localhost:8502
```

---

## STEP 8 — Apply Ingress (Public HTTPS Access)

```bash
# Check ingress IP
kubectl get svc -n ingress-nginx
# Note the EXTERNAL-IP

# Ensure DNS A records exist (in your domain registrar):
#   app.manmas.online  ->  <EXTERNAL-IP>
#   ai.manmas.online   ->  <EXTERNAL-IP>

kubectl apply -f azure-cost/gpt/lab3-ai_virtual/5.ingress/lab3-ingress.yaml

# Wait for TLS certs (2-3 minutes)
kubectl get certificate -n frontend
kubectl get certificate -n ai
# READY column must show: True
```

---

## STEP 9 — Final Check

```bash
kubectl get pods -n ai
kubectl get pods -n frontend
kubectl get ingress -n frontend
kubectl get ingress -n ai
```

Open in browser:
- `https://app.manmas.online` — Streamlit chat dashboard
- `https://ai.manmas.online/health` — AI agent health
- `https://ai.manmas.online/docs` — FastAPI Swagger UI

---

## Folder Structure

```
lab3-ai_virtual/
├── guide.md                              <- You are here
├── lab3-readme.md                        <- Overview
├── lab3-init.yaml                        <- DONE: pgvector job
│
├── 1.langgraph-agent/
│   ├── main.py                           <- FastAPI + LangGraph + AzureChatOpenAI
│   ├── tools.py                          <- 5 PostgreSQL query tools
│   ├── requirements.txt                  <- includes azure-identity
│   └── Dockerfile
│
├── 2.agent-deployment/
│   ├── workload-identity-setup.sh        <- Run first (one-time)
│   └── agent-deployment.yaml            <- Namespace + SA + Secret + Deploy + Svc
│
├── 3.streamlit-dashboard/
│   ├── app.py                            <- Chat UI + quick action buttons
│   ├── requirements.txt
│   └── Dockerfile
│
├── 4.dashboard-deployment/
│   └── dashboard-deployment.yaml        <- frontend namespace + Deploy + Svc
│
└── 5.ingress/
    └── lab3-ingress.yaml                <- TLS ingress for both domains
```

---

## Replicating on Office / Corporate Account

| Item | Personal (now) | Office (production) |
|------|---------------|-------------------|
| LLM | Azure OpenAI S0 gpt-4o-mini | Azure OpenAI S0 gpt-4o |
| Auth | Workload Identity | Workload Identity (same) |
| Secrets | K8s Secret for DB | Key Vault CSI Driver |
| Subscriptions | 1 test subscription | All corporate subscriptions |
| AKS nodes | 1 x B2als_v2 | System + spot node pools |
| Scale | Manual | KEDA (scale to zero) |

For office, grant the Managed Identity `Cost Management Reader` on each corporate subscription:
```bash
az role assignment create \
  --assignee <MI_CLIENT_ID> \
  --role "Cost Management Reader" \
  --scope /subscriptions/<OFFICE_SUBSCRIPTION_ID>
```
Run once per subscription to give the platform visibility across all accounts.
