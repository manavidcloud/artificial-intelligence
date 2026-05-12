#!/bin/bash

# Set variables (following your naming pattern)
resourceGroup="rg-finops-prod-network"
location="centralindia"  # matching your existing resources
vnetName="finops-prod-vnet"
vnetPrefix="10.0.0.0/16"

# Create the VNet with first subnet (vm)
az network vnet create \
  --name $vnetName \
  --resource-group $resourceGroup \
  --location $location \
  --address-prefix $vnetPrefix \
  --subnet-name vm-subnet \
  --subnet-prefixes 10.0.0.0/24

# Add second subnet (flexiserver)
az network vnet subnet create \
  --name flexiserver-subnet \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --address-prefix 10.0.1.0/24

# Add third subnet (aks)
az network vnet subnet create \
  --name aks-subnet \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --address-prefix 10.0.2.0/24

# Verify the VNet and subnets
az network vnet show \
  --name $vnetName \
  --resource-group $resourceGroup \
  --query "{Name:name, Location:location, Subnets:subnets[*].{Name:name, Prefix:addressPrefix}}" \
  --output table

# List all subnets
az network vnet subnet list \
  --resource-group $resourceGroup \
  --vnet-name $vnetName \
  --output table