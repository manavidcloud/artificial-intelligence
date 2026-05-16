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
   - [Step 8 — First Login & Initial Sync](#step-8--first-login--initial-sync)
7. [Dashboard Pages](#dashboard-pages)
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
┌──────────────────────────────────────────────────────────────────┐
│                        Internet / Users                          │
└──────────────────┬───────────────────────────────────────────────┘
                   │  HTTPS   app.manmas.online
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AKS Ingress Controller                        │
│              (nginx / AGIC — with TLS termination)               │
└───────┬──────────────────────┬───────────────────────────────────┘
        │                      │
        ▼ frontend ns           ▼ platform / ai ns
┌──────────────────┐   ┌──────────────────────┐  ┌───────────────┐
│   4-Dashboard    │   │  2-Platform API       │  │  3-AI Agent   │
│  (Streamlit)     │──▶│  (FastAPI / uvicorn)  │  │  (LangGraph)  │
│  port 8501       │   │  port 8080            │  │  port 8000    │
│  namespace:      │   │  namespace: platform  │  │  namespace:ai │
│   frontend       │   │                       │  │               │
└──────────────────┘   └──────────┬────────────┘  └──────┬────────┘
        │                         │                       │
        │  /chat POST             │                       │
        └────────────────────────▶│◀──────────────────────┘
                                  │ (AI agent calls Platform API)
                    ┌─────────────▼──────────────┐
                    │   PostgreSQL Flexible Server│
                    │   (private VNet, port 5432) │
                    │   Tables:                   │
                    │   • cost_records            │
                    │   • resources               │
                    │   • advisor_recommendations │
                    │   • subscriptions           │
                    └────────────────────────────┘

Azure Services Used:
  ┌──────────────────────────────────────────────────────────────┐
  │  Azure Cost Management   →  billing data (ActualCost API)    │
  │  Azure Resource Graph    →  resource inventory (KQL)         │
  │  Azure Advisor           →  Cost recommendations             │
  │  Azure OpenAI            →  gpt-4.1-nano (AI chat)           │
  │  Azure Container Registry→  Docker image storage             │
  │  Azure Key Vault         →  secret management (RBAC)         │
  │  Managed Identity        →  passwordless auth to Azure APIs  │
  └──────────────────────────────────────────────────────────────┘

Identity & Auth Flow:
  AKS Pod  →  OIDC Token  →  Entra ID  →  Managed Identity
                                          (Cost Mgmt Reader +
                                           Resource Graph Reader +
                                           Key Vault Secrets User +
                                           OpenAI User)
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
├── 1-infrastructure/
│   └── scripts/
│       ├── setup.sh                 # Full Azure infrastructure provisioner
│       └── apply-secrets.sh         # K8s namespaces, secrets, service accounts
│
├── 2-platform-api/                  # FastAPI backend — data sync & REST API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── k8s/
│   │   └── deployment.yaml          # Namespace, Deployment, Service, HPA
│   └── src/
│       ├── main.py                  # All API endpoints
│       ├── database.py              # SQLAlchemy engine + session
│       ├── models.py                # ORM models (4 tables)
│       ├── notifications.py         # Email alerts (cost spikes, digests, budgets)
│       └── providers/
│           ├── base.py              # Abstract CloudProvider interface
│           └── azure.py             # Azure implementation (Cost Mgmt, RG, Advisor)
│
├── 3-ai-agent/                      # LangGraph ReAct agent — natural language Q&A
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── k8s/
│   │   └── deployment.yaml          # Namespace, SA, Deployment, Service
│   └── src/
│       └── main.py                  # FastAPI wrapper + LangGraph agent + tools
│
└── 4-dashboard/                     # Streamlit multi-page dashboard
    ├── Dockerfile
    ├── requirements.txt
    ├── k8s/
    │   └── deployment.yaml          # Namespace, Deployment, Service
    └── src/
        ├── Home.py                  # Overview: KPIs, daily trend, top services
        ├── auth.py                  # Login wall, bcrypt auth, sidebar user chip
        ├── users.yaml.template      # Copy → users.yaml and fill in
        ├── .streamlit/
        │   └── config.toml          # Dark theme, server settings
        ├── pages/
        │   ├── 1_Costs.py           # Full cost analysis (trend, service, RG, sub)
        │   ├── 2_Resources.py       # Resource inventory (type, location breakdown)
        │   ├── 3_Advisor.py         # Advisor recommendations with savings cards
        │   ├── 4_AI_Chat.py         # AI assistant chat interface
        │   └── 5_Settings.py        # Admin: manual sync, email tests, health
        └── utils/
            ├── api.py               # HTTP client for Platform API + AI Agent
            └── theme.py             # Dark CSS + Plotly dark template
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
app.manmas.online   →  <EXTERNAL-IP>
api.manmas.online   →  <EXTERNAL-IP>
ai.manmas.online    →  <EXTERNAL-IP>
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

---

### Step 8 — First Login & Initial Sync

1. Open the dashboard (e.g., `http://localhost:8501`)
2. Log in with the credentials from `users.yaml` (default: `admin` / `changeme-use-strong-password`)
3. Click **🔄 Sync All Data** in the sidebar — this pulls 30 days of data from Azure (takes 1-3 minutes)
4. Navigate to **Costs**, **Resources**, **Advisor** pages to verify data
5. Open **AI Chat** and ask: *"What are my top 5 spending services this month?"*

---

## Dashboard Pages

| Page | Icon | Description |
|---|---|---|
| Home | ⚡ | KPI summary, daily trend chart, top 5 services, Advisor summary |
| Costs | 💰 | Full analysis: daily/service/subscription/resource-group breakdowns |
| Resources | 🖥️ | Resource inventory with type/location/RG filters |
| Advisor | 💡 | Cost optimization recommendations with savings potential |
| AI Chat | 🤖 | Natural language Q&A backed by live cost data |
| Settings | ⚙️ | Manual sync, email alert testing, system health (admin only) |

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

The AI Agent exposes two endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Returns status and model name |
| POST | `/chat` | Chat with the FinOps AI |

**Chat request format:**
```json
{
  "messages": [
    {"role": "user", "content": "What are my top 3 spending services this week?"}
  ]
}
```

**Chat response format:**
```json
{
  "response": "Your top 3 spending services in the last 7 days are: 1. Azure Kubernetes Service ($245.30)...",
  "tool_calls": ["get_top_services", "get_cost_summary"]
}
```

The agent has access to 6 tools that call the Platform API. It uses a ReAct loop to gather data before answering.

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
| **Total** | | **~$55-60/month** |

Adding a Spot node pool for the AI agent can reduce costs further. The AKS free tier is used (no SLA charge).

---

## Troubleshooting

### Pod not starting

```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
```

### Platform API returns 503 (DB error)

1. Check PostgreSQL is accessible from AKS subnet
2. Verify `DB_HOST`, `DB_USER`, `DB_PASSWORD` in the secret: `kubectl get secret finops-platform-secret -n platform -o yaml`
3. Check private DNS resolution: `kubectl run -it --rm debug --image=busybox -- nslookup finops-pgflex.postgres.database.azure.com`

### Cost sync returns 0 rows

1. Ensure `AZURE_SUBSCRIPTION_IDS` is set correctly
2. Verify the Managed Identity has `Cost Management Reader` role on the subscription
3. Check that data exists in Azure Cost Management (new subscriptions may have a 24-48h delay)

### AI Agent chat fails

1. Check AI Agent pod is Running: `kubectl get pods -n ai`
2. Verify `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT` in `finops-ai-secret`
3. Test agent health: `kubectl port-forward -n ai svc/finops-ai-agent-svc 8000:80` then `curl http://localhost:8000/health`

### Workload Identity not working

```bash
# Check OIDC issuer is set on AKS
az aks show --name finops-aks --resource-group rg-finops-prod-core --query oidcIssuerProfile.issuerUrl -o tsv

# Check federated credentials exist
az identity federated-credential list --identity-name mi-finops-prod --resource-group rg-finops-prod-core

# Check service account annotation
kubectl get sa cost-platform-sa -n platform -o yaml | grep azure.workload
```

### Images not pulling from ACR

```bash
# Re-grant AcrPull to AKS kubelet identity (setup.sh uses direct role assignment, not az aks update)
ACR_ID=$(az acr show --name finopsacrmanmas --resource-group rg-finops-prod-core --query id -o tsv)
KUBELET_OID=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query "identityProfile.kubeletidentity.objectId" -o tsv)
az role assignment create --role AcrPull --assignee-object-id "$KUBELET_OID" \
  --assignee-principal-type ServicePrincipal --scope "$ACR_ID"
```

### TLS certificate stuck in Pending / not issuing

cert-manager uses HTTP-01 challenge — it temporarily serves a token at
`http://<domain>/.well-known/acme-challenge/<token>`. This requires:

1. DNS resolves to the NGINX ingress external IP **before** applying TLS Ingress
2. Port 80 is reachable from the internet (check Azure NSG on the node subnet)
3. cert-manager pods are healthy

```bash
# See what cert-manager is doing
kubectl describe certificaterequest -n frontend
kubectl describe order -n frontend
kubectl describe challenge -n frontend

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=50

# Verify HTTP-01 challenge is reachable from outside
curl -v http://app.manmas.online/.well-known/acme-challenge/test
```

Common causes:
- DNS not propagated yet → wait and retry
- NSG blocking port 80 → add inbound rule for port 80 on `rg-finops-prod-network`
- Rate limit hit on production issuer → use staging issuer to test, switch to prod once working

### Certificate shows Ready=True but browser still shows "Not Secure"

You tested with `letsencrypt-staging` — staging certs are not browser-trusted by design.
Delete the staging secret and switch to `letsencrypt-prod`:

```bash
sed -i 's/letsencrypt-staging/letsencrypt-prod/g' k8s/ingress.yaml
kubectl delete secret finops-dashboard-tls -n frontend
kubectl apply -f k8s/ingress.yaml
```

---

### CrashLoopBackOff: `ModuleNotFoundError: No module named 'six'`

**Symptom:** platform-api pod crashes immediately on startup with:
```
File "...azure/mgmt/resourcegraph/models/_resource_graph_client_enums.py"
ModuleNotFoundError: No module named 'six'
```

**Cause:** `azure-mgmt-resourcegraph==8.0.0` has a transitive dependency on `six` (a Python 2/3 compat library) that is not declared in its own package metadata.

**Fix:** Already applied — `six` is explicitly listed in `2-platform-api/requirements.txt`. No action needed on a fresh build from this repo.

---

### CrashLoopBackOff: `AzureChatOpenAI proxies validation error`

**Symptom:** ai-agent pod crashes with:
```
pydantic.v1.error_wrappers.ValidationError: 1 validation error for AzureChatOpenAI
__root__
  Client.__init__() got an unexpected keyword argument 'proxies'
```

**Cause:** `langchain-openai<0.1.9` passes `proxies=None` to the `openai` client constructor. `openai>=1.0.0` does not accept a `proxies` kwarg — it was removed in the 1.x rewrite. Additionally, `langchain-openai>=0.1.20` requires `openai>=1.40.0`.

**Fix:** Already applied in `3-ai-agent/requirements.txt`:
```
langchain==0.2.16
langchain-openai==0.1.23
langgraph==0.2.14
openai>=1.40.0,<2.0.0
```
No action needed on a fresh build from this repo.

---

### CrashLoopBackOff: `PostgreSQL — FATAL: no pg_hba.conf entry … no encryption`

**Symptom:** platform-api pod crashes with:
```
FATAL:  no pg_hba.conf entry for host "10.0.2.x", user "pgadmin",
        database "finops-db", no encryption
```

**Cause:** Azure PostgreSQL Flexible Server rejects connections that are not encrypted with SSL. The SQLAlchemy engine was not passing `sslmode=require`.

**Fix:** Already applied in `2-platform-api/src/database.py`:
```python
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"}, ...)
```
No action needed on a fresh build from this repo.

---

### CrashLoopBackOff: `PostgreSQL — FATAL: password authentication failed`

**Symptom:** platform-api pod crashes with:
```
FATAL:  password authentication failed for user "pgadmin"
```

**Cause:** The `DB_PASSWORD` in the Kubernetes secret does not match the actual PostgreSQL admin password. This happens when `apply-secrets.sh` was run before `secrets.env` had the correct password, or when the PostgreSQL password was reset separately.

**Fix:**

1. Verify what password is in the K8s secret:
   ```bash
   kubectl get secret finops-platform-secret -n platform \
     -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo
   ```

2. If it does not match, reset the PostgreSQL password to match `secrets.env`, then re-sync the secret:
   ```bash
   # Reset DB password in Azure (use single quotes — see note below)
   az postgres flexible-server update \
     --resource-group rg-finops-prod-data \
     --name finops-pgflex \
     --admin-password 'AzFleX!admi9'

   # Re-sync K8s secrets from secrets.env
   bash 1-infrastructure/scripts/apply-secrets.sh

   # Restart the deployment
   kubectl rollout restart deployment/finops-platform-api -n platform
   ```

> **Bash tip:** Passwords containing `!` must be wrapped in **single quotes** in bash. Double quotes cause `bash: !xxx: event not found` because `!` triggers history expansion. Always use `'password'` not `"password"` when passing passwords on the command line.

---

### Docker build: `AUTH_*` variable warning / BuildKit lint error

**Symptom:** `docker buildx build` for the dashboard fails or warns:
```
SecretsUsedInArgOrEnv: Do not use ARG or ENV instructions for sensitive data (ENV "AUTH_MODE")
```

**Cause:** Docker BuildKit treats any env var containing `AUTH` in the name as potentially sensitive and lints against it in `ENV` instructions.

**Fix:** Already applied — `ENV AUTH_MODE=local` was removed from `4-dashboard/Dockerfile`. The app already defaults to `local` via `os.getenv("AUTH_MODE", "local")`. `AUTH_MODE` is injected at runtime via the Kubernetes manifest (`4-dashboard/k8s/deployment.yaml`) as a plain `env` value, not via the image.

---

### Pod stuck in Pending: `Insufficient cpu` / `node(s) didn't match node affinity`

**Symptom:**
```
0/2 nodes are available: 1 Insufficient cpu,
1 node(s) didn't match Pod's node affinity/selector.
```

**Cause:** The system nodepool node has run out of CPU headroom for new pods.

**Fix options:**

Option A — Scale up the system nodepool node to a larger VM (requires cluster recreation or node pool update):
```bash
az aks nodepool update \
  --cluster-name finops-aks \
  --resource-group rg-finops-prod-core \
  --name nodepool1 \
  --node-vm-size Standard_B4als_v2
```

Option B — Move workloads to the `apppool` ARM node by removing the `nodeSelector` from their manifests (only for multi-arch images).

Option C — Check what is consuming CPU and reduce limits:
```bash
kubectl top nodes
kubectl top pods -A
```

The platform-api and dashboard deployments use `requests: cpu: 100m` — if the node is still exhausted, an KEDA-scaled or rogue pod may be consuming spare capacity.

---

### `az postgres flexible-server` fails with module error

**Symptom:**
```
No module named 'azure.mgmt.rdbms.mysql_flexibleservers'
```

**Cause:** The Azure CLI's `rdbms` extension is installed but has a broken Python dependency (common after partial upgrades).

**Fix:** Reinstall the Azure CLI from scratch:
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```
Then re-login: `az login`.
