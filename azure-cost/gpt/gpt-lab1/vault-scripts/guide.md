bash setup-keyvault.sh           # creates kv-finops-prod-002, stores 6 secrets
bash setup-workload-identity.sh  # MI, federated cred, RBAC, ServiceAccount
bash setup-oauth2-proxy.sh       # Entra App Registration, deploy to security NS
bash verify-lab1.sh              # confirms everything green before Lab 2


az provider show \
  --namespace Microsoft.Authorization \
  --query "registrationState" \
  --output tsv


  