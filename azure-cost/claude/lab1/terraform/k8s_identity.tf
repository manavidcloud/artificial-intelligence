# Namespace for all cost platform workloads
resource "kubernetes_namespace" "cost_platform" {
  metadata {
    name = local.k8s_namespace

    labels = {
      "app.kubernetes.io/managed-by"              = "terraform"
      "azure.workload.identity/use"               = "true"
    }
  }

  depends_on = [azurerm_kubernetes_cluster.main]
}

# ServiceAccount annotated with the Managed Identity client ID
# Any pod that uses this SA gets Azure tokens automatically via OIDC
resource "kubernetes_service_account" "platform" {
  metadata {
    name      = local.k8s_sa_name
    namespace = kubernetes_namespace.cost_platform.metadata[0].name

    annotations = {
      "azure.workload.identity/client-id" = azurerm_user_assigned_identity.platform.client_id
      "azure.workload.identity/tenant-id" = var.tenant_id
    }

    labels = {
      "azure.workload.identity/use" = "true"
    }
  }

  depends_on = [
    azurerm_federated_identity_credential.platform,
    kubernetes_namespace.cost_platform,
  ]
}

# SecretProviderClass — mounts Key Vault secrets as files into pods
# Labs 2+ pods reference this to get db conn strings, Foundry endpoint etc.
resource "kubernetes_manifest" "secret_provider_class" {
  manifest = {
    apiVersion = "secrets-store.csi.x-k8s.io/v1"
    kind       = "SecretProviderClass"
    metadata = {
      name      = "cost-platform-secrets"
      namespace = local.k8s_namespace
    }
    spec = {
      provider = "azure"
      parameters = {
        usePodIdentity       = "false"
        clientID             = azurerm_user_assigned_identity.platform.client_id
        keyvaultName         = azurerm_key_vault.main.name
        tenantId             = var.tenant_id
        cloudName            = "AzurePublicCloud"
        objects = yamlencode([
          {
            objectName = "db-connection-string"
            objectType = "secret"
            objectAlias = "DB_CONNECTION_STRING"
          },
          {
            objectName = "foundry-endpoint"
            objectType = "secret"
            objectAlias = "FOUNDRY_ENDPOINT"
          },
          {
            objectName = "redis-connection-string"
            objectType = "secret"
            objectAlias = "REDIS_CONNECTION_STRING"
          },
        ])
      }
      secretObjects = [
        {
          secretName = "cost-platform-secrets"
          type       = "Opaque"
          data = [
            { objectName = "DB_CONNECTION_STRING",    key = "db-connection-string" },
            { objectName = "FOUNDRY_ENDPOINT",        key = "foundry-endpoint" },
            { objectName = "REDIS_CONNECTION_STRING", key = "redis-connection-string" },
          ]
        }
      ]
    }
  }

  depends_on = [
    kubernetes_namespace.cost_platform,
    azurerm_kubernetes_cluster.main,
    azurerm_key_vault.main,
  ]
}
