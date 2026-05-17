# ⚡ FinOps AI Dashboard

> **Azure Cost Intelligence Platform** — Pull cost, resource, and Advisor data from Azure into a Streamlit dashboard with an AI-powered chat assistant for natural-language cost analysis.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [How Everything Works](#how-everything-works)
   - [Authentication](#authentication)
   - [Multi-Cloud Architecture & Extensibility](#multi-cloud-architecture--extensibility)
   - [Azure Identity (Workload Identity)](#azure-identity-workload-identity)
   - [AI Agent Tool Calling](#ai-agent-tool-calling)
5. [Prerequisites](#prerequisites)
6. [Step-by-Step Setup From Scratch](#step-by-step-setup-from-scratch)
   - [Step 1 — Configure `config.yaml`](#step-1--configure-configyaml)
   - [Step 2 — Provision Azure Infrastructure](#step-2--provision-azure-infrastructure)
   - [Step 3 — Fill Secrets](#step-3--fill-secrets)
   - [Step 4 — Apply Kubernetes Secrets](#step-4--apply-kubernetes-secrets)
   - [Step 5 — Build & Push Docker Images](#step-5--build--push-docker-images)
   - [Step 6 — Deploy to AKS](#step-6--deploy-to-aks)
   - [Step 7 — Expose via Ingress](#step-7--expose-via-ingress)
   - [Step 7b — Install OpenCost + Prometheus + Azure Integration](#step-7b--install-opencost--prometheus-k8s-cost-allocation)
   - [Step 8 — First Login & Initial Sync](#step-8--first-login--initial-sync)
   - [Step 9 — Sanity Check](#step-9--sanity-check)
7. [Dashboard Pages & Features](#dashboard-pages--features)
8. [API Reference](#api-reference)
9. [AI Agent](#ai-agent)
10. [Cost Estimates](#cost-estimates)
11. [Troubleshooting](#troubleshooting)

---

## What This Is

The FinOps AI Dashboard is a **self-hosted, Kubernetes-native platform** that:

- **Pulls** Azure cost, resource, and Advisor data on a schedule (every 6 hours by default)
- **Stores** everything in a private PostgreSQL database inside your VNet
- **Exposes** a REST API (Platform API) consumed by the dashboard and the AI agent
- **Renders** a dark-theme Streamlit dashboard with charts, tables, and filters
- **Answers questions** via a LangGraph ReAct AI agent powered by Azure OpenAI — ask in plain English, get cost insights backed by real data

```
User → Streamlit Dashboard → Platform API → PostgreSQL
                          ↘ AI Agent (LangGraph) → Azure OpenAI
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Internet / Users                                 │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │  HTTPS  app.manmas.online / api.manmas.online / ai.manmas.online
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       AKS NGINX Ingress Controller                           │
│                    (TLS termination via cert-manager / Let's Encrypt)        │
└──┬─────────────────┬──────────────────┬──────────────────┬───────────────────┘
   │ frontend ns      │ platform ns       │ ai ns             │ opencost ns
   ▼                  ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌──────────────────┐
│ 4-Dashboard  │  │ 2-Platform API   │  │ 3-AI Agent  │  │ 5-OpenCost       │
│ (Streamlit)  │─▶│ (FastAPI)        │◀─│ (LangGraph) │  │ K8s cost alloc   │
│ port 8501    │  │ port 8080        │  │ port 8000   │  │ UI:9090 API:9003 │
└──────────────┘  └────────┬─────────┘  └─────────────┘  └────────┬─────────┘
        │                  │   (AI calls Platform API)              │
        │                  │                                        │
        │     ┌────────────▼──────────────┐              ┌─────────▼──────────┐
        │     │  PostgreSQL Flexible Svr  │              │  Prometheus         │
        │     │  (private VNet, port 5432)│              │  (K8s metrics)      │
        │     │  • cost_records           │              │  port 9090          │
        │     │  • resources              │              └────────────────────┘
        │     │  • advisor_recommendations│
        │     │  • subscriptions          │
        │     └───────────────────────────┘
        │
        └──────────── Auth: LOCAL yaml/bcrypt  │  OAUTH Azure AD  │  LDAP/AD
                      (AUTH_MODE env var — see Authentication section)

Azure Services Used:
  ┌──────────────────────────────────────────────────────────────────┐
  │  Azure Cost Management   →  billing data (ActualCost API)        │
  │  Azure Resource Graph    →  resource inventory (KQL)             │
  │  Azure Advisor           →  Cost + security recommendations      │
  │  Azure OpenAI            →  gpt-4.1-nano (AI chat)               │
  │  Azure Container Registry→  Docker image storage                 │
  │  Azure Key Vault         →  secret management (RBAC mode)        │
  │  Managed Identity        →  passwordless auth to Azure APIs      │
  └──────────────────────────────────────────────────────────────────┘

Identity & Auth Flow:
  AKS Pod  →  OIDC Token  →  Entra ID  →  Managed Identity
                                          (Cost Mgmt Reader +
                                           Resource Graph Reader +
                                           Key Vault Secrets User +
                                           OpenAI User)

Cloud Provider Extensibility (Platform API):
  CLOUD_PROVIDER=azure  →  providers/azure.py   ✅ implemented
  CLOUD_PROVIDER=aws    →  providers/aws.py      🔲 stub ready (boto3)
  CLOUD_PROVIDER=gcp    →  providers/gcp.py      🔲 stub ready (google-cloud-billing)

OpenCost Multi-Cloud (Helm values: 4-dashboard/k8s/opencost-helm-values.yaml):
  Azure AKS   →  native (this repo)
  AWS EKS     →  set cloudProvider: aws + AWS pricing secret
  GCP GKE     →  set cloudProvider: gcp + GCP pricing secret
  On-prem K8s →  set cloudProvider: custom + custom pricing CSV
```

### Network Layout

```
VNet: 10.0.0.0/16  (finops-prod-vnet)
  ├── general-subnet    10.0.0.0/24   (reserved)
  ├── postgres-subnet   10.0.1.0/24   (delegated to PostgreSQL Flex)
  └── aks-subnet        10.0.2.0/24   (AKS nodes + pods)

AKS Service CIDR: 10.96.0.0/16
```

### Resource Groups

| Group | Purpose |
|---|---|
| `rg-finops-prod-network` | VNet, subnets, NSGs, Private DNS |
| `rg-finops-prod-core` | AKS, ACR, Managed Identity |
| `rg-finops-prod-security` | Key Vault (isolated for least-privilege) |
| `rg-finops-prod-data` | PostgreSQL Flexible Server |
| `rg-finops-prod-ai` | Azure OpenAI |

---

## Project Structure

```
finops-dashborad/
├── config.yaml                      # Single source of truth — edit first
├── secrets.env.template             # Template for secrets (never commit secrets.env)
├── .gitignore
│
├── sanity-check/
│   └── sanity.sh                    # Post-deploy health check script
│
├── k8s/
│   └── ingress.yaml                 # Shared NGINX Ingress + TLS for all services
│
├── 1-infrastructure/
│   └── scripts/
│       ├── setup.sh                 # Full Azure infrastructure provisioner
│       ├── apply-secrets.sh         # K8s namespaces, secrets, service accounts
│       └── setup-opencost-azure.sh  # OpenCost Azure integration (Rate Card + billing export)
│
├── 2-platform-api/                  # FastAPI backend — data sync & REST API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── TROUBLESHOOTING.md
│   ├── k8s/
│   │   └── deployment.yaml          # Namespace, Deployment, Service, HPA
│   └── src/
│       ├── main.py                  # All API endpoints
│       ├── database.py              # SQLAlchemy engine + session
│       ├── models.py                # ORM models (4 tables)
│       ├── notifications.py         # Email alerts (cost spikes, digests, budgets)
│       └── providers/
│           ├── base.py              # Abstract CloudProvider interface
│           ├── azure.py             # Azure implementation (Cost Mgmt, RG, Advisor)
│           ├── aws.py               # 🔲 AWS stub (boto3 / Cost Explorer)
│           └── gcp.py               # 🔲 GCP stub (google-cloud-billing)
│
├── 3-ai-agent/                      # LangGraph ReAct agent — natural language Q&A
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── TROUBLESHOOTING.md
│   ├── k8s/
│   │   └── deployment.yaml          # Namespace, SA, Deployment, Service
│   └── src/
│       └── main.py                  # FastAPI wrapper + LangGraph agent + 9 tools
│
├── 4-dashboard/                     # Streamlit multi-page dashboard
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── TROUBLESHOOTING.md
│   ├── k8s/
│   │   ├── deployment.yaml                          # Namespace, Deployment, Service (OPENCOST_URL: port 9003)
│   │   ├── opencost-prometheus-values.yaml          # Prometheus Helm values (AKS scrape config)
│   │   ├── opencost-helm-values.yaml                # OpenCost Helm values (Azure pricing + cloud costs)
│   │   ├── opencost-service-key.json.template       # Rate Card SP key template (never commit the real file)
│   │   └── opencost-cloud-integration.json.template # Billing export config template (never commit the real file)
│   └── src/
│       ├── Home.py                  # Overview: KPIs, daily trend, top services
│       ├── auth.py                  # Login wall — local/oauth/ldap (AUTH_MODE)
│       ├── users.yaml.template      # Copy → users.yaml and fill in
│       ├── .streamlit/
│       │   └── config.toml          # Dark theme, server settings
│       ├── pages/
│       │   ├── 1_Costs.py           # Full cost analysis (8 tabs inc. MoM)
│       │   ├── 2_Resources.py       # Resource inventory + type drill-down
│       │   ├── 3_Advisor.py         # 7-tab Advisor intelligence centre
│       │   ├── 4_AI_Chat.py         # AI assistant chat interface
│       │   ├── 5_OpenCost.py        # K8s cost allocation (OpenCost + Prometheus)
│       │   └── 6_Settings.py        # Admin: manual sync, email tests, health
│       └── utils/
│           ├── api.py               # HTTP client for Platform API + AI Agent
│           ├── currency.py          # Currency conversion + formatting helpers
│           ├── opencost_api.py      # OpenCost REST client (allocation, assets, sizing)
│           └── theme.py             # Dark CSS + Plotly dark template
```

---

## How Everything Works

### Data Flow

```
Every 6 hours (or manually via Settings):

Azure Cost Management API
        │  ActualCost query, DAILY granularity, grouped by
        │  ServiceName + ResourceGroupName
        ▼
Platform API  /sync/costs
        │  Upserts rows into cost_records table
        │  (unique constraint: sub_id + date + service + rg)
        ▼
PostgreSQL  cost_records table
        │  Queried by dashboard on every page load
        ▼
Streamlit  1_Costs.py  →  charts + tables
```

### Authentication

The auth backend is selected by the `AUTH_MODE` environment variable injected at runtime. The Docker image has **no default baked in** — the app falls back to `local` when `AUTH_MODE` is absent. Always inject it via a Kubernetes Secret or ConfigMap, never via `ENV` in the Dockerfile (Docker BuildKit lints "AUTH" variable names as sensitive).

| `AUTH_MODE` | Backend | Status |
|---|---|---|
| `local` | YAML + bcrypt | Ready — default |
| `oauth` | Azure AD / Entra ID SSO | Stub ready — needs `msal` wired in |
| `ldap` | Active Directory / OpenLDAP | Stub ready — needs `ldap3` wired in |
| _(any new value)_ | Custom backend | Add `_verify_<mode>()` in `auth.py` |

#### Local auth (current)

1. Copy `4-dashboard/src/users.yaml.template` → `users.yaml`
2. Add usernames and plaintext passwords
3. On first login, plaintext passwords are **auto-upgraded to bcrypt hashes** and written back to `users.yaml`
4. Session is stored in Streamlit `session_state` — no JWT, no cookies, no external dependency

#### Azure AD / Entra ID SSO (oauth)

When you're ready to switch to Azure AD, follow these steps:

1. **Register an app in Azure AD (Entra ID)**
   - Go to Azure Portal → Entra ID → App Registrations → New Registration
   - Set redirect URI: `https://app.manmas.online` (or your domain)
   - Under API Permissions, add `User.Read` (Microsoft Graph, Delegated)
   - Create a Client Secret and copy the value

2. **Add env vars to `secrets.env`**
   ```env
   AUTH_MODE=oauth
   OAUTH_CLIENT_ID=<app-registration-client-id>
   OAUTH_CLIENT_SECRET=<client-secret-value>
   OAUTH_TENANT_ID=<your-azure-tenant-id>
   ```

3. **Add `msal` to the dashboard requirements**
   ```bash
   echo "msal>=1.28.0" >> 4-dashboard/requirements.txt
   ```

4. **Implement `_verify_oauth()` in `auth.py`**
   The stub is already in place with step-by-step MSAL instructions in the comments. Replace the `raise NotImplementedError` with the MSAL token acquisition block shown there.

5. **Rebuild and redeploy the dashboard**
   ```bash
   docker build -t $ACR/finops-dashboard:latest 4-dashboard/
   docker push $ACR/finops-dashboard:latest
   kubectl rollout restart deployment -n frontend
   ```

> The SSO button is already rendered in the login UI — it activates automatically when `OAUTH_CLIENT_ID` is set in the environment.

#### LDAP / Active Directory

Same pattern as OAuth:
1. Add `LDAP_SERVER`, `LDAP_BASE_DN`, `LDAP_DOMAIN` to `secrets.env` and set `AUTH_MODE=ldap`
2. Add `ldap3` to `requirements.txt`
3. Implement `_verify_ldap()` in `auth.py` (stub + instructions already in place)
4. Rebuild and redeploy

#### Adding any new auth backend

1. Add `_verify_<mode>(username, password) → dict | None` in `auth.py`
2. Add an `elif AUTH_MODE == "<mode>"` branch in `_verify()`
3. Inject `AUTH_MODE=<mode>` via Kubernetes Secret at runtime — no image changes needed

---

### Azure Identity (Workload Identity)

Instead of storing Azure credentials as secrets, pods use **Workload Identity**:

```
Pod in AKS  →  Projected Service Account Token (OIDC)
             →  Entra ID token exchange
             →  Managed Identity token
             →  Azure APIs (no password needed)
```

This is set up by `setup.sh` (federated credentials) and `apply-secrets.sh` (service account annotations).

---

### Multi-Cloud Architecture & Extensibility

The platform is designed for Azure today but built to support multiple clouds without touching the API or dashboard layers.

#### How it works

All cloud data fetching is isolated behind a single abstract interface:

```python
# 2-platform-api/src/providers/base.py
class CloudProvider(ABC):
    def sync_subscriptions(self, db) -> int: ...  # accounts / projects
    def sync_costs(self, db, days: int) -> int: ...  # billing data
    def sync_resources(self, db) -> int: ...         # resource inventory
    def sync_advisor(self, db) -> int: ...           # cost recommendations
```

The active provider is selected at startup by the `CLOUD_PROVIDER` environment variable (default: `azure`):

```
CLOUD_PROVIDER=azure  →  providers/azure.py  (AzureProvider)   ✅ implemented
CLOUD_PROVIDER=aws    →  providers/aws.py    (AWSProvider)      🔲 stub ready
CLOUD_PROVIDER=gcp    →  providers/gcp.py    (GCPProvider)      🔲 stub ready
```

The Platform API (`main.py`), dashboard, and AI agent are **completely unaware** of which cloud is active — they only call the 4 methods above.

#### Adding AWS support

1. **Create `2-platform-api/src/providers/aws.py`**
   ```python
   import boto3
   from .base import CloudProvider

   class AWSProvider(CloudProvider):
       def sync_subscriptions(self, db) -> int:
           # boto3: organizations.list_accounts()
           ...
       def sync_costs(self, db, days: int) -> int:
           # boto3: ce.get_cost_and_usage() (Cost Explorer)
           ...
       def sync_resources(self, db) -> int:
           # boto3: resourcegroupstaggingapi.get_resources()
           ...
       def sync_advisor(self, db) -> int:
           # boto3: support.describe_trusted_advisor_checks() + results
           ...
   ```

2. **Add AWS SDK to requirements**
   ```bash
   echo "boto3>=1.34.0" >> 2-platform-api/requirements.txt
   ```

3. **Set env vars in `secrets.env`**
   ```env
   CLOUD_PROVIDER=aws
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_DEFAULT_REGION=us-east-1
   AZURE_SUBSCRIPTION_IDS=<aws-account-ids>   # reuse same field, comma-separated
   ```

4. **Rebuild and redeploy Platform API and AI Agent** — dashboard needs no changes.

#### Adding GCP support

Same pattern: create `providers/gcp.py` implementing `GCPProvider`, use `google-cloud-billing` + `google-cloud-asset` SDKs, set `CLOUD_PROVIDER=gcp`.

#### Multi-cloud (running Azure + AWS simultaneously)

Currently the factory loads one provider per deployment. To support multiple clouds in a single instance, the API layer would need to be extended to fan out across multiple provider instances — the data model (`cost_records`, `resources`, etc.) already stores a `subscription_id` field that naturally differentiates accounts across clouds.

---

### AI Agent Tool Calling

The AI Agent uses **LangGraph ReAct** pattern:

```
User question
    │
    ▼ LLM (gpt-4.1-nano) decides which tool to call
    │
    ├── get_cost_summary()        → GET /costs/summary
    ├── get_top_services()        → GET /costs/by-service
    ├── get_cost_trend()          → GET /costs/daily
    ├── get_advisor_recommendations() → GET /advisor
    ├── get_resource_list()       → GET /resources
    └── get_cost_by_subscription() → GET /costs/by-subscription
    │
    ▼ Tool result returned to LLM
    │
    ▼ LLM synthesizes answer with cited numbers
    │
    ▼ Response returned to Dashboard
```

The agent loops until it has enough information to answer, then returns a final human-readable response with cited amounts and dates.

### Email Notifications

Three email types are supported via SMTP:

| Type | Trigger | Content |
|---|---|---|
| Cost Spike | POST `/alerts/cost-spike` | Service, prev/current period, % change |
| Daily Digest | POST `/alerts/digest` | Total spend, top 10 services, Advisor count |
| Budget Alert | POST `/alerts/budget` | Spent vs budget, progress bar, projected total |

All emails use an HTML dark-theme / glassmorphism template matching the dashboard UI.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Azure CLI (`az`) | ≥ 2.55 | Provision all Azure resources |
| `kubectl` | ≥ 1.28 | Manage AKS cluster |
| Docker | ≥ 24 | Build and push container images |
| Python 3 | ≥ 3.11 | Used by setup.sh for password generation |
| Bash | ≥ 5 | Run the shell scripts |

You also need:
- An **Azure subscription** with Owner or Contributor + User Access Administrator rights
- **Key Vault Secrets Officer** role on the Key Vault (auto-assigned by `apply-secrets.sh` for the caller)
- **Azure OpenAI access** approved for your subscription (request at aka.ms/oai/access)
- A domain name pointing to your AKS ingress IP (optional — you can use `kubectl port-forward` instead)

---

## Step-by-Step Setup From Scratch

### Step 1 — Configure `config.yaml`

Edit the master config file. The only values you **must** change:

```yaml
azure:
  subscription_ids:
    - "YOUR-SUBSCRIPTION-UUID"   # az account show --query id -o tsv
  tenant_id: "YOUR-TENANT-UUID"  # az account show --query tenantId -o tsv
  location: "centralindia"       # change to your preferred region
  ai_location: "southindia"      # must support Azure OpenAI
  names:
    acr: "finopsacrmanmas"        # globally unique, lowercase, no hyphens
    key_vault: "kv-finops-prod00" # globally unique
```

All scripts read from these hardcoded variables (they mirror `config.yaml` so you only need to edit one place).

---

### Step 2 — Provision Azure Infrastructure

```bash
# 1. Log in to Azure
az login

# 2. Set your subscription
az account set --subscription "YOUR-SUBSCRIPTION-ID"

# 3. Run the provisioner (takes 15-20 minutes)
chmod +x 1-infrastructure/scripts/setup.sh
./1-infrastructure/scripts/setup.sh
```

**What `setup.sh` creates (in order):**

| Step | Resource | Notes |
|---|---|---|
| 1 | 5 Resource Groups | network, core, security, data, ai |
| 2 | Managed Identity | `mi-finops-prod` with Cost Reader + Reader roles |
| 3 | VNet + 3 Subnets | 10.0.0.0/16, AKS subnet, Postgres subnet |
| 4 | Private DNS Zone | `finops-pgflex.private.postgres.database.azure.com` |
| 5 | Azure Container Registry | `finopsacrmanmas`, Basic SKU, no admin credentials |
| 6 | AKS Cluster | System node (Standard_B2als_v2), KEDA enabled, Workload Identity |
| 6b | App Node Pool | `apppool`, Standard_D2pds_v6, User mode (for workloads) |
| 7 | ACR → AKS | AcrPull role assigned directly to kubelet identity |
| 8 | Key Vault | `kv-finops-prod00`, RBAC mode, 7-day soft delete |
| 9 | PostgreSQL Flex | Burstable B1ms, 32 GB, private VNet, pgvector — password stored to KV immediately |
| 10 | Azure OpenAI | gpt-4.1-nano deployed as `gpt-4o-mini` |
| 11 | AKS Kubeconfig | Sets local kubectl context |
| 12 | OIDC Issuer | Retrieved for Workload Identity federation |
| 13 | Federated Credentials | Links `cost-platform-sa` and `cost-ai-sa` to Managed Identity |
| 14 | Summary | Prints all connection values |

> **Idempotent** — re-running `setup.sh` is safe. Each step checks whether the resource already exists and skips creation if it does, validating key properties (location, CIDR, SKU) and warning on any mismatch.

<details>
<summary><strong>Troubleshooting — Step 2</strong></summary>

**`az postgres flexible-server` fails with module error**
```
No module named 'azure.mgmt.rdbms.mysql_flexibleservers'
```
The Azure CLI has a broken Python dependency. Reinstall and re-login:
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
```

---

**Azure OpenAI resource soft-deleted / `ResourceExists` error**

If setup.sh fails on the OpenAI step because the resource was previously deleted (Azure retains it in soft-delete for 48h by default), purge it first:
```bash
# List soft-deleted Cognitive Services resources
az cognitiveservices account list-deleted

# Purge the soft-deleted resource so it can be recreated
az cognitiveservices account purge \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --location southindia

# Verify it's gone
az cognitiveservices account list --output table
```
Then re-run `setup.sh`.

---

**Key Vault name already taken globally**

Key Vault names are globally unique across all Azure tenants. If `VaultAlreadyExists` appears, change `KV_NAME` in `setup.sh` (e.g., `kv-finops-prod00`) and update `config.yaml` and `apply-secrets.sh` to match.

---

**AKS `K8sVersionNotSupported` on `az aks update --attach-acr`**

AKS free tier blocks certain update operations. Use direct role assignment instead:
```bash
ACR_ID=$(az acr show --name finopsacrmanmas --resource-group rg-finops-prod-core --query id -o tsv)
KUBELET_OID=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query "identityProfile.kubeletidentity.objectId" -o tsv)
az role assignment create --role AcrPull --assignee-object-id "$KUBELET_OID" \
  --assignee-principal-type ServicePrincipal --scope "$ACR_ID"
```

</details>

---

### Step 3 — Fill Secrets

```bash
cp secrets.env.template secrets.env
# Edit secrets.env and fill in all values from Step 2 output
nano secrets.env
```

Minimum required values:

```env
DB_HOST=finops-pgflex.postgres.database.azure.com
DB_NAME=finops-db
DB_USER=pgadmin
DB_PASSWORD=<configured in setup.sh as POSTGRES_PASSWORD>

AZURE_OPENAI_ENDPOINT=https://finops-ai-brain.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
# AZURE_OPENAI_API_KEY is optional — leave blank to use Workload Identity

MI_CLIENT_ID=<from setup.sh output>
AZURE_SUBSCRIPTION_IDS=<your-subscription-uuid>
```

Optional (for email alerts):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com
ALERT_RECIPIENTS=you@gmail.com,team@company.com
```

<details>
<summary><strong>Troubleshooting — Step 3</strong></summary>

**`bash: !xxx: event not found` when pasting a password**

Bash treats `!` as a history expansion character inside double quotes. Always use **single quotes** for passwords on the command line:
```bash
# Wrong — bash expands !admi9
az postgres flexible-server update --admin-password "AzFleX!admi9"

# Correct
az postgres flexible-server update --admin-password 'AzFleX!admi9'
```

</details>

---

### Step 4 — Apply Kubernetes Secrets

This script reads `secrets.env` and creates Kubernetes namespaces, secrets, and service accounts. It is idempotent — re-running skips anything already in the correct state:

```bash
chmod +x 1-infrastructure/scripts/apply-secrets.sh
./1-infrastructure/scripts/apply-secrets.sh
```

> The script auto-assigns **Key Vault Secrets Officer** to the current caller if missing — no manual role assignment needed.

**What it creates:**

| Resource | Namespace | Contents |
|---|---|---|
| `finops-platform-secret` | `platform` | DB creds, OpenAI, MI_CLIENT_ID, subscriptions, SMTP |
| `finops-ai-secret` | `ai` | OpenAI endpoint, deployment, MI_CLIENT_ID |
| `finops-frontend-secret` | `frontend` | Internal service URLs |
| `cost-platform-sa` | `platform` | Service Account annotated with MI_CLIENT_ID |
| `cost-ai-sa` | `ai` | Service Account annotated with MI_CLIENT_ID |

Verify:
```bash
kubectl get secrets -A
kubectl get serviceaccounts -n platform
kubectl get serviceaccounts -n ai
```

<details>
<summary><strong>Troubleshooting — Step 4</strong></summary>

**Key Vault write fails: `ForbiddenByRbac`**

The script auto-assigns `Key Vault Secrets Officer` to the caller. If it still fails, assign manually:
```bash
KV_ID=$(az keyvault show --name kv-finops-prod00 --resource-group rg-finops-prod-security --query id -o tsv)
CALLER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --role "Key Vault Secrets Officer" \
  --assignee-object-id "$CALLER_OID" --scope "$KV_ID"
# Wait ~30s for RBAC propagation, then re-run apply-secrets.sh
```

---

**K8s secret has wrong DB password after re-running**

If the pod crashes with password auth failure, re-sync the secret from `secrets.env` and restart:
```bash
bash 1-infrastructure/scripts/apply-secrets.sh
kubectl rollout restart deployment/finops-platform-api -n platform
```

</details>

---

### Step 5 — Build & Push Docker Images

> **Important:** Use `docker buildx build --push` (not `docker build` + `docker push`). The cluster has a mixed architecture: the system nodepool is **amd64** and the apppool (`apppool`) is **ARM64** (`Standard_D2pds_v6`). Each image must be built for the correct platform(s) or the pod will fail with `no match for platform in manifest`.

```bash
# Log in to ACR
az acr login --name finopsacrmanmas

ACR="finopsacrmanmas.azurecr.io"

# Platform API — amd64 only (nodeSelector: kubernetes.io/arch=amd64, runs on system nodepool)
docker buildx build \
  --platform linux/amd64 \
  --push \
  -t $ACR/finops-platform-api:latest \
  2-platform-api/

# AI Agent — multi-arch (no nodeSelector, may land on amd64 system node or ARM apppool)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t $ACR/finops-ai-agent:latest \
  3-ai-agent/

# Dashboard — amd64 only (nodeSelector: kubernetes.io/arch=amd64, runs on system nodepool)
# Set up users first:
cp 4-dashboard/src/users.yaml.template 4-dashboard/src/users.yaml
nano 4-dashboard/src/users.yaml   # set real usernames/passwords

docker buildx build \
  --platform linux/amd64 \
  --push \
  -t $ACR/finops-dashboard:latest \
  4-dashboard/
```

> **`users.yaml` is in `.gitignore` — never commit it.** The dashboard pod mounts it from a Kubernetes Secret (`finops-dashboard-users`). Create that secret before deploying:

```bash
kubectl create secret generic finops-dashboard-users \
  --from-file=users.yaml=4-dashboard/src/users.yaml \
  -n frontend
```

If the secret is missing, the pod starts but falls back to the `users.yaml` baked into the image (from template — no real passwords). Always create the secret before or right after Step 6.

<details>
<summary><strong>Troubleshooting — Step 5</strong></summary>

**Docker BuildKit warns: `Do not use ENV instructions for sensitive data (ENV "AUTH_MODE")`**

Docker BuildKit lints any `ENV` var containing `AUTH` as potentially sensitive. `AUTH_MODE` must not be set in the Dockerfile — it is already injected at runtime via `4-dashboard/k8s/deployment.yaml`. The Dockerfile in this repo has no `ENV AUTH_MODE` line. If you added one, remove it.

---

**Build fails: `pip install` conflict — `langchain-openai 0.1.23 depends on openai>=1.40.0`**

The `openai` version in `3-ai-agent/requirements.txt` must be `>=1.40.0`. The file in this repo already has `openai>=1.40.0,<2.0.0`. If you see this error, check you are building from the latest source.

---

**Pod fails with `no match for platform in manifest`**

The image was built without the correct `--platform` flag. See the build commands above — platform-api and dashboard require `--platform linux/amd64`; ai-agent requires `--platform linux/amd64,linux/arm64`.

</details>

---

### Step 6 — Deploy to AKS

Apply the Kubernetes manifests in order:

```bash
# Platform API (includes Namespace, SA, Deployment, Service, HPA)
kubectl apply -f 2-platform-api/k8s/deployment.yaml

# AI Agent (includes Namespace, SA, Deployment, Service)
kubectl apply -f 3-ai-agent/k8s/deployment.yaml

# Dashboard (includes Namespace, Deployment, Service)
kubectl apply -f 4-dashboard/k8s/deployment.yaml
```

Watch pods come up:
```bash
kubectl get pods -A -w
```

Expected state (all `Running`):
```
platform     finops-platform-api-xxx    1/1   Running
ai           finops-ai-agent-xxx        1/1   Running
frontend     finops-dashboard-xxx       1/1   Running
```

> **OpenCost (☸️ page):** The dashboard is pre-configured to talk to
> `http://opencost.opencost.svc.cluster.local:9003` (cost-model API port — not 9090 which is the UI).
> Deploy OpenCost after this step — see **Step 7b** below.
> The page renders immediately; cost data appears once OpenCost + Prometheus are running.

<details>
<summary><strong>Troubleshooting — Step 6</strong></summary>

**CrashLoopBackOff: `ModuleNotFoundError: No module named 'six'`** (platform-api)

Already fixed in `2-platform-api/requirements.txt` — `six` is listed explicitly. Rebuild the image if you see this on an older build.

---

**CrashLoopBackOff: `AzureChatOpenAI proxies validation error`** (ai-agent)

```
pydantic.v1.error_wrappers.ValidationError: Client.__init__() got an unexpected keyword argument 'proxies'
```
Already fixed — `langchain-openai==0.1.23` + `openai>=1.40.0` in `3-ai-agent/requirements.txt`. Rebuild the image if you see this.

---

**CrashLoopBackOff: `FATAL: no pg_hba.conf entry … no encryption`** (platform-api)

Azure PostgreSQL Flexible Server rejects unencrypted connections. Already fixed — `connect_args={"sslmode": "require"}` is in `2-platform-api/src/database.py`. Rebuild if you see this.

---

**CrashLoopBackOff: `FATAL: password authentication failed for user "pgadmin"`** (platform-api)

The K8s secret has a different password than what PostgreSQL has. Fix both:
```bash
# Reset DB password in Azure (single quotes required for passwords containing !)
az postgres flexible-server update \
  --resource-group rg-finops-prod-data \
  --name finops-pgflex \
  --admin-password 'AzFleX!admi9'

# Re-sync K8s secret from secrets.env
bash 1-infrastructure/scripts/apply-secrets.sh
kubectl rollout restart deployment/finops-platform-api -n platform
```

---

**Pod stuck in Pending: `Insufficient cpu` / node affinity mismatch**

The system nodepool node is out of CPU headroom. Check usage and options:
```bash
kubectl top nodes
kubectl top pods -A
```
Options: scale the node VM up, or reduce resource requests in the deployment manifests. The platform-api and dashboard both use `requests: cpu: 100m`.

---

**ImagePullBackOff 401 — images not pulling from ACR**

The kubelet identity is missing the AcrPull role. Re-assign:
```bash
ACR_ID=$(az acr show --name finopsacrmanmas --resource-group rg-finops-prod-core --query id -o tsv)
KUBELET_OID=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query "identityProfile.kubeletidentity.objectId" -o tsv)
az role assignment create --role AcrPull --assignee-object-id "$KUBELET_OID" \
  --assignee-principal-type ServicePrincipal --scope "$ACR_ID"
```

</details>

---

### Step 7 — Expose via Ingress + TLS (Let's Encrypt)

**Option A: kubectl port-forward (local/dev testing — no TLS needed)**

```bash
# Dashboard
kubectl port-forward -n frontend svc/finops-dashboard-svc 8501:80
# Open: http://localhost:8501

# Platform API (Swagger UI)
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80
# Open: http://localhost:8080/docs
```

---

**Option B: NGINX Ingress + Let's Encrypt TLS (production)**

TLS certificates are provisioned automatically by **cert-manager** using the
Let's Encrypt ACME protocol (HTTP-01 challenge). cert-manager watches Ingress
objects, requests a certificate from Let's Encrypt, stores it as a Kubernetes
Secret, and renews it ~30 days before expiry — no manual intervention needed.

```
Browser  →  HTTPS (port 443)  →  NGINX Ingress (TLS termination)
                                  cert-manager ←→ Let's Encrypt ACME
                                  (auto-renews every 60 days)
         →  HTTP (pod-to-pod, inside cluster)
```

#### 7a — Install NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.service.externalTrafficPolicy=Local
```

Get the public IP assigned to the LoadBalancer (takes ~2 minutes):
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller --watch
# Copy the EXTERNAL-IP once it appears (not <pending>)
```

#### 7b — Point DNS to the Ingress IP

In your DNS provider (wherever `manmas.online` is managed), create **A records**:

```
app.manmas.online   →  <EXTERNAL-IP>   # FinOps Dashboard (all pages, including ☸️ OpenCost)
api.manmas.online   →  <EXTERNAL-IP>   # Platform API
ai.manmas.online    →  <EXTERNAL-IP>   # AI Agent
```

> Let's Encrypt's HTTP-01 challenge requires DNS to resolve **before** you apply
> the Ingress with TLS. Wait for DNS propagation (`nslookup app.manmas.online`).



#### 7c — Install cert-manager

cert-manager handles certificate lifecycle automatically inside the cluster.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true \
  --version v1.15.0
```

Verify cert-manager pods are running:
```bash
kubectl get pods -n cert-manager
# Expected: cert-manager, cert-manager-cainjector, cert-manager-webhook — all Running
```

#### 7d — Create ClusterIssuers (staging first, then production)

Always test with **staging** first — Let's Encrypt production has strict rate limits
(5 failed certificates per domain per hour). Staging certs are not trusted by
browsers but are functionally identical.

```bash
kubectl apply -f k8s/ingress.yaml
```

The file `k8s/ingress.yaml` (included in this repo) contains:
- `ClusterIssuer` — letsencrypt-staging
- `ClusterIssuer` — letsencrypt-prod
- `Ingress` — dashboard (app.manmas.online) with TLS
- `Ingress` — Platform API (api.manmas.online) with TLS
- `Ingress` — AI Agent (ai.manmas.online) with TLS

**Test with staging first:**

Edit `k8s/ingress.yaml` — all three Ingress objects default to
`letsencrypt-staging`. Apply and wait for the certificate:

```bash
kubectl apply -f k8s/ingress.yaml

# Watch certificate status (takes 30-90 seconds)
kubectl get certificate -A --watch
# Wait for READY = True

# Inspect if it gets stuck
kubectl describe certificaterequest -n frontend
kubectl describe order -n frontend
```

Once staging works, switch to production:
```bash
# Change all occurrences of letsencrypt-staging → letsencrypt-prod in k8s/ingress.yaml
sed -i 's/letsencrypt-staging/letsencrypt-prod/g' k8s/ingress.yaml

# Delete the old staging certs so cert-manager re-issues them
kubectl delete secret finops-dashboard-tls    -n frontend
kubectl delete secret finops-platform-api-tls -n platform
kubectl delete secret finops-ai-agent-tls     -n ai

kubectl apply -f k8s/ingress.yaml
```

After ~60 seconds, your sites will have valid, browser-trusted HTTPS:
```
https://app.manmas.online   →  FinOps Dashboard
https://api.manmas.online   →  Platform API (Swagger at /docs)
https://ai.manmas.online    →  AI Agent health check
```

#### Certificate Renewal

cert-manager automatically renews certificates ~30 days before expiry (Let's
Encrypt certs are valid for 90 days). No action needed. To check renewal status:

```bash
kubectl get certificate -A
kubectl describe certificate finops-dashboard-tls -n frontend
```

<details>
<summary><strong>Troubleshooting — Step 7</strong></summary>

**`curl: (60) SSL certificate problem: unable to get local issuer certificate`**

You are on the staging certificate, which is not trusted by browsers or curl. This is expected when `letsencrypt-staging` is the issuer. Switch to production:
```bash
sed -i 's/letsencrypt-staging/letsencrypt-prod/g' k8s/ingress.yaml

kubectl delete secret finops-dashboard-tls    -n frontend
kubectl delete secret finops-platform-api-tls -n platform
kubectl delete secret finops-ai-agent-tls     -n ai

kubectl apply -f k8s/ingress.yaml
kubectl get certificate -A --watch   # wait for READY=True (~60s)
```

---

**Certificate stuck in Pending / not issuing**

cert-manager uses HTTP-01 challenge — it serves a token at `http://<domain>/.well-known/acme-challenge/<token>`. Requirements:
1. DNS must resolve to the NGINX ingress IP **before** applying the Ingress
2. Port 80 must be reachable from the internet (check Azure NSG on the AKS subnet)

Diagnose:
```bash
kubectl describe certificaterequest -n frontend
kubectl describe order -n frontend
kubectl describe challenge -n frontend
kubectl logs -n cert-manager -l app=cert-manager --tail=50

# Test HTTP-01 reachability
curl -v http://app.manmas.online/.well-known/acme-challenge/test
```

---

**Browser shows "Not Secure" even though certificate is Ready=True**

You're on the staging issuer. Staging certs are valid but not trusted by browsers by design. Follow the "switch to production" steps above.

</details>

---

### Step 7b — Install OpenCost + Prometheus (K8s Cost Allocation)

This wires up the ☸️ OpenCost page in the dashboard. Prometheus scrapes AKS node/pod metrics; OpenCost calculates per-namespace/workload/node costs and optionally ingests Azure billing export data for the ☁️ Cloud Costs tab.

#### 7b-1 — Install Prometheus

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace opencost --create-namespace \
  -f 4-dashboard/k8s/opencost-prometheus-values.yaml
kubectl rollout status deployment/prometheus-server -n opencost
```

#### 7b-2 — Install OpenCost

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update
helm install opencost opencost/opencost \
  --namespace opencost \
  -f 4-dashboard/k8s/opencost-helm-values.yaml
kubectl rollout status deployment/opencost -n opencost
```

Verify pods — all should be `Running`:
```bash
kubectl get pods -n opencost
```

K8s cost data (Namespaces, Workloads, Nodes, Savings tabs) appears within **5 minutes** of the first Prometheus scrape.

---

#### 7b-3 — Azure Integration (Rate Card pricing + ☁️ Cloud Costs)

Run the automation script — it handles both parts and is fully idempotent:

```bash
chmod +x 1-infrastructure/scripts/setup-opencost-azure.sh
./1-infrastructure/scripts/setup-opencost-azure.sh
```

**What it does:**

| Part | What | Result |
|---|---|---|
| A — Rate Card | Creates `OpenCostRateCardRole` custom role + `opencost-ratecard-sp` Service Principal | K8s secret `azure-service-key` in `opencost` ns |
| B — Cloud Costs | Creates storage account `finopsocexports`, daily Cost Management export, retrieves access key | K8s secret `cloud-costs` in `opencost` ns; `cloud-integration.json` written locally (gitignored) |

Run Part A only: `./setup-opencost-azure.sh --part-a`
Run Part B only: `./setup-opencost-azure.sh --part-b`

> **Note:** Part B registers the `Microsoft.CostManagementExports` resource provider automatically if not already registered. This can take ~60 seconds.

After the script finishes, update `AZURE_CLIENT_ID` in the helm values:

```bash
# Get your managed identity client ID
az identity show --name mi-finops-prod \
  --resource-group rg-finops-prod-core \
  --query clientId -o tsv
```

Edit `4-dashboard/k8s/opencost-helm-values.yaml`:
```yaml
opencost:
  exporter:
    extraEnv:
      AZURE_CLIENT_ID: "<paste-client-id-here>"
```

Then upgrade OpenCost to apply all secrets:
```bash
helm upgrade opencost opencost/opencost \
  --namespace opencost \
  -f 4-dashboard/k8s/opencost-helm-values.yaml
kubectl rollout restart deployment/opencost -n opencost
```

Confirm Azure integration is active:
```bash
kubectl logs -n opencost -l app=opencost --tail=50 | grep -i "cloud costs"
# Expected: Cloud Costs enabled: true
```

> **Cloud Costs tab data:** The first billing export run is triggered automatically by the script. Data appears in the ☁️ Cloud Costs tab within **15–30 minutes** of the first export completing.

---

<details>
<summary><strong>Troubleshooting — Step 7b</strong></summary>

**`Cloud Costs enabled: false` in OpenCost logs**

`cloudCost.enabled` must be nested under `opencost:` in the helm values — not at the root level:
```yaml
# WRONG (root level — ignored by the chart)
cloudCost:
  enabled: true

# CORRECT (under opencost:)
opencost:
  cloudCost:
    enabled: true
```
Fix the values file and run `helm upgrade`.

---

**`json: cannot unmarshal number into Go struct field EnvVar...env.name`**

`extraEnv` in the OpenCost helm chart is a **map**, not a list. Use:
```yaml
# CORRECT
extraEnv:
  AZURE_CLIENT_ID: "your-uuid"

# WRONG
extraEnv:
  - name: AZURE_CLIENT_ID
    value: "your-uuid"
```
If the deployment is already corrupted in the cluster, delete it first then reinstall:
```bash
kubectl delete deployment opencost -n opencost
helm upgrade --install opencost opencost/opencost \
  --namespace opencost \
  -f 4-dashboard/k8s/opencost-helm-values.yaml
```

---

**`volumeMounts[x].name: Not found` on helm upgrade**

The OpenCost helm chart does not support `extraVolumes` — volume mounts added via `extraVolumeMounts` will have no matching volume. Remove `extraVolumeMounts` from the helm values entirely. Use `AZURE_CLIENT_ID` in `extraEnv` for Managed Identity auth (no file mount needed).

---

**`(400) RP Not Registered. Register destination storage account subscription with Microsoft.CostManagementExports`**

The resource provider is not registered. The `setup-opencost-azure.sh` script registers it automatically (step B2.5). If running manually:
```bash
az provider register --namespace Microsoft.CostManagementExports
# Wait ~60 s then retry
az provider show --namespace Microsoft.CostManagementExports --query registrationState -o tsv
```

---

**`Identity not found` / Rate Card URL has empty subscription ID (`subscriptions//providers`)**

The managed identity client ID set in `AZURE_CLIENT_ID` is the control-plane identity, not accessible from pod IMDS. OpenCost automatically falls back to the **Azure Retail Prices API** (public, no auth) and successfully retrieves pricing. This is non-critical — pricing still works, just uses public rates rather than your negotiated Rate Card.

To fix properly: add `AZURE_SUBSCRIPTION_ID` to `extraEnv` in helm values and set up Workload Identity for the `opencost` service account (federated credential linking `opencost/opencost` SA to `mi-finops-prod`).

---

**☁️ Cloud Costs tab shows setup instructions (data not appearing)**

Check in order:
1. Confirm `Cloud Costs enabled: true` in logs (see above)
2. Check if billing export data has landed in storage:
   ```bash
   az storage blob list \
     --account-name finopsocexports \
     --container-name cost-exports \
     --query "[].name" -o table
   ```
   If empty, wait 15–30 minutes for the first export run to complete.
3. Check OpenCost logs for cloud cost ingestion errors:
   ```bash
   kubectl logs -n opencost -l app=opencost --tail=100 | \
     grep -iE "cloud|integrat|storage|blob"
   ```

---

**Pod `opencost` in CrashLoopBackOff**

Check Prometheus is reachable:
```bash
kubectl logs -n opencost deployment/opencost --tail=50
kubectl get svc prometheus-server -n opencost
```

---

**No K8s cost data (OpenCost Online but $0)**

Wait 5–10 minutes for Prometheus initial scrape. Check targets:
```bash
kubectl port-forward svc/prometheus-server 9090:80 -n opencost
# Open http://localhost:9090/targets — all targets should be UP
```

---

**`KeyError: 'total_cost'` on OpenCost page**

Rebuild the dashboard image (fixed in `5_OpenCost.py`):
```bash
az acr login --name finopsacrmanmas
docker buildx build --platform linux/amd64 --push \
  -t finopsacrmanmas.azurecr.io/finops-dashboard:latest 4-dashboard/
kubectl rollout restart deployment/finops-dashboard -n frontend
```

---

**OpenCost API returning HTML instead of JSON**

The dashboard is connecting to port 9090 (UI) instead of 9003 (cost-model API). Verify `OPENCOST_URL` in `4-dashboard/k8s/deployment.yaml`:
```yaml
- name: OPENCOST_URL
  value: "http://opencost.opencost.svc.cluster.local:9003"   # API port — not 9090
```

</details>

---

### Step 8 — First Login & Initial Sync

1. Open the dashboard (`https://app.manmas.online` or `http://localhost:8501` via port-forward)
2. Log in with the credentials from `users.yaml` — the **YAML key** is the login username, not the `name:` field:
   ```
   username: admin          ← the key in users.yaml, e.g.  admin:
   password: <your value>   ← the password: field
   ```
   The `name:` field (e.g. `finaiadmin`) is the display name shown in the sidebar after login — it is not used for authentication.
3. Click **🔄 Sync All Data** in the sidebar — this pulls 30 days of data from Azure (takes 1-3 minutes)
4. Navigate to **Costs**, **Resources**, **Advisor** pages to verify data
5. Open **AI Chat** and ask: *"What are my top 5 spending services this month?"*

<details>
<summary><strong>Troubleshooting — Step 8</strong></summary>

**Login: "Invalid credentials" — using the display name instead of the username**

The `name:` field in `users.yaml` is the display name shown in the sidebar after login. The **login username** is the YAML key above it:
```yaml
users:
  admin:            # ← type this in the Username field
    name: "finaiadmin"   # ← this is NOT the username
```
Always use the key (`admin`, `viewer`, etc.) as the username, not the `name` value.

---

**Login: "Invalid credentials" after a `kubectl rollout restart`**

`kubectl port-forward` tunnels to a specific pod at the time it is started. After a deployment restart, the old tunnel points at the terminated pod. Kill and restart:
```bash
pkill -f "port-forward"
kubectl port-forward -n frontend svc/finops-dashboard-svc 8501:80
```
Then open `http://localhost:8501` in an **incognito window** (clears stale Streamlit websocket state).

---

**Login: "Invalid credentials" and you are sure the password is correct**

Verify what the pod actually reads from its mounted `users.yaml`:
```bash
kubectl exec -n frontend \
  $(kubectl get pod -n frontend -l app=finops-dashboard -o jsonpath='{.items[0].metadata.name}') \
  -- python3 -c "
import yaml, bcrypt
from pathlib import Path
data = yaml.safe_load(Path('/app/src/users.yaml').read_bytes().decode())
stored = data['users']['admin']['password']
test_pw = 'YOUR_PASSWORD'
print('stored:', repr(stored))
print('plaintext match:', stored == test_pw)
"
```
If `plaintext match: False`, recreate the secret with the correct password:
```bash
kubectl delete secret finops-dashboard-users -n frontend
kubectl create secret generic finops-dashboard-users \
  --from-file=users.yaml=4-dashboard/src/users.yaml -n frontend
kubectl rollout restart deployment/finops-dashboard -n frontend
```

</details>

---

### Step 9 — Sanity Check

After the full deployment, run the sanity check script to verify every component is healthy:

```bash
chmod +x sanity-check/sanity.sh
./sanity-check/sanity.sh
```

The script checks (in order):

| Check | What it tests |
|---|---|
| 1. kubectl connectivity | Can reach the AKS API server |
| 2. Pod health | All 3 pods Running + Ready (platform, ai, frontend namespaces) |
| 3. Ingress + TLS | Ingress objects exist; cert-manager certs are Ready and not expired |
| 4. Platform API health | `/health` endpoint responds (external URL or in-cluster exec) |
| 5. AI Agent health | `/health` endpoint responds (external URL or in-cluster exec) |
| 6. Dashboard reachability | Dashboard URL returns HTTP 200/302 |
| 7. Platform API logs | Last 20 lines shown; flags password/SSL errors automatically |

**Expected passing output:**

```
[PASS] kubectl can reach the cluster
[PASS] Platform API  (namespace: platform, status: Running)
[PASS] AI Agent      (namespace: ai, status: Running)
[PASS] Dashboard     (namespace: frontend, status: Running)
[PASS] Ingress finops-dashboard-ingress (ns: frontend) exists
[PASS] TLS cert finops-dashboard-tls (ns: frontend) — Ready, expires: 2025-08-13T...
[PASS] Platform API health OK via https://api.manmas.online/health
[PASS] AI Agent health OK via https://ai.manmas.online/health
[PASS] Dashboard reachable at https://app.manmas.online (HTTP 200)
============================================================
  All checks passed.
============================================================
```

**Override URLs** if you use different domains or port-forward:
```bash
DASHBOARD_URL=http://localhost:8501 \
API_URL=http://localhost:8080 \
AI_URL=http://localhost:8000 \
./sanity-check/sanity.sh
```

<details>
<summary><strong>Troubleshooting — Step 9 (Sanity Check)</strong></summary>

**`[FAIL] kubectl cannot reach the cluster`**

Your kubeconfig is stale or missing:
```bash
az aks get-credentials --name finops-aks --resource-group rg-finops-prod-core --overwrite-existing
kubectl cluster-info
```

---

**`[FAIL] Platform API — status: CrashLoopBackOff`**

Check which error is causing the crash:
```bash
kubectl logs -n platform -l app=finops-platform-api --tail=50 --previous
```
Common causes and fixes are documented in [Troubleshooting — Step 6](#step-6--deploy-to-aks).

---

**`[FAIL] TLS cert not Ready`**

cert-manager is still issuing or the HTTP-01 challenge failed:
```bash
kubectl describe certificate finops-dashboard-tls -n frontend
kubectl describe certificaterequest -n frontend
kubectl describe order -n frontend
kubectl logs -n cert-manager -l app=cert-manager --tail=30
```
Ensure DNS resolves to the ingress IP and port 80 is open.

---

**`[FAIL] Dashboard returned HTTP 000`**

The NGINX Ingress LoadBalancer IP may have changed, or DNS is pointing to the wrong IP:
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
# Compare EXTERNAL-IP with your DNS A record
nslookup app.manmas.online
```

</details>

---

## Dashboard Pages & Features

| Page | Icon | Description |
|---|---|---|
| Home | ⚡ | KPI cards, Cost Summary, Savings Summary, Sankey cost flow, daily trend with anomaly detection, efficiency scorecard |
| Costs | 💰 | 8 tabs: Daily Trend, By Service, By Subscription, By RG, Storage, Network, Savings Leaderboard, MoM Comparison |
| Resources | 🖥️ | Inventory with type/location/RG filters; type drill-down (see every resource by type); Watch List (idle/orphaned); untagged report |
| Advisor | 💡 | 7-tab intelligence centre: Priority Matrix, All Recs, Savings Leaderboard, By RG, Rightsizing, Advisor Score radar, 12-month ROI |
| AI Chat | 🤖 | Context-aware Q&A; Explain the Bill prompts; Optimization tips — backed by live Platform API data |
| Settings | ⚙️ | Manual sync, email alert testing, system health (admin only) |
| OpenCost | ☸️ | K8s cost allocation + Azure cloud billing; 8 tabs: Overview, Namespaces, Workloads, Nodes, Storage, Labels/Chargeback, ☁️ Cloud Costs, Savings |

### Home Page — What Each Section Does

| Section | What it shows |
|---|---|
| 5 KPI Cards | Total Spend, Previous Period, Avg Daily, Savings Potential, Budget % (or Days in Period) |
| Cost Summary | Large billed cost + period change % + Current/Previous/Projected horizontal bars |
| Savings Summary | Total savings available (large) + High/Medium/Low impact bars with rec counts |
| Budget Tracker | Progress bar + spent/budget/remaining/% used (shown only when a budget is set in the sidebar) |
| Daily Trend + Forecast | Trend chart with 7-day rolling avg + anomaly spikes; linear forecast for month-end projected total |
| Cost Flow Sankey | How spend flows: Total → 6 categories (Compute/Storage/Network/Database/Monitor & Security/Other) → top 8 services |
| Top Services + Distribution | Horizontal bar with share % + donut chart |
| Cost by Category | Bar chart — hover for category definitions (what services are included) |
| Advisor Opportunities | Impact cards showing count + savings; expandable list of the actual recommendation titles |
| Efficiency Scorecard | Tag compliance %, untagged resource count, waste grade (A–F) based on open Advisor recs + tag gap |

### Costs Page — 8 Tabs

| Tab | Key feature |
|---|---|
| Daily Trend | Line/Bar/Area chart, 7-day rolling avg, anomaly detection (mean + 2σ), spike warning banner |
| By Service | Horizontal bar + pie/treemap, share % column, CSV/Excel download |
| By Subscription | Pie/Bar/Treemap, subscription names resolved from UUIDs |
| By Resource Group | Bar/Treemap by resource group |
| Storage | Filtered: Storage Accounts, Blob, Disk, Backup, Data Lake — with % of total spend |
| Network | Filtered: Bandwidth, VNet, CDN, VPN, Load Balancer, Firewall — with % of total spend |
| Savings Leaderboard | All services ranked, share %, cumulative % (find your Pareto 80/20 line) |
| **MoM Comparison** | Current period vs previous equivalent period per category — grouped bar + per-category change metrics |

### AI Chat — v1.1 Features

| Feature | Description |
|---|---|
| Dashboard Context | Fetches current period spend + top 5 services + Advisor savings and sends as AI context automatically |
| Context Inspector | Expandable "📡 Context being sent to AI" panel so you can verify what the AI knows |
| Explain the Bill | Tab of prompts for explaining Azure billing items (Bandwidth, Monitor, Backup, Reserved Instances…) |
| `explain_azure_service` tool | Agent has built-in plain-English explanations for 20+ Azure billing line items |
| Tool Visibility | Each AI response shows which Platform API tools were called |
| Organized Suggestions | Three tabs: Cost Analysis / Explain the Bill / Optimization |

---

## API Reference

The Platform API runs at `http://finops-platform-api-svc.platform.svc.cluster.local` (internal) or `api.manmas.online` (external). Full Swagger docs at `/docs`.

### Cost Endpoints

| Method | Path | Query Params | Description |
|---|---|---|---|
| GET | `/costs/summary` | `days=30` | Total + previous period + % change |
| GET | `/costs/daily` | `days`, `subscription_id` | Per-day spend |
| GET | `/costs/by-service` | `days`, `limit=20`, `subscription_id` | Top services |
| GET | `/costs/by-subscription` | `days` | Per-subscription spend |
| GET | `/costs/by-resource-group` | `days`, `limit=20`, `subscription_id` | Per-RG spend |
| GET | `/costs/trend` | `days`, `subscription_id` | Alias for `/costs/daily` |

### Sync Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/sync/subscriptions` | Pull subscription list |
| POST | `/sync/costs?days=30` | Pull cost data from Cost Management |
| POST | `/sync/resources` | Pull resource inventory from Resource Graph |
| POST | `/sync/advisor` | Pull Advisor Cost recommendations |
| POST | `/sync/all?days=30` | Run all four syncs in sequence |

### Alert Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/alerts/test` | Send test email |
| POST | `/alerts/cost-spike` | Send cost spike alert |
| POST | `/alerts/budget` | Send budget threshold alert |
| POST | `/alerts/digest?days=1` | Send daily cost digest |

---

## AI Agent

The AI Agent (v1.1) exposes two endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Returns status, model name, and version |
| POST | `/chat` | Chat with the FinOps AI |

**Chat request format (v1.1 — with optional dashboard context):**
```json
{
  "messages": [
    {"role": "user", "content": "What are my top 3 spending services this week?"}
  ],
  "context": "Total spend: $1,234.56 USD\nTime range: Last 30 days\nTop service: Azure Kubernetes Service: $456.78"
}
```

The `context` field is optional. When provided, it is injected into the agent's system prompt so it can answer without making redundant tool calls for data the dashboard already fetched.

**Chat response format:**
```json
{
  "response": "Your top 3 spending services in the last 7 days are: 1. Azure Kubernetes Service ($245.30)...",
  "tool_calls": ["get_top_services", "get_cost_summary"]
}
```

**Available tools (v1.1 — 9 tools):**

| Tool | Description |
|---|---|
| `get_cost_summary` | Total + previous period + % change |
| `get_top_services` | Top services by cost (up to 15) |
| `get_cost_trend` | Daily cost data for anomaly and trend queries |
| `get_advisor_recommendations` | Recommendations by impact level |
| `get_all_advisor_recommendations` | All recommendations regardless of impact |
| `get_resource_list` | Resource inventory, optional type filter |
| `get_cost_by_subscription` | Per-subscription breakdown |
| `get_cost_by_resource_group` | Per-RG breakdown |
| `explain_azure_service` | Plain-English explanation of any Azure billing line item |

The agent uses a **LangGraph ReAct loop** — it calls tools until it has enough data to answer, then synthesises a final response with cited numbers. The system prompt includes built-in billing knowledge for 20+ Azure services, covering common finance-team questions like "why did my bill spike on the 1st?" (Reserved Instance amortization) or "what are Bandwidth charges?" (egress fees).

---

## Cost Estimates

Running this platform on the chosen SKUs costs approximately:

| Resource | SKU | Est. Monthly Cost |
|---|---|---|
| AKS (1 node) | Standard_B2als_v2 | ~$30 |
| PostgreSQL | Standard_B1ms | ~$15 |
| Azure OpenAI | gpt-4.1-nano | ~$1-5 (usage-based) |
| ACR | Basic | ~$5 |
| Key Vault | Standard | <$1 |
| VNet / DNS | — | ~$2 |
| Prometheus | 8 Gi PVC + ~100m CPU | ~$3-5/month |
| OpenCost | ~50m CPU / 64 Mi | <$1/month |
| **Total** | | **~$60-65/month** |

Adding a Spot node pool for the AI agent can reduce costs further. The AKS free tier is used (no SLA charge).
OpenCost is free and open-source; the only added cost is the Prometheus persistent volume for storing K8s metrics.

---

## Troubleshooting

> Each component has a dedicated, comprehensive troubleshooting guide. Start with the guide for the component that is failing:

| Component | Guide | Covers |
|---|---|---|
| Infrastructure | [1-infrastructure/TROUBLESHOOTING.md](1-infrastructure/TROUBLESHOOTING.md) | `setup.sh` failures, Workload Identity, TLS/cert-manager, cost sync roles |
| Platform API | [2-platform-api/TROUBLESHOOTING.md](2-platform-api/TROUBLESHOOTING.md) | CrashLoopBackOff, DB connection, data sync 0 rows, email notifications |
| AI Agent | [3-ai-agent/TROUBLESHOOTING.md](3-ai-agent/TROUBLESHOOTING.md) | OpenAI auth, tool errors, context not working, LangChain version conflicts |
| Dashboard | [4-dashboard/TROUBLESHOOTING.md](4-dashboard/TROUBLESHOOTING.md) | Login failures, data not showing, Docker build, TLS, AI chat offline |
| OpenCost | [4-dashboard/TROUBLESHOOTING.md](4-dashboard/TROUBLESHOOTING.md) | Pod crash, Prometheus unreachable, no cost data, KeyError in dashboard |

Step-specific troubleshooting (inline `<details>` blocks) also appears after each setup step above.

### Quick Reference — Most Common Issues

| Symptom | Most Likely Cause | Fix |
|---|---|---|
| Pod `CrashLoopBackOff` (platform-api) | Wrong DB password in K8s secret | See [2-platform-api/TROUBLESHOOTING.md](2-platform-api/TROUBLESHOOTING.md) |
| "Invalid credentials" on login | Using `name:` field instead of YAML key | See [4-dashboard/TROUBLESHOOTING.md](4-dashboard/TROUBLESHOOTING.md) |
| Cost data shows $0 after sync | MI missing `Cost Management Reader` role | See [1-infrastructure/TROUBLESHOOTING.md](1-infrastructure/TROUBLESHOOTING.md) |
| AI chat says "Agent: Offline" | AI agent pod not running or wrong URL | See [3-ai-agent/TROUBLESHOOTING.md](3-ai-agent/TROUBLESHOOTING.md) |
| Sankey chart `ValueError: Invalid color` | 8-digit hex in Plotly link colors | Fixed in current `Home.py` — rebuild dashboard image |
| Certificate stuck in Pending | DNS not propagated before Ingress applied | See [1-infrastructure/TROUBLESHOOTING.md](1-infrastructure/TROUBLESHOOTING.md) |

### General Pod Diagnostics

```bash
# Any namespace, any pod
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --tail=100
kubectl logs <pod-name> -n <namespace> --previous   # logs of last crash

# Check secrets are present
kubectl get secrets -A | grep finops

# Check service account annotations (Workload Identity)
kubectl get sa -n platform cost-platform-sa -o yaml | grep azure.workload
kubectl get sa -n ai cost-ai-sa -o yaml | grep azure.workload
```
