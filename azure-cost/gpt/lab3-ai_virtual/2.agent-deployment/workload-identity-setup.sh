#!/bin/bash
# Lab 3 — Workload Identity Setup for AI Namespace
# Run this ONCE before applying agent-deployment.yaml
# This extends the Lab 1 Managed Identity to also cover the ai namespace

set -e

RESOURCE_GROUP="rg-finops-prod-core"
OPENAI_RESOURCE_GROUP="rg-finops-prod-ai"
AKS_NAME="finops-aks"
IDENTITY_NAME="mi-finops-prod"
OPENAI_RESOURCE="finops-ai-brain"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
NAMESPACE="ai"
SERVICE_ACCOUNT="ai-platform-sa"

echo "==> Getting AKS OIDC Issuer URL..."
OIDC_ISSUER=$(az aks show \
  --name $AKS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "oidcIssuerProfile.issuerUrl" -o tsv)
echo "    OIDC Issuer: $OIDC_ISSUER"

echo ""
echo "==> Getting Managed Identity Client ID..."
MI_CLIENT_ID=$(az identity show \
  --name $IDENTITY_NAME \
  --resource-group $RESOURCE_GROUP \
  --query clientId -o tsv)
echo "    Client ID: $MI_CLIENT_ID"

echo ""
echo "==> Getting Azure OpenAI Endpoint..."
OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name $OPENAI_RESOURCE \
  --resource-group $OPENAI_RESOURCE_GROUP \
  --query properties.endpoint -o tsv)
echo "    Endpoint: $OPENAI_ENDPOINT"

echo ""
echo "==> Creating Federated Credential for ai namespace..."
az identity federated-credential create \
  --name "finops-ai-federated" \
  --identity-name $IDENTITY_NAME \
  --resource-group $RESOURCE_GROUP \
  --issuer $OIDC_ISSUER \
  --subject "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT}" \
  --audience "api://AzureADTokenExchange"
echo "    Federated credential created."

echo ""
echo "==> Granting Managed Identity access to Azure OpenAI..."
OPENAI_RESOURCE_ID=$(az cognitiveservices account show \
  --name $OPENAI_RESOURCE \
  --resource-group $OPENAI_RESOURCE_GROUP \
  --query id -o tsv)

az role assignment create \
  --assignee $MI_CLIENT_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $OPENAI_RESOURCE_ID
echo "    Role assigned: Cognitive Services OpenAI User"

echo ""
echo "==> Summary — paste these values into agent-deployment.yaml:"
echo ""
echo "    annotations:"
echo "      azure.workload.identity/client-id: \"$MI_CLIENT_ID\""
echo ""
echo "    env:"
echo "    - name: AZURE_OPENAI_ENDPOINT"
echo "      value: \"$OPENAI_ENDPOINT\""
echo ""
echo "Done. Now apply agent-deployment.yaml with these values filled in."
