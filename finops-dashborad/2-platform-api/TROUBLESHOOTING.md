# Platform API Troubleshooting

> FastAPI backend that syncs Azure cost, resource, and Advisor data into PostgreSQL.
> Runs in the `platform` namespace on AKS. Pod name: `finops-platform-api-*`.

---

## Quick Diagnosis

```bash
# Check pod state
kubectl get pods -n platform
kubectl describe pod -n platform -l app=finops-platform-api

# Check logs (live)
kubectl logs -n platform -l app=finops-platform-api --tail=100 -f

# Check logs of previous crashed pod
kubectl logs -n platform -l app=finops-platform-api --previous --tail=100

# Test API health (from inside cluster)
kubectl exec -n platform -l app=finops-platform-api -- \
  curl -s http://localhost:8080/health | python3 -m json.tool

# Test API health (via port-forward)
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80 &
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

---

## CrashLoopBackOff Causes

### `FATAL: password authentication failed for user "pgadmin"`

The K8s secret has a different password than PostgreSQL has set.

**Fix:**

```bash
# Option A — reset PostgreSQL password to match secrets.env
az postgres flexible-server update \
  --resource-group rg-finops-prod-data \
  --name finops-pgflex \
  --admin-password 'AzFleX!admi9'   # single quotes required for passwords with !

# Re-sync K8s secret
bash 1-infrastructure/scripts/apply-secrets.sh
kubectl rollout restart deployment/finops-platform-api -n platform

# Option B — update secrets.env to match the actual PostgreSQL password, then re-sync
nano secrets.env   # update DB_PASSWORD
bash 1-infrastructure/scripts/apply-secrets.sh
kubectl rollout restart deployment/finops-platform-api -n platform
```

---

### `FATAL: no pg_hba.conf entry … no encryption` or SSL error

Azure PostgreSQL Flexible Server requires SSL. Already fixed in `database.py` with `connect_args={"sslmode": "require"}`. If you see this on an older build:

```bash
# Rebuild the image
docker buildx build --platform linux/amd64 --push \
  -t $ACR/finops-platform-api:latest 2-platform-api/
kubectl rollout restart deployment/finops-platform-api -n platform
```

---

### `ModuleNotFoundError: No module named 'six'`

```bash
# Rebuild the image (six is listed in requirements.txt)
docker buildx build --platform linux/amd64 --push \
  -t $ACR/finops-platform-api:latest 2-platform-api/
kubectl rollout restart deployment/finops-platform-api -n platform
```

---

### `DefaultAzureCredential failed` / 401 from Azure APIs

Workload Identity is not configured correctly. See `1-infrastructure/TROUBLESHOOTING.md` — Workload Identity section.

Quick check:

```bash
# Verify service account annotation
kubectl get sa cost-platform-sa -n platform -o yaml | grep azure.workload

# Check pod has the label
kubectl get pod -n platform -l app=finops-platform-api -o yaml | grep "azure.workload.identity"

# Test Azure credential from inside the pod
kubectl exec -n platform -l app=finops-platform-api -- \
  python3 -c "
from azure.identity import DefaultAzureCredential
token = DefaultAzureCredential().get_token('https://management.azure.com/.default')
print('Token acquired OK, expires:', token.expires_on)
"
```

---

### Pod stuck in `Pending` — `Insufficient cpu` or `Unschedulable`

```bash
# Check node resources
kubectl top nodes

# Check pending pod events
kubectl describe pod -n platform -l app=finops-platform-api | grep -A 10 Events

# Scale down a non-critical pod to free space, or increase the node pool:
az aks nodepool scale \
  --name apppool \
  --cluster-name finops-aks \
  --resource-group rg-finops-prod-core \
  --node-count 2
```

---

### `ImagePullBackOff` — 401 unauthorized from ACR

```bash
# Re-assign AcrPull role to kubelet identity
ACR_ID=$(az acr show --name finopsacrmanmas --resource-group rg-finops-prod-core --query id -o tsv)
KUBELET_OID=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query "identityProfile.kubeletidentity.objectId" -o tsv)
az role assignment create --role AcrPull \
  --assignee-object-id "$KUBELET_OID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$ACR_ID"
```

---

## Data Sync Issues

### Cost sync returns 0 rows

```bash
# Trigger sync manually and watch logs
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80 &
curl -X POST 'http://localhost:8080/sync/costs?days=30'

# Check logs for errors
kubectl logs -n platform -l app=finops-platform-api --tail=50
```

Common causes:
1. `AZURE_SUBSCRIPTION_IDS` missing or wrong UUID
2. Managed Identity lacks `Cost Management Reader` role
3. New subscription — Azure cost data has a 24-48h delay
4. Cost Management API not enabled on the subscription

```bash
# Verify subscription ID in the secret
kubectl get secret finops-platform-secret -n platform \
  -o jsonpath='{.data.AZURE_SUBSCRIPTION_IDS}' | base64 -d && echo

# Verify Cost Management Reader role
MI_OID=$(az identity show --name mi-finops-prod --resource-group rg-finops-prod-core \
  --query principalId -o tsv)
az role assignment list --assignee "$MI_OID" \
  --query "[?contains(roleDefinitionName,'Cost')]" -o table
```

---

### Advisor sync returns 0 rows

Azure Advisor recommendations are generated asynchronously. They may not be populated immediately on a new subscription or after a large infrastructure change.

```bash
# Check if Advisor has any recommendations in the portal
az advisor recommendation list --category Cost --query "[0:5].{impact:impact,desc:shortDescription.problem}" -o table

# Force a sync
curl -X POST 'http://localhost:8080/sync/advisor'
kubectl logs -n platform -l app=finops-platform-api --tail=30
```

---

### Resource sync returns 0 rows

```bash
# Test Resource Graph directly (requires Reader role)
az graph query \
  -q "Resources | limit 5 | project name, type, location" \
  -o table

# If this fails, the managed identity lacks Reader role on the subscription
MI_OID=$(az identity show --name mi-finops-prod --resource-group rg-finops-prod-core \
  --query principalId -o tsv)
az role assignment create --role Reader \
  --assignee-object-id "$MI_OID" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/$(az account show --query id -o tsv)"
```

---

## Database Issues

### PostgreSQL not reachable from AKS

The database is on a private VNet — AKS pods must be on the same VNet.

```bash
# Check PostgreSQL private endpoint DNS from inside a pod
kubectl exec -n platform -l app=finops-platform-api -- \
  python3 -c "import socket; print(socket.gethostbyname('finops-pgflex.postgres.database.azure.com'))"

# Should return a private IP in 10.0.1.x range
# If it returns a public IP, the private DNS zone is not linked to the AKS VNet
```

Fix DNS zone link:

```bash
VNET_ID=$(az network vnet show --name finops-prod-vnet --resource-group rg-finops-prod-network --query id -o tsv)
az network private-dns link vnet create \
  --name finops-dns-link \
  --resource-group rg-finops-prod-network \
  --zone-name "finops-pgflex.private.postgres.database.azure.com" \
  --virtual-network "$VNET_ID" \
  --registration-enabled false
```

---

### Database tables missing (first run)

Tables are auto-created on pod startup via `init_db()`. If they are missing:

```bash
# Check startup logs
kubectl logs -n platform -l app=finops-platform-api | grep -i "database\|init\|error"

# Connect to PostgreSQL directly and check tables
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80 &
curl http://localhost:8080/health   # should show "db: connected"

# Or connect directly via psql (from a pod with psql)
kubectl run psql-debug --rm -it --image=postgres:16 -- \
  psql "host=finops-pgflex.postgres.database.azure.com dbname=finops-db user=pgadmin sslmode=require"
```

---

## Email Notification Issues

### Emails not sending

```bash
# Test SMTP configuration
curl -X POST http://localhost:8080/alerts/test

# Check SMTP env vars in the secret
kubectl get secret finops-platform-secret -n platform \
  -o jsonpath='{.data}' | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
for k in ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_FROM', 'ALERT_RECIPIENTS']:
    if k in d:
        print(k, '=', base64.b64decode(d[k]).decode())
    else:
        print(k, '= NOT SET')
"
```

**Gmail App Passwords:** If using Gmail, you must use an App Password (not your account password). Go to Google Account → Security → 2-Step Verification → App passwords.

---

## Performance Issues

### API response time > 5 seconds

The Platform API makes synchronous Azure API calls during `/sync/*`. Dashboard page loads only hit PostgreSQL (fast). If page loads are slow:

```bash
# Check DB query performance
kubectl exec -n platform -l app=finops-platform-api -- \
  python3 -c "
from src.database import SessionLocal
from sqlalchemy import text
import time
db = SessionLocal()
start = time.time()
db.execute(text('SELECT count(*) FROM cost_records'))
print(f'Query time: {time.time()-start:.3f}s')
"
```

Common causes:
- Too many cost records without indexes (auto-indexed by the ORM)
- PostgreSQL Burstable B1ms CPU throttling — upgrade to Standard_B2ms if needed

---

## Recovery Procedures

### Full platform-api redeploy

```bash
# Rebuild and push image
docker buildx build --platform linux/amd64 --push \
  -t $ACR/finops-platform-api:latest 2-platform-api/

# Re-apply K8s manifest
kubectl apply -f 2-platform-api/k8s/deployment.yaml

# Watch rollout
kubectl rollout status deployment/finops-platform-api -n platform
```

### Reset database (DESTRUCTIVE — loses all synced data)

```bash
# Connect and drop/recreate all tables
kubectl run psql-reset --rm -it --image=postgres:16 \
  --env="PGPASSWORD=AzFleX!admi9" -- \
  psql -h finops-pgflex.postgres.database.azure.com -U pgadmin -d finops-db \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restart platform-api to re-init tables
kubectl rollout restart deployment/finops-platform-api -n platform

# Trigger full sync
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80 &
curl -X POST 'http://localhost:8080/sync/all?days=30'
```
