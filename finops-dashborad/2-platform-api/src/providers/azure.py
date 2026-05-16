"""
Azure cloud provider implementation for FinOps Platform API.

Syncs subscriptions, cost records, resource inventory, and Advisor
recommendations from Azure into the local PostgreSQL database.
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import List

from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from azure.mgmt.advisor import AdvisorManagementClient
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .base import CloudProvider
from ..models import Subscription, CostRecord, Resource, AdvisorRecommendation

COST_MGMT_API = "https://management.azure.com"
COST_MGMT_API_VERSION = "2023-11-01"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_credential() -> DefaultAzureCredential:
    """Return a DefaultAzureCredential instance.

    Supports Workload Identity (pod), Managed Identity, environment variables,
    and interactive browser fallback automatically.
    """
    return DefaultAzureCredential()


def _subscription_ids() -> List[str]:
    """Read AZURE_SUBSCRIPTION_IDS from environment (comma-separated)."""
    raw = os.getenv("AZURE_SUBSCRIPTION_IDS", "")
    return [s.strip() for s in raw.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------

class AzureProvider(CloudProvider):
    """Concrete Azure implementation of CloudProvider."""

    # ------------------------------------------------------------------
    # sync_subscriptions
    # ------------------------------------------------------------------

    def sync_subscriptions(self, db: Session) -> int:
        """Upsert subscription rows from AZURE_SUBSCRIPTION_IDS env var.

        Optionally enriches with display name / state via SubscriptionClient
        if the azure-mgmt-subscription package is installed; otherwise stores
        the subscription ID with placeholder values.
        """
        sub_ids = _subscription_ids()
        if not sub_ids:
            logger.warning("AZURE_SUBSCRIPTION_IDS is empty – skipping subscription sync.")
            return 0

        count = 0
        credential = get_credential()

        # Try to resolve display names via SubscriptionClient (optional dep)
        sub_details: dict = {}
        try:
            from azure.mgmt.subscription import SubscriptionClient  # type: ignore

            sub_client = SubscriptionClient(credential)
            for sub in sub_client.subscriptions.list():
                sub_details[sub.subscription_id] = {
                    "name": sub.display_name,
                    "tenant_id": sub.tenant_id,
                    "state": sub.state.value if sub.state else None,
                }
        except Exception as exc:
            logger.warning("SubscriptionClient not available or failed (%s). Using IDs only.", exc)

        for sub_id in sub_ids:
            details = sub_details.get(sub_id, {})
            stmt = (
                pg_insert(Subscription)
                .values(
                    id=sub_id,
                    name=details.get("name", sub_id),
                    tenant_id=details.get("tenant_id"),
                    state=details.get("state", "Enabled"),
                    synced_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": details.get("name", sub_id),
                        "tenant_id": details.get("tenant_id"),
                        "state": details.get("state", "Enabled"),
                        "synced_at": datetime.utcnow(),
                    },
                )
            )
            db.execute(stmt)
            count += 1

        db.commit()
        logger.info("sync_subscriptions: upserted %d rows.", count)
        return count

    # ------------------------------------------------------------------
    # sync_costs
    # ------------------------------------------------------------------

    def sync_costs(self, db: Session, days: int = 30) -> int:
        """Fetch cost data from Azure Cost Management REST API and upsert into cost_records."""
        sub_ids = _subscription_ids()
        if not sub_ids:
            logger.warning("AZURE_SUBSCRIPTION_IDS is empty – skipping cost sync.")
            return 0

        credential = get_credential()
        total_rows = 0

        for sub_id in sub_ids:
            try:
                token = credential.get_token(f"{COST_MGMT_API}/.default").token
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                time_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
                time_to = datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

                url = (
                    f"{COST_MGMT_API}/subscriptions/{sub_id}"
                    f"/providers/Microsoft.CostManagement/query"
                    f"?api-version={COST_MGMT_API_VERSION}"
                )
                body = {
                    "type": "ActualCost",
                    "timeframe": "Custom",
                    "timePeriod": {"from": time_from, "to": time_to},
                    "dataset": {
                        "granularity": "Daily",
                        "aggregation": {
                            "totalCost": {"name": "Cost", "function": "Sum"}
                        },
                        "grouping": [
                            {"type": "Dimension", "name": "ServiceName"},
                            {"type": "Dimension", "name": "ResourceGroupName"},
                        ],
                    },
                }

                resp = requests.post(url, headers=headers, json=body, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                # Azure wraps results in "properties" at the top level
                props = data.get("properties", data)
                columns = props.get("columns", [])
                rows = props.get("rows", [])

                logger.info(
                    "sync_costs: sub=%s columns=%s rows=%d",
                    sub_id, [c["name"] for c in columns], len(rows),
                )

                # Build case-insensitive column index
                col_index = {c["name"].lower(): i for i, c in enumerate(columns)}

                # Flexible column name matching — handles different API versions
                cost_key = next(
                    (k for k in col_index if k in ("cost", "pretaxcost", "costinbillingcurrency")), None
                )
                date_key = next(
                    (k for k in col_index if k in ("usagedate", "date", "billingperiodstartdate")), None
                )
                service_key = next((k for k in col_index if "service" in k), None)
                rg_key = next(
                    (k for k in col_index if "resourcegroup" in k or "resource_group" in k), None
                )
                currency_key = next((k for k in col_index if "currency" in k), None)

                rows_for_sub = 0
                for row in rows:
                    try:
                        cost = float(row[col_index[cost_key]]) if cost_key else 0.0
                        service = str(row[col_index[service_key]]) if service_key else "Unknown"
                        rg = str(row[col_index[rg_key]]) if rg_key else ""
                        currency_val = str(row[col_index[currency_key]]) if currency_key else "USD"

                        raw_date = row[col_index[date_key]] if date_key else None
                        if raw_date is None:
                            continue
                        if isinstance(raw_date, int):
                            date_val = datetime.strptime(str(raw_date), "%Y%m%d").date()
                        else:
                            date_val = datetime.fromisoformat(str(raw_date)[:10]).date()

                        stmt = (
                            pg_insert(CostRecord)
                            .values(
                                subscription_id=sub_id,
                                date=date_val,
                                service_name=service or "Unknown",
                                resource_group=rg or "",
                                resource_id=None,
                                amount=cost,
                                currency=currency_val or "USD",
                                synced_at=datetime.utcnow(),
                            )
                            .on_conflict_do_update(
                                constraint="uq_cost_record",
                                set_={
                                    "amount": cost,
                                    "currency": currency_val or "USD",
                                    "synced_at": datetime.utcnow(),
                                },
                            )
                        )
                        db.execute(stmt)
                        rows_for_sub += 1

                    except Exception as row_exc:
                        logger.warning(
                            "sub=%s: skipping cost row: %s | row=%s",
                            sub_id, row_exc, row,
                        )

                db.commit()
                total_rows += rows_for_sub
                logger.info("sync_costs: sub=%s upserted %d rows.", sub_id, rows_for_sub)

            except Exception as exc:
                logger.error("sync_costs: sub=%s failed: %s", sub_id, exc)
                db.rollback()

        return total_rows

    # ------------------------------------------------------------------
    # sync_resources
    # ------------------------------------------------------------------

    def sync_resources(self, db: Session) -> int:
        """Query Azure Resource Graph and upsert into resources table."""
        sub_ids = _subscription_ids()
        if not sub_ids:
            logger.warning("AZURE_SUBSCRIPTION_IDS is empty – skipping resource sync.")
            return 0

        credential = get_credential()
        total_rows = 0

        # Resource Graph supports cross-subscription queries
        try:
            rg_client = ResourceGraphClient(credential)

            kql = (
                "Resources "
                "| project id, name, type, location, resourceGroup, "
                "          subscriptionId, sku, tags, properties "
                "| limit 1000"
            )

            request = QueryRequest(
                subscriptions=sub_ids,
                query=kql,
            )
            response = rg_client.resources(request)

            for item in (response.data or []):
                try:
                    sku_val = None
                    raw_sku = item.get("sku")
                    if raw_sku:
                        if isinstance(raw_sku, dict):
                            sku_val = raw_sku.get("name") or raw_sku.get("tier")
                        else:
                            sku_val = str(raw_sku)

                    stmt = (
                        pg_insert(Resource)
                        .values(
                            id=item.get("id", ""),
                            name=item.get("name"),
                            type=item.get("type"),
                            location=item.get("location"),
                            resource_group=item.get("resourceGroup"),
                            subscription_id=item.get("subscriptionId"),
                            sku=sku_val,
                            tags=item.get("tags"),
                            properties=item.get("properties"),
                            synced_at=datetime.utcnow(),
                        )
                        .on_conflict_do_update(
                            index_elements=["id"],
                            set_={
                                "name": item.get("name"),
                                "type": item.get("type"),
                                "location": item.get("location"),
                                "resource_group": item.get("resourceGroup"),
                                "subscription_id": item.get("subscriptionId"),
                                "sku": sku_val,
                                "tags": item.get("tags"),
                                "properties": item.get("properties"),
                                "synced_at": datetime.utcnow(),
                            },
                        )
                    )
                    db.execute(stmt)
                    total_rows += 1

                except Exception as item_exc:
                    logger.warning(
                        "sync_resources: skipping resource %s: %s",
                        item.get("id"),
                        item_exc,
                    )

            db.commit()
            logger.info("sync_resources: upserted %d resources.", total_rows)

        except Exception as exc:
            logger.error("sync_resources failed: %s", exc)
            db.rollback()

        return total_rows

    # ------------------------------------------------------------------
    # sync_advisor
    # ------------------------------------------------------------------

    def sync_advisor(self, db: Session) -> int:
        """Fetch Azure Advisor Cost recommendations and upsert into advisor_recommendations."""
        sub_ids = _subscription_ids()
        if not sub_ids:
            logger.warning("AZURE_SUBSCRIPTION_IDS is empty – skipping advisor sync.")
            return 0

        credential = get_credential()
        total_rows = 0

        for sub_id in sub_ids:
            try:
                advisor_client = AdvisorManagementClient(credential, sub_id)

                for rec in advisor_client.recommendations.list():
                    try:
                        category = (
                            rec.category.value
                            if hasattr(rec.category, "value")
                            else str(rec.category)
                        )

                        # Filter to Cost recommendations only
                        if category != "Cost":
                            continue

                        impact = (
                            rec.impact.value
                            if hasattr(rec.impact, "value")
                            else str(rec.impact)
                        )

                        description = ""
                        if rec.short_description:
                            description = (
                                rec.short_description.solution
                                or rec.short_description.problem
                                or ""
                            )

                        # Extract potential savings from extended properties
                        savings = None
                        currency_val = None
                        if rec.extended_properties:
                            try:
                                savings_raw = rec.extended_properties.get(
                                    "savingsAmount",
                                    rec.extended_properties.get("annualSavingsAmount"),
                                )
                                if savings_raw is not None:
                                    savings = float(savings_raw)
                                currency_val = rec.extended_properties.get("savingsCurrency")
                            except (TypeError, ValueError):
                                pass

                        # Resource name from impacted value or resource ID
                        resource_name = rec.impacted_value or ""
                        resource_id_val = rec.resource_metadata.resource_id if rec.resource_metadata else None

                        stmt = (
                            pg_insert(AdvisorRecommendation)
                            .values(
                                id=rec.id or f"{sub_id}-{rec.name}",
                                subscription_id=sub_id,
                                category=category,
                                impact=impact,
                                short_description=description,
                                resource_id=resource_id_val,
                                resource_name=resource_name,
                                potential_savings=savings,
                                currency=currency_val,
                                synced_at=datetime.utcnow(),
                            )
                            .on_conflict_do_update(
                                index_elements=["id"],
                                set_={
                                    "impact": impact,
                                    "short_description": description,
                                    "resource_id": resource_id_val,
                                    "resource_name": resource_name,
                                    "potential_savings": savings,
                                    "currency": currency_val,
                                    "synced_at": datetime.utcnow(),
                                },
                            )
                        )
                        db.execute(stmt)
                        total_rows += 1

                    except Exception as rec_exc:
                        logger.warning(
                            "sync_advisor: sub=%s skipping recommendation: %s",
                            sub_id,
                            rec_exc,
                        )

                db.commit()
                logger.info("sync_advisor: sub=%s upserted recommendations.", sub_id)

            except Exception as exc:
                logger.error("sync_advisor: sub=%s failed: %s", sub_id, exc)
                db.rollback()

        return total_rows
