#!/usr/bin/env bash
# =============================================================================
#  navuAI — Phase 9: Multi-Cloud Terraform Modules
#
#  What this script builds:
#    1. Terraform root module — wires all sub-modules together
#    2. modules/networking — VNet/VPC (Azure | AWS | GCP)
#    3. modules/aks        — Kubernetes cluster (AKS | EKS | GKE)
#    4. modules/keyvault   — Secrets store (Key Vault | Secrets Manager | GCP SM)
#    5. modules/gpu-vm     — GPU VM for self-hosted LLMs (cross-cloud)
#    6. modules/vpn        — B2B VPN gateway (cross-cloud)
#    7. docs/multi-cloud-swap-guide.md — step-by-step provider swap guide
#
#  Prerequisites: terraform installed | navuai.env filled in
#  Run from:     WSL or Azure Cloud Shell
#  Time:         ~10 minutes (writes files; no cloud resources provisioned here)
#
#  NOTE: This phase WRITES Terraform files only. To provision infrastructure
#        from scratch using Terraform instead of the Phase 1 scripts, run:
#          cd infrastructure/terraform && terraform init && terraform apply
# =============================================================================

set -euo pipefail

RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   BOLD='\033[1m';  NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${CYAN}${BOLD}──────────────────────────────────────────${NC}"; \
            echo -e "${CYAN}${BOLD}  STEP $*${NC}"; \
            echo -e "${CYAN}${BOLD}──────────────────────────────────────────${NC}"; }

banner() {
  echo -e "${BOLD}"
  echo "=============================================="
  echo "  navuAI — Phase 9: Multi-Cloud Terraform"
  echo "=============================================="
  echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/navuai.env"

TF_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)/infrastructure/terraform"

# ── Step 1: Check terraform is available ─────────────────────────────────────
check_prerequisites() {
  step "1 — Check prerequisites"
  command -v terraform &>/dev/null && success "terraform $(terraform version -json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('terraform_version',''))" 2>/dev/null) found" \
    || warn "terraform not installed — files will still be written but you cannot run them"
  mkdir -p "$TF_ROOT/modules/"{networking,aks,keyvault,gpu-vm,vpn}
  success "Terraform directory structure ready: $TF_ROOT"
}

# ── Step 2: Root Terraform module ─────────────────────────────────────────────
write_root_module() {
  step "2 — Write root Terraform module"

  cat > "$TF_ROOT/main.tf" << 'HCL'
# =============================================================================
# navuAI — Root Terraform Module
# Provisions the full navuAI platform on Azure (default) or swap to AWS/GCP
# Run: terraform init && terraform plan && terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.0" }
    aws     = { source = "hashicorp/aws",     version = "~> 5.0" }
    google  = { source = "hashicorp/google",  version = "~> 5.0" }
  }
  # Remote state: uncomment and fill in your storage account
  # backend "azurerm" {
  #   resource_group_name  = "navuai-rg"
  #   storage_account_name = "navuaistateXXXX"
  #   container_name       = "tfstate"
  #   key                  = "navuai.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# ── Networking ────────────────────────────────────────────────────────────────
module "networking" {
  source              = "./modules/networking"
  resource_group_name = var.resource_group_name
  location            = var.location
  vnet_name           = var.vnet_name
  vnet_cidr           = var.vnet_cidr
  aks_subnet_cidr     = var.aks_subnet_cidr
  gpu_subnet_cidr     = var.gpu_subnet_cidr
  pe_subnet_cidr      = var.pe_subnet_cidr
  tags                = var.common_tags
}

# ── Kubernetes Cluster ────────────────────────────────────────────────────────
module "aks" {
  source               = "./modules/aks"
  resource_group_name  = var.resource_group_name
  location             = var.location
  cluster_name         = var.aks_cluster_name
  aks_subnet_id        = module.networking.aks_subnet_id
  acr_name             = var.acr_name
  node_vm_size         = var.aks_node_vm_size
  node_count_min       = var.aks_node_count_min
  node_count_max       = var.aks_node_count_max
  kubernetes_version   = var.kubernetes_version
  tags                 = var.common_tags
}

# ── Key Vault ─────────────────────────────────────────────────────────────────
module "keyvault" {
  source              = "./modules/keyvault"
  resource_group_name = var.resource_group_name
  location            = var.location
  keyvault_name       = var.keyvault_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  aks_identity_id     = module.aks.kubelet_identity_object_id
  pe_subnet_id        = module.networking.pe_subnet_id
  tags                = var.common_tags
}

# ── GPU VM (optional — set skip_gpu_vm=true in vars to skip) ─────────────────
module "gpu_vm" {
  count               = var.skip_gpu_vm ? 0 : 1
  source              = "./modules/gpu-vm"
  resource_group_name = var.resource_group_name
  location            = var.location
  vm_name             = var.gpu_vm_name
  vm_size             = var.gpu_vm_size
  subnet_id           = module.networking.gpu_subnet_id
  admin_username      = var.gpu_vm_admin_user
  ssh_public_key_path = var.gpu_vm_ssh_key_path
  tags                = var.common_tags
}

# ── VPN Gateway (optional — set skip_vpn=true in vars to skip) ───────────────
module "vpn" {
  count               = var.skip_vpn ? 0 : 1
  source              = "./modules/vpn"
  resource_group_name = var.resource_group_name
  location            = var.location
  vnet_name           = module.networking.vnet_name
  gateway_subnet_cidr = var.vpn_gateway_subnet_cidr
  tags                = var.common_tags
}

data "azurerm_client_config" "current" {}
HCL

  # ── variables.tf ──────────────────────────────────────────────────────────
  cat > "$TF_ROOT/variables.tf" << HCL
# =============================================================================
# navuAI — Terraform Variables
# =============================================================================

variable "resource_group_name" {
  description = "Azure Resource Group"
  type        = string
  default     = "${RESOURCE_GROUP}"
}
variable "location" {
  description = "Azure region"
  type        = string
  default     = "${AZURE_LOCATION}"
}
variable "vnet_name"          { type = string; default = "${VNET_NAME}" }
variable "vnet_cidr"          { type = string; default = "${VNET_CIDR}" }
variable "aks_subnet_cidr"    { type = string; default = "${AKS_SUBNET_CIDR}" }
variable "gpu_subnet_cidr"    { type = string; default = "${GPU_SUBNET_CIDR}" }
variable "pe_subnet_cidr"     { type = string; default = "${PE_SUBNET_CIDR}" }
variable "aks_cluster_name"   { type = string; default = "${AKS_CLUSTER_NAME}" }
variable "acr_name"           { type = string; default = "${ACR_NAME}" }
variable "keyvault_name"      { type = string; default = "${KEYVAULT_NAME}" }
variable "aks_node_vm_size"   { type = string; default = "${AKS_NODE_VM_SIZE}" }
variable "aks_node_count_min" { type = number; default = ${AKS_NODE_COUNT_MIN} }
variable "aks_node_count_max" { type = number; default = ${AKS_NODE_COUNT_MAX} }
variable "kubernetes_version" { type = string; default = "1.30" }
variable "gpu_vm_name"        { type = string; default = "${GPU_VM_NAME}" }
variable "gpu_vm_size"        { type = string; default = "${GPU_VM_SIZE}" }
variable "gpu_vm_admin_user"  { type = string; default = "${GPU_VM_ADMIN_USER}" }
variable "gpu_vm_ssh_key_path"{ type = string; default = "~/.ssh/navuai_gpu_rsa.pub" }
variable "skip_gpu_vm"        { type = bool;   default = true }
variable "skip_vpn"           { type = bool;   default = true }
variable "vpn_gateway_subnet_cidr" { type = string; default = "10.0.4.0/27" }
variable "common_tags" {
  type    = map(string)
  default = { project = "navuai", managed_by = "terraform" }
}
HCL

  # ── outputs.tf ────────────────────────────────────────────────────────────
  cat > "$TF_ROOT/outputs.tf" << 'HCL'
output "aks_cluster_name"          { value = module.aks.cluster_name }
output "aks_kubeconfig_command"    { value = "az aks get-credentials --resource-group ${var.resource_group_name} --name ${module.aks.cluster_name}" }
output "acr_login_server"          { value = module.aks.acr_login_server }
output "keyvault_uri"              { value = module.keyvault.vault_uri }
output "vnet_id"                   { value = module.networking.vnet_id }
output "gpu_vm_private_ip"         { value = length(module.gpu_vm) > 0 ? module.gpu_vm[0].private_ip : "skipped" }
HCL

  success "Root module written: main.tf, variables.tf, outputs.tf"
}

# ── Step 3: Networking module ─────────────────────────────────────────────────
write_networking_module() {
  step "3 — Write networking module"
  MOD="$TF_ROOT/modules/networking"

  cat > "$MOD/main.tf" << 'HCL'
# navuAI Networking Module — Azure VNet
# Swap guide: for AWS replace azurerm_virtual_network → aws_vpc, subnets → aws_subnet
# Swap guide: for GCP replace azurerm_virtual_network → google_compute_network

resource "azurerm_resource_group" "navuai" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  address_space       = [var.vnet_cidr]
  location            = azurerm_resource_group.navuai.location
  resource_group_name = azurerm_resource_group.navuai.name
  tags                = var.tags
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.navuai.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.aks_subnet_cidr]
}

resource "azurerm_subnet" "gpu" {
  name                 = "gpu-subnet"
  resource_group_name  = azurerm_resource_group.navuai.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.gpu_subnet_cidr]
}

resource "azurerm_subnet" "pe" {
  name                 = "pe-subnet"
  resource_group_name  = azurerm_resource_group.navuai.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.pe_subnet_cidr]
  private_endpoint_network_policies_enabled = false
}

resource "azurerm_network_security_group" "aks" {
  name                = "navuai-aks-nsg"
  location            = azurerm_resource_group.navuai.location
  resource_group_name = azurerm_resource_group.navuai.name
  tags                = var.tags

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowHTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}
HCL

  cat > "$MOD/variables.tf" << 'HCL'
variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "vnet_name"           { type = string }
variable "vnet_cidr"           { type = string }
variable "aks_subnet_cidr"     { type = string }
variable "gpu_subnet_cidr"     { type = string }
variable "pe_subnet_cidr"      { type = string }
variable "tags"                { type = map(string); default = {} }
HCL

  cat > "$MOD/outputs.tf" << 'HCL'
output "vnet_id"        { value = azurerm_virtual_network.main.id }
output "vnet_name"      { value = azurerm_virtual_network.main.name }
output "aks_subnet_id"  { value = azurerm_subnet.aks.id }
output "gpu_subnet_id"  { value = azurerm_subnet.gpu.id }
output "pe_subnet_id"   { value = azurerm_subnet.pe.id }
HCL

  success "modules/networking written"
}

# ── Step 4: AKS module ────────────────────────────────────────────────────────
write_aks_module() {
  step "4 — Write AKS module"
  MOD="$TF_ROOT/modules/aks"

  cat > "$MOD/main.tf" << 'HCL'
# navuAI AKS Module
# Swap: for AWS replace with aws_eks_cluster + aws_eks_node_group
# Swap: for GCP replace with google_container_cluster + google_container_node_pool

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = true
  tags                = var.tags
}

resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.kubernetes_version
  tags                = var.tags

  default_node_pool {
    name                = "system"
    node_count          = 1
    vm_size             = "Standard_D2s_v3"
    vnet_subnet_id      = var.aks_subnet_id
    enable_auto_scaling = false
    type                = "VirtualMachineScaleSets"
  }

  identity { type = "SystemAssigned" }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.96.0.0/16"
    dns_service_ip    = "10.96.0.10"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  lifecycle {
    ignore_changes = [default_node_pool[0].node_count]
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "app" {
  name                  = "app"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.node_vm_size
  enable_auto_scaling   = true
  min_count             = var.node_count_min
  max_count             = var.node_count_max
  vnet_subnet_id        = var.aks_subnet_id
  tags                  = var.tags
}

# Grant AKS kubelet identity permission to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}
HCL

  cat > "$MOD/variables.tf" << 'HCL'
variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "cluster_name"        { type = string }
variable "aks_subnet_id"       { type = string }
variable "acr_name"            { type = string }
variable "node_vm_size"        { type = string; default = "Standard_D2s_v3" }
variable "node_count_min"      { type = number; default = 1 }
variable "node_count_max"      { type = number; default = 3 }
variable "kubernetes_version"  { type = string; default = "1.30" }
variable "tags"                { type = map(string); default = {} }
HCL

  cat > "$MOD/outputs.tf" << 'HCL'
output "cluster_name"                { value = azurerm_kubernetes_cluster.main.name }
output "cluster_id"                  { value = azurerm_kubernetes_cluster.main.id }
output "kubelet_identity_object_id"  { value = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id }
output "acr_login_server"            { value = azurerm_container_registry.acr.login_server }
output "kube_config_raw"             { value = azurerm_kubernetes_cluster.main.kube_config_raw; sensitive = true }
HCL

  success "modules/aks written"
}

# ── Step 5: Key Vault module ──────────────────────────────────────────────────
write_keyvault_module() {
  step "5 — Write Key Vault module"
  MOD="$TF_ROOT/modules/keyvault"

  cat > "$MOD/main.tf" << 'HCL'
# navuAI Key Vault Module
# Swap: for AWS replace with aws_secretsmanager_secret
# Swap: for GCP replace with google_secret_manager_secret

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = var.keyvault_name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = var.tags
}

# Allow the Terraform runner to manage secrets
resource "azurerm_role_assignment" "deployer_kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow AKS kubelet identity to read secrets
resource "azurerm_role_assignment" "aks_kv_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.aks_identity_id
}

# Private endpoint for Key Vault
resource "azurerm_private_endpoint" "kv" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "${var.keyvault_name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.pe_subnet_id

  private_service_connection {
    name                           = "${var.keyvault_name}-psc"
    private_connection_resource_id = azurerm_key_vault.main.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }
}
HCL

  cat > "$MOD/variables.tf" << 'HCL'
variable "resource_group_name"      { type = string }
variable "location"                 { type = string }
variable "keyvault_name"            { type = string }
variable "tenant_id"                { type = string }
variable "aks_identity_id"          { type = string }
variable "pe_subnet_id"             { type = string; default = "" }
variable "enable_private_endpoint"  { type = bool;   default = false }
variable "tags"                     { type = map(string); default = {} }
HCL

  cat > "$MOD/outputs.tf" << 'HCL'
output "vault_id"    { value = azurerm_key_vault.main.id }
output "vault_uri"   { value = azurerm_key_vault.main.vault_uri }
output "vault_name"  { value = azurerm_key_vault.main.name }
HCL

  success "modules/keyvault written"
}

# ── Step 6: GPU VM module ─────────────────────────────────────────────────────
write_gpu_vm_module() {
  step "6 — Write GPU VM module"
  MOD="$TF_ROOT/modules/gpu-vm"

  cat > "$MOD/main.tf" << 'HCL'
# navuAI GPU VM Module — self-hosted LLMs via Ollama or vLLM
# Swap: for AWS use aws_instance with p3/g4dn instance type
# Swap: for GCP use google_compute_instance with accelerator { type = "nvidia-tesla-t4" }

resource "azurerm_public_ip" "gpu" {
  name                = "${var.vm_name}-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_network_interface" "gpu" {
  name                = "${var.vm_name}-nic"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.gpu.id
  }
}

resource "azurerm_linux_virtual_machine" "gpu" {
  name                  = var.vm_name
  location              = var.location
  resource_group_name   = var.resource_group_name
  size                  = var.vm_size
  admin_username        = var.admin_username
  network_interface_ids = [azurerm_network_interface.gpu.id]
  tags                  = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # Bootstrap: install NVIDIA drivers + Ollama
  custom_data = base64encode(<<-SCRIPT
    #!/bin/bash
    apt-get update -y
    apt-get install -y nvidia-driver-535 nvidia-utils-535 || true
    curl -fsSL https://ollama.ai/install.sh | sh
    systemctl enable ollama
    systemctl start ollama
    # Pull default model
    ollama pull llama3.2:3b || true
  SCRIPT
  )
}
HCL

  cat > "$MOD/variables.tf" << 'HCL'
variable "resource_group_name"  { type = string }
variable "location"             { type = string }
variable "vm_name"              { type = string; default = "navuai-gpu-vm" }
variable "vm_size"              { type = string; default = "Standard_NC4as_T4_v3" }
variable "subnet_id"            { type = string }
variable "admin_username"       { type = string; default = "navuaiadmin" }
variable "ssh_public_key_path"  { type = string; default = "~/.ssh/navuai_gpu_rsa.pub" }
variable "tags"                 { type = map(string); default = {} }
HCL

  cat > "$MOD/outputs.tf" << 'HCL'
output "private_ip"  { value = azurerm_network_interface.gpu.private_ip_address }
output "public_ip"   { value = azurerm_public_ip.gpu.ip_address }
output "vm_id"       { value = azurerm_linux_virtual_machine.gpu.id }
HCL

  success "modules/gpu-vm written"
}

# ── Step 7: VPN module ────────────────────────────────────────────────────────
write_vpn_module() {
  step "7 — Write VPN Gateway module"
  MOD="$TF_ROOT/modules/vpn"

  cat > "$MOD/main.tf" << 'HCL'
# navuAI VPN Gateway Module — B2B VPN for on-premise connectivity
# Swap: for AWS use aws_vpn_gateway + aws_customer_gateway
# Swap: for GCP use google_compute_vpn_gateway

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = var.vnet_name
  address_prefixes     = [var.gateway_subnet_cidr]
}

resource "azurerm_public_ip" "vpn_gw" {
  name                = "navuai-vpn-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_virtual_network_gateway" "main" {
  name                = "navuai-vpn-gw"
  location            = var.location
  resource_group_name = var.resource_group_name
  type                = "Vpn"
  vpn_type            = "RouteBased"
  sku                 = "VpnGw1"
  active_active       = false
  enable_bgp          = false
  tags                = var.tags

  ip_configuration {
    name                          = "vnetGatewayConfig"
    public_ip_address_id          = azurerm_public_ip.vpn_gw.id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway.id
  }
}

# Add a local network gateway (on-premise side) for each connected site
resource "azurerm_local_network_gateway" "onprem" {
  for_each            = var.vpn_sites
  name                = each.key
  location            = var.location
  resource_group_name = var.resource_group_name
  gateway_address     = each.value.public_ip
  address_space       = each.value.address_space
  tags                = var.tags
}

resource "azurerm_virtual_network_gateway_connection" "onprem" {
  for_each                   = var.vpn_sites
  name                       = "${each.key}-connection"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  type                       = "IPsec"
  virtual_network_gateway_id = azurerm_virtual_network_gateway.main.id
  local_network_gateway_id   = azurerm_local_network_gateway.onprem[each.key].id
  shared_key                 = each.value.shared_key
  tags                       = var.tags
}
HCL

  cat > "$MOD/variables.tf" << 'HCL'
variable "resource_group_name"    { type = string }
variable "location"               { type = string }
variable "vnet_name"              { type = string }
variable "gateway_subnet_cidr"    { type = string; default = "10.0.4.0/27" }
variable "tags"                   { type = map(string); default = {} }
variable "vpn_sites" {
  description = "Map of VPN site name → { public_ip, address_space, shared_key }"
  type = map(object({
    public_ip     = string
    address_space = list(string)
    shared_key    = string
  }))
  default = {}
}
HCL

  cat > "$MOD/outputs.tf" << 'HCL'
output "vpn_gateway_id"        { value = azurerm_virtual_network_gateway.main.id }
output "vpn_gateway_public_ip" { value = azurerm_public_ip.vpn_gw.ip_address }
HCL

  success "modules/vpn written"
}

# ── Step 8: Multi-cloud swap guide ────────────────────────────────────────────
write_swap_guide() {
  step "8 — Write multi-cloud swap guide"
  DOCS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/docs"
  mkdir -p "$DOCS_DIR"

  cat > "$DOCS_DIR/multi-cloud-swap-guide.md" << 'MD'
# navuAI — Multi-Cloud Swap Guide

navuAI runs on Azure by default. Swap these components to move to AWS or GCP.

---

## Azure → AWS

| navuAI Component | Azure (default) | AWS equivalent |
|-----------------|----------------|----------------|
| Kubernetes      | AKS             | EKS            |
| Container Reg   | ACR             | ECR            |
| Secrets store   | Key Vault       | Secrets Manager |
| GPU VM          | NC4as_T4_v3     | p3.2xlarge / g4dn.xlarge |
| VPN             | VPN Gateway     | AWS VPN Gateway + Customer Gateway |
| DNS/TLS         | cert-manager    | cert-manager (same) |
| Load Balancer   | Azure LB        | AWS ALB / NLB  |
| LLM provider    | Azure AI Foundry| AWS Bedrock (already in LiteLLM config) |

### Steps to swap to AWS

1. **Terraform**: Change provider block from `azurerm` → `aws` in `main.tf`
2. **AKS → EKS**:
   ```hcl
   # modules/aks/main.tf — replace azurerm_kubernetes_cluster with:
   resource "aws_eks_cluster" "main" {
     name     = var.cluster_name
     role_arn = aws_iam_role.eks_cluster.arn
     vpc_config {
       subnet_ids = var.subnet_ids
     }
   }
   ```
3. **ACR → ECR**: Replace `azurerm_container_registry` with `aws_ecr_repository`
4. **Key Vault → Secrets Manager**: Replace `azurerm_key_vault` with `aws_secretsmanager_secret`
5. **LiteLLM**: Already supports Bedrock — add AWS creds to navuai.env
6. **DNS**: Replace Azure DNS with Route53 records
7. **NGINX ingress**: Same — install via Helm on EKS

---

## Azure → GCP

| navuAI Component | Azure (default) | GCP equivalent |
|-----------------|----------------|----------------|
| Kubernetes      | AKS             | GKE            |
| Container Reg   | ACR             | Artifact Registry |
| Secrets store   | Key Vault       | Secret Manager |
| GPU VM          | NC4as_T4_v3     | n1-standard-4 + nvidia-tesla-t4 |
| VPN             | VPN Gateway     | Cloud VPN      |
| LLM provider    | Azure AI Foundry| Google Vertex AI (already in LiteLLM config) |

### Steps to swap to GCP

1. **Terraform**: Change provider block to `google` in `main.tf`
2. **AKS → GKE**:
   ```hcl
   resource "google_container_cluster" "main" {
     name     = var.cluster_name
     location = var.location
     initial_node_count = 1
   }
   ```
3. **LiteLLM**: Already supports Vertex AI — set VERTEX_PROJECT, VERTEX_LOCATION in navuai.env
4. **DNS**: Replace with Cloud DNS

---

## What does NOT change across clouds

- **LiteLLM gateway**: provider-agnostic by design
- **Open WebUI**: Kubernetes deployment — same YAML everywhere
- **BillBot / Billy / MCP Server**: Python FastAPI on K8s — same everywhere
- **Phase scripts**: Pass `--cloud aws` flag (future enhancement) or copy-paste K8s manifests
- **NGINX ingress + cert-manager**: Helm charts work on all three clouds

---

## LiteLLM provider switching

All LLM providers are already configured in LiteLLM (Phase 2). Enable/disable by setting keys in navuai.env:

```bash
# Azure AI Foundry (active when AZURE_OPENAI_KEY is set)
AZURE_OPENAI_KEY="..."
AZURE_OPENAI_ENDPOINT="..."

# AWS Bedrock (active when AWS_ACCESS_KEY_ID is set)
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."

# Google Vertex AI (active when VERTEX_PROJECT is set)
VERTEX_PROJECT="my-gcp-project"
VERTEX_LOCATION="us-central1"

# OpenAI (active when OPENAI_API_KEY is set)
OPENAI_API_KEY="sk-..."
```

After updating navuai.env, re-run Phase 2 to push new credentials and restart LiteLLM.
MD

  success "docs/multi-cloud-swap-guide.md written"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "=============================================="
  echo "  Phase 9 Complete!"
  echo "=============================================="
  echo -e "${NC}"
  echo -e "${GREEN}What was written:${NC}"
  echo "  ✓ infrastructure/terraform/main.tf"
  echo "  ✓ infrastructure/terraform/variables.tf"
  echo "  ✓ infrastructure/terraform/outputs.tf"
  echo "  ✓ modules/networking — VNet, subnets, NSG"
  echo "  ✓ modules/aks        — AKS cluster, ACR, node pools"
  echo "  ✓ modules/keyvault   — Key Vault with private endpoint"
  echo "  ✓ modules/gpu-vm     — GPU VM with Ollama bootstrap"
  echo "  ✓ modules/vpn        — VPN Gateway for B2B connectivity"
  echo "  ✓ docs/multi-cloud-swap-guide.md"
  echo ""
  echo -e "${YELLOW}To provision infrastructure using Terraform instead of Phase 1 scripts:${NC}"
  echo "  cd infrastructure/terraform"
  echo "  terraform init"
  echo "  terraform plan -out=tfplan"
  echo "  terraform apply tfplan"
  echo ""
  echo -e "${YELLOW}To target a different cloud:${NC}"
  echo "  Read: docs/multi-cloud-swap-guide.md"
  echo ""
  echo -e "${GREEN}${BOLD}All 9 phases complete — navuAI is fully built!${NC}"
  echo ""
  echo "  Platform URL : https://chat.${DOMAIN}"
  echo "  API URL      : https://api.${DOMAIN}"
  echo ""
}

main() {
  banner
  check_prerequisites
  write_root_module
  write_networking_module
  write_aks_module
  write_keyvault_module
  write_gpu_vm_module
  write_vpn_module
  write_swap_guide
  print_summary
}

main "$@"
