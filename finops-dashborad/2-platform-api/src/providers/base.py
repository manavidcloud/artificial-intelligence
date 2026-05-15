from abc import ABC, abstractmethod


class CloudProvider(ABC):
    """Abstract base class for cloud cost/resource data providers."""

    @abstractmethod
    def sync_subscriptions(self, db) -> int:
        """Upsert subscription records. Returns number of records upserted."""
        ...

    @abstractmethod
    def sync_costs(self, db, days: int = 30) -> int:
        """Fetch and upsert cost records for the last *days* days. Returns row count."""
        ...

    @abstractmethod
    def sync_resources(self, db) -> int:
        """Fetch and upsert resource inventory records. Returns row count."""
        ...

    @abstractmethod
    def sync_advisor(self, db) -> int:
        """Fetch and upsert Advisor recommendations. Returns row count."""
        ...
