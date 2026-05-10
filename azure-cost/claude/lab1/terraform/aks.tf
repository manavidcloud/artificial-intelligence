resource "azurerm_kubernetes_cluster" "main" {
  name                      = "aks-${local.prefix}"
  location                  = azurerm_resource_group.main.location
  resource_group_name       = azurerm_resource_group.main.name
  dns_prefix                = local.prefix
  kubernetes_version        = var.aks_kubernetes_version
  automatic_channel_upgrade = "patch"
  node_resource_group       = "rg-${local.prefix}-nodes"

  # OIDC + Workload Identity — the two flags that make MI federation work
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # System nodepool — runs kube-system, cert-manager, CSI drivers
  default_node_pool {
    name                = "system"
    node_count          = var.aks_system_node_count
    vm_size             = var.aks_system_vm_size
    vnet_subnet_id      = azurerm_subnet.aks.id
    os_disk_size_gb     = 64
    os_disk_type        = "Managed"
    type                = "VirtualMachineScaleSets"
    only_critical_addons_enabled = true

    node_labels = {
      "nodepool-type" = "system"
      "environment"   = var.environment
    }

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  # AAD integration with Entra ID groups for RBAC
  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
    service_cidr      = "10.100.0.0/16"
    dns_service_ip    = "10.100.0.10"
  }

  oms_agent {
    log_analytics_workspace_id      = azurerm_log_analytics_workspace.main.id
    msi_auth_for_monitoring_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  maintenance_window_auto_upgrade {
    frequency   = "Weekly"
    interval    = 1
    day_of_week = "Sunday"
    start_time  = "02:00"
    utc_offset  = "+00:00"
    duration    = 4
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [
      default_node_pool[0].node_count,
    ]
  }
}

# App nodepool — runs FastAPI, MCP server, dashboard pods
resource "azurerm_kubernetes_cluster_node_pool" "app" {
  name                  = "app"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.aks_app_vm_size
  node_count            = var.aks_app_node_count
  min_count             = var.aks_app_min_nodes
  max_count             = var.aks_app_max_nodes
  enable_auto_scaling   = true
  vnet_subnet_id        = azurerm_subnet.aks.id
  os_disk_size_gb       = 128
  os_disk_type          = "Managed"

  node_labels = {
    "nodepool-type" = "app"
    "environment"   = var.environment
    "workload"      = "cost-platform"
  }

  node_taints = []

  upgrade_settings {
    max_surge = "33%"
  }

  tags = local.common_tags
}

# Grant AKS system identity permission to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Grant AKS system identity permission to manage NICs/routes in node RG
resource "azurerm_role_assignment" "aks_network_contributor" {
  principal_id         = azurerm_kubernetes_cluster.main.identity[0].principal_id
  role_definition_name = "Network Contributor"
  scope                = azurerm_virtual_network.main.id
}
