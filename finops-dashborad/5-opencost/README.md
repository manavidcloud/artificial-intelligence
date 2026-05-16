# 5 — OpenCost Integration

> **OPTIONAL COMPONENT** — Deploy OpenCost to get Kubernetes-native cost allocation
> (pod-level, namespace-level, workload-level breakdown) alongside Azure Cost Management data.
>
> OpenCost UI:        **https://opencost.manmas.online**
> K8s Cost Dashboard: **https://k8scost.manmas.online**

---

## What OpenCost Adds

| Feature | Azure Cost Management | OpenCost |
|---|---|---|
| Azure resource costs | ✅ | ❌ |
| Kubernetes pod/workload costs | ❌ | ✅ |
| Namespace cost allocation | ❌ | ✅ |
| Idle / shared cost distribution | ❌ | ✅ |
| Real-time cost view | ❌ (24–48h delay) | ✅ (live) |
| Rightsizing by CPU/mem request | ❌ | ✅ |
| Multi-cloud K8s costs | ❌ | ✅ |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Internet / Users                                    │
└────────┬──────────────────────────┬─────────────────────────────────────────┘
         │ https://opencost.manmas.online    │ https://k8scost.manmas.online
         ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Shared NGINX Ingress Controller                          │
│              (TLS termination via cert-manager / Let's Encrypt)             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │  opencost namespace
             ┌─────────────────┼──────────────────────────────┐
             │                 │                              │
             ▼                 ▼                              ▼
  ┌───────────────────┐  ┌─────────────────┐    ┌─────────────────────────┐
  │  OpenCost         │  │  K8s Cost        │    │  Prometheus             │
  │  (port 9090)      │  │  Dashboard       │    │  (port 9090/9003)       │
  │  Official UI      │  │  (Streamlit)     │    │  Scrapes kubelet +      │
  │  + REST API       │  │  port 8502       │    │  node-exporter metrics  │
  └─────────┬─────────┘  └────────┬─────────┘    └───────────┬─────────────┘
            │                     │                           │
            │  REST API calls     │                           │
            └─────────────────────┘                           │
                       ▲                                      │
                       │  Prometheus queries                  │
                       └──────────────────────────────────────┘

AKS Cluster:
  ┌──────────────────────────────────────────────────────────────┐
  │  Node 1         Node 2         Node 3                        │
  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                   │
  │  │ pod-A   │    │ pod-C   │    │ pod-E   │                   │
  │  │ pod-B   │    │ pod-D   │    │ pod-F   │                   │
  │  └─────────┘    └─────────┘    └─────────┘                   │
  │  OpenCost allocates node cost → pods proportional to         │
  │  their CPU/memory requests vs node capacity                  │
  └──────────────────────────────────────────────────────────────┘

Cost Allocation Logic:
  Node hourly price  (from cloud pricing API or custom CSV)
        │
        ├── Pod A cost = node_price × (pod_A_requests / node_capacity)
        ├── Pod B cost = node_price × (pod_B_requests / node_capacity)
        └── Idle cost  = node_price × (1 - sum(all_pod_requests) / node_capacity)
```

---

## Cloud Provider Support

OpenCost supports multiple cloud providers. The `cloudProvider` setting in
`k8s/helm-values.yaml` controls which pricing source is used.

### Azure AKS (this repo — fully configured)

```yaml
# helm-values.yaml
opencost:
  cloudProvider: azure
```

No additional setup needed — OpenCost auto-discovers node SKU pricing from the
Azure pricing API using the node's `node.kubernetes.io/instance-type` label.

---

### AWS EKS

```yaml
opencost:
  cloudProvider: aws
  aws:
    spot_label: "eks.amazonaws.com/capacityType"
    spot_label_value: "SPOT"
```

Additional requirements:

1. **IAM permissions** — the OpenCost service account needs:
   - `ce:GetProducts` (Cost Explorer pricing lookup)
   - `ec2:DescribeInstances`, `ec2:DescribeSpotPriceHistory`

   ```yaml
   # Add to helm-values.yaml
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/opencost-role
   ```

2. **S3 billing export** (optional, for accurate spot/savings pricing):
   ```yaml
   opencost:
     aws:
       athena_bucket: s3://my-cur-bucket
       athena_region: us-east-1
       athena_database: athenacurcfn
       athena_table: my_cost_report
   ```

---

### GCP GKE

```yaml
opencost:
  cloudProvider: gcp
  gcp:
    projectID: "my-gcp-project"
```

Additional requirements:

1. **Workload Identity** — bind the OpenCost KSA to a GCP service account:
   ```bash
   gcloud iam service-accounts create opencost-sa
   gcloud projects add-iam-policy-binding MY_PROJECT \
     --member="serviceAccount:opencost-sa@MY_PROJECT.iam.gserviceaccount.com" \
     --role="roles/bigquery.jobUser"
   gcloud iam service-accounts add-iam-policy-binding \
     opencost-sa@MY_PROJECT.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser \
     --member "serviceAccount:MY_PROJECT.svc.id.goog[opencost/opencost]"
   ```

2. **BigQuery billing export** — enable in GCP Console → Billing → Export → BigQuery.

---

### On-Premises / Custom Pricing

For on-prem Kubernetes clusters or any cloud with non-standard pricing:

```yaml
opencost:
  cloudProvider: custom

customPricing:
  enabled: true
  configmapName: custom-pricing-model
  # Define node price per CPU-hour and per RAM-GB-hour
  CPU: "0.031611"        # $ per vCPU-hour
  spotCPU: "0.006655"
  RAM: "0.004237"        # $ per GB RAM-hour
  spotRAM: "0.000892"
  GPU: "0.95"            # $ per GPU-hour
  storage: "0.00005479"  # $ per GB-hour (PVC)
  zoneNetworkEgress: "0.01"
  regionNetworkEgress: "0.01"
  internetNetworkEgress: "0.12"
```

Apply the custom pricing ConfigMap:

```bash
kubectl create configmap custom-pricing-model \
  --from-file=pricing.json=5-opencost/k8s/custom-pricing.json \
  -n opencost
```

---

## Optional — Authentication (SSO / Active Directory / LDAP)

OpenCost itself does not natively include an authentication layer. For production
enterprise deployments, authentication should be enforced at the **ingress level**
using one of the following approaches.

### Option A — Azure AD (Entra ID) SSO via oauth2-proxy

This is the recommended approach if your company uses Azure AD / Microsoft 365.

```
Browser → NGINX Ingress → oauth2-proxy (Azure AD OIDC) → OpenCost
                          Redirects unauthenticated users to Azure AD login
```

**Step 1 — Register an app in Azure AD**

```bash
# Portal: Entra ID → App Registrations → New Registration
# Redirect URI: https://opencost.manmas.online/oauth2/callback
# Supported account types: Accounts in this organizational directory only

# Note the Client ID and Tenant ID after registration
# Create a Client Secret: Certificates & secrets → New client secret
```

**Step 2 — Deploy oauth2-proxy**

```bash
helm repo add oauth2-proxy https://oauth2-proxy.github.io/manifests
helm repo update

helm install oauth2-proxy oauth2-proxy/oauth2-proxy \
  --namespace opencost \
  --set config.clientID="<APP_CLIENT_ID>" \
  --set config.clientSecret="<APP_CLIENT_SECRET>" \
  --set config.cookieSecret="$(openssl rand -base64 32 | head -c 32)" \
  --set extraArgs.provider="azure" \
  --set extraArgs.azure-tenant="<TENANT_ID>" \
  --set extraArgs.email-domain="yourcompany.com" \
  --set extraArgs.upstream="http://opencost.opencost.svc.cluster.local:9090" \
  --set ingress.enabled=true \
  --set ingress.ingressClassName=nginx \
  --set "ingress.hosts[0]=opencost.manmas.online" \
  --set "ingress.tls[0].secretName=opencost-tls" \
  --set "ingress.tls[0].hosts[0]=opencost.manmas.online"
```

**Step 3 — Remove the existing OpenCost ingress** (oauth2-proxy takes over):

```bash
kubectl delete ingress opencost-ingress -n opencost
```

Now only users authenticated with `@yourcompany.com` Azure AD accounts can reach OpenCost.

---

### Option B — On-Premises Active Directory / LDAP via oauth2-proxy

For companies using on-prem Active Directory (LDAP):

```bash
helm install oauth2-proxy oauth2-proxy/oauth2-proxy \
  --namespace opencost \
  --set config.clientID="<CLIENT_ID>" \
  --set config.clientSecret="<CLIENT_SECRET>" \
  --set config.cookieSecret="$(openssl rand -base64 32 | head -c 32)" \
  --set extraArgs.provider="oidc" \
  --set extraArgs.oidc-issuer-url="https://your-keycloak-or-dex-server/auth/realms/company" \
  --set extraArgs.email-domain="*" \
  --set extraArgs.upstream="http://opencost.opencost.svc.cluster.local:9090"
```

This works with any OIDC-compatible identity provider fronting your AD/LDAP:
- **Keycloak** (self-hosted, connects to AD/LDAP)
- **Dex** (lightweight OIDC provider)
- **ADFS** (Active Directory Federation Services)

LDAP configuration example for Keycloak:

```
Keycloak realm → LDAP User Federation
  LDAP URL:      ldap://dc01.company.local:389
  Bind DN:       cn=keycloak-svc,ou=service,dc=company,dc=local
  User DN:       ou=users,dc=company,dc=local
  Username Attr: sAMAccountName
  Email Attr:    mail
```

---

### Option C — IP Allowlist (Simple / Internal Only)

For internal dashboards accessible only from the office network or VPN:

```yaml
# Add to 5-opencost/k8s/ingress.yaml annotations
nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,192.168.0.0/16,203.0.113.45/32"
```

Re-apply: `kubectl apply -f 5-opencost/k8s/ingress.yaml`

---

### Auth Summary

| Method | Best For | Complexity |
|---|---|---|
| None (open) | Development / internal VNet only | None |
| IP Allowlist | Office-network-only access | Low |
| Azure AD SSO (oauth2-proxy) | Microsoft 365 companies | Medium |
| On-prem AD / LDAP (Keycloak) | Companies with on-prem Active Directory | High |

---

## Prerequisites

- AKS cluster running (same cluster as the rest of the FinOps platform)
- `helm` CLI installed
- NGINX Ingress Controller + cert-manager already deployed (Step 7 in main README)
- DNS A records pointing to NGINX ingress EXTERNAL-IP:
  - `opencost.manmas.online` — OpenCost official UI
  - `k8scost.manmas.online` — K8s Cost Dashboard (Streamlit)

---

## Step 1 — Install Prometheus

OpenCost requires a Prometheus instance to store metrics.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/prometheus \
  --namespace opencost \
  --create-namespace \
  --set alertmanager.enabled=false \
  --set pushgateway.enabled=false \
  --set server.persistentVolume.size=8Gi \
  --set server.retention=15d

kubectl get pods -n opencost -l app=prometheus
```

---

## Step 2 — Install OpenCost via Helm

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  -f 5-opencost/k8s/helm-values.yaml

kubectl rollout status deployment/opencost -n opencost

# Verify health
kubectl port-forward svc/opencost 9090:9090 -n opencost &
curl http://localhost:9090/healthz
```

---

## Step 3 — Deploy K8s Cost Dashboard

```bash
# Build and push (amd64 only — same as main dashboard)
ACR="finopsacrmanmas.azurecr.io"
docker buildx build \
  --platform linux/amd64 \
  --push \
  -t $ACR/opencost-dashboard:latest \
  5-opencost/dashboard/

# Deploy to AKS
kubectl apply -f 5-opencost/dashboard/k8s/deployment.yaml
kubectl rollout status deployment/opencost-dashboard -n opencost

# Apply ingress
kubectl apply -f 5-opencost/k8s/ingress.yaml
```

---

## Step 4 — Add DNS Records

```bash
# Get NGINX ingress IP
kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Add two A records in your DNS provider:
#   opencost.manmas.online  → <EXTERNAL-IP>
#   k8scost.manmas.online   → <EXTERNAL-IP>
```

---

## Step 5 — Verify

```bash
# OpenCost health
curl https://opencost.manmas.online/healthz

# Allocation query
curl "https://opencost.manmas.online/allocation/compute?window=1d&aggregate=namespace"

# K8s Cost Dashboard
curl -I https://k8scost.manmas.online
```

---

## Uninstall

```bash
helm uninstall opencost   -n opencost
helm uninstall prometheus -n opencost
kubectl delete -f 5-opencost/dashboard/k8s/deployment.yaml
kubectl delete ingress opencost-ingress -n opencost 2>/dev/null || true
kubectl delete namespace opencost
```
