from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    DateTime,
    Numeric,
    JSON,
    UniqueConstraint,
)
from .database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True)  # Azure subscription ID (UUID)
    name = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True)
    state = Column(String, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    amount = Column(Numeric(18, 6), nullable=False, default=0)
    currency = Column(String(10), default="USD")
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "date",
            "service_name",
            "resource_group",
            name="uq_cost_record",
        ),
    )


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True)  # Full Azure resource ID path
    name = Column(String, nullable=True, index=True)
    type = Column(String, nullable=True, index=True)
    location = Column(String, nullable=True)
    resource_group = Column(String, nullable=True, index=True)
    subscription_id = Column(String, nullable=True, index=True)
    sku = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    properties = Column(JSON, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdvisorRecommendation(Base):
    __tablename__ = "advisor_recommendations"

    id = Column(String, primary_key=True)  # Azure recommendation ID
    subscription_id = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)  # Cost, Security, Performance, HighAvailability, OperationalExcellence
    impact = Column(String, nullable=True)                 # High, Medium, Low
    short_description = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    resource_name = Column(String, nullable=True)
    potential_savings = Column(Numeric(18, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
