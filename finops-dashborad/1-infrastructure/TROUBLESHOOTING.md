# Infrastructure Troubleshooting

> Covers `setup.sh` (Azure provisioning) and `apply-secrets.sh` (Kubernetes secrets).
> For pod-level issues see the troubleshooting files in `2-platform-api/`, `3-ai-agent/`, or `4-dashboard/`.

---

## Quick Diagnosis

```bash
# Check Azure login
az account show

# Verify subscription
az account set --subscription "<YOUR-SUB-ID>"
az account show --query "{sub:id, tenant:tenantId}" -o table

# Check all resources are present
az group list --query "[?starts_with(name,'rg-finops')].{name:name,location:location}" -o table

# Check AKS health
kubectl get nodes -o wide
kubectl get pods -A
```

---

## setup.sh Failures

### `az postgres flexible-server` fails — module error

```
No module named 'azure.mgmt.rdbms.mysql_flexibleservers'
```

**Fix:** Reinstall Azure CLI:

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
```

Or on macOS:

```bash
brew update && brew upgrade azure-cli
az login
```

---

### Azure OpenAI — `ResourceExists` / soft-delete conflict

If setup.sh fails on the OpenAI step because the resource was previously deleted (Azure retains soft-deleted Cognitive Services for 48h):

```bash
# List soft-deleted resources
az cognitiveservices account list-deleted

# Purge the soft-deleted resource
az cognitiveservices account purge \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --location southindia

# Verify it's gone
az cognitiveservices account list-deleted

# Re-run setup
./1-infrastructure/scripts/setup.sh
```

---

### Key Vault name already taken globally

Key Vault names are globally unique across all Azure tenants. If `VaultAlreadyExists` appears:

1. Change `KV_NAME` in `setup.sh` (e.g., `kv-finops-prod01`)
2. Update the same value in `apply-secrets.sh` and `config.yaml`
3. Re-run `setup.sh`

---

### AKS `K8sVersionNotSupported` on `az aks update --attach-acr`

```bash
# Use direct role assignment instead
ACR_ID=$(az acr show --name finopsacrmanmas --resource-group rg-finops-prod-core --query id -o tsv)
KUBELET_OID=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query "identityProfile.kubeletidentity.objectId" -o tsv)
az role assignment create --role AcrPull \
  --assignee-object-id "$KUBELET_OID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$ACR_ID"
```

---

### AKS cluster creation fails — quota exceeded

```
Operation results in exceeding quota limits of Core
```

Check your regional vCPU quota:

```bash
az vm list-usage --location centralindia --query "[?contains(name.value,'cores')]" -o table
```

Options:
- Switch to a smaller system node VM: change `SYSTEM_NODE_SIZE` to `Standard_B2s` in `setup.sh`
- Request quota increase via Azure Portal → Subscriptions → Usage + quotas

---

### PostgreSQL creation fails — subnet delegation conflict

```
Subnet already delegated to another service
```

The postgres-subnet already has a delegation. Check:

```bash
az network vnet subnet show \
  --name postgres-subnet \
  --vnet-name finops-prod-vnet \
  --resource-group rg-finops-prod-network \
  --query "delegations[*].serviceName" -o tsv
```

If delegated to `Microsoft.DBforPostgreSQL/flexibleServers`, it's already correct — this warning is safe to ignore. If delegated to something else, you need a new subnet CIDR.

---

### Federated credentials fail — OIDC issuer empty

```bash
# Verify OIDC is enabled
az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query oidcIssuerProfile -o json

# If issuerUrl is empty, enable it:
az aks update \
  --name finops-aks \
  --resource-group rg-finops-prod-core \
  --enable-oidc-issuer \
  --enable-workload-identity
```

---

## apply-secrets.sh Failures

### Key Vault write fails: `ForbiddenByRbac`

The script auto-assigns `Key Vault Secrets Officer` to the caller. If it still fails:

```bash
KV_ID=$(az keyvault show --name kv-finops-prod00 --resource-group rg-finops-prod-security --query id -o tsv)
CALLER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee-object-id "$CALLER_OID" \
  --scope "$KV_ID"
# Wait 30s for RBAC propagation, then re-run
sleep 30
bash 1-infrastructure/scripts/apply-secrets.sh
```

---

### K8s secret has wrong password after re-running

```bash
# Re-sync secrets from secrets.env
bash 1-infrastructure/scripts/apply-secrets.sh

# Force pod restart to pick up new secret
kubectl rollout restart deployment/finops-platform-api -n platform
```

---

### `kubectl` not found or wrong context

```bash
# Fetch/refresh AKS credentials
az aks get-credentials \
  --name finops-aks \
  --resource-group rg-finops-prod-core \
  --overwrite-existing

kubectl config current-context
kubectl cluster-info
```

---

## Workload Identity Not Working

Pods use Azure Workload Identity (OIDC federation) to authenticate with Azure APIs without stored credentials. When this breaks, pods log `DefaultAzureCredential failed` or `401 Unauthorized from Azure`.

**Full diagnosis sequence:**

```bash
# 1. Check OIDC issuer is set on AKS
az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query oidcIssuerProfile.issuerUrl -o tsv

# 2. Check federated credentials exist on the managed identity
az identity federated-credential list \
  --identity-name mi-finops-prod \
  --resource-group rg-finops-prod-core \
  --query "[].{name:name, subject:subject}" -o table

# 3. Check service account annotation (must have azure.workload.identity/client-id)
kubectl get sa cost-platform-sa -n platform -o yaml | grep azure.workload

# 4. Check pod has the correct label (azure.workload.identity/use: "true")
kubectl get pod -n platform -l app=finops-platform-api -o yaml | grep "azure.workload"

# 5. Check managed identity has the right roles
MI_OID=$(az identity show --name mi-finops-prod --resource-group rg-finops-prod-core \
  --query principalId -o tsv)
az role assignment list --assignee "$MI_OID" --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

**Required roles for the managed identity:**
- `Cost Management Reader` — subscription scope
- `Reader` — subscription scope
- `Key Vault Secrets User` — Key Vault scope
- `Cognitive Services OpenAI User` — OpenAI resource scope

**Re-apply federated credentials if missing:**

```bash
OIDC=$(az aks show --name finops-aks --resource-group rg-finops-prod-core \
  --query oidcIssuerProfile.issuerUrl -o tsv)

az identity federated-credential create \
  --name finops-cost-platform-sa \
  --identity-name mi-finops-prod \
  --resource-group rg-finops-prod-core \
  --issuer "$OIDC" \
  --subject "system:serviceaccount:platform:cost-platform-sa" \
  --audiences api://AzureADTokenExchange
```

---

## TLS / Ingress Issues

See also: `4-dashboard/TROUBLESHOOTING.md` for dashboard-specific ingress issues.

### cert-manager certificate stuck in Pending

```bash
kubectl describe certificate -n frontend
kubectl describe certificaterequest -n frontend
kubectl describe order -n frontend
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

Requirements for HTTP-01 challenge:
1. DNS A record must resolve to the NGINX ingress IP **before** applying the Ingress
2. Port 80 must be open inbound on the Azure NSG covering the AKS subnet

```bash
# Test DNS resolution
nslookup app.manmas.online

# Test port 80 reachability
curl -v http://app.manmas.online/.well-known/acme-challenge/test

# Check NSG rules on AKS subnet
az network nsg rule list \
  --nsg-name <your-nsg-name> \
  --resource-group rg-finops-prod-network \
  --query "[].{name:name, priority:priority, direction:direction, access:access, destPort:destinationPortRange}" \
  -o table
```

---

## Cost Sync Issues

### Cost data is 0 after sync

1. Verify subscription ID is correct:
   ```bash
   az account show --query id -o tsv
   # Compare to AZURE_SUBSCRIPTION_IDS in the platform secret
   kubectl get secret finops-platform-secret -n platform -o jsonpath='{.data.AZURE_SUBSCRIPTION_IDS}' | base64 -d
   ```

2. Verify the managed identity has Cost Management Reader:
   ```bash
   MI_OID=$(az identity show --name mi-finops-prod --resource-group rg-finops-prod-core \
     --query principalId -o tsv)
   az role assignment list --assignee "$MI_OID" --query "[?contains(roleDefinitionName,'Cost')]" -o table
   ```

3. New subscriptions have a 24-48h delay before cost data appears in Azure Cost Management.

---

## Recovery — Full Teardown and Rebuild

If you need to start from scratch:

```bash
# Delete all resource groups (irreversible — deletes everything)
for RG in rg-finops-prod-network rg-finops-prod-core rg-finops-prod-security rg-finops-prod-data rg-finops-prod-ai; do
  az group delete --name "$RG" --yes --no-wait
done

# Wait for deletion (~10-15 min), then re-run setup
./1-infrastructure/scripts/setup.sh
./1-infrastructure/scripts/apply-secrets.sh
```
