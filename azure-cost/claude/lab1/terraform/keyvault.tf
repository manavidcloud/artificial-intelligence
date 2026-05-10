data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.prefix}-001"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  # Disable public network access — all access via private endpoint
  public_network_access_enabled = false
  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  # Use Azure RBAC for access control (not legacy access policies)
  enable_rbac_authorization = true

  tags = local.common_tags
}

# Private endpoint — Key Vault accessible only from AKS subnet
resource "azurerm_private_endpoint" "key_vault" {
  name                = "pe-kv-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "psc-kv-${local.prefix}"
    private_connection_resource_id = azurerm_key_vault.main.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "pdnszg-kv"
    private_dns_zone_ids = [azurerm_private_dns_zone.key_vault.id]
  }
}

resource "azurerm_private_dns_zone" "key_vault" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "key_vault" {
  name                  = "pdnsl-kv-${local.prefix}"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.key_vault.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
  tags                  = local.common_tags
}

# Grant the Terraform runner Key Vault Administrator so it can write secrets
resource "azurerm_role_assignment" "kv_admin_terraform" {
  principal_id         = data.azurerm_client_config.current.object_id
  role_definition_name = "Key Vault Administrator"
  scope                = azurerm_key_vault.main.id
}

# Grant AKS CSI secrets driver identity read access to Key Vault
resource "azurerm_role_assignment" "kv_csi_driver" {
  principal_id         = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].object_id
  role_definition_name = "Key Vault Secrets User"
  scope                = azurerm_key_vault.main.id
}

# Placeholder secrets — values populated in later labs
resource "azurerm_key_vault_secret" "db_connection_string" {
  name         = "db-connection-string"
  value        = "placeholder-set-in-lab2"
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.common_tags

  depends_on = [azurerm_role_assignment.kv_admin_terraform]
}

resource "azurerm_key_vault_secret" "foundry_endpoint" {
  name         = "foundry-endpoint"
  value        = "placeholder-set-in-lab4"
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.common_tags

  depends_on = [azurerm_role_assignment.kv_admin_terraform]
}

resource "azurerm_key_vault_secret" "redis_connection_string" {
  name         = "redis-connection-string"
  value        = "placeholder-set-in-lab2"
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.common_tags

  depends_on = [azurerm_role_assignment.kv_admin_terraform]
}
