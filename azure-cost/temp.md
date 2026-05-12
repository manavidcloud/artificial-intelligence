# Quick overview of all resources
echo "=== RESOURCE SUMMARY ===" && \
echo "Resource Groups: $(az group list --query "length([])")" && \
echo "Resources: $(az resource list --query "length([])")" && \
echo "AKS Clusters: $(az aks list --query "length([])")" && \
echo "PostgreSQL: $(az postgres flexible-server list --query "length([])")" && \
echo "ACR: $(az acr list --query "length([])")" && \
echo "Key Vaults: $(az keyvault list --query "length([])")" && \
echo "Storage Accounts: $(az storage account list --query "length([])")"


#!/bin/bash

echo "==================================================================="
echo "  ORPHANED RESOURCE IDENTIFICATION (VIEW ONLY - NO DELETION YET)"
echo "==================================================================="

# 1. Unattached Managed Disks
echo ""
echo "📀 UNATTACHED MANAGED DISKS:"
DISKS=$(az disk list --query "[?managedBy==null].[name, location, diskSizeGb]" -o tsv)
if [ -n "$DISKS" ]; then
    echo "$DISKS"
    echo "Total count: $(az disk list --query "[?managedBy==null]" --output tsv | wc -l)"
else
    echo "None found"
fi

# 2. Unattached Public IPs
echo ""
echo "🌐 UNATTACHED PUBLIC IP ADDRESSES:"
IPS=$(az network public-ip list --query "[?ipConfiguration==null].[name, location, ipAddress]" -o tsv)
if [ -n "$IPS" ]; then
    echo "$IPS"
    echo "Total count: $(az network public-ip list --query "[?ipConfiguration==null]" --output tsv | wc -l)"
else
    echo "None found"
fi

# 3. Unused Network Interfaces
echo ""
echo "🔌 UNUSED NETWORK INTERFACES:"
NICS=$(az network nic list --query "[?virtualMachine==null].[name, location]" -o tsv)
if [ -n "$NICS" ]; then
    echo "$NICS"
    echo "Total count: $(az network nic list --query "[?virtualMachine==null]" --output tsv | wc -l)"
else
    echo "None found"
fi

# 4. Resources by Type (Summary)
echo ""
echo "📊 RESOURCE TYPE SUMMARY:"
az resource list --query "[].type" -o tsv | sort | uniq -c | sort -rn

echo ""
echo "==================================================================="
echo "  To delete orphaned resources, run delete command with specific IDs"
echo "  Example: az disk delete --ids <disk-id> --yes"
echo "==================================================================="