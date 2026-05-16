"""
FinOps Platform API – main FastAPI application entry point.

Endpoints:
  GET  /health                  – liveness / db connectivity check
  GET  /subscriptions           – list synced Azure subscriptions
  GET  /costs/summary           – aggregated spend for a rolling window
  GET  /costs/daily             – per-day spend for a rolling window
  GET  /costs/by-service        – spend grouped by service name
  GET  /costs/by-subscription   – spend grouped by subscription
  GET  /costs/trend             – alias for /costs/daily (used by AI agent tools)
  GET  /resources               – resource inventory with optional filters
  GET  /advisor                 – Advisor recommendations with optional filters
  POST /sync/costs              – trigger cost data sync
  POST /sync/resources          – trigger resource inventory sync
  POST /sync/advisor            – trigger Advisor recommendations sync
  POST /sync/subscriptions      – trigger subscription sync
  POST /alerts/test             – verify email notification setup
"""

import os
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc

from .database import get_db, init_db
from .models import CostRecord, Resource, AdvisorRecommendation, Subscription
from .providers import get_provider
from .notifications import notifier

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & provider
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FinOps Platform API",
    version="1.0.0",
    description=(
        "Azure FinOps data platform: syncs cost, resource, and Advisor data "
        "from Azure into a PostgreSQL database and exposes REST endpoints "
        "consumed by the FinOps dashboard and AI agent."
    ),
)

provider = get_provider()


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    """Initialise database tables on application start."""
    logger.info("Starting FinOps Platform API …")
    init_db()
    logger.info("Database ready.")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
def health(db: Session = Depends(get_db)):
    """Liveness probe – also verifies DB connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected", "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB error: {exc}")


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@app.get("/subscriptions", tags=["data"])
def list_subscriptions(db: Session = Depends(get_db)):
    """Return all synced Azure subscriptions."""
    rows = db.query(Subscription).order_by(Subscription.name).all()
    return {
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "tenant_id": r.tenant_id,
                "state": r.state,
                "synced_at": r.synced_at.isoformat() if r.synced_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------

@app.get("/costs/summary", tags=["costs"])
def cost_summary(
    days: int = Query(30, ge=1, le=365, description="Rolling window in days"),
    db: Session = Depends(get_db),
):
    """Aggregate total cost for the current and previous equivalent periods."""
    today = datetime.utcnow().date()
    since = today - timedelta(days=days)
    prev_since = today - timedelta(days=days * 2)

    current = (
        db.query(func.sum(CostRecord.amount), func.max(CostRecord.currency))
        .filter(CostRecord.date >= since)
        .first()
    )
    previous = (
        db.query(func.sum(CostRecord.amount))
        .filter(CostRecord.date >= prev_since, CostRecord.date < since)
        .first()
    )

    total = float(current[0] or 0)
    prev_total = float(previous[0] or 0)
    currency = current[1] or "USD"
    change_pct = (
        ((total - prev_total) / prev_total * 100) if prev_total else None
    )

    return {
        "data": {
            "total_cost": round(total, 6),
            "prev_period_cost": round(prev_total, 6),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "currency": currency,
            "days": days,
            "period_start": str(since),
            "period_end": str(today),
        }
    }


@app.get("/costs/daily", tags=["costs"])
def cost_daily(
    days: int = Query(30, ge=1, le=365),
    subscription_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """Per-day spend for the rolling window. Optionally filter by subscription."""
    since = datetime.utcnow().date() - timedelta(days=days)
    q = (
        db.query(
            CostRecord.date,
            func.sum(CostRecord.amount).label("total_cost"),
            func.max(CostRecord.currency).label("currency"),
        )
        .filter(CostRecord.date >= since)
    )
    if subscription_id:
        q = q.filter(CostRecord.subscription_id == subscription_id)

    rows = q.group_by(CostRecord.date).order_by(CostRecord.date).all()

    return {
        "data": [
            {
                "date": str(r.date),
                "total_cost": float(r.total_cost),
                "currency": r.currency,
            }
            for r in rows
        ]
    }


@app.get("/costs/by-service", tags=["costs"])
def cost_by_service(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    subscription_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """Spend grouped and ranked by service name."""
    since = datetime.utcnow().date() - timedelta(days=days)
    q = (
        db.query(
            CostRecord.service_name,
            func.sum(CostRecord.amount).label("total_cost"),
            func.max(CostRecord.currency).label("currency"),
        )
        .filter(CostRecord.date >= since)
    )
    if subscription_id:
        q = q.filter(CostRecord.subscription_id == subscription_id)

    rows = (
        q.group_by(CostRecord.service_name)
        .order_by(desc("total_cost"))
        .limit(limit)
        .all()
    )

    return {
        "data": [
            {
                "service_name": r.service_name,
                "total_cost": float(r.total_cost),
                "currency": r.currency,
            }
            for r in rows
        ]
    }


@app.get("/costs/by-subscription", tags=["costs"])
def cost_by_subscription(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Spend grouped by subscription ID for the rolling window."""
    since = datetime.utcnow().date() - timedelta(days=days)
    rows = (
        db.query(
            CostRecord.subscription_id,
            func.sum(CostRecord.amount).label("total_cost"),
            func.max(CostRecord.currency).label("currency"),
        )
        .filter(CostRecord.date >= since)
        .group_by(CostRecord.subscription_id)
        .order_by(desc("total_cost"))
        .all()
    )

    return {
        "data": [
            {
                "subscription_id": r.subscription_id,
                "total_cost": float(r.total_cost),
                "currency": r.currency,
            }
            for r in rows
        ]
    }


@app.get("/costs/by-resource-group", tags=["costs"])
def cost_by_resource_group(
    days: int = Query(30, ge=1, le=365),
    subscription_id: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Spend grouped by resource group for the rolling window."""
    since = datetime.utcnow().date() - timedelta(days=days)
    q = (
        db.query(
            CostRecord.resource_group,
            func.sum(CostRecord.amount).label("total_cost"),
            func.max(CostRecord.currency).label("currency"),
        )
        .filter(CostRecord.date >= since, CostRecord.resource_group.isnot(None))
    )
    if subscription_id:
        q = q.filter(CostRecord.subscription_id == subscription_id)

    rows = (
        q.group_by(CostRecord.resource_group)
        .order_by(desc("total_cost"))
        .limit(limit)
        .all()
    )

    return {
        "data": [
            {
                "resource_group": r.resource_group,
                "total_cost": float(r.total_cost),
                "currency": r.currency,
            }
            for r in rows
        ]
    }


@app.get("/costs/trend", tags=["costs"])
def cost_trend(
    days: int = Query(30, ge=1, le=365),
    subscription_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """Daily cost trend – alias for /costs/daily, exposed for AI agent tool discovery."""
    since = datetime.utcnow().date() - timedelta(days=days)
    q = (
        db.query(
            CostRecord.date,
            func.sum(CostRecord.amount).label("total_cost"),
            func.max(CostRecord.currency).label("currency"),
        )
        .filter(CostRecord.date >= since)
    )
    if subscription_id:
        q = q.filter(CostRecord.subscription_id == subscription_id)

    rows = q.group_by(CostRecord.date).order_by(CostRecord.date).all()

    return {
        "data": [
            {
                "date": str(r.date),
                "total_cost": float(r.total_cost),
                "currency": r.currency,
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@app.get("/resources", tags=["resources"])
def list_resources(
    type: str = Query(None, description="Filter by resource type (partial match)"),
    resource_group: str = Query(None, description="Filter by resource group (partial match)"),
    subscription_id: str = Query(None),
    location: str = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """Return resource inventory with optional filters."""
    q = db.query(Resource)
    if type:
        q = q.filter(Resource.type.ilike(f"%{type}%"))
    if resource_group:
        q = q.filter(Resource.resource_group.ilike(f"%{resource_group}%"))
    if subscription_id:
        q = q.filter(Resource.subscription_id == subscription_id)
    if location:
        q = q.filter(Resource.location.ilike(f"%{location}%"))

    rows = q.order_by(Resource.name).limit(limit).all()

    return {
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "location": r.location,
                "resource_group": r.resource_group,
                "subscription_id": r.subscription_id,
                "sku": r.sku,
                "tags": r.tags,
                "synced_at": r.synced_at.isoformat() if r.synced_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@app.get("/resources/types", tags=["resources"])
def resource_types(db: Session = Depends(get_db)):
    """Return distinct resource types present in the inventory."""
    rows = (
        db.query(Resource.type, func.count(Resource.id).label("count"))
        .group_by(Resource.type)
        .order_by(desc("count"))
        .all()
    )
    return {"data": [{"type": r.type, "count": r.count} for r in rows]}


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

@app.get("/advisor", tags=["advisor"])
def list_advisor(
    category: str = Query("Cost", description="Recommendation category"),
    impact: str = Query(None, description="Filter by impact level: High, Medium, Low"),
    subscription_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """Return Advisor recommendations ordered by potential savings."""
    q = db.query(AdvisorRecommendation).filter(
        AdvisorRecommendation.category == category
    )
    if impact:
        q = q.filter(AdvisorRecommendation.impact == impact)
    if subscription_id:
        q = q.filter(AdvisorRecommendation.subscription_id == subscription_id)

    rows = (
        q.order_by(desc(AdvisorRecommendation.potential_savings))
        .limit(100)
        .all()
    )

    return {
        "data": [
            {
                "id": r.id,
                "subscription_id": r.subscription_id,
                "category": r.category,
                "impact": r.impact,
                "short_description": r.short_description,
                "resource_id": r.resource_id,
                "resource_name": r.resource_name,
                "potential_savings": float(r.potential_savings or 0),
                "currency": r.currency,
                "synced_at": r.synced_at.isoformat() if r.synced_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@app.get("/advisor/summary", tags=["advisor"])
def advisor_summary(db: Session = Depends(get_db)):
    """Return total potential savings and counts by category and impact."""
    rows = (
        db.query(
            AdvisorRecommendation.category,
            AdvisorRecommendation.impact,
            func.count(AdvisorRecommendation.id).label("count"),
            func.sum(AdvisorRecommendation.potential_savings).label("total_savings"),
        )
        .group_by(AdvisorRecommendation.category, AdvisorRecommendation.impact)
        .all()
    )

    return {
        "data": [
            {
                "category": r.category,
                "impact": r.impact,
                "count": r.count,
                "total_savings": float(r.total_savings or 0),
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Sync triggers
# ---------------------------------------------------------------------------

@app.post("/sync/subscriptions", tags=["sync"])
def sync_subscriptions(db: Session = Depends(get_db)):
    """Trigger a subscription sync from Azure."""
    try:
        count = provider.sync_subscriptions(db)
        return {"status": "ok", "rows": count}
    except Exception as exc:
        logger.error("sync_subscriptions endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/sync/costs", tags=["sync"])
def sync_costs(
    days: int = Query(30, ge=1, le=365, description="Number of days to back-fill"),
    db: Session = Depends(get_db),
):
    """Trigger a cost data sync from Azure Cost Management."""
    try:
        count = provider.sync_costs(db, days)
        return {"status": "ok", "rows": count}
    except Exception as exc:
        logger.error("sync_costs endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/sync/resources", tags=["sync"])
def sync_resources(db: Session = Depends(get_db)):
    """Trigger a resource inventory sync from Azure Resource Graph."""
    try:
        count = provider.sync_resources(db)
        return {"status": "ok", "rows": count}
    except Exception as exc:
        logger.error("sync_resources endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/sync/advisor", tags=["sync"])
def sync_advisor(db: Session = Depends(get_db)):
    """Trigger an Advisor recommendation sync from Azure."""
    try:
        count = provider.sync_advisor(db)
        return {"status": "ok", "rows": count}
    except Exception as exc:
        logger.error("sync_advisor endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/sync/all", tags=["sync"])
def sync_all(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Run all sync operations in sequence: subscriptions → costs → resources → advisor."""
    results = {}
    try:
        results["subscriptions"] = provider.sync_subscriptions(db)
    except Exception as exc:
        logger.error("sync_all subscriptions failed: %s", exc)
        results["subscriptions"] = f"error: {exc}"

    try:
        results["costs"] = provider.sync_costs(db, days)
    except Exception as exc:
        logger.error("sync_all costs failed: %s", exc)
        results["costs"] = f"error: {exc}"

    try:
        results["resources"] = provider.sync_resources(db)
    except Exception as exc:
        logger.error("sync_all resources failed: %s", exc)
        results["resources"] = f"error: {exc}"

    try:
        results["advisor"] = provider.sync_advisor(db)
    except Exception as exc:
        logger.error("sync_all advisor failed: %s", exc)
        results["advisor"] = f"error: {exc}"

    return {"status": "completed", "results": results}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@app.post("/alerts/test", tags=["alerts"])
def test_alert(db: Session = Depends(get_db)):
    """Send a test email to verify SMTP configuration."""
    html = (
        "<h2 style='color:#818cf8;'>Test from FinOps Platform</h2>"
        "<p>Your notification setup is working correctly.</p>"
        f"<p style='color:#64748b;font-size:12px;'>Sent at {datetime.utcnow().isoformat()} UTC</p>"
    )
    sent = notifier.send("Test Alert", html)
    return {"sent": sent, "configured": notifier.is_configured()}


@app.post("/alerts/cost-spike", tags=["alerts"])
def send_cost_spike_alert(
    service: str = Query(...),
    prev: float = Query(...),
    curr: float = Query(...),
    currency: str = Query("USD"),
):
    """Send a cost spike alert email for the specified service."""
    pct = ((curr - prev) / prev * 100) if prev else 0.0
    html = notifier.build_cost_spike_email(service, prev, curr, pct, currency)
    sent = notifier.send(f"Cost Spike – {service} (+{pct:.1f}%)", html)
    return {"sent": sent, "pct_change": round(pct, 2)}


@app.post("/alerts/budget", tags=["alerts"])
def send_budget_alert(
    spent: float = Query(...),
    budget: float = Query(...),
    currency: str = Query("USD"),
    days_remaining: int = Query(0, ge=0),
):
    """Send a budget threshold alert email."""
    pct = (spent / budget * 100) if budget else 0.0
    html = notifier.build_budget_alert_email(spent, budget, pct, currency, days_remaining)
    sent = notifier.send(f"Budget Alert – {pct:.1f}% consumed", html)
    return {"sent": sent, "pct_consumed": round(pct, 2)}


@app.post("/alerts/digest", tags=["alerts"])
def send_daily_digest(
    days: int = Query(1, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Build and send the daily cost digest email from live DB data."""
    since = datetime.utcnow().date() - timedelta(days=days)

    # Total spend
    total_row = (
        db.query(func.sum(CostRecord.amount), func.max(CostRecord.currency))
        .filter(CostRecord.date >= since)
        .first()
    )
    total = float(total_row[0] or 0)
    currency = total_row[1] or "USD"

    # Top services
    top_rows = (
        db.query(
            CostRecord.service_name,
            func.sum(CostRecord.amount).label("total_cost"),
        )
        .filter(CostRecord.date >= since)
        .group_by(CostRecord.service_name)
        .order_by(desc("total_cost"))
        .limit(10)
        .all()
    )
    top_services = [{"service_name": r.service_name, "total_cost": float(r.total_cost)} for r in top_rows]

    # Advisor count
    rec_count = (
        db.query(func.count(AdvisorRecommendation.id))
        .filter(AdvisorRecommendation.category == "Cost")
        .scalar()
        or 0
    )

    html = notifier.build_daily_digest_email(total, currency, top_services, rec_count)
    sent = notifier.send("Daily Cost Digest", html)
    return {
        "sent": sent,
        "total_cost": round(total, 2),
        "currency": currency,
        "advisor_count": rec_count,
    }
