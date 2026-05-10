output "resource_group_name" {
  description = "Main resource group name"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "AKS cluster name — use in: az aks get-credentials"
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_oidc_issuer_url" {
  description = "AKS OIDC issuer URL — used in federated credential"
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "managed_identity_client_id" {
  description = "MI client ID — set as annotation on the ServiceAccount"
  value       = azurerm_user_assigned_identity.platform.client_id
}

output "managed_identity_principal_id" {
  description = "MI principal ID — used for RBAC assignments"
  value       = azurerm_user_assigned_identity.platform.principal_id
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "container_registry_login_server" {
  description = "ACR login server — use in docker push / helm values"
  value       = azurerm_container_registry.main.login_server
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

output "k8s_namespace" {
  description = "Kubernetes namespace for the cost platform"
  value       = local.k8s_namespace
}

output "k8s_service_account_name" {
  description = "Kubernetes ServiceAccount name"
  value       = local.k8s_sa_name
}

output "vnet_id" {
  description = "VNet ID — referenced by Lab 2 private endpoints"
  value       = azurerm_virtual_network.main.id
}

output "pe_subnet_id" {
  description = "Private endpoint subnet ID — used in Lab 2"
  value       = azurerm_subnet.private_endpoints.id
}

output "aks_subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}

output "get_credentials_command" {
  description = "Run this to configure kubectl after apply"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name} --overwrite-existing"
}
