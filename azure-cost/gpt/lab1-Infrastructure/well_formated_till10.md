# LAB 1 — Foundation & Authentication Layer

## Goal of this Lab

Build the secure Azure-native platform foundation.

After completing this lab, you will have:

* ✅ Azure infrastructure baseline
* ✅ AKS cluster
* ✅ Container registry
* ✅ PostgreSQL
* ✅ Key Vault
* ✅ Entra ID authentication
* ✅ oauth2-proxy
* ✅ ingress + TLS
* ✅ production-ready Kubernetes base

This lab intentionally avoids:

* LangGraph
* AI
* Cost engines
* Dashboards

Because infrastructure foundation must come first.

---

# LAB 1 Architecture

```text
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

## Supporting Services

```text
AKS
ACR
PostgreSQL Flexible Server
Key Vault
Managed Identity
```

---

# Infrastructure Mapping

| Resource     | Resource Group         | Subnet                           |
| ------------ | ---------------------- | -------------------------------- |
| AKS Cluster  | rg-finops-prod-core    | aks-subnet (10.0.2.0/24)         |
| ACR          | rg-finops-prod-core    | N/A (Global Service)             |
| PostgreSQL   | rg-finops-prod-core*   | flexiserver-subnet (10.0.1.0/24) |
| VNet/Subnets | rg-finops-prod-network | N/A                              |

---

# Step 1 — Create Resource Groups

## Find All Region Names

```bash
az account list-locations --output table
```

## Recommended Structure

```text
rg-finops-prod-core
rg-finops-prod-data
rg-finops-prod-network
```

### Purpose of Each Resource Group

* `rg-finops-prod-network`

  * Holds foundation networking resources (VNet, Subnets).
  * Networking usually outlives applications.

* `rg-finops-prod-core`

  * Holds compute and identity resources (AKS, ACR).

* `rg-finops-prod-data`

  * Holds stateful resources (PostgreSQL).

## Create Resource Groups

```bash
az group create \
  --name rg-finops-prod-core \
  --location centralindia \
  --tags Environment=Test Project=ai-finops

az group create \
  --name rg-finops-prod-data \
  --location centralindia \
  --tags Environment=Test Project=ai-finops

az group create \
  --name rg-finops-prod-network \
  --location centralindia \
  --tags Environment=Test Project=ai-finops

az group list --output table
```

```bash
az account list-locations -o table
```

---

# Step 2 — Create Azure Container Registry (ACR)

* ACR name must be globally unique.
* Use Premium SKU only if needed later.

## Recommended SKU

```text
Basic SKU
```

## Create ACR

```bash
az acr create \
  --name finopsacrmanmas \
  --resource-group rg-finops-prod-core \
  --sku Basic
```

---

# Common Issue While Creating ACR

## Error

```text
(MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'.
```

## Solution

```bash
az provider register --namespace Microsoft.ContainerRegistry
```

Retry:

```bash
az acr create \
  --name finopsacrmanmas \
  --resource-group rg-finops-prod-core \
  --sku Basic
```

## Verify

```bash
az acr list -o table
```

### Azure Portal Navigation

```text
Portal → All Services → Search "Container Registries"
```

---

# Step 2.1 — Create VNet and Subnets

## Objective

Create:

* 1 VNet
* 3 Subnets:

  * vm-subnet
  * flexiserver-subnet
  * aks-subnet

> Small subnet ranges are used here because this setup targets free-tier/lab usage.

## Create VNet and Subnets

```bash
# Variables
resourceGroup="rg-finops-prod-network"
location="centralindia"
vnetName="finops-prod-vnet"
vnetPrefix="10.0.0.0/16"

# Create VNet with VM subnet
az network vnet create \
  --name $vnetName \
  --resource-group $resourceGroup \
  --location $location \
  --address-prefix $vnetPrefix \
  --subnet-name vm-subnet \
  --subnet-prefixes 10.0.0.0/24

# Create PostgreSQL subnet
az network vnet subnet create \
  --name flexiserver-subnet \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --address-prefix 10.0.1.0/24

# Create AKS subnet
az network vnet subnet create \
  --name aks-subnet \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --address-prefix 10.0.2.0/24
```

## Verify VNet and Subnets

```bash
az network vnet show \
  --name $vnetName \
  --resource-group $resourceGroup \
  --query "{Name:name, Location:location, Subnets:subnets[*].{Name:name, Prefix:addressPrefix}}" \
  --output table
```

## List All Subnets

```bash
az network vnet subnet list \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --output table
```

---

# Step 3 — Create AKS Cluster

# Recommended Minimal Production Setup

## Node Pools

| Pool   | Type       | Purpose     |
| ------ | ---------- | ----------- |
| system | Regular    | ingress/api |
| spot   | Spot nodes | workers/AI  |

---

# Recommended VM Sizes

## System Pool

```text
Standard_D4as_v5
```

## Spot Pool

```text
Standard_B4ms
```

---

# AKS Features to Enable

* ✅ Managed Identity
* ✅ OIDC issuer
* ✅ Workload identity
* ✅ Cluster autoscaler
* ✅ Azure CNI Overlay
* ✅ Azure Monitor (optional)

---

# Register Required Providers

```bash
az provider register --namespace Microsoft.ManagedIdentity
az provider register --namespace Microsoft.Network
```

## Verify Registrations

```bash
az provider list \
  --query "[?contains(namespace, 'Microsoft.ContainerService') || contains(namespace, 'Microsoft.ManagedIdentity')].{Provider:namespace, Status:registrationState}" \
  --output table
```

---

# Common AKS VM SKU Error

## Error Example

```text
The VM size of Standard_DS2_v2 is not allowed in your subscription in location 'centralindia'.
```

## Solution

Use another VM SKU supported in your subscription.

---

# Create AKS Cluster

```bash
az aks create \
  --resource-group rg-finops-prod-core \
  --name finops-aks \
  --node-count 1 \
  --node-osdisk-size 32 \
  --enable-managed-identity \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --tier free \
  --node-vm-size Standard_B2als_v2 \
  --generate-ssh-keys
```

---

# AKS with Custom VNet/Subnet

## Common Error

```text
(ServiceCidrOverlapExistingSubnetsCidr)
The specified service CIDR 10.0.0.0/16 is conflicted with an existing subnet CIDR 10.0.0.0/24.
```

## Correct Command (Windows CMD Format)

```cmd
az aks create ^
  --resource-group rg-finops-prod-core ^
  --name finops-aks ^
  --node-count 1 ^
  --node-osdisk-size 32 ^
  --enable-managed-identity ^
  --enable-oidc-issuer ^
  --enable-workload-identity ^
  --network-plugin azure ^
  --network-plugin-mode overlay ^
  --tier free ^
  --node-vm-size Standard_B2als_v2 ^
  --vnet-subnet-id "/subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f/resourceGroups/rg-finops-prod-network/providers/Microsoft.Network/virtualNetworks/finops-prod-vnet/subnets/aks-subnet" ^
  --service-cidr 10.96.0.0/16 ^
  --dns-service-ip 10.96.0.10 ^
  --generate-ssh-keys
```

---

# Add Spot Node Pool

```bash
az aks nodepool add \
  --resource-group rg-finops-prod-core \
  --cluster-name finops-aks \
  --name spotpool \
  --priority Spot \
  --eviction-policy Delete \
  --enable-cluster-autoscaler \
  --node-count 1 \
  --min-count 0 \
  --max-count 2 \
  --node-vm-size Standard_D2pds_v6
```

---

# Step 4 — Connect ACR to AKS

```bash
az aks update \
  --name finops-aks \
  --resource-group rg-finops-prod-core \
  --attach-acr finopsacrmanmas
```

---

# Step 5 — Install kubectl + Helm

```bash
az aks install-cli
```

---

# Get AKS Credentials

```bash
az aks get-credentials \
  --resource-group rg-finops-prod-core \
  --name finops-aks
```

---

# Step 6 — Install NGINX Ingress

## Add Helm Repository

```bash
helm repo add ingress-nginx \
https://kubernetes.github.io/ingress-nginx
```

## Install Ingress Controller

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-nginx
```

## Health Probe Annotation

If required:

```bash
kubectl annotate service ingress-nginx-controller \
  -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz \
  --overwrite
```

---

# Step 7 — Install cert-manager

## Add Helm Repository

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

## Install cert-manager

```bash
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

## Alternative Version-Pinned Installation

```bash
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.20.0 \
  --set crds.enabled=true
```

## Verify Installation

```bash
helm list -n cert-manager
```

## Verify CRDs

```bash
helm get values cert-manager -n cert-manager
```

---

# Step 8 — Configure DNS

## Example Domains

```text
app.company.com
api.company.com
ai.company.com

app.manmas.online
api.manmas.online
ai.manmas.online
```

---

# Find Ingress Public IP

```bash
kubectl get service -n ingress-nginx
```

## Example Output

```text
NAME                                 TYPE           CLUSTER-IP    EXTERNAL-IP    PORT(S)                      AGE
ingress-nginx-controller             LoadBalancer   10.0.231.35   4.182.209.93   80:32496/TCP,443:30605/TCP   13m
ingress-nginx-controller-admission   ClusterIP      10.0.23.240   <none>         443/TCP                      13m
```

---

# DNS Records

| Type | Host | Value (IP Address) | TTL  |
| ---- | ---- | ------------------ | ---- |
| A    | app  | YOUR_INGRESS_IP    | 3600 |
| A    | api  | YOUR_INGRESS_IP    | 3600 |
| A    | ai   | YOUR_INGRESS_IP    | 3600 |

---

# Verify DNS

```bash
nslookup app.manmas.online
```

## Expected Output

```text
Name:    app.manmas.online
Address: 4.182.209.93
```

If the returned IP matches the ingress public IP, then Step 8 is complete.

---

# Step 9 — Configure TLS

## Verify cert-manager Pods

```bash
kubectl get pods -n cert-manager
```

## Verify CRDs

```bash
kubectl get crd certificates.cert-manager.io -o jsonpath='{.metadata.annotations.helm\.sh/resource-policy}'
```

---

# Step 9.1 — Fix Health Probe Annotation (Mandatory)

```bash
kubectl annotate service ingress-nginx-controller \
  -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz
```

## Verify Annotation

```bash
kubectl get service ingress-nginx-controller \
  -n ingress-nginx \
  -o yaml | grep -A3 "annotations:"
```

## Restart NGINX

```bash
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx

kubectl rollout status deployment ingress-nginx-controller \
  -n ingress-nginx \
  --timeout=120s
```

---

# Step 9.2 — Create ClusterIssuer

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    email: admin@manmas.online
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
EOF
```

## Verify ClusterIssuer

```bash
kubectl get clusterissuer letsencrypt-prod
```

## Expected Output

```text
NAME               READY   AGE
letsencrypt-prod   True    5s
```

---

# Deploy Test Application

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  namespace: ingress-nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: test-app
  namespace: ingress-nginx
spec:
  selector:
    app: test-app
  ports:
  - port: 80
    targetPort: 80
EOF
```

---

# Create TLS Ingress

```bash
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: ingress-nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.manmas.online
    secretName: app-manmas-online-tls
  rules:
  - host: app.manmas.online
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: test-app
            port:
              number: 80
EOF
```

---

# Verify Certificate and Ingress

## Certificates

```bash
kubectl get certificate -A
```

## Ingress

```bash
kubectl get ingress -A
```

---

# Check Certificate Details

```bash
kubectl describe certificate app-manmas-online-tls -n ingress-nginx
```

## Verify Secret

```bash
kubectl get secret app-manmas-online-tls -n ingress-nginx
```

## Check cert-manager Logs

```bash
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

---

# Test the Setup

## HTTP → HTTPS Redirect

```bash
curl -I http://app.manmas.online
```

## HTTPS Access

```bash
curl -k https://app.manmas.online
```

## Test via Load Balancer IP

```bash
curl -H "Host: test.manmas.online" http://4.182.209.93
```

---

# Optional Cleanup

```bash
kubectl delete certificate app-manmas-online-tls -n ingress-nginx
kubectl delete certificaterequest --all -n ingress-nginx
kubectl delete order --all -n ingress-nginx
kubectl delete challenge --all -n ingress-nginx
```

---

# Save TLS Information

```bash
echo "TLS Certificate: app-manmas-online-tls"

echo "Certificate Ready: $(kubectl get certificate app-manmas-online-tls -n ingress-nginx -o jsonpath='{.status.conditions[0].status}')"
```

---

# Step 10 — Create PostgreSQL Flexible Server

## Register PostgreSQL Provider

```bash
az provider register --namespace Microsoft.DBforPostgreSQL
```

## Verify Registration

```bash
az provider show \
  --namespace Microsoft.DBforPostgreSQL \
  --query "{Provider:namespace, RegistrationState:registrationState}"
```

```bash
az provider show \
  --namespace Microsoft.DBforPostgreSQL \
  --query registrationState \
  -o tsv
```

---

# List Available PostgreSQL SKUs

```bash
az postgres flexible-server list-skus \
  --location centralindia \
  --query "[].{Name:name, Tier:tier}" \
  -o table
```

---

# Recommended SKU

```text
Burstable B2ms
```

---

# PostgreSQL Features

Enable:

* ✅ Private access
* ✅ Backup
* ✅ HA (optional later)

---

# Verify VNet and Subnets

```bash
az network vnet list --output table
```

```bash
az network vnet subnet list \
  --resource-group rg-finops-prod-network \
  --vnet-name finops-prod-vnet \
  --output table
```

---

# Create PostgreSQL Flexible Server

## Windows CMD Format

```cmd
az postgres flexible-server create ^
  --resource-group rg-finops-prod-data ^
  --name finops-pgflex ^
  --location centralindia ^
  --admin-user pgadmin ^
  --admin-password "YourStr0ngPass!" ^
  --sku-name Standard_B1ms ^
  --tier Burstable ^
  --storage-size 32 ^
  --version 16 ^
  --subnet "/subscriptions/3ab4323c-e2ad-449e-ab64-565b17412d8f/resourceGroups/rg-finops-prod-network/providers/Microsoft.Network/virtualNetworks/finops-prod-vnet/subnets/flexiserver-subnet" ^
  --yes
```

---

# Database Structure

## Initial Database

```text
finops-db
```

## Create Database

```cmd
az postgres flexible-server db create ^
  --resource-group rg-finops-prod-data ^
  --server-name finops-pgflex ^
  --database-name finops-db
```
