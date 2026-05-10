# LAB 1 — Foundation & Authentication Layer

Goal of this lab:

# Build the secure Azure-native platform foundation

After this lab you will have:

✅ Azure infrastructure baseline
✅ AKS cluster
✅ Container registry
✅ PostgreSQL
✅ Key Vault
✅ Entra ID authentication
✅ oauth2-proxy
✅ ingress + TLS
✅ production-ready Kubernetes base

This lab intentionally avoids:

* LangGraph
* AI
* cost engines
* dashboards

because infrastructure foundation must come first.

---

# LAB 1 Architecture

```text id="u4u0wq"
Users
  ↓
Entra ID
  ↓
oauth2-proxy
  ↓
NGINX Ingress
  ↓
AKS Cluster
```

Supporting services:

```text id="ic70lc"
AKS
ACR
PostgreSQL Flexible Server
Key Vault
Managed Identity
```

---

# Step 1 — Create Resource Groups

Recommended structure:

```text id="r0yrv5"
rg-finops-prod-core
rg-finops-prod-data
rg-finops-prod-network
```

---

# Step 2 — Create Azure Container Registry

Use Premium only if needed later.

For now:

```text id="b7nlkf"
Basic SKU
```

Example:

```bash
az acr create \
  --name finopsacr \
  --resource-group rg-finops-prod-core \
  --sku Basic
```

---

# Step 3 — Create AKS Cluster

---

# Recommended Minimal Production Setup

## Node Pools

| Pool   | Type       | Purpose     |
| ------ | ---------- | ----------- |
| system | regular    | ingress/api |
| spot   | spot nodes | workers/AI  |

---

# Recommended VM Sizes

## System Pool

```text id="vqiv8x"
Standard_D4as_v5
```

## Spot Pool

```text id="ylz0ur"
Standard_B4ms
```

---

# AKS Features

Enable:

✅ Managed Identity
✅ OIDC issuer
✅ Workload identity
✅ Cluster autoscaler
✅ Azure CNI Overlay
✅ Azure Monitor optional

---

# Example AKS Creation

```bash
az aks create \
  --resource-group rg-finops-prod-core \
  --name finops-aks \
  --node-count 2 \
  --enable-managed-identity \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --generate-ssh-keys
```

---

# Add Spot Pool

```bash
az aks nodepool add \
  --resource-group rg-finops-prod-core \
  --cluster-name finops-aks \
  --name spotpool \
  --priority Spot \
  --eviction-policy Delete \
  --enable-cluster-autoscaler \
  --min-count 0 \
  --max-count 5 \
  --node-vm-size Standard_B4ms
```

---

# Step 4 — Connect ACR to AKS

```bash
az aks update \
  --name finops-aks \
  --resource-group rg-finops-prod-core \
  --attach-acr finopsacr
```

---

# Step 5 — Install kubectl + Helm

```bash
az aks install-cli
```

---

# Get Credentials

```bash
az aks get-credentials \
  --resource-group rg-finops-prod-core \
  --name finops-aks
```

---

# Step 6 — Install NGINX Ingress

Use Helm.

```bash
helm repo add ingress-nginx \
https://kubernetes.github.io/ingress-nginx
```

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-nginx
```

---

# Step 7 — Install cert-manager

For HTTPS certificates.

```bash
helm repo add jetstack https://charts.jetstack.io
```

```bash
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

---

# Step 8 — Configure DNS

Example domains:

```text id="t1p3l7"
app.company.com
api.company.com
ai.company.com
```

Point DNS to ingress public IP.

---

# Step 9 — Configure TLS

Use Let’s Encrypt ClusterIssuer.

Example:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt
spec:
  acme:
    email: admin@company.com
    server: https://acme-v02.api.letsencrypt.org/directory
```

---

# Step 10 — Create PostgreSQL Flexible Server

---

# Recommended SKU

Minimal production:

```text id="mj7x08"
Burstable B2ms
```

---

# Enable

✅ Private access
✅ Backup
✅ HA optional later

---

# Database Structure

Initially create:

```text id="w21vjo"
finops
```

---

# Step 11 — Create Key Vault

Purpose:

* secrets
* API keys
* DB creds
* OpenAI keys later

---

# Enable

✅ RBAC authorization
✅ soft delete
✅ purge protection

---

# Step 12 — Configure Managed Identity

Critical step.

Create:

* AKS workload identity
* pod identities

This avoids:

* secrets in Kubernetes
* static credentials

---

# Permissions Needed

At Management Group/Tenant:

| Role                   | Purpose         |
| ---------------------- | --------------- |
| Reader                 | inventory       |
| Cost Management Reader | billing         |
| Monitoring Reader      | metrics         |
| Advisor Reader         | recommendations |

---

# Step 13 — Install oauth2-proxy

This is your authentication gateway.

---

# Why oauth2-proxy?

It provides:

✅ Entra ID SSO
✅ RBAC integration
✅ session management
✅ secure headers
✅ low operational overhead

Excellent choice from your original design.

---

# oauth2-proxy Flow

```text id="h3cghy"
User
 ↓
Entra Login
 ↓
oauth2-proxy
 ↓
FastAPI
```

---

# Configure Entra App Registration

Create:

```text id="k4npwc"
finops-platform
```

Redirect URL:

```text id="g5n4lw"
https://app.company.com/oauth2/callback
```

---

# Required Scopes

```text id="b7v3c8"
openid
profile
email
```

---

# Step 14 — Deploy oauth2-proxy

Use Helm chart.

Configure:

* client ID
* client secret
* tenant ID
* cookie secret

---

# Step 15 — Create Kubernetes Namespaces

Recommended structure:

```text id="cjgxjz"
frontend
platform
ai
infra
security
monitoring
```

---

# Step 16 — Install External Secrets Operator

This syncs Key Vault → Kubernetes secrets.

VERY important.

---

# Why?

Avoid:

* manual secret management
* hardcoded credentials

---

# Step 17 — Configure Monitoring (Minimal)

Do NOT overbuild initially.

Install:

```text id="sr9gc9"
Prometheus
Grafana
```

Optional:

```text id="o7n1m3"
Loki
```

---

# Step 18 — Install KEDA

Important for cost optimization.

KEDA enables:

* scale-to-zero
* event-driven autoscaling

Huge Azure savings later.

---

# Step 19 — Base CI/CD

Recommended:

## GitHub Actions

Pipeline stages:

```text id="c4g0eb"
lint
test
build
docker push
deploy
```

---

# Container Strategy

| Service  | Image      |
| -------- | ---------- |
| frontend | nextjs-ui  |
| api      | fastapi    |
| ai       | langgraph  |
| worker   | celery     |
| mcp      | mcp-server |

---

# Step 20 — Validate Foundation

At end of LAB 1 you should have:

---

# Infrastructure Checklist

## Azure

✅ AKS
✅ ACR
✅ PostgreSQL
✅ Key Vault
✅ Managed Identity

---

## Kubernetes

✅ ingress-nginx
✅ cert-manager
✅ oauth2-proxy
✅ KEDA
✅ namespaces

---

## Security

✅ Entra ID SSO
✅ TLS
✅ workload identity
✅ RBAC

---

## DevOps

✅ CI/CD pipeline
✅ image builds
✅ Helm deployment

---

# LAB 1 Final Architecture

```text id="38jlwm"
Users
   ↓
Entra ID
   ↓
oauth2-proxy
   ↓
NGINX Ingress
   ↓
AKS
 ├── frontend namespace
 ├── platform namespace
 ├── ai namespace
 └── infra namespace

AKS Connected To:
 ├── ACR
 ├── PostgreSQL
 ├── Key Vault
 └── Azure APIs
```

---

# What Comes In LAB 2

Next lab will build:

# Core Platform API Layer

Including:

✅ FastAPI platform service
✅ subscription discovery
✅ Azure Resource Graph integration
✅ Cost Management API integration
✅ PostgreSQL schemas
✅ background workers
✅ cost ingestion pipeline
✅ resource inventory engine
✅ initial REST APIs

This is where the actual FinOps platform begins.
