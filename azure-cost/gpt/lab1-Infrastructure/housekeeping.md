# Delete the Core group (Removes AKS, ACR, and Managed Identities)
az group delete --name rg-finops-prod-core --yes --no-wait

# Delete the Network group (Removes VNet, Subnets, and Public IPs)
az group delete --name rg-finops-prod-network --yes --no-wait

# Delete the Data group (Removes PostgreSQL if you started it, or any volumes)
az group delete --name rg-finops-prod-data --yes --no-wait

# List groups to see if any MC_ groups remain
az group list --query "[?contains(name, 'MC_')].name" -o table

# If one exists, delete it manually (replace with your actual MC_ name)
# az group delete --name MC_rg-finops-prod-core_finops-aks_germanywestcentral --yes


kubectl config delete-context finops-aks
kubectl config delete-cluster finops-aks

helm repo remove ingress-nginx
helm repo remove jetstack


az group list --output table