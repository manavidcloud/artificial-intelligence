# Azure AI & Generative AI Engineering Labs

A hands-on, from-scratch lab guide for building production-ready AI and Generative AI solutions on Microsoft Azure — covering Azure AI Foundry, Azure OpenAI, RAG pipelines, AI agents, vector search, APIs, containers, CI/CD, security, monitoring, evaluation, and cost governance.

Every lab gives you **three equivalent ways** to do the same task:

| Method | Best for |
|---|---|
| 🖱️ **Azure Portal** | Understanding the resource model visually, first-time setup |
| 💻 **Azure CLI** (`az`) | Cross-platform scripting (bash/zsh/PowerShell), Linux/macOS/CI pipelines |
| 🔷 **Azure PowerShell** (`Az` module) | Windows-native automation, integration with existing PS scripts |

Follow whichever method matches your environment — or do all three to build muscle memory. Steps are written **assuming zero prior setup**, so nothing is skipped.

---

## Table of Contents

- [Lab 0: Environment Setup & Tooling](#lab-0-environment-setup--tooling)
- [Lab 1: Resource Groups & Naming/Tagging Governance](#lab-1-resource-groups--namingtagging-governance)
- [Lab 2: Microsoft Entra ID — Identity, RBAC & Service Principals for AI Workloads](#lab-2-microsoft-entra-id--identity-rbac--service-principals-for-ai-workloads)
- [Lab 3: Azure Storage & Key Vault for AI Data](#lab-3-azure-storage--key-vault-for-ai-data)
- [Lab 4: Azure AI Foundry Hub & Project](#lab-4-azure-ai-foundry-hub--project)
- [Lab 5: Deploy Azure OpenAI Models (Chat + Embeddings)](#lab-5-deploy-azure-openai-models-chat--embeddings)
- [Lab 6: Prompt Engineering & Playground Testing](#lab-6-prompt-engineering--playground-testing)
- [Lab 7: Azure AI Search — Vector & Hybrid Search Index](#lab-7-azure-ai-search--vector--hybrid-search-index)
- [Lab 8: Build a RAG Pipeline in Python](#lab-8-build-a-rag-pipeline-in-python)
- [Lab 9: Build an AI Agent with Azure AI Foundry Agent Service](#lab-9-build-an-ai-agent-with-azure-ai-foundry-agent-service)
- [Lab 10: Deploy the AI App as an Azure Function API](#lab-10-deploy-the-ai-app-as-an-azure-function-api)
- [Lab 11: Containerize & Deploy to Azure Kubernetes Service (AKS)](#lab-11-containerize--deploy-to-azure-kubernetes-service-aks)
- [Lab 12: Monitoring, Logging & Application Insights for AI Apps](#lab-12-monitoring-logging--application-insights-for-ai-apps)
- [Lab 13: Azure DevOps CI/CD Pipeline for the AI Application](#lab-13-azure-devops-cicd-pipeline-for-the-ai-application)
- [Lab 14: Model Evaluation, Content Safety & Quality Metrics](#lab-14-model-evaluation-content-safety--quality-metrics)
- [Lab 15: Cost Optimization & Governance for AI Workloads](#lab-15-cost-optimization--governance-for-ai-workloads)
- [Appendix: Full Cleanup Script](#appendix-full-cleanup-script)

### Naming convention used throughout

To keep resources consistent across labs, we use one running example:

```
Subscription : (yours)
Location     : eastus2          # change to a region with Azure OpenAI quota
Resource Grp : rg-aif-labs
Prefix       : aifab             (AI Foundry AB = "AI-Foundry-Application-Build")
```

Replace `eastus2` / `rg-aif-labs` / `aifab` with your own values consistently if you rename them — every lab reuses these.

---

## Lab 0: Environment Setup & Tooling

### Objective
Get a working machine with an Azure subscription, Azure CLI, Azure PowerShell, Python, Docker, and Git — logged in and ready — before touching any AI service.

### Prerequisites
- A Microsoft account or work/school account
- Admin rights on your laptop/desktop (to install CLI tools)
- Internet access

### Step 1 — Get an Azure subscription
1. Go to https://azure.microsoft.com/free and sign up (or use an existing enterprise/pay-as-you-go subscription).
2. Once provisioned, sign in to the **Azure Portal**: https://portal.azure.com
3. In the Portal search bar, type **Subscriptions** → open it → note your **Subscription ID** and **Subscription Name**. You will need this ID repeatedly.
4. Check region availability for Azure OpenAI (not all regions support all models): Portal → search **Azure OpenAI** → **Create** → the region dropdown shows only supported regions. Pick one (e.g., `eastus2`, `swedencentral`, `westeurope`) and use it for every lab below.

### Step 2 — Install Azure CLI

**Windows (PowerShell, run as Administrator):**
```powershell
winget install -e --id Microsoft.AzureCLI
```

**macOS:**
```bash
brew update && brew install azure-cli
```

**Linux (Debian/Ubuntu):**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

Verify:
```bash
az version
```

### Step 3 — Install Azure PowerShell (`Az` module)

Works on Windows, macOS, and Linux (PowerShell 7+ required on non-Windows).

```powershell
# Install PowerShell 7 first if you don't have it: https://aka.ms/powershell
Install-Module -Name Az -Repository PSGallery -Force -Scope CurrentUser
```

Verify:
```powershell
Get-InstalledModule -Name Az -AllVersions | Select-Object Name, Version
```

### Step 4 — Log in with all three tools

**Portal:** open https://portal.azure.com and sign in interactively.

**CLI:**
```bash
az login
# Browser opens -> sign in -> tool lists your subscriptions
az account list --output table
az account set --subscription "<SUBSCRIPTION_ID_OR_NAME>"
az account show --output table
```

**PowerShell:**
```powershell
Connect-AzAccount
# Browser opens -> sign in
Get-AzSubscription | Format-Table Name, Id, State
Set-AzContext -Subscription "<SUBSCRIPTION_ID_OR_NAME>"
Get-AzContext
```

### Step 5 — Install supporting developer tools

```bash
# Python 3.11+
python3 --version || (sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip)

# Git
git --version || sudo apt-get install -y git

# Docker Desktop / Docker Engine
docker --version   # install from https://docs.docker.com/get-docker/ if missing

# Azure Functions Core Tools (for Lab 10)
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# kubectl + Helm (for Lab 11)
az aks install-cli          # installs kubectl + kubelogin
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Step 6 — Register required resource providers (one-time per subscription)

**CLI:**
```bash
for ns in Microsoft.CognitiveServices Microsoft.MachineLearningServices Microsoft.Search Microsoft.Web Microsoft.ContainerService Microsoft.OperationalInsights Microsoft.Insights Microsoft.KeyVault Microsoft.Storage Microsoft.ContainerRegistry; do
  az provider register --namespace $ns
done
az provider show -n Microsoft.CognitiveServices --query registrationState -o tsv
```

**PowerShell:**
```powershell
$namespaces = @('Microsoft.CognitiveServices','Microsoft.MachineLearningServices','Microsoft.Search',
  'Microsoft.Web','Microsoft.ContainerService','Microsoft.OperationalInsights','Microsoft.Insights',
  'Microsoft.KeyVault','Microsoft.Storage','Microsoft.ContainerRegistry')
foreach ($ns in $namespaces) { Register-AzResourceProvider -ProviderNamespace $ns }
Get-AzResourceProvider -ProviderNamespace Microsoft.CognitiveServices | Select-Object ProviderNamespace, RegistrationState
```

**Portal:** Subscriptions → your subscription → **Resource providers** (left menu) → search each namespace above → **Register** if status is "NotRegistered".

### ✅ Validation
- `az account show` and `Get-AzContext` both return your correct subscription.
- Portal home page shows your name/tenant top-right.
- `docker run hello-world` succeeds.
- `python3 -m venv --help` runs without error.

### Cleanup
Nothing to clean up — this lab only sets up tooling.

---

## Lab 1: Resource Groups & Naming/Tagging Governance

### Objective
Create the resource group that will host every resource in this guide, apply consistent tags, and (optionally) a budget alert.

### Prerequisites
Lab 0 completed.

### Part A — Azure Portal
1. Sign in to https://portal.azure.com.
2. Search bar → type **Resource groups** → click **+ Create**.
3. **Subscription**: select yours. **Resource group**: `rg-aif-labs`. **Region**: `East US 2` (or your chosen region).
4. Click **Next: Tags**. Add tags:
   - `environment = lab`
   - `owner = <your name>`
   - `project = azure-ai-labs`
5. Click **Review + create** → **Create**.
6. Once deployed, click **Go to resource group**. Pin it to your dashboard (pin icon top-right) for quick access in later labs.
7. (Optional cost guardrail) In the resource group blade → left menu **Cost Management** → **Budgets** → **+ Add** → name `budget-aif-labs`, amount e.g. `50` (your currency), reset period **Monthly**, add an alert at 80% → **Create**.

### Part B — Azure CLI
```bash
LOCATION="eastus2"
RG="rg-aif-labs"

az group create \
  --name $RG \
  --location $LOCATION \
  --tags environment=lab owner="$(whoami)" project=azure-ai-labs

az group show --name $RG --output table

# Optional: budget via CLI (requires Cost Management API access)
az consumption budget create \
  --budget-name "budget-aif-labs" \
  --amount 50 \
  --category cost \
  --time-grain monthly \
  --start-date $(date +%Y-%m-01) \
  --end-date $(date -d "+1 year" +%Y-%m-01) \
  --resource-group $RG
```

### Part C — Azure PowerShell
```powershell
$Location = "eastus2"
$RG       = "rg-aif-labs"

New-AzResourceGroup -Name $RG -Location $Location -Tag @{
  environment = "lab"
  owner       = $env:USERNAME
  project     = "azure-ai-labs"
}

Get-AzResourceGroup -Name $RG | Format-Table ResourceGroupName, Location, ProvisioningState

# Optional budget
New-AzConsumptionBudget -Name "budget-aif-labs" -Amount 50 -Category Cost `
  -TimeGrain Monthly -StartDate (Get-Date -Day 1) -EndDate (Get-Date).AddYears(1) `
  -ResourceGroupFilter $RG
```

### ✅ Validation
`az group show -n rg-aif-labs` / `Get-AzResourceGroup -Name rg-aif-labs` return `ProvisioningState: Succeeded`, and the group is visible in Portal with the three tags applied.

### Cleanup
Keep this resource group — every later lab deploys into it. Full teardown instructions are in the [Appendix](#appendix-full-cleanup-script).

---

## Lab 2: Microsoft Entra ID — Identity, RBAC & Service Principals for AI Workloads

### Objective
Create an app registration / service principal with least-privilege RBAC roles so applications (not humans) can call Azure OpenAI, AI Search, Storage, and Key Vault securely — plus enable Managed Identity for later labs.

### Prerequisites
Lab 1 completed. You need **Application Administrator** or **Global Administrator** rights in Microsoft Entra ID to create app registrations (or ask your tenant admin to do this step for you).

### Part A — Azure Portal
1. Portal search → **Microsoft Entra ID** → left menu **App registrations** → **+ New registration**.
2. Name: `sp-aif-labs-app`. Supported account types: **Single tenant**. Redirect URI: leave blank. Click **Register**.
3. Note the **Application (client) ID** and **Directory (tenant) ID** shown on the Overview page.
4. Left menu **Certificates & secrets** → **+ New client secret** → description `lab-secret`, expiry `180 days` → **Add**. **Copy the secret value immediately** (shown only once).
5. Go to **Resource groups → rg-aif-labs → Access control (IAM)** → **+ Add** → **Add role assignment**.
   - Role: **Cognitive Services OpenAI User** → Members: select `sp-aif-labs-app` → **Review + assign**.
   - Repeat, adding role **Search Index Data Contributor** for the same principal (needed in Lab 7/8).
   - Repeat, adding role **Storage Blob Data Contributor** (needed in Lab 3/8).
6. (For later labs) Also assign **Contributor** on `rg-aif-labs` to your own user account if not already the case, so you can create resources.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
SUB_ID=$(az account show --query id -o tsv)

# Create the app registration + service principal
az ad app create --display-name "sp-aif-labs-app" --query appId -o tsv > /tmp/appid.txt
APP_ID=$(cat /tmp/appid.txt)
az ad sp create --id $APP_ID
TENANT_ID=$(az account show --query tenantId -o tsv)

# Create a client secret (valid 180 days)
SECRET=$(az ad app credential reset --id $APP_ID --years 0.5 --query password -o tsv)
echo "AppId=$APP_ID TenantId=$TENANT_ID Secret=$SECRET"   # store these safely, e.g., in Key Vault (Lab 3)

# Assign least-privilege roles scoped to the resource group
az role assignment create --assignee $APP_ID --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/$SUB_ID/resourceGroups/$RG

az role assignment create --assignee $APP_ID --role "Search Index Data Contributor" \
  --scope /subscriptions/$SUB_ID/resourceGroups/$RG

az role assignment create --assignee $APP_ID --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$SUB_ID/resourceGroups/$RG

az role assignment list --assignee $APP_ID --output table
```

### Part C — Azure PowerShell
```powershell
$RG    = "rg-aif-labs"
$SubId = (Get-AzContext).Subscription.Id

# App registration + service principal
$App = New-AzADApplication -DisplayName "sp-aif-labs-app"
$Sp  = New-AzADServicePrincipal -ApplicationId $App.AppId

# Client secret
$Secret = New-AzADAppCredential -ApplicationId $App.AppId -EndDate (Get-Date).AddMonths(6)
Write-Host "AppId=$($App.AppId) TenantId=$((Get-AzContext).Tenant.Id) Secret=$($Secret.SecretText)"

# Role assignments scoped to the resource group
New-AzRoleAssignment -ApplicationId $App.AppId -RoleDefinitionName "Cognitive Services OpenAI User" `
  -Scope "/subscriptions/$SubId/resourceGroups/$RG"

New-AzRoleAssignment -ApplicationId $App.AppId -RoleDefinitionName "Search Index Data Contributor" `
  -Scope "/subscriptions/$SubId/resourceGroups/$RG"

New-AzRoleAssignment -ApplicationId $App.AppId -RoleDefinitionName "Storage Blob Data Contributor" `
  -Scope "/subscriptions/$SubId/resourceGroups/$RG"

Get-AzRoleAssignment -ObjectId $Sp.Id | Format-Table RoleDefinitionName, Scope
```

### ✅ Validation
`az role assignment list --assignee $APP_ID` (or the PowerShell equivalent) shows exactly the 3 roles above, scoped only to `rg-aif-labs` — never at subscription scope, following least privilege.

### Security notes
- Prefer **Managed Identity** over client secrets wherever the compute is Azure-hosted (Function App, AKS pod, VM) — you'll enable this in Labs 10 and 11 instead of using this service principal's secret.
- Never commit `Secret` to source control. Store it in Key Vault (next lab) and reference it from there.

### Cleanup
Keep the app registration for use in later labs. To remove: `az ad app delete --id $APP_ID` / `Remove-AzADApplication -ApplicationId $App.AppId`.

---

## Lab 3: Azure Storage & Key Vault for AI Data

### Objective
Provision a Storage Account (for source documents used by RAG) and a Key Vault (to hold secrets, keys, and connection strings) — the secure backbone every later lab pulls credentials from.

### Prerequisites
Labs 1–2 completed.

### Part A — Azure Portal

**Storage Account:**
1. Portal search → **Storage accounts** → **+ Create**.
2. Resource group: `rg-aif-labs`. Storage account name: `staifablabs<random4digits>` (must be globally unique, lowercase, no dashes). Region: same as your RG. Performance: **Standard**. Redundancy: **LRS** (lab-grade).
3. **Next: Advanced** → enable **Hierarchical namespace** only if you plan Data Lake features (not required for this guide — leave off).
4. **Review + create** → **Create**.
5. Once deployed → **Containers** (left menu) → **+ Container** → name `rag-documents` → Public access level: **Private**.
6. Upload a few sample PDFs/docs into `rag-documents` (Upload button) — you'll index these in Lab 8.

**Key Vault:**
1. Portal search → **Key vaults** → **+ Create**.
2. Resource group: `rg-aif-labs`. Key vault name: `kv-aifab-<random4digits>` (globally unique). Region: same. Pricing tier: **Standard**.
3. **Next: Access configuration** → Permission model: **Azure role-based access control (recommended)**.
4. **Review + create** → **Create**.
5. Assign yourself the role **Key Vault Secrets Officer** on this vault (Access control (IAM) → Add role assignment) so you can add secrets.
6. Left menu **Secrets** → **+ Generate/Import** → name `sp-client-secret`, value = the client secret from Lab 2 → **Create**. Repeat for `storage-connection-string` (get the value from Storage Account → **Access keys**).

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"
STORAGE="staifablabs$RANDOM"
KEYVAULT="kv-aifab-$RANDOM"

# Storage account
az storage account create \
  --name $STORAGE --resource-group $RG --location $LOCATION \
  --sku Standard_LRS --kind StorageV2

# Container for RAG source docs
az storage container create \
  --account-name $STORAGE --name rag-documents --auth-mode login

# Upload sample files (replace with your own path)
az storage blob upload-batch \
  --account-name $STORAGE --destination rag-documents --source ./sample-docs --auth-mode login

# Key Vault (RBAC-based)
az keyvault create \
  --name $KEYVAULT --resource-group $RG --location $LOCATION \
  --enable-rbac-authorization true

# Give yourself rights to manage secrets
MY_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee $MY_OBJECT_ID --role "Key Vault Secrets Officer" \
  --scope $(az keyvault show -n $KEYVAULT -g $RG --query id -o tsv)

# Store secrets
STORAGE_CONN=$(az storage account show-connection-string -n $STORAGE -g $RG --query connectionString -o tsv)
az keyvault secret set --vault-name $KEYVAULT --name storage-connection-string --value "$STORAGE_CONN"
az keyvault secret set --vault-name $KEYVAULT --name sp-client-secret --value "$SECRET"   # from Lab 2

echo "Storage=$STORAGE  KeyVault=$KEYVAULT"
```

### Part C — Azure PowerShell
```powershell
$RG       = "rg-aif-labs"
$Location = "eastus2"
$Storage  = "staifablabs$(Get-Random -Maximum 9999)"
$KeyVault = "kv-aifab-$(Get-Random -Maximum 9999)"

# Storage account
New-AzStorageAccount -ResourceGroupName $RG -Name $Storage -Location $Location `
  -SkuName Standard_LRS -Kind StorageV2

$Ctx = (Get-AzStorageAccount -ResourceGroupName $RG -Name $Storage).Context
New-AzStorageContainer -Name "rag-documents" -Context $Ctx -Permission Off

# Upload sample files
Get-ChildItem -Path .\sample-docs -File | ForEach-Object {
  Set-AzStorageBlobContent -File $_.FullName -Container "rag-documents" -Blob $_.Name -Context $Ctx
}

# Key Vault (RBAC-based)
New-AzKeyVault -Name $KeyVault -ResourceGroupName $RG -Location $Location -EnableRbacAuthorization

$MyObjectId = (Get-AzADUser -SignedIn).Id
New-AzRoleAssignment -ObjectId $MyObjectId -RoleDefinitionName "Key Vault Secrets Officer" `
  -Scope (Get-AzKeyVault -VaultName $KeyVault).ResourceId

# Store secrets
$StorageKey  = (Get-AzStorageAccountKey -ResourceGroupName $RG -Name $Storage)[0].Value
$StorageConn = "DefaultEndpointsProtocol=https;AccountName=$Storage;AccountKey=$StorageKey;EndpointSuffix=core.windows.net"
Set-AzKeyVaultSecret -VaultName $KeyVault -Name "storage-connection-string" -SecretValue (ConvertTo-SecureString $StorageConn -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $KeyVault -Name "sp-client-secret" -SecretValue (ConvertTo-SecureString $Secret.SecretText -AsPlainText -Force)

Write-Host "Storage=$Storage  KeyVault=$KeyVault"
```

### ✅ Validation
- Portal → Storage account → Containers shows `rag-documents` with your uploaded files.
- Portal → Key vault → Secrets shows `storage-connection-string` and `sp-client-secret`, each with one version.
- `az keyvault secret list --vault-name $KEYVAULT -o table` / `Get-AzKeyVaultSecret -VaultName $KeyVault` returns both.

### Cleanup
Keep both — reused in Labs 8, 10, 11, 12. Teardown is in the [Appendix](#appendix-full-cleanup-script).

---

## Lab 4: Azure AI Foundry Hub & Project

### Objective
Provision an Azure AI Foundry **Hub** (the shared infrastructure: connections, compute, security) and a **Project** inside it (the workspace where you build, test, and deploy AI apps).

### Prerequisites
Labs 1–3 completed.

### Part A — Azure Portal
1. Go to https://ai.azure.com (Azure AI Foundry portal) and sign in with the same account.
2. Click **+ Create new** → **Hub**.
3. Hub name: `hub-aifab`. Subscription: yours. Resource group: `rg-aif-labs`. Region: same as before (must support Azure OpenAI). Leave default **Storage account** / **Key Vault** as "create new," or point to the ones from Lab 3 under **Advanced options** → **Resources** if you want to reuse them.
4. Click **Create** and wait for deployment (2–5 minutes).
5. Once inside the hub, click **+ New project**. Project name: `proj-aifab-rag`. Confirm the hub is `hub-aifab` → **Create**.
6. Open the project → left menu **Overview** shows the **Project connection string**/**Endpoint** — copy it, you'll need it in Lab 8/9.
7. Left menu **Management center → Connected resources** confirms the hub is linked to your Storage, Key Vault, and (soon) Azure OpenAI resource.

### Part B — Azure CLI
Azure AI Foundry hubs/projects are Azure Machine Learning workspaces under the hood, managed with the `az ml` extension.

```bash
az extension add -n ml --upgrade

RG="rg-aif-labs"
LOCATION="eastus2"
HUB="hub-aifab"
PROJECT="proj-aifab-rag"
STORAGE="<storage-account-name-from-lab-3>"
KEYVAULT="<keyvault-name-from-lab-3>"

# Create the Hub (kind=hub)
az ml workspace create \
  --kind hub \
  --resource-group $RG \
  --name $HUB \
  --location $LOCATION \
  --storage-account $(az storage account show -n $STORAGE -g $RG --query id -o tsv) \
  --key-vault $(az keyvault show -n $KEYVAULT -g $RG --query id -o tsv)

HUB_ID=$(az ml workspace show -n $HUB -g $RG --query id -o tsv)

# Create the Project inside the Hub
az ml workspace create \
  --kind project \
  --resource-group $RG \
  --name $PROJECT \
  --location $LOCATION \
  --hub-id $HUB_ID

az ml workspace show -n $PROJECT -g $RG --query "{name:name,kind:kind,hub:hubResourceId}" -o jsonc
```

### Part C — Azure PowerShell
The `Az` module does not yet expose hub/project cmdlets directly for every property, so the supported pattern is to call the same `az ml` CLI extension from within PowerShell (PowerShell can invoke any CLI command) — or use ARM templates via `New-AzResourceGroupDeployment`. Both are shown; pick one.

**Option 1 — invoke `az ml` from PowerShell (simplest, identical result to Part B):**
```powershell
az extension add -n ml --upgrade

$RG        = "rg-aif-labs"
$Location  = "eastus2"
$Hub       = "hub-aifab"
$Project   = "proj-aifab-rag"
$Storage   = "<storage-account-name-from-lab-3>"
$KeyVault  = "<keyvault-name-from-lab-3>"

$StorageId  = az storage account show -n $Storage -g $RG --query id -o tsv
$KeyVaultId = az keyvault show -n $KeyVault -g $RG --query id -o tsv

az ml workspace create --kind hub --resource-group $RG --name $Hub --location $Location `
  --storage-account $StorageId --key-vault $KeyVaultId

$HubId = az ml workspace show -n $Hub -g $RG --query id -o tsv
az ml workspace create --kind project --resource-group $RG --name $Project --location $Location --hub-id $HubId
```

**Option 2 — pure ARM/Bicep deployment via PowerShell:**
```powershell
$RG = "rg-aif-labs"
New-AzResourceGroupDeployment -ResourceGroupName $RG `
  -TemplateUri "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/machine-learning-workspace-hub-project/main.bicep" `
  -hubName "hub-aifab" -projectName "proj-aifab-rag" -location "eastus2"
```
> If the quickstart template path above has moved, search "Azure AI Foundry hub bicep quickstart" on https://github.com/Azure/azure-quickstart-templates and substitute the current URI — quickstart template locations are updated periodically by Microsoft.

### ✅ Validation
- https://ai.azure.com shows `hub-aifab` → `proj-aifab-rag` with status **Succeeded**.
- `az ml workspace show -n proj-aifab-rag -g rg-aif-labs --query provisioningState -o tsv` returns `Succeeded`.
- The project's **Connected resources** tab lists your Storage and Key Vault from Lab 3.

### Cleanup
Keep both — every remaining lab builds on this project. Teardown is in the [Appendix](#appendix-full-cleanup-script).

---

## Lab 5: Deploy Azure OpenAI Models (Chat + Embeddings)

### Objective
Create an Azure OpenAI resource, deploy a chat model (e.g., `gpt-4o`) and an embeddings model (e.g., `text-embedding-3-large`), and test both with a live API call.

### Prerequisites
Labs 1–4 completed. Your subscription must have Azure OpenAI access approved (most pay-as-you-go subscriptions now have it by default; if not, apply at https://aka.ms/oai/access).

### Part A — Azure Portal
1. Portal search → **Azure OpenAI** → **+ Create**.
2. Resource group: `rg-aif-labs`. Region: pick one with quota for `gpt-4o` (check https://learn.microsoft.com/azure/ai-services/openai/concepts/models for current region availability). Name: `aoai-aifab`. Pricing tier: **Standard S0**.
3. **Next: Network** → **All networks** (lab-grade; use Private Endpoint in production) → **Next: Tags** → add same tags as Lab 1 → **Review + create** → **Create**.
4. Once deployed, click **Go to resource** → **Go to Azure AI Foundry portal** (or open https://ai.azure.com and select this resource under your project's **Connected resources**, adding it as a connection if not already linked).
5. In Azure AI Foundry → left menu **Deployments** → **+ Deploy model** → **Deploy base model** → choose `gpt-4o` → deployment name `gpt-4o-chat` → capacity per your quota (start with 10K TPM) → **Deploy**.
6. Repeat: **+ Deploy model** → `text-embedding-3-large` → deployment name `text-embedding-3-large` → **Deploy**.
7. Go to **Playground → Chat**, select `gpt-4o-chat`, type a test prompt, click **Run** to confirm it responds.
8. Back on the Azure OpenAI resource in the Azure Portal → left menu **Keys and Endpoint** → copy **KEY 1** and **Endpoint** — store both in Key Vault (see CLI snippet below) rather than pasting into code.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"          # must support gpt-4o in your subscription
AOAI="aoai-aifab"
KEYVAULT="<keyvault-name-from-lab-3>"

# Create the Azure OpenAI resource
az cognitiveservices account create \
  --name $AOAI \
  --resource-group $RG \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0 \
  --custom-domain $AOAI

# Deploy a chat model
az cognitiveservices account deployment create \
  --name $AOAI --resource-group $RG \
  --deployment-name gpt-4o-chat \
  --model-name gpt-4o --model-version "2024-11-20" --model-format OpenAI \
  --sku-name "Standard" --sku-capacity 10

# Deploy an embeddings model
az cognitiveservices account deployment create \
  --name $AOAI --resource-group $RG \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large --model-version "1" --model-format OpenAI \
  --sku-name "Standard" --sku-capacity 10

# Retrieve endpoint + key, store in Key Vault
ENDPOINT=$(az cognitiveservices account show -n $AOAI -g $RG --query properties.endpoint -o tsv)
KEY=$(az cognitiveservices account keys list -n $AOAI -g $RG --query key1 -o tsv)
az keyvault secret set --vault-name $KEYVAULT --name "aoai-endpoint" --value "$ENDPOINT"
az keyvault secret set --vault-name $KEYVAULT --name "aoai-key" --value "$KEY"

# Quick smoke test with curl
curl -s "$ENDPOINT/openai/deployments/gpt-4o-chat/chat/completions?api-version=2024-10-21" \
  -H "Content-Type: application/json" -H "api-key: $KEY" \
  -d '{"messages":[{"role":"user","content":"Say hello in one sentence."}]}'
```

### Part C — Azure PowerShell
```powershell
$RG       = "rg-aif-labs"
$Location = "eastus2"
$Aoai     = "aoai-aifab"
$KeyVault = "<keyvault-name-from-lab-3>"

# Create the Azure OpenAI resource
New-AzCognitiveServicesAccount -ResourceGroupName $RG -Name $Aoai -Type "OpenAI" `
  -SkuName "S0" -Location $Location -CustomSubdomainName $Aoai

# Deploy a chat model
New-AzCognitiveServicesAccountDeployment -ResourceGroupName $RG -AccountName $Aoai `
  -Name "gpt-4o-chat" -Model @{Name="gpt-4o"; Version="2024-11-20"; Format="OpenAI"} `
  -Sku @{Name="Standard"; Capacity=10}

# Deploy an embeddings model
New-AzCognitiveServicesAccountDeployment -ResourceGroupName $RG -AccountName $Aoai `
  -Name "text-embedding-3-large" -Model @{Name="text-embedding-3-large"; Version="1"; Format="OpenAI"} `
  -Sku @{Name="Standard"; Capacity=10}

# Retrieve endpoint + key, store in Key Vault
$Endpoint = (Get-AzCognitiveServicesAccount -ResourceGroupName $RG -Name $Aoai).Endpoint
$Key      = (Get-AzCognitiveServicesAccountKey -ResourceGroupName $RG -Name $Aoai).Key1
Set-AzKeyVaultSecret -VaultName $KeyVault -Name "aoai-endpoint" -SecretValue (ConvertTo-SecureString $Endpoint -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $KeyVault -Name "aoai-key" -SecretValue (ConvertTo-SecureString $Key -AsPlainText -Force)

# Quick smoke test
$Headers = @{ "api-key" = $Key; "Content-Type" = "application/json" }
$Body    = @{ messages = @(@{ role = "user"; content = "Say hello in one sentence." }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$Endpoint/openai/deployments/gpt-4o-chat/chat/completions?api-version=2024-10-21" -Method Post -Headers $Headers -Body $Body
```

### ✅ Validation
- Both deployments show **Succeeded** state: `az cognitiveservices account deployment list -n $AOAI -g $RG -o table`.
- The curl/`Invoke-RestMethod` smoke test returns a JSON response with a `choices[0].message.content` field containing a greeting.
- Key Vault now holds `aoai-endpoint` and `aoai-key` secrets.

### Cleanup
Keep — every remaining lab depends on these deployments. Teardown is in the [Appendix](#appendix-full-cleanup-script).

---

## Lab 6: Prompt Engineering & Playground Testing

### Objective
Practice prompt-engineering techniques (system prompts, few-shot examples, grounding, temperature/top-p tuning) using the Azure AI Foundry Playground, then reproduce the same calls via CLI and PowerShell so you can automate regression testing of prompts.

### Prerequisites
Lab 5 completed.

### Part A — Azure Portal (AI Foundry Playground)
1. Open https://ai.azure.com → your project `proj-aifab-rag` → left menu **Playgrounds → Chat**.
2. Deployment: select `gpt-4o-chat`.
3. In **System message**, enter:
   ```
   You are a precise IT infrastructure assistant. Answer only from provided context.
   If the answer isn't in the context, say "I don't have that information."
   Keep answers under 100 words.
   ```
4. In the chat box, ask a question unrelated to any context (e.g., "What's the capital of France?") — observe the model still answers freely (system prompt alone doesn't restrict knowledge, only tone/behavior).
5. Click **Parameters** (right panel): set **Temperature = 0.2** (more deterministic), **Top P = 0.9**, **Max response = 300** tokens. Re-run the same question — compare consistency across 3 runs.
6. Add a **few-shot example**: in the chat, manually add a User/Assistant pair showing your desired answer format, then ask a new but similar question — observe the model mimics the format.
7. Click **View code** (top-right) — Azure AI Foundry generates ready-to-use Python/CLI/REST snippets for the exact configuration you just tested. Copy the Python snippet; you'll reuse it in Lab 8.

### Part B — Azure CLI (scripted prompt testing)
CLI doesn't have a "playground," but you can script the same completions call for repeatable prompt regression tests:
```bash
ENDPOINT=$(az keyvault secret show --vault-name <KEYVAULT> --name aoai-endpoint --query value -o tsv)
KEY=$(az keyvault secret show --vault-name <KEYVAULT> --name aoai-key --query value -o tsv)

test_prompt () {
  local user_msg="$1"
  curl -s "$ENDPOINT/openai/deployments/gpt-4o-chat/chat/completions?api-version=2024-10-21" \
    -H "Content-Type: application/json" -H "api-key: $KEY" \
    -d "{
      \"messages\": [
        {\"role\":\"system\",\"content\":\"You are a precise IT infrastructure assistant. Answer only from provided context. If unknown, say so. Under 100 words.\"},
        {\"role\":\"user\",\"content\":\"$user_msg\"}
      ],
      \"temperature\": 0.2, \"top_p\": 0.9, \"max_tokens\": 300
    }" | jq -r '.choices[0].message.content'
}

test_prompt "Explain what Azure AI Search is."
test_prompt "What is the boiling point of nitrogen?"
```
Run this script for a fixed set of prompts before/after any system-prompt change to catch regressions — this is the basis of prompt version control.

### Part C — Azure PowerShell (scripted prompt testing)
```powershell
$Endpoint = Get-AzKeyVaultSecret -VaultName "<KEYVAULT>" -Name "aoai-endpoint" -AsPlainText
$Key      = Get-AzKeyVaultSecret -VaultName "<KEYVAULT>" -Name "aoai-key" -AsPlainText

function Test-Prompt {
  param([string]$UserMessage)
  $Body = @{
    messages = @(
      @{ role = "system"; content = "You are a precise IT infrastructure assistant. Answer only from provided context. If unknown, say so. Under 100 words." },
      @{ role = "user";   content = $UserMessage }
    )
    temperature = 0.2
    top_p       = 0.9
    max_tokens  = 300
  } | ConvertTo-Json -Depth 6

  $Headers = @{ "api-key" = $Key; "Content-Type" = "application/json" }
  $Result = Invoke-RestMethod -Uri "$Endpoint/openai/deployments/gpt-4o-chat/chat/completions?api-version=2024-10-21" -Method Post -Headers $Headers -Body $Body
  return $Result.choices[0].message.content
}

Test-Prompt -UserMessage "Explain what Azure AI Search is."
Test-Prompt -UserMessage "What is the boiling point of nitrogen?"
```

### Prompt-engineering checklist to practice in this lab
- **Role/system prompt** — define persona, constraints, output format (JSON, bullet list, word limit).
- **Few-shot examples** — 2–3 input/output pairs to anchor style.
- **Grounding instructions** — "answer only from context," "cite the source," "say 'I don't know' if unsure" (reduces hallucination).
- **Decoding parameters** — lower `temperature`/`top_p` for factual/deterministic tasks; raise for creative tasks.
- **Chain-of-thought / step-by-step** — ask the model to "think step by step" internally then give only the final answer, for multi-step reasoning tasks.
- **Structured output** — request strict JSON with a schema description, then validate with a JSON parser in code (you'll do this in Lab 8/9).

### ✅ Validation
You can reproduce, from CLI or PowerShell alone (no Portal), the exact same response behavior you tuned in the Playground — proving the configuration is captured as code, not "trapped" in the UI.

### Cleanup
Nothing to delete — this lab only exercises the existing deployment.

---

## Lab 7: Azure AI Search — Vector & Hybrid Search Index

### Objective
Provision an Azure AI Search service, create a vector index, and load embeddings so it can serve as the retrieval layer of a RAG pipeline (Lab 8).

### Prerequisites
Labs 3 and 5 completed.

### Part A — Azure Portal
1. Portal search → **Azure AI Search** → **+ Create**.
2. Resource group: `rg-aif-labs`. Service name: `srch-aifab` (globally unique). Location: same region. Pricing tier: **Basic** (supports vector search; use **Free** only for pure keyword tests — Free tier limits vector index size).
3. **Review + create** → **Create**.
4. Once deployed → open the resource → left menu **Indexes** → **+ Add index** (or better: use **Import and vectorize data** wizard):
   - Click **Import and vectorize data** → Data source: **Azure Blob Storage** → select the `staifablabs...` account and `rag-documents` container from Lab 3.
   - **Vectorize your text**: choose **Azure OpenAI** → select `aoai-aifab` resource → embedding deployment `text-embedding-3-large`.
   - Index name: `idx-rag-documents`. Schema: keep defaults (chunks + vector + metadata fields).
   - Click **Create** — the wizard automatically creates an **indexer**, **skillset** (chunking + embedding), **data source**, and **index**.
5. Left menu **Search explorer** → select `idx-rag-documents` → run a query like `search=*&$top=3` to confirm documents were indexed. Try a vector query by switching the query type to **Semantic** or supplying a `vectorQueries` JSON block.

### Part B — Azure CLI
The CLI can create the Search service; index/indexer/skillset JSON definitions are pushed via `az search` (data-plane, if installed) or REST/SDK. Both are shown.

```bash
RG="rg-aif-labs"
LOCATION="eastus2"
SEARCH="srch-aifab"

# Create the Azure AI Search service
az search service create \
  --name $SEARCH --resource-group $RG --location $LOCATION \
  --sku basic --partition-count 1 --replica-count 1

# Get admin key (data-plane auth)
ADMIN_KEY=$(az search admin-key show --resource-group $RG --service-name $SEARCH --query primaryKey -o tsv)
SEARCH_ENDPOINT="https://$SEARCH.search.windows.net"

# Define the vector index via REST (index schema)
curl -s -X PUT "$SEARCH_ENDPOINT/indexes/idx-rag-documents?api-version=2024-07-01" \
  -H "Content-Type: application/json" -H "api-key: $ADMIN_KEY" \
  -d '{
    "name": "idx-rag-documents",
    "fields": [
      {"name":"id","type":"Edm.String","key":true,"filterable":true},
      {"name":"content","type":"Edm.String","searchable":true},
      {"name":"metadata_storage_name","type":"Edm.String","filterable":true,"searchable":true},
      {"name":"contentVector","type":"Collection(Edm.Single)","searchable":true,"dimensions":3072,
        "vectorSearchProfile":"vp-default"}
    ],
    "vectorSearch": {
      "algorithms": [{"name":"hnsw-default","kind":"hnsw"}],
      "profiles": [{"name":"vp-default","algorithm":"hnsw-default"}]
    }
  }'

# Data source pointing at your Storage container
STORAGE_CONN=$(az storage account show-connection-string -n <STORAGE> -g $RG --query connectionString -o tsv)
curl -s -X PUT "$SEARCH_ENDPOINT/datasources/ds-rag-documents?api-version=2024-07-01" \
  -H "Content-Type: application/json" -H "api-key: $ADMIN_KEY" \
  -d "{\"name\":\"ds-rag-documents\",\"type\":\"azureblob\",
       \"credentials\":{\"connectionString\":\"$STORAGE_CONN\"},
       \"container\":{\"name\":\"rag-documents\"}}"

# Indexer that pulls from the data source into the index (add a skillset for chunking+embedding in production;
# see Microsoft Learn "Index and vectorize" tutorial for the full skillset JSON)
curl -s -X PUT "$SEARCH_ENDPOINT/indexers/idxr-rag-documents?api-version=2024-07-01" \
  -H "Content-Type: application/json" -H "api-key: $ADMIN_KEY" \
  -d '{"name":"idxr-rag-documents","dataSourceName":"ds-rag-documents","targetIndexName":"idx-rag-documents"}'

# Check indexer status
curl -s "$SEARCH_ENDPOINT/indexers/idxr-rag-documents/status?api-version=2024-07-01" -H "api-key: $ADMIN_KEY"
```

> For production-grade chunking + vectorization at index time, use the Portal's **Import and vectorize data** wizard (Part A) once to generate the skillset JSON, then export it (**Indexes → idx-rag-documents → ... → Export** or via REST `GET /skillsets/{name}`) and version-control it for CLI/CI redeployment.

### Part C — Azure PowerShell
```powershell
$RG       = "rg-aif-labs"
$Location = "eastus2"
$Search   = "srch-aifab"

# Create the Azure AI Search service
New-AzSearchService -ResourceGroupName $RG -Name $Search -Location $Location `
  -Sku "Basic" -PartitionCount 1 -ReplicaCount 1

# Get admin key
$AdminKey = (Get-AzSearchAdminKeyPair -ResourceGroupName $RG -ServiceName $Search).PrimaryKey
$SearchEndpoint = "https://$Search.search.windows.net"
$Headers = @{ "api-key" = $AdminKey; "Content-Type" = "application/json" }

# Define the vector index (same schema as Part B)
$IndexBody = @{
  name   = "idx-rag-documents"
  fields = @(
    @{ name="id"; type="Edm.String"; key=$true; filterable=$true },
    @{ name="content"; type="Edm.String"; searchable=$true },
    @{ name="metadata_storage_name"; type="Edm.String"; filterable=$true; searchable=$true },
    @{ name="contentVector"; type="Collection(Edm.Single)"; searchable=$true; dimensions=3072; vectorSearchProfile="vp-default" }
  )
  vectorSearch = @{
    algorithms = @(@{ name="hnsw-default"; kind="hnsw" })
    profiles   = @(@{ name="vp-default"; algorithm="hnsw-default" })
  }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "$SearchEndpoint/indexes/idx-rag-documents?api-version=2024-07-01" -Method Put -Headers $Headers -Body $IndexBody

# Data source
$StorageConn = (Get-AzStorageAccount -ResourceGroupName $RG -Name "<STORAGE>").Context.ConnectionString
$DsBody = @{
  name = "ds-rag-documents"; type = "azureblob"
  credentials = @{ connectionString = $StorageConn }
  container   = @{ name = "rag-documents" }
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri "$SearchEndpoint/datasources/ds-rag-documents?api-version=2024-07-01" -Method Put -Headers $Headers -Body $DsBody

# Indexer
$IdxrBody = @{ name="idxr-rag-documents"; dataSourceName="ds-rag-documents"; targetIndexName="idx-rag-documents" } | ConvertTo-Json
Invoke-RestMethod -Uri "$SearchEndpoint/indexers/idxr-rag-documents?api-version=2024-07-01" -Method Put -Headers $Headers -Body $IdxrBody

# Check indexer status
Invoke-RestMethod -Uri "$SearchEndpoint/indexers/idxr-rag-documents/status?api-version=2024-07-01" -Method Get -Headers $Headers
```

### ✅ Validation
- Portal → **Search explorer** on `idx-rag-documents` returns documents for `search=*`.
- Indexer status (CLI/PowerShell REST call) shows `"lastResult": {"status": "success"}`.
- A vector query (`vectorQueries` in the request body with a sample embedding) returns semantically relevant results, not just keyword matches.

### Cleanup
Keep — reused directly in Lab 8. Teardown is in the [Appendix](#appendix-full-cleanup-script).

---

## Lab 8: Build a RAG Pipeline in Python

### Objective
Wire together Azure OpenAI (Lab 5) and Azure AI Search (Lab 7) into a working Retrieval-Augmented Generation pipeline: embed the user's question, retrieve top-k relevant chunks, and ground the LLM's answer in that retrieved context.

### Prerequisites
Labs 3, 5, 7 completed.

### Part A — Azure Portal (verify wiring before coding)
1. https://ai.azure.com → project `proj-aifab-rag` → **Playgrounds → Chat**.
2. Click **Add your data** → **+ Add a data source** → select **Azure AI Search** → choose `srch-aifab` and index `idx-rag-documents` → Search type: **Vector**.
3. Ask a question that should be answerable only from your uploaded documents. Confirm the response includes **citations** back to your source files — this proves retrieval + grounding works end-to-end before you write any code.
4. Click **View code** → copy the generated Python snippet (it already includes the `extra_body` "data_sources" block wiring Search + OpenAI together) as a starting reference for the script below.

### Part B — Azure CLI (environment + running the pipeline)
```bash
# 1) Create and activate a Python virtual environment
python3 -m venv .venv && source .venv/bin/activate
pip install openai azure-search-documents azure-identity python-dotenv

# 2) Pull secrets from Key Vault into a local .env (never commit this file)
KEYVAULT="<keyvault-name-from-lab-3>"
cat > .env <<EOT
AOAI_ENDPOINT=$(az keyvault secret show --vault-name $KEYVAULT --name aoai-endpoint --query value -o tsv)
AOAI_KEY=$(az keyvault secret show --vault-name $KEYVAULT --name aoai-key --query value -o tsv)
SEARCH_ENDPOINT=https://srch-aifab.search.windows.net
SEARCH_KEY=$(az search admin-key show -g rg-aif-labs --service-name srch-aifab --query primaryKey -o tsv)
SEARCH_INDEX=idx-rag-documents
CHAT_DEPLOYMENT=gpt-4o-chat
EMBED_DEPLOYMENT=text-embedding-3-large
EOT
echo ".env written"
```

Create `rag_pipeline.py`:
```python
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.environ["AOAI_ENDPOINT"],
    api_key=os.environ["AOAI_KEY"],
    api_version="2024-10-21",
)

search_client = SearchClient(
    endpoint=os.environ["SEARCH_ENDPOINT"],
    index_name=os.environ["SEARCH_INDEX"],
    credential=AzureKeyCredential(os.environ["SEARCH_KEY"]),
)

def embed(text: str):
    resp = client.embeddings.create(model=os.environ["EMBED_DEPLOYMENT"], input=text)
    return resp.data[0].embedding

def retrieve(question: str, k: int = 3):
    vector = VectorizedQuery(vector=embed(question), k_nearest_neighbors=k, fields="contentVector")
    results = search_client.search(search_text=question, vector_queries=[vector], top=k)
    return [r["content"] for r in results]

def answer(question: str) -> str:
    chunks = retrieve(question)
    context = "\n---\n".join(chunks) if chunks else "No relevant context found."
    system_prompt = (
        "You are an assistant that answers ONLY using the provided context. "
        "If the answer is not in the context, say 'I don't have that information.' "
        "Cite which context chunk you used by number."
    )
    resp = client.chat.completions.create(
        model=os.environ["CHAT_DEPLOYMENT"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    print(answer("Summarize the key points of the uploaded documents."))
```

Run it:
```bash
python rag_pipeline.py
```

### Part C — Azure PowerShell (environment + running the pipeline)
```powershell
# 1) Python venv (PowerShell works the same way on Windows/macOS/Linux)
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1        # on Linux/macOS: source .venv/bin/activate
pip install openai azure-search-documents azure-identity python-dotenv

# 2) Pull secrets from Key Vault into a local .env
$KeyVault = "<keyvault-name-from-lab-3>"
$AoaiEndpoint  = Get-AzKeyVaultSecret -VaultName $KeyVault -Name "aoai-endpoint" -AsPlainText
$AoaiKey       = Get-AzKeyVaultSecret -VaultName $KeyVault -Name "aoai-key" -AsPlainText
$SearchKey     = (Get-AzSearchAdminKeyPair -ResourceGroupName "rg-aif-labs" -ServiceName "srch-aifab").PrimaryKey

@"
AOAI_ENDPOINT=$AoaiEndpoint
AOAI_KEY=$AoaiKey
SEARCH_ENDPOINT=https://srch-aifab.search.windows.net
SEARCH_KEY=$SearchKey
SEARCH_INDEX=idx-rag-documents
CHAT_DEPLOYMENT=gpt-4o-chat
EMBED_DEPLOYMENT=text-embedding-3-large
"@ | Out-File -FilePath .env -Encoding utf8

# 3) Run the same rag_pipeline.py from Part B
python rag_pipeline.py
```

### ✅ Validation
- Running `rag_pipeline.py` prints a grounded answer that reflects content from your uploaded documents, not generic model knowledge.
- Ask an out-of-scope question (e.g., about a topic never uploaded) and confirm the pipeline correctly responds "I don't have that information."

### Cleanup
No extra resources created beyond a local `.venv` and `.env` — delete both when done: `rm -rf .venv .env` (Linux/macOS) or `Remove-Item -Recurse .venv, .env` (PowerShell). **Never commit `.env` to Git.**

---

## Lab 9: Build an AI Agent with Azure AI Foundry Agent Service

### Objective
Create a stateful AI Agent with tool-calling (code interpreter + your Lab 7 search index as a "File Search"/knowledge tool), then invoke it programmatically.

### Prerequisites
Labs 4, 5, 7 completed.

### Part A — Azure Portal
1. https://ai.azure.com → project `proj-aifab-rag` → left menu **Agents** → **+ New agent**.
2. Name: `agent-infra-assistant`. Deployment: `gpt-4o-chat`. Instructions:
   ```
   You are an infrastructure operations assistant. Use the knowledge tool to answer
   questions about our runbooks. Use the code interpreter for any calculation or
   data-transformation request. Always state which tool you used.
   ```
3. Under **Knowledge**, click **+ Add** → **Azure AI Search** → select `srch-aifab` / `idx-rag-documents` (reuses Lab 7).
4. Under **Actions**, enable **Code interpreter**.
5. Click **Create**, then use the built-in **Test in playground** chat panel: ask a knowledge question, then ask it to "calculate the average of 12, 45, 78" to confirm the code-interpreter tool triggers.
6. Click **View code** to get the Python snippet for invoking this exact agent by ID — copy the `agent_id` shown in the Overview tab.

### Part B — Azure CLI (programmatic agent invocation)
The Agent Service is invoked through the Azure AI Foundry SDK; CLI's role here is environment/credential setup, then Python does the call (identical pattern to Lab 8 — CLI/PowerShell provision credentials, SDK code drives the AI-specific logic).
```bash
pip install azure-ai-projects azure-identity

PROJECT_CONN_STRING=$(az ml workspace show -n proj-aifab-rag -g rg-aif-labs --query discoveryUrl -o tsv)
echo "Use the project endpoint shown in AI Foundry portal Overview tab; discoveryUrl above helps confirm the workspace region/host."
```
```python
# invoke_agent.py
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str="<PROJECT_CONNECTION_STRING_FROM_PORTAL_OVERVIEW>",
)

agent = project.agents.get_agent("<AGENT_ID_FROM_PORTAL>")
thread = project.agents.create_thread()
project.agents.create_message(thread_id=thread.id, role="user", content="What does our runbook say about PostgreSQL restarts?")
run = project.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)

messages = project.agents.list_messages(thread_id=thread.id)
print(messages.data[0].content[0].text.value)
```
```bash
az login   # DefaultAzureCredential picks up your az CLI session automatically
python invoke_agent.py
```

### Part C — Azure PowerShell (programmatic agent invocation)
```powershell
Connect-AzAccount   # DefaultAzureCredential in the Python SDK can also use this token via Azure CLI/PowerShell chained credential

pip install azure-ai-projects azure-identity
python invoke_agent.py   # same script as Part B — PowerShell's role is auth + environment, identical pattern to every prior lab
```

### ✅ Validation
- The agent's response cites your runbook content (proves the Knowledge tool fired).
- Asking it a math/data question returns a **code interpreter** result (visible as a distinct tool-call step in `list_messages` output or the Portal thread view).

### Cleanup
Delete the agent from the Portal (Agents → `agent-infra-assistant` → **Delete**) when no longer needed, or leave it — it costs nothing when idle beyond token usage.

---

## Lab 10: Deploy the AI App as an Azure Function API

### Objective
Wrap the Lab 8 RAG pipeline in an HTTP-triggered Azure Function, deploy it, secure it with Managed Identity (no more keys in code), and call it as a REST API.

### Prerequisites
Labs 3, 5, 7, 8 completed. Azure Functions Core Tools installed (Lab 0).

### Step 1 — Scaffold the function app locally (all platforms, same commands)
```bash
func init rag-function-app --python
cd rag-function-app
func new --name AskQuestion --template "HTTP trigger" --authlevel function
```
Edit `AskQuestion/__init__.py` to reuse the `answer()` logic from Lab 8 (import via a shared `rag_pipeline.py` module placed in the project root), reading secrets from environment variables (App Settings) instead of `.env`:
```python
import json
import azure.functions as func
from rag_pipeline import answer   # reuse Lab 8 logic, refactored to read os.environ directly

def main(req: func.HttpRequest) -> func.HttpResponse:
    question = req.params.get("question") or req.get_json().get("question")
    if not question:
        return func.HttpResponse("Pass a 'question' parameter.", status_code=400)
    return func.HttpResponse(json.dumps({"answer": answer(question)}), mimetype="application/json")
```
Add `azure.identity`, `openai`, `azure-search-documents` to `requirements.txt`.

### Part A — Azure Portal (create the Function App resource)
1. Portal search → **Function App** → **+ Create**.
2. Resource group: `rg-aif-labs`. Function App name: `func-aifab-rag` (globally unique). Runtime stack: **Python 3.11**. Region: same as before. Hosting: **Consumption (Serverless)** for lab cost, or **Premium** for production VNET integration.
3. **Next: Storage** → select the Storage account from Lab 3 (or create a new one dedicated to Functions).
4. **Review + create** → **Create**.
5. Once deployed → open resource → left menu **Identity** → **System assigned** → toggle **On** → **Save**. Copy the generated **Object (principal) ID**.
6. Go to `rg-aif-labs` → **Access control (IAM)** → **+ Add role assignment** → role **Cognitive Services OpenAI User** → assign to the Function App's managed identity (search by name `func-aifab-rag`). Repeat for **Search Index Data Reader**.
7. Left menu **Configuration → Application settings** → **+ New application setting** for each: `AOAI_ENDPOINT`, `SEARCH_ENDPOINT`, `SEARCH_INDEX`, `CHAT_DEPLOYMENT`, `EMBED_DEPLOYMENT` (values, no keys needed now — code will use `DefaultAzureCredential` against the managed identity instead of API keys). **Save**.
8. Left menu **Deployment Center** or use `func azure functionapp publish` from your terminal (Part B) to push code.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"
FUNCAPP="func-aifab-rag"
STORAGE="<storage-account-name-from-lab-3>"

az functionapp create \
  --resource-group $RG --consumption-plan-location $LOCATION \
  --runtime python --runtime-version 3.11 --functions-version 4 \
  --name $FUNCAPP --storage-account $STORAGE --os-type Linux

# Enable system-assigned managed identity
az functionapp identity assign --name $FUNCAPP --resource-group $RG
PRINCIPAL_ID=$(az functionapp identity show --name $FUNCAPP --resource-group $RG --query principalId -o tsv)

# Grant least-privilege roles to the managed identity
SUB_ID=$(az account show --query id -o tsv)
az role assignment create --assignee $PRINCIPAL_ID --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/$SUB_ID/resourceGroups/$RG
az role assignment create --assignee $PRINCIPAL_ID --role "Search Index Data Reader" \
  --scope /subscriptions/$SUB_ID/resourceGroups/$RG

# App settings (no secrets needed — DefaultAzureCredential uses the managed identity)
az functionapp config appsettings set --name $FUNCAPP --resource-group $RG --settings \
  AOAI_ENDPOINT="https://aoai-aifab.openai.azure.com/" \
  SEARCH_ENDPOINT="https://srch-aifab.search.windows.net" \
  SEARCH_INDEX="idx-rag-documents" \
  CHAT_DEPLOYMENT="gpt-4o-chat" \
  EMBED_DEPLOYMENT="text-embedding-3-large"

# Deploy the code (run from inside rag-function-app/)
func azure functionapp publish $FUNCAPP

# Test
FUNC_URL=$(az functionapp function show --name $FUNCAPP --resource-group $RG --function-name AskQuestion --query invokeUrlTemplate -o tsv)
FUNC_KEY=$(az functionapp function keys list --name $FUNCAPP --resource-group $RG --function-name AskQuestion --query default -o tsv)
curl "${FUNC_URL}?code=${FUNC_KEY}&question=Summarize+the+uploaded+documents"
```

### Part C — Azure PowerShell
```powershell
$RG      = "rg-aif-labs"
$Location = "eastus2"
$FuncApp = "func-aifab-rag"
$Storage = "<storage-account-name-from-lab-3>"

New-AzFunctionApp -ResourceGroupName $RG -Name $FuncApp -StorageAccountName $Storage `
  -Location $Location -Runtime Python -RuntimeVersion 3.11 -FunctionsVersion 4 -OSType Linux

# Enable managed identity
Update-AzFunctionApp -ResourceGroupName $RG -Name $FuncApp -IdentityType SystemAssigned
$PrincipalId = (Get-AzFunctionApp -ResourceGroupName $RG -Name $FuncApp).IdentityPrincipalId

# Grant least-privilege roles
$SubId = (Get-AzContext).Subscription.Id
New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName "Cognitive Services OpenAI User" -Scope "/subscriptions/$SubId/resourceGroups/$RG"
New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName "Search Index Data Reader" -Scope "/subscriptions/$SubId/resourceGroups/$RG"

# App settings
Update-AzFunctionAppSetting -ResourceGroupName $RG -Name $FuncApp -AppSetting @{
  AOAI_ENDPOINT     = "https://aoai-aifab.openai.azure.com/"
  SEARCH_ENDPOINT   = "https://srch-aifab.search.windows.net"
  SEARCH_INDEX      = "idx-rag-documents"
  CHAT_DEPLOYMENT   = "gpt-4o-chat"
  EMBED_DEPLOYMENT  = "text-embedding-3-large"
}

# Deploy code (run from inside rag-function-app/, uses Core Tools CLI, same as Part B)
func azure functionapp publish $FuncApp

# Test
$FuncKey = (Invoke-AzResourceAction -ResourceGroupName $RG -ResourceType "Microsoft.Web/sites/functions" `
  -ResourceName "$FuncApp/AskQuestion" -Action "listkeys" -ApiVersion 2022-03-01 -Force).default
Invoke-RestMethod -Uri "https://$FuncApp.azurewebsites.net/api/AskQuestion?code=$FuncKey&question=Summarize+the+uploaded+documents"
```

### ✅ Validation
- `curl`/`Invoke-RestMethod` against the deployed function returns `{"answer": "..."}` grounded in your documents.
- Portal → Function App → **Identity** shows **Status: On** and the role assignments are visible under `rg-aif-labs → Access control (IAM) → Role assignments`.
- No API keys exist anywhere in App Settings or code — confirms Managed Identity is doing the authentication.

### Cleanup
`az functionapp delete -n $FUNCAPP -g $RG` / `Remove-AzFunctionApp -ResourceGroupName $RG -Name $FuncApp -Force` when done experimenting, or keep for Lab 12/13.

---

## Lab 11: Containerize & Deploy to Azure Kubernetes Service (AKS)

### Objective
Package the RAG API as a Docker container, push it to Azure Container Registry (ACR), deploy it to AKS with Workload Identity (no keys), and expose it via a LoadBalancer/Ingress.

### Prerequisites
Labs 5, 7, 8 completed. Docker, kubectl, Helm installed (Lab 0).

### Step 0 — Create a simple Flask/FastAPI wrapper and Dockerfile
`app.py`:
```python
from fastapi import FastAPI
from rag_pipeline import answer   # from Lab 8, refactored to read env vars

app = FastAPI()

@app.get("/ask")
def ask(question: str):
    return {"answer": answer(question)}

@app.get("/healthz")
def health():
    return {"status": "ok"}
```
`Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Part A — Azure Portal
1. **Create ACR:** Portal search → **Container registries** → **+ Create** → Resource group `rg-aif-labs`, Registry name `acraifab<unique>`, SKU **Basic** → **Review + create** → **Create**.
2. **Create AKS cluster:** Portal search → **Kubernetes services** → **+ Create** → **Create a Kubernetes cluster**.
   - Resource group `rg-aif-labs`, Cluster name `aks-aifab`, Region same, Node size `Standard_D2s_v5`, Node count `2`.
   - **Integrations** tab → Container registry: select `acraifab<unique>` (auto-grants AcrPull to the cluster's kubelet identity).
   - Enable **Azure AD Workload Identity** and **OIDC issuer** under the **Security** tab (needed for keyless auth to Azure OpenAI/Search from pods).
   - **Review + create** → **Create** (takes ~5–10 minutes).
3. Once deployed → **Connect** button on the Overview page shows the exact `az aks get-credentials` command — run it locally (Part B) to get `kubectl` access; Portal alone cannot apply YAML manifests, so CLI/PowerShell + kubectl is required for the deployment step.
4. Use Portal's **Kubernetes resources → Workloads** view afterward to visually confirm your pod is `Running` once deployed via CLI.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"
ACR="acraifab$RANDOM"
AKS="aks-aifab"

# Container registry
az acr create --resource-group $RG --name $ACR --sku Basic

# Build & push the image using ACR Tasks (no local Docker daemon required)
az acr build --registry $ACR --image rag-api:v1 .

# AKS cluster with OIDC issuer + workload identity enabled, attached to ACR
az aks create \
  --resource-group $RG --name $AKS --location $LOCATION \
  --node-count 2 --node-vm-size Standard_D2s_v5 \
  --enable-oidc-issuer --enable-workload-identity \
  --attach-acr $ACR \
  --generate-ssh-keys

# Get kubectl credentials
az aks get-credentials --resource-group $RG --name $AKS

# Set up Workload Identity: federated credential linking a K8s service account to an Azure AD identity
az identity create --resource-group $RG --name id-aifab-workload
IDENTITY_CLIENT_ID=$(az identity show -g $RG -n id-aifab-workload --query clientId -o tsv)
OIDC_ISSUER=$(az aks show -g $RG -n $AKS --query oidcIssuerProfile.issuerUrl -o tsv)

kubectl create namespace rag
kubectl create serviceaccount rag-sa -n rag

az identity federated-credential create \
  --name fed-rag-sa --identity-name id-aifab-workload --resource-group $RG \
  --issuer $OIDC_ISSUER --subject system:serviceaccount:rag:rag-sa --audience api://AzureADTokenExchange

# Grant the identity the same least-privilege roles as before
SUB_ID=$(az account show --query id -o tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show -g $RG -n id-aifab-workload --query principalId -o tsv)
az role assignment create --assignee $IDENTITY_PRINCIPAL_ID --role "Cognitive Services OpenAI User" --scope /subscriptions/$SUB_ID/resourceGroups/$RG
az role assignment create --assignee $IDENTITY_PRINCIPAL_ID --role "Search Index Data Reader" --scope /subscriptions/$SUB_ID/resourceGroups/$RG

# Annotate the service account, then apply the deployment manifest (below)
kubectl annotate serviceaccount rag-sa -n rag azure.workload.identity/client-id=$IDENTITY_CLIENT_ID
kubectl apply -f k8s-deployment.yaml -n rag
kubectl get pods -n rag -w
kubectl get svc -n rag
```

`k8s-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  labels: { app: rag-api }
spec:
  replicas: 2
  selector: { matchLabels: { app: rag-api } }
  template:
    metadata:
      labels: { app: rag-api, azure.workload.identity/use: "true" }
    spec:
      serviceAccountName: rag-sa
      containers:
        - name: rag-api
          image: <ACR_LOGIN_SERVER>/rag-api:v1
          ports: [{ containerPort: 8000 }]
          env:
            - { name: AOAI_ENDPOINT, value: "https://aoai-aifab.openai.azure.com/" }
            - { name: SEARCH_ENDPOINT, value: "https://srch-aifab.search.windows.net" }
            - { name: SEARCH_INDEX, value: "idx-rag-documents" }
            - { name: CHAT_DEPLOYMENT, value: "gpt-4o-chat" }
            - { name: EMBED_DEPLOYMENT, value: "text-embedding-3-large" }
          readinessProbe: { httpGet: { path: /healthz, port: 8000 }, initialDelaySeconds: 5 }
---
apiVersion: v1
kind: Service
metadata: { name: rag-api-svc }
spec:
  type: LoadBalancer
  selector: { app: rag-api }
  ports: [{ port: 80, targetPort: 8000 }]
```

### Part C — Azure PowerShell
```powershell
$RG       = "rg-aif-labs"
$Location = "eastus2"
$Acr      = "acraifab$(Get-Random -Maximum 9999)"
$Aks      = "aks-aifab"

# Container registry
New-AzContainerRegistry -ResourceGroupName $RG -Name $Acr -Sku Basic

# Build & push via ACR Tasks (invokes the same underlying build service as `az acr build`)
az acr build --registry $Acr --image rag-api:v1 .

# AKS cluster with OIDC + workload identity, attached to ACR
New-AzAksCluster -ResourceGroupName $RG -Name $Aks -Location $Location `
  -NodeCount 2 -NodeVmSize Standard_D2s_v5 -EnableOidcIssuerProfile -EnableWorkloadIdentity `
  -AcrNameToAttach $Acr -GenerateSshKey

Import-AzAksCredential -ResourceGroupName $RG -Name $Aks

# Managed identity + federated credential for Workload Identity
New-AzUserAssignedIdentity -ResourceGroupName $RG -Name "id-aifab-workload" -Location $Location
$IdentityClientId    = (Get-AzUserAssignedIdentity -ResourceGroupName $RG -Name "id-aifab-workload").ClientId
$IdentityPrincipalId = (Get-AzUserAssignedIdentity -ResourceGroupName $RG -Name "id-aifab-workload").PrincipalId
$OidcIssuer = (Get-AzAksCluster -ResourceGroupName $RG -Name $Aks).OidcIssuerProfile.IssuerUrl

kubectl create namespace rag
kubectl create serviceaccount rag-sa -n rag

New-AzFederatedIdentityCredential -ResourceGroupName $RG -IdentityName "id-aifab-workload" `
  -Name "fed-rag-sa" -Issuer $OidcIssuer -Subject "system:serviceaccount:rag:rag-sa" `
  -Audience "api://AzureADTokenExchange"

$SubId = (Get-AzContext).Subscription.Id
New-AzRoleAssignment -ObjectId $IdentityPrincipalId -RoleDefinitionName "Cognitive Services OpenAI User" -Scope "/subscriptions/$SubId/resourceGroups/$RG"
New-AzRoleAssignment -ObjectId $IdentityPrincipalId -RoleDefinitionName "Search Index Data Reader" -Scope "/subscriptions/$SubId/resourceGroups/$RG"

kubectl annotate serviceaccount rag-sa -n rag azure.workload.identity/client-id=$IdentityClientId
kubectl apply -f k8s-deployment.yaml -n rag
kubectl get pods -n rag -w
kubectl get svc -n rag
```

### ✅ Validation
- `kubectl get pods -n rag` shows both replicas `Running` and `READY 1/1`.
- `kubectl get svc -n rag` shows an `EXTERNAL-IP`; `curl http://<EXTERNAL-IP>/ask?question=...` returns a grounded answer.
- No connection strings or API keys appear in the pod's environment (`kubectl exec ... -- env`) — only endpoints, proving Workload Identity is authenticating.

### Cleanup
`az aks delete -g $RG -n $AKS --yes` and `az acr delete -g $RG -n $ACR --yes` (or PowerShell `Remove-AzAksCluster` / `Remove-AzContainerRegistry`) when finished — AKS nodes bill hourly even when idle.

---

## Lab 12: Monitoring, Logging & Application Insights for AI Apps

### Objective
Instrument the RAG API with Application Insights (traces, dependencies, exceptions), enable Azure OpenAI diagnostic logging, and build a simple dashboard/alert for latency and token usage.

### Prerequisites
Labs 5, 10 (or 11) completed.

### Part A — Azure Portal
1. Portal search → **Application Insights** → **+ Create**. Resource group `rg-aif-labs`, name `appi-aifab`, Region same, Resource mode **Workspace-based** → link to a new/existing **Log Analytics workspace** `law-aifab` → **Review + create** → **Create**.
2. Copy the **Connection String** from the Overview page.
3. Go to your Function App (`func-aifab-rag`) → left menu **Application Insights** → **Turn on Application Insights** → select `appi-aifab` → **Apply**. (For the AKS version, add the connection string as an env var and add the `opencensus-ext-azure` / `azure-monitor-opentelemetry` package instead — see Part B.)
4. Enable Azure OpenAI diagnostics: open `aoai-aifab` resource → left menu **Diagnostic settings** → **+ Add diagnostic setting** → name `diag-aoai-to-law` → check **Audit Logs**, **Request and Response Logs**, **Trace Logs**, **AllMetrics** → destination: **Send to Log Analytics workspace** → `law-aifab` → **Save**.
5. Go to `appi-aifab` → **Application Map** to visually see the dependency chain (Function → Azure OpenAI → Azure AI Search) after a few real requests.
6. Left menu **Alerts** → **+ Create → Alert rule** → Scope: `appi-aifab` → Condition: **Failed requests** > 5 in 5 minutes → Action group: create one that emails you → **Create**.
7. **Workbooks** → **+ New** → build a simple chart of `requests | summarize avg(duration) by bin(timestamp, 5m)` using Kusto (KQL) to track latency over time.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"
LAW="law-aifab"
APPI="appi-aifab"
FUNCAPP="func-aifab-rag"

# Log Analytics workspace + Application Insights (workspace-based)
az monitor log-analytics workspace create --resource-group $RG --workspace-name $LAW --location $LOCATION
LAW_ID=$(az monitor log-analytics workspace show -g $RG -n $LAW --query id -o tsv)

az monitor app-insights component create \
  --app $APPI --location $LOCATION --resource-group $RG --workspace $LAW_ID

APPI_CONN=$(az monitor app-insights component show -g $RG -a $APPI --query connectionString -o tsv)

# Wire the Function App to Application Insights
az functionapp config appsettings set --name $FUNCAPP --resource-group $RG \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$APPI_CONN"

# Enable Azure OpenAI diagnostic logs to the same workspace
AOAI_ID=$(az cognitiveservices account show -n aoai-aifab -g $RG --query id -o tsv)
az monitor diagnostic-settings create \
  --name diag-aoai-to-law --resource $AOAI_ID --workspace $LAW_ID \
  --logs '[{"category":"RequestResponse","enabled":true},{"category":"Audit","enabled":true},{"category":"Trace","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'

# Create an alert for failed requests > 5 in 5 minutes
az monitor metrics alert create \
  --name alert-high-failures --resource-group $RG \
  --scopes $(az monitor app-insights component show -g $RG -a $APPI --query id -o tsv) \
  --condition "count requests/failed > 5" \
  --window-size 5m --evaluation-frequency 1m --severity 2
```
For the AKS deployment, add to `requirements.txt`: `azure-monitor-opentelemetry`, then at the top of `app.py`:
```python
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"])
```
and add the env var to the pod spec / `kubectl set env deployment/rag-api APPLICATIONINSIGHTS_CONNECTION_STRING="$APPI_CONN" -n rag`.

### Part C — Azure PowerShell
```powershell
$RG      = "rg-aif-labs"
$Location = "eastus2"
$Law     = "law-aifab"
$Appi    = "appi-aifab"
$FuncApp = "func-aifab-rag"

# Log Analytics workspace + Application Insights
New-AzOperationalInsightsWorkspace -ResourceGroupName $RG -Name $Law -Location $Location
$LawId = (Get-AzOperationalInsightsWorkspace -ResourceGroupName $RG -Name $Law).ResourceId

New-AzApplicationInsights -ResourceGroupName $RG -Name $Appi -Location $Location -WorkspaceResourceId $LawId
$AppiConn = (Get-AzApplicationInsights -ResourceGroupName $RG -Name $Appi).ConnectionString

# Wire the Function App
Update-AzFunctionAppSetting -ResourceGroupName $RG -Name $FuncApp -AppSetting @{
  APPLICATIONINSIGHTS_CONNECTION_STRING = $AppiConn
}

# Enable Azure OpenAI diagnostic logs
$AoaiId = (Get-AzCognitiveServicesAccount -ResourceGroupName $RG -Name "aoai-aifab").Id
$Logs = @(
  @{ Category = "RequestResponse"; Enabled = $true },
  @{ Category = "Audit"; Enabled = $true },
  @{ Category = "Trace"; Enabled = $true }
)
Set-AzDiagnosticSetting -ResourceId $AoaiId -WorkspaceId $LawId -Name "diag-aoai-to-law" `
  -Log $Logs -Metric @(@{ Category = "AllMetrics"; Enabled = $true })

# Alert for failed requests
$Condition = New-AzMetricAlertRuleV2Criteria -MetricName "requests/failed" -TimeAggregation Count -Operator GreaterThan -Threshold 5
Add-AzMetricAlertRule -ResourceGroupName $RG -Name "alert-high-failures" `
  -TargetResourceId (Get-AzApplicationInsights -ResourceGroupName $RG -Name $Appi).Id `
  -Condition $Condition -WindowSize (New-TimeSpan -Minutes 5) -Frequency (New-TimeSpan -Minutes 1) -Severity 2
```

### Useful KQL queries to run in Log Analytics (`law-aifab` → Logs)
```kql
// Average latency of the RAG API over time
requests
| summarize avg(duration) by bin(timestamp, 5m)
| render timechart

// Azure OpenAI token usage from diagnostic logs
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
| where Category == "RequestResponse"
| summarize TotalRequests = count() by bin(TimeGenerated, 1h)

// Exceptions in the last 24 hours
exceptions
| where timestamp > ago(24h)
| summarize count() by problemId
```

### ✅ Validation
- Application Insights **Live Metrics** shows real-time requests while you call the API.
- **Application Map** shows the Function → Azure OpenAI + Azure AI Search dependency graph.
- The alert rule fires a test notification when you simulate failures (e.g., temporarily point `AOAI_ENDPOINT` to a wrong value and hit the API a few times).

### Cleanup
Keep `law-aifab`/`appi-aifab` if continuing to Lab 13; otherwise remove via the [Appendix](#appendix-full-cleanup-script).

---

## Lab 13: Azure DevOps CI/CD Pipeline for the AI Application

### Objective
Automate build → test → deploy of the RAG API (Function App or AKS) using Azure DevOps Pipelines (or Azure Repos + Pipelines), triggered on every push to `main`.

### Prerequisites
Labs 10 or 11 completed. An Azure DevOps organization (https://dev.azure.com — free to create) and a Git repo containing your `rag-function-app/` or container project.

### Part A — Azure Portal / Azure DevOps Portal
1. Go to https://dev.azure.com → **New organization** (if you don't have one) → **New project** → name `azure-ai-labs`.
2. **Repos** → push your local project (`git remote add origin <repo-url>`, `git push -u origin main`) or import from GitHub.
3. **Project settings → Service connections** → **New service connection** → **Azure Resource Manager** → **Workload identity federation (automatic)** → select your subscription and `rg-aif-labs` → name it `sc-aif-labs` → **Save**. (This avoids storing any Azure credentials in DevOps — it uses OIDC federation, the DevOps equivalent of the Workload Identity pattern from Lab 11.)
4. **Pipelines** → **New pipeline** → select your repo → **Azure Pipelines YAML file** → point at `azure-pipelines.yml` (created in Part B) → **Save and run**.
5. Watch the pipeline run under **Pipelines → Runs**; each stage (Build, Test, Deploy) shows live logs.
6. **Pipelines → Releases** (classic) or the **Environments** tab (YAML) can be used to add manual approval gates before deploying to a "Production" environment — add one for good practice.

### Part B — Azure CLI (pipeline definition + supporting Azure resources)
CLI here manages the Azure-side prerequisites and can also drive Azure DevOps itself via the `az devops` extension:
```bash
az extension add --name azure-devops

az devops configure --defaults organization=https://dev.azure.com/<your-org> project=azure-ai-labs

# Create the pipeline from the CLI, pointing at the YAML file in your repo
az pipelines create --name rag-ci-cd \
  --repository <repo-url> --branch main --yml-path azure-pipelines.yml --skip-first-run false
```

`azure-pipelines.yml` (place at the repo root):
```yaml
trigger: [ main ]

variables:
  azureServiceConnection: 'sc-aif-labs'
  functionAppName: 'func-aifab-rag'
  resourceGroup: 'rg-aif-labs'

stages:
- stage: Build
  jobs:
  - job: BuildAndTest
    pool: { vmImage: 'ubuntu-latest' }
    steps:
    - task: UsePythonVersion@0
      inputs: { versionSpec: '3.11' }
    - script: |
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        pip install pytest
        pytest tests/ --junitxml=test-results.xml
      displayName: 'Install deps & run unit tests'
    - task: PublishTestResults@2
      inputs: { testResultsFiles: 'test-results.xml' }
    - task: ArchiveFiles@2
      inputs: { rootFolderOrFile: '$(System.DefaultWorkingDirectory)', archiveFile: '$(Build.ArtifactStagingDirectory)/app.zip' }
    - publish: '$(Build.ArtifactStagingDirectory)/app.zip'
      artifact: drop

- stage: DeployDev
  dependsOn: Build
  jobs:
  - deployment: DeployToFunctionApp
    environment: 'dev'
    pool: { vmImage: 'ubuntu-latest' }
    strategy:
      runOnce:
        deploy:
          steps:
          - download: current
            artifact: drop
          - task: AzureFunctionApp@2
            inputs:
              azureSubscription: $(azureServiceConnection)
              appType: 'functionAppLinux'
              appName: $(functionAppName)
              package: '$(Pipeline.Workspace)/drop/app.zip'
```

### Part C — Azure PowerShell
```powershell
# The az devops extension works identically whether invoked from bash or PowerShell —
# this mirrors Part B exactly, which is the point: your pipeline definition is
# CLI-tool-agnostic. Use whichever shell your team standardizes on.
az extension add --name azure-devops
az devops configure --defaults organization=https://dev.azure.com/<your-org> project=azure-ai-labs

az pipelines create --name rag-ci-cd `
  --repository <repo-url> --branch main --yml-path azure-pipelines.yml --skip-first-run false

# Alternative: trigger a run manually and watch status
az pipelines run --name rag-ci-cd
az pipelines runs list --pipeline-ids (az pipelines show --name rag-ci-cd --query id -o tsv) --top 1 -o table
```

For an AKS target instead of Functions, swap the `DeployDev` stage's task for:
```yaml
          - task: KubernetesManifest@1
            inputs:
              action: 'deploy'
              connectionType: 'azureResourceManager'
              azureSubscriptionConnection: $(azureServiceConnection)
              azureResourceGroup: $(resourceGroup)
              kubernetesCluster: 'aks-aifab'
              namespace: 'rag'
              manifests: 'k8s-deployment.yaml'
              containers: '<ACR_LOGIN_SERVER>/rag-api:$(Build.BuildId)'
```
and add a preceding `Docker@2` task to build/push the image to ACR with tag `$(Build.BuildId)` for full traceability.

### ✅ Validation
- A `git push` to `main` automatically triggers **Build → DeployDev** in Azure DevOps within seconds.
- Pipeline run history shows green checkmarks for both stages; the **Tests** tab shows your `pytest` results.
- Hitting the Function/AKS endpoint after the run shows the newly deployed code (e.g., bump a version string and confirm it changes post-deploy).

### Cleanup
Delete the pipeline (`az pipelines delete --id <id>`) and service connection when the lab guide is retired; the underlying Azure resources are cleaned up via the [Appendix](#appendix-full-cleanup-script).

---

## Lab 14: Model Evaluation, Content Safety & Quality Metrics

### Objective
Run a structured evaluation of the RAG pipeline (groundedness, relevance, coherence) using Azure AI Foundry's built-in evaluators, and enable Azure AI Content Safety to filter harmful inputs/outputs.

### Prerequisites
Labs 5, 8 completed.

### Part A — Azure Portal
1. https://ai.azure.com → project `proj-aifab-rag` → left menu **Evaluation** → **+ New evaluation**.
2. Evaluation type: **Evaluate a dataset**. Upload a small CSV/JSONL with columns `question`, `context`, `answer` (10–20 rows sampled from your Lab 8 test runs).
3. Select evaluators: **Groundedness**, **Relevance**, **Coherence**, **Fluency** (all AI-assisted, scored 1–5 by a judge model) plus **similarity** if you have ground-truth answers.
4. Judge model: `gpt-4o-chat`. Click **Run evaluation**. Review the results grid and the aggregate scores/charts once complete.
5. Left menu **Content Safety** (or the standalone **Azure AI Content Safety** resource — create one the same way as Azure OpenAI in Lab 5, kind `ContentSafety`) → **Try it out** in the Portal's Content Safety Studio (https://contentsafety.cognitive.azure.com) → paste sample text/prompts to see category scores (Hate, Violence, Sexual, Self-harm) and severity levels.
6. On your Azure OpenAI resource → deployments already include a **default content filter**; to customize, go to `aoai-aifab` → **Content filters** (left menu) → **+ Create custom content filter** → adjust severity thresholds per category → apply it to your `gpt-4o-chat` deployment.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"
LOCATION="eastus2"
CS="cs-aifab-safety"

# Create an Azure AI Content Safety resource
az cognitiveservices account create \
  --name $CS --resource-group $RG --location $LOCATION \
  --kind ContentSafety --sku S0 --custom-domain $CS

CS_ENDPOINT=$(az cognitiveservices account show -n $CS -g $RG --query properties.endpoint -o tsv)
CS_KEY=$(az cognitiveservices account keys list -n $CS -g $RG --query key1 -o tsv)

# Analyze a piece of text for harmful content
curl -s -X POST "$CS_ENDPOINT/contentsafety/text:analyze?api-version=2024-09-01" \
  -H "Content-Type: application/json" -H "Ocp-Apim-Subscription-Key: $CS_KEY" \
  -d '{"text": "Sample user-submitted question to screen.", "categories": ["Hate","SelfHarm","Sexual","Violence"]}'
```
Programmatic evaluation is driven by the `azure-ai-evaluation` Python SDK (CLI/PowerShell provision credentials, Python runs the eval — same pattern as earlier labs):
```bash
pip install azure-ai-evaluation
```
```python
# evaluate_rag.py
from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator, CoherenceEvaluator, evaluate

model_config = {
    "azure_endpoint": "<AOAI_ENDPOINT>",
    "api_key": "<AOAI_KEY>",
    "azure_deployment": "gpt-4o-chat",
}

result = evaluate(
    data="eval_dataset.jsonl",   # rows: {"question":..., "context":..., "answer":...}
    evaluators={
        "groundedness": GroundednessEvaluator(model_config),
        "relevance": RelevanceEvaluator(model_config),
        "coherence": CoherenceEvaluator(model_config),
    },
    output_path="eval_results.json",
)
print(result["metrics"])
```
```bash
python evaluate_rag.py
```

### Part C — Azure PowerShell
```powershell
$RG       = "rg-aif-labs"
$Location = "eastus2"
$Cs       = "cs-aifab-safety"

New-AzCognitiveServicesAccount -ResourceGroupName $RG -Name $Cs -Type "ContentSafety" `
  -SkuName "S0" -Location $Location -CustomSubdomainName $Cs

$CsEndpoint = (Get-AzCognitiveServicesAccount -ResourceGroupName $RG -Name $Cs).Endpoint
$CsKey      = (Get-AzCognitiveServicesAccountKey -ResourceGroupName $RG -Name $Cs).Key1

$Headers = @{ "Ocp-Apim-Subscription-Key" = $CsKey; "Content-Type" = "application/json" }
$Body = @{ text = "Sample user-submitted question to screen."; categories = @("Hate","SelfHarm","Sexual","Violence") } | ConvertTo-Json
Invoke-RestMethod -Uri "$CsEndpoint/contentsafety/text:analyze?api-version=2024-09-01" -Method Post -Headers $Headers -Body $Body

# Trigger the same Python evaluation script as Part B
pip install azure-ai-evaluation
python evaluate_rag.py
```

### ✅ Validation
- Portal **Evaluation** run completes and shows per-row scores plus an aggregate summary (e.g., average groundedness ≥ 4/5 is a healthy target).
- Content Safety `analyze` call returns a JSON body with `categoriesAnalysis` severity scores for each category (0 = safe, higher = more severe).
- A deliberately harmful test string returns a high severity score, confirming the filter is active before you rely on it in production.

### Cleanup
Keep `cs-aifab-safety` if continuing; delete via the [Appendix](#appendix-full-cleanup-script) otherwise.

---

## Lab 15: Cost Optimization & Governance for AI Workloads

### Objective
Apply Azure Policy guardrails, right-size/scale resources, set up token/cost monitoring for Azure OpenAI, and identify optimization levers (provisioned throughput vs. pay-as-you-go, autoscale, caching).

### Prerequisites
Labs 5, 12 completed.

### Part A — Azure Portal
1. Portal search → **Cost Management + Billing** → **Cost analysis** → scope to `rg-aif-labs` → group by **Service name** to see which resource (Azure OpenAI vs. AKS vs. Search) drives spend.
2. **Cost alerts** (if not already set in Lab 1) → confirm the budget alert exists and add a second at 100% threshold.
3. Portal search → **Policy** → **Definitions** → search "Allowed locations" → **Assign** → scope `rg-aif-labs` → restrict deployments to your approved region(s) only (prevents accidental costly resources in unexpected regions).
4. Assign another built-in policy: **Allowed resource types** → restrict to only the services you use in this guide (Cognitive Services, Search, Storage, Key Vault, Functions, AKS, Container Registry, Application Insights) to prevent sprawl.
5. On `aoai-aifab` → **Deployments** → for steady, predictable high-volume workloads, evaluate switching from **Standard (pay-as-you-go)** to **Provisioned Throughput Units (PTU)** — Portal shows an estimated PTU calculator when you select "Provisioned-Managed" as the deployment type; PTU gives predictable latency/cost at scale but requires reserved capacity, so it's worth it only above a certain steady request volume.
6. On AKS (`aks-aifab`) → left menu **Node pools** → enable **Cluster autoscaler** (min 1, max 3 nodes) so you don't pay for idle capacity outside peak hours.

### Part B — Azure CLI
```bash
RG="rg-aif-labs"

# See cost breakdown by service (requires Cost Management Reader role)
az consumption usage list --start-date $(date -d "-30 days" +%Y-%m-%d) --end-date $(date +%Y-%m-%d) \
  --query "[?contains(instanceName,'aifab')].{Resource:instanceName, Cost:pretaxCost}" -o table

# Assign the "Allowed locations" policy scoped to the resource group
az policy assignment create \
  --name "allowed-locations-aifab" \
  --scope $(az group show -n $RG --query id -o tsv) \
  --policy "e56962a6-4747-49cd-b67b-bf8b01975c4c" \
  --params '{"listOfAllowedLocations":{"value":["eastus2"]}}'

# Enable AKS cluster autoscaler (min 1, max 3 nodes)
az aks nodepool update \
  --resource-group $RG --cluster-name aks-aifab --name nodepool1 \
  --enable-cluster-autoscaler --min-count 1 --max-count 3

# Right-size an idle Azure OpenAI deployment's capacity (lower TPM to reduce reserved cost)
az cognitiveservices account deployment update \
  --name aoai-aifab --resource-group $RG --deployment-name gpt-4o-chat \
  --sku-capacity 5
```

### Part C — Azure PowerShell
```powershell
$RG = "rg-aif-labs"

# Cost breakdown for the last 30 days
Get-AzConsumptionUsageDetail -StartDate (Get-Date).AddDays(-30) -EndDate (Get-Date) |
  Where-Object { $_.InstanceName -like "*aifab*" } |
  Select-Object InstanceName, PretaxCost | Format-Table

# Assign the "Allowed locations" policy
$PolicyDef = Get-AzPolicyDefinition -Id "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
New-AzPolicyAssignment -Name "allowed-locations-aifab" -Scope (Get-AzResourceGroup -Name $RG).ResourceId `
  -PolicyDefinition $PolicyDef -PolicyParameterObject @{ listOfAllowedLocations = @("eastus2") }

# Enable AKS cluster autoscaler
Update-AzAksNodePool -ResourceGroupName $RG -ClusterName "aks-aifab" -Name "nodepool1" `
  -EnableAutoScaling -MinCount 1 -MaxCount 3

# Right-size the OpenAI deployment capacity
Update-AzCognitiveServicesAccountDeployment -ResourceGroupName $RG -AccountName "aoai-aifab" `
  -Name "gpt-4o-chat" -Sku @{ Name = "Standard"; Capacity = 5 }
```

### Cost-optimization levers worth knowing for interviews and real projects
- **Pay-as-you-go vs. PTU** for Azure OpenAI — PTU reduces per-token cost at high, steady volume but requires reserved capacity commitment.
- **Prompt/response caching** — cache repeated identical queries (e.g., FAQ-style RAG questions) at the app layer to avoid redundant model calls.
- **Chunking/embedding reuse** — only re-embed documents that changed (track a content hash) instead of re-indexing everything nightly.
- **Right-size Search tier/replicas** — Basic tier is enough for most lab/small-prod workloads; scale replicas only for query-throughput needs, partitions only for storage needs.
- **AKS autoscaling + spot node pools** for non-critical batch workloads (e.g., nightly re-indexing jobs).
- **Function App Consumption plan** for spiky/low-traffic APIs instead of always-on Premium/AKS.
- **Model selection** — use a smaller/cheaper model (e.g., `gpt-4o-mini`) for simple classification/extraction tasks and reserve `gpt-4o` for complex reasoning.

### ✅ Validation
- `az policy assignment list -g rg-aif-labs -o table` / `Get-AzPolicyAssignment` shows both policies as `Enforce`.
- Cost Management → Cost analysis chart reflects the resource-group scope correctly, and the budget alert from Lab 1 is still active.
- AKS `nodepool1` shows `enableAutoScaling: true` with `minCount: 1, maxCount: 3`.

### Cleanup
See the [Appendix](#appendix-full-cleanup-script) to tear down everything built across all 15 labs.

---

## Appendix: Full Cleanup Script

Because every lab deployed into the single resource group `rg-aif-labs`, tearing down the entire environment is one command — **but this deletes everything irreversibly**, so only run it once you're fully done.

### Azure CLI
```bash
az group delete --name rg-aif-labs --yes --no-wait

# Also remove the service principal / app registration from Lab 2 (not inside the RG)
az ad app delete --id "$APP_ID"

# And the Azure DevOps pipeline/service connection from Lab 13, if created
az pipelines delete --id <pipeline-id> --yes
```

### Azure PowerShell
```powershell
Remove-AzResourceGroup -Name "rg-aif-labs" -Force -AsJob

# Also remove the app registration from Lab 2
Remove-AzADApplication -ApplicationId $App.AppId -Force
```

### Azure Portal
1. Search **Resource groups** → open `rg-aif-labs` → **Delete resource group** → type the name to confirm → **Delete**.
2. **Microsoft Entra ID → App registrations** → `sp-aif-labs-app` → **Delete**.
3. If used, delete the Azure DevOps project (**Project settings → Overview → Delete**) and the AKS-attached ACR if it lived outside the RG.

### Post-deletion checklist
- Confirm no lingering **Cost Management** charges after 24–48 hours (deletion is not always instantaneous for metered resources like AKS).
- Revoke any locally stored `.env` files, App Settings secrets, or Key Vault soft-deleted secrets (Key Vault soft-delete may retain secrets for a retention period — purge via `az keyvault secret purge` / `Remove-AzKeyVaultSecret -InRemovedState -PermanentlyDelete` if you need them gone immediately).

---

*End of guide. Work through Labs 0–15 in order the first time; once comfortable, they can be run independently since each lab's prerequisites are explicitly stated at the top.*
