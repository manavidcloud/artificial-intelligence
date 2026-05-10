# User-Assigned Managed Identity — one identity for all platform pods
resource "azurerm_user_assigned_identity" "platform" {
  name                = "mi-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

# Federated credential — binds the MI to the Kubernetes ServiceAccount
# This is what lets pods get Azure tokens without any secret
resource "azurerm_federated_identity_credential" "platform" {
  name                = local.mi_federated_name
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.platform.id

  # AKS OIDC issuer URL (only available after cluster is created)
  issuer = azurerm_kubernetes_cluster.main.oidc_issuer_url

  # Must match the Kubernetes ServiceAccount name and namespace exactly
  subject = "system:serviceaccount:${local.k8s_namespace}:${local.k8s_sa_name}"

  # Azure AD audience — always this value for Workload Identity
  audience = ["api://AzureADTokenExchange"]
}

# ─── RBAC across all target subscriptions ────────────────────────────────────
# Each role_assignment iterates over var.target_subscription_ids
# Cost Management Reader — read actual cost data, budgets, forecasts
resource "azurerm_role_assignment" "cost_management_reader" {
  for_each = toset(var.target_subscription_ids)

  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Cost Management Reader"
  scope                = "/subscriptions/${each.value}"
}

# Reader — enumerate all resources via Resource Graph
resource "azurerm_role_assignment" "reader" {
  for_each = toset(var.target_subscription_ids)

  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Reader"
  scope                = "/subscriptions/${each.value}"
}

# Monitoring Reader — read Azure Monitor metrics (CPU, mem, IOPS per resource)
resource "azurerm_role_assignment" "monitoring_reader" {
  for_each = toset(var.target_subscription_ids)

  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Monitoring Reader"
  scope                = "/subscriptions/${each.value}"
}

# Advisor Reader — pull resize/shutdown/RI recommendations
# Note: there is no built-in "Advisor Reader" — Reader already grants
# read access to Advisor. This assignment is kept explicit for clarity
# and in case a custom role is introduced later.
resource "azurerm_role_assignment" "advisor_reader" {
  for_each = toset(var.target_subscription_ids)

  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Reader"
  scope                = "/subscriptions/${each.value}"
}

# Reservation Reader — read RI coverage and unused reservations
# This is a built-in role at tenant/billing scope, assigned per subscription
resource "azurerm_role_assignment" "reservation_reader" {
  for_each = toset(var.target_subscription_ids)

  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Reservations Reader"
  scope                = "/subscriptions/${each.value}"
}

# Key Vault Secrets User — read secrets (Foundry endpoint, DB conn strings)
# Scoped to the Key Vault resource, not subscription-wide
resource "azurerm_role_assignment" "kv_secrets_user" {
  principal_id         = azurerm_user_assigned_identity.platform.principal_id
  role_definition_name = "Key Vault Secrets User"
  scope                = azurerm_key_vault.main.id
}
