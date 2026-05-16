"""
Provider factory — returns the correct CloudProvider for the configured cloud.

Set CLOUD_PROVIDER env var to select the backend:
  azure  (default) — Azure Cost Management, Resource Graph, Advisor
  aws    (future)  — AWS Cost Explorer, Resource Groups Tagging API
  gcp    (future)  — GCP Billing API, Asset Inventory API

Adding a new cloud:
  1. Create providers/aws.py (or gcp.py) implementing CloudProvider
  2. Add an elif branch below — no other files need to change
"""

import os
from .base import CloudProvider


def get_provider() -> CloudProvider:
    cloud = os.getenv("CLOUD_PROVIDER", "azure").lower().strip()

    if cloud == "azure":
        from .azure import AzureProvider
        return AzureProvider()

    if cloud == "aws":
        try:
            from .aws import AWSProvider  # type: ignore[import]
            return AWSProvider()
        except ImportError:
            raise ImportError(
                "AWS provider is not yet implemented. "
                "Create providers/aws.py implementing CloudProvider."
            )

    if cloud == "gcp":
        try:
            from .gcp import GCPProvider  # type: ignore[import]
            return GCPProvider()
        except ImportError:
            raise ImportError(
                "GCP provider is not yet implemented. "
                "Create providers/gcp.py implementing CloudProvider."
            )

    raise ValueError(
        f"Unknown CLOUD_PROVIDER={cloud!r}. "
        "Supported values: azure | aws | gcp"
    )
