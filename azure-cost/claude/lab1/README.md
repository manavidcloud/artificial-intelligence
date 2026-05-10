# Lab 1 — AKS + Workload Identity

## What this lab provisions

| Resource | Name pattern | Purpose |
|---|---|---|
| Resource Group | rg-costplatform-prod | Container for all lab resources |
| VNet | vnet-costplatform-prod | Private network, 10.10.0.0/16 |
| AKS cluster | aks-costplatform-prod | 1 system nodepool + 1 app nodepool |
| User-Assigned MI | mi-costplatform-prod | Identity used by all platform pods |
| Federated credential | cost-platform-federation | Binds MI to K8s ServiceAccount via OIDC |
| RBAC assignments | (per subscription) | Cost Mgmt Reader + Reader + Monitoring Reader |
| Key Vault | kv-costplatform-prod-001 | Secrets store, private endpoint only |
| ACR | acrcostplatformprod001 | Container registry |
| Log Analytics | law-costplatform-prod | AKS monitoring |

## Prerequisites

```bash
# Tools required
az --version          # Azure CLI >= 2.57
terraform --version   # >= 1.7
kubectl version       # >= 1.29
helm version          # >= 3.14

# Login
az login --tenant <your-tenant-id>
az account set --subscription <subscription-where-AKS-lives>

# The Terraform SP or your user needs these roles on the AKS subscription:
# - Contributor (to create resources)
# - User Access Administrator (to create role assignments)
# - Key Vault Administrator
```

## Bootstrap: Terraform state storage

Run once before the first `terraform init`:

```bash
LOCATION="westeurope"
RG="rg-tfstate"
SA="satfstatecostplatform"
CONTAINER="tfstate"

az group create -n $RG -l $LOCATION
az storage account create -n $SA -g $RG -l $LOCATION --sku Standard_LRS \
  --min-tls-version TLS1_2 --allow-blob-public-access false
az storage container create -n $CONTAINER --account-name $SA
```

## Deploy

```bash
cd terraform

# 1. Copy and fill in your values
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — fill tenant_id, target_subscription_ids, admin_group_object_ids

# 2. Initialise
terraform init

# 3. Plan — review every resource before applying
terraform plan -out=lab1.tfplan

# 4. Apply — takes ~8-12 minutes (AKS is the slow part)
terraform apply lab1.tfplan
```

## Verify

```bash
chmod +x scripts/verify.sh
./scripts/verify.sh
```

The script:
1. Reads all Terraform outputs
2. Configures kubectl
3. Checks all nodes are Ready
4. Checks Workload Identity webhook + CSI driver are running
5. Deploys a debug pod using the platform ServiceAccount
6. Acquires an Azure token from inside the pod (proves OIDC federation works)
7. Calls the Cost Management API (proves RBAC assignments work)
8. Reads a Key Vault secret (proves KV access works)
9. Cleans up the debug pod

## How Workload Identity works (the key pieces)

```
Pod spec
  serviceAccountName: cost-platform-sa          ← annotated with MI client ID
  labels:
    azure.workload.identity/use: "true"
            │
            ▼
AKS injects environment variables into the pod:
  AZURE_CLIENT_ID       = <MI client ID>
  AZURE_TENANT_ID       = <tenant ID>
  AZURE_FEDERATED_TOKEN_FILE = /var/run/secrets/azure/tokens/azure-identity-token
            │
            ▼
azure-identity SDK (DefaultAzureCredential) reads these automatically
No connection strings. No client secrets. No certificates.
```

## Outputs passed to Lab 2

After `terraform apply`, save these for Lab 2's `terraform.tfvars`:

```bash
terraform output pe_subnet_id     # private endpoint subnet
terraform output vnet_id          # VNet for DNS zone linking
terraform output managed_identity_client_id
terraform output key_vault_name
terraform output k8s_namespace
terraform output k8s_service_account_name
```

## Cost estimate (westeurope, prod sizing)

| Resource | Est. monthly cost |
|---|---|
| AKS system nodepool (2× D2s_v3) | ~€120 |
| AKS app nodepool (2× D4s_v3, autoscale 2-6) | ~€240 baseline |
| Key Vault (Standard) | ~€3 |
| Log Analytics (30d retention) | ~€5-20 depending on volume |
| ACR (Standard) | ~€18 |
| Public IP (load balancer) | ~€3 |
| **Total Lab 1** | **~€390-420/month** |

Labs 2-8 add PostgreSQL, Redis, Foundry, and egress costs on top.

## Destroy

```bash
cd terraform
terraform destroy
```

Note: Key Vault has soft-delete with 90-day retention. If you need to recreate
with the same name, either purge it first or use a different name suffix.

```bash
az keyvault purge --name kv-costplatform-prod-001 --location westeurope
```
