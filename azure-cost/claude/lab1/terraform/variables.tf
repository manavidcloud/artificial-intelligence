variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "environment" {
  description = "Environment tag applied to all resources"
  type        = string
  default     = "prod"
}

variable "project" {
  description = "Short project name used in resource naming"
  type        = string
  default     = "costplatform"
}

variable "tenant_id" {
  description = "Entra ID tenant ID"
  type        = string
}

variable "target_subscription_ids" {
  description = "List of subscription IDs the platform will read cost data from"
  type        = list(string)
}

variable "aks_system_node_count" {
  description = "Number of nodes in the system nodepool"
  type        = number
  default     = 2
}

variable "aks_system_vm_size" {
  description = "VM size for system nodepool"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "aks_app_node_count" {
  description = "Initial node count for app nodepool"
  type        = number
  default     = 2
}

variable "aks_app_min_nodes" {
  type    = number
  default = 2
}

variable "aks_app_max_nodes" {
  type    = number
  default = 6
}

variable "aks_app_vm_size" {
  description = "VM size for app nodepool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "aks_kubernetes_version" {
  type    = string
  default = "1.30"
}

variable "vnet_address_space" {
  type    = string
  default = "10.10.0.0/16"
}

variable "aks_subnet_cidr" {
  type    = string
  default = "10.10.1.0/24"
}

variable "pe_subnet_cidr" {
  description = "Subnet CIDR reserved for private endpoints"
  type        = string
  default     = "10.10.2.0/24"
}

variable "log_analytics_retention_days" {
  type    = number
  default = 30
}

variable "admin_group_object_ids" {
  description = "Entra ID group object IDs that get AKS cluster-admin"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Extra tags merged onto all resources"
  type        = map(string)
  default     = {}
}
