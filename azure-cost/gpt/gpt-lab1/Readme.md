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

az group create \
  --name rg-finops-prod-core \
  --location germanywestcentral \
  --tags Environment=Test Project=ai-finops

az group create \
  --name rg-finops-prod-data \
  --location germanywestcentral \
  --tags Environment=Test Project=ai-finops

az group create \
  --name rg-finops-prod-network \
  --location germanywestcentral \
  --tags Environment=Test Project=ai-finops

az group list --output table
```

---

# Step 2 — Create Azure Container Registry
- ACR name should be globally unique
Use Premium only if needed later.

For now:

```text id="b7nlkf"
Basic SKU
```

Example:

```bash
az acr create \
  --name finopsacr-manmas \
  --resource-group rg-finops-prod-core \
  --sku Basic
```

# Issues while creating the ACR 
```
$ az acr create   --name finopsacrmanmas   --resource-group rg-finops-prod-core   --sku Basic
(MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'. See https://aka.ms/rps-not-found for how to register subscriptions.
Code: MissingSubscriptionRegistration
Message: The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'. See https://aka.ms/rps-not-found for how to register subscriptions.
Exception Details:      (MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'. See https://aka.ms/rps-not-found for how to register subscriptions.
        Code: MissingSubscriptionRegistration
        Message: The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'. See https://aka.ms/rps-not-found for how to register subscriptions.
        Target: Microsoft.ContainerRegistry
```
# SOLUTION:
az provider register --namespace Microsoft.ContainerRegistry
az acr create \
  --name finopsacrmanmas \
  --resource-group rg-finops-prod-core \
  --sku Basic

az acr list -otable 

Portal -> All services -> search "registory" -> Container registries 
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
# Error while creating aks 
$ az aks create \
  --resource-group rg-finops-prod-core \
  --name finops-aks \
  --node-count 2 \
  --enable-managed-identity \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --generate-ssh-keys
SSH key files 'C:\Users\manav\.ssh\id_rsa' and 'C:\Users\manav\.ssh\id_rsa.pub' have been generated under ~/.ssh to allow SSH access to the VM. If using machines without permanent storage like Azure Cloud Shell without an attached file share, back up your keys to a safe location
(MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.ContainerService'. See https://aka.ms/rps-not-found for how to register subscriptions.
Code: MissingSubscriptionRegistration
Message: The subscription is not registered to use namespace 'Microsoft.ContainerService'. See https://aka.ms/rps-not-found for how to register subscriptions.
Exception Details:      (MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.ContainerService'. See https://aka.ms/rps-not-found for how to register subscriptions.
        Code: MissingSubscriptionRegistration
        Message: The subscription is not registered to use namespace 'Microsoft.ContainerService'. See https://aka.ms/rps-not-found for how to register subscriptions.
        Target: Microsoft.ContainerService

# aks fix
# Register for Managed Identity and Advanced Networking
az provider register --namespace Microsoft.ManagedIdentity
az provider register --namespace Microsoft.Network


az provider list --query "[?contains(namespace, 'Microsoft.ContainerService') || contains(namespace, 'Microsoft.ManagedIdentity')].{Provider:namespace, Status:registrationState}" --output table


If it fail like this again 
Message: The VM size of Standard_DS2_v2 is not allowed in your subscription in location 'germanywestcentral'. The available VM sizes are 

Try with spefici sku in the command 


az aks create \
  --resource-group rg-finops-prod-core \
  --name finops-aks \
  --node-count 2 \
  --enable-managed-identity \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --tier free \
  --node-vm-size Standard_D2pds_v6 \
  --generate-ssh-keys
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
  --max-count 2 \
  --node-vm-size Standard_D2pds_v6

OR 

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
- validate path should be like this 
- if not then applied the annotation
service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path: /healthz

kubectl annotate service ingress-nginx-controller   -n ingress-nginx   service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz   --overwrite

```

---

# Step 7 — Install cert-manager

For HTTPS certificates.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

```bash
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true


helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.18.0 \
  --set crds.enabled=true  
```


---

# Step 8 — Configure DNS

Example domains:

```text id="t1p3l7"
app.company.com
api.company.com
ai.company.com

app.manmas.online
api.manmas.online
ai.manmas.online

To point your domains to your AKS cluster, you first need to find the External Public IP of your Ingress Controller (like NGINX). Once you have that IP, you will create A Records in your DNS provider's control panel (e.g., GoDaddy, Cloudflare, or Azure DNS).

1. Find your Ingress Public IP
Assuming you have already installed an Ingress Controller (like NGINX), run the following

kubectl get service -n ingress-nginx

2. Look for the EXTERNAL-IP column. It should be a public IP address (e.g., 20.x.x.x).

Type,Host/Name,Value (IP Address),TTL
A,app,YOUR_INGRESS_IP,3600 (Auto)
A,api,YOUR_INGRESS_IP,3600 (Auto)
A,ai,YOUR_INGRESS_IP,3600 (Auto)
```

Point DNS to ingress public IP.

In this case my nginx ip is 4.182.209.93 which i have added in my dns record 

nsloolup with app.manmas.online must return 4.182.209.93

$ kubectl get service -n ingress-nginx
NAME                                 TYPE           CLUSTER-IP    EXTERNAL-IP    PORT(S)                      AGE
ingress-nginx-controller             LoadBalancer   10.0.231.35   4.182.209.93   80:32496/TCP,443:30605/TCP   13m
ingress-nginx-controller-admission   ClusterIP      10.0.23.240   <none>         443/TCP                      13m

manav@DESKTOP-D00CME9 MINGW64 /
$ kubectl get ing -A
No resources found

manav@DESKTOP-D00CME9 MINGW64 /
$ kubectl get service ingress-nginx-controller -n ingress-nginx
NAME                       TYPE           CLUSTER-IP    EXTERNAL-IP    PORT(S)                      AGE
ingress-nginx-controller   LoadBalancer   10.0.231.35   4.182.209.93   80:32496/TCP,443:30605/TCP   26m

manav@DESKTOP-D00CME9 MINGW64 /
$ nslookup app.manmas.online
Server:  UnKnown
Address:  192.168.0.1

Non-authoritative answer:
Name:    app.manmas.online
Address:  4.182.209.93

If yes then step 8 is completed.
```
---
# Step 9 — Configure TLS

# Add the health probe annotation to fix the ACME challenge routing
kubectl annotate service ingress-nginx-controller \
  -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz
- Kindly check if any other path added if then 
kubectl get svc ingress-nginx-controller -n ingress-nginx -oyaml > abc.yaml
vi abc.yaml
- remmove wrong annotation
- kubectl apply -f abc.yaml 

# Verify the annotation was added
kubectl get service ingress-nginx-controller -n ingress-nginx -o yaml | grep -A3 "annotations:"

# Restart NGINX to apply changes
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
kubectl rollout status deployment ingress-nginx-controller -n ingress-nginx --timeout=120s
```

### 2. **Install cert-manager Fresh**

```bash
# Add the Jetstack repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager (using stable version)
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.14.5 \
  --set installCRDs=true

# Wait for cert-manager pods to be ready
kubectl wait --for=condition=ready pod -l app=cert-manager -n cert-manager --timeout=120s
kubectl wait --for=condition=ready pod -l app=cainjector -n cert-manager --timeout=120s
kubectl wait --for=condition=ready pod -l app=webhook -n cert-manager --timeout=120s

# Verify all pods are running
kubectl get pods -n cert-manager
```

Expected output:
```
NAME                                           READY   STATUS    RESTARTS   AGE
cert-manager-xxxxxxxxxx-xxxxx                  1/1     Running   0          30s
cert-manager-cainjector-xxxxxxxxxx-xxxxx       1/1     Running   0          30s
cert-manager-webhook-xxxxxxxxxx-xxxxx          1/1     Running   0          30s
```

### 3. **Create the ClusterIssuer**

```bash
# Create the production ClusterIssuer
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

# Verify ClusterIssuer is ready
kubectl get clusterissuer letsencrypt-prod
```

Expected output:
```
NAME               READY   AGE
letsencrypt-prod   True    5s
```

### 4. **Create a Simple Test Deployment First**

Let's deploy a simple nginx to test the ingress and TLS:

```bash
# Create a test deployment
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

### 5. **Create the TLS Ingress**

```bash
# Create ingress with TLS
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

### 6. **Monitor Certificate Creation (Watch this closely)**

```bash
# Watch certificates in real-time
kubectl get certificate -A -w
```

In another terminal, watch the challenges:

```bash
# Watch challenges
kubectl get challenge -A -w
```

### 7. **Check Certificate Status**

```bash
# After a minute, check the certificate details
kubectl describe certificate app-manmas-online-tls -n ingress-nginx

# Check if secret was created
kubectl get secret app-manmas-online-tls -n ingress-nginx

# Check cert-manager logs if something goes wrong
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

### 8. **Test the Setup**

Once the certificate is ready (shows `READY: True`):

```bash
# Test HTTP to HTTPS redirect
curl -I http://app.manmas.online

# Test HTTPS directly
curl -k https://app.manmas.online

# Should return nginx welcome page
```

### 9. **If It Still Fails - Create a Debug Ingress**

Let's create an ingress without TLS first to verify routing works:

```bash
# Create HTTP-only ingress for testing
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: test-http-ingress
  namespace: ingress-nginx
spec:
  ingressClassName: nginx
  rules:
  - host: test.manmas.online
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

# Test HTTP access
curl -H "Host: test.manmas.online" http://4.182.209.93
```

### 10. **Quick Diagnostic Commands**

If certificate isn't becoming ready, run these:

```bash
# Check if the ingress controller is receiving the challenge
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=100 | grep -i acme

# Check if the challenge endpoint is accessible
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -v http://app.manmas.online/.well-known/acme-challenge/test

# Check Azure Load Balancer health probe status
az network lb probe list \
  --resource-group $(az aks show --resource-group rg-finops-prod-core --name finops-aks --query nodeResourceGroup -o tsv) \
  --lb-name kubernetes \
  --output table
```

## What's Expected

After successful setup, you should see:

```bash
$ kubectl get certificate -A
NAMESPACE       NAME                     READY   SECRET                   AGE
ingress-nginx   app-manmas-online-tls    True    app-manmas-online-tls    2m

$ kubectl get ingress -A
NAMESPACE       NAME          CLASS   HOSTS               ADDRESS        PORTS     AGE
ingress-nginx   app-ingress   nginx   app.manmas.online   4.182.209.93   80,443    2m
```

## Proceed to Step 10

Once TLS is working, save your progress:

```bash
# Save the certificate secret name for reference
echo "TLS Certificate: app-manmas-online-tls"
echo "Certificate Ready: $(kubectl get certificate app-manmas-online-tls -n ingress-nginx -o jsonpath='{.status.conditions[0].status}')"
```

























#    # # # ############################################



## Step 10 — Create PostgreSQL Flexible Server


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
