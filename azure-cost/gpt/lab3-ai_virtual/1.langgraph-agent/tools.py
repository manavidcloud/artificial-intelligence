import os
import psycopg2
from datetime import datetime, timedelta
from langchain_core.tools import tool


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "finops-pgflex.postgres.database.azure.com"),
        database="finops-db",
        user="pgadmin",
        password=os.getenv("DB_PASSWORD")
    )


@tool
def get_cost_summary(days: int = 7) -> str:
    """Get Azure cost summary for the last N days grouped by service name."""
    conn = get_db_connection()
    cur = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).date()
    cur.execute("""
        SELECT service_name, SUM(cost_amount) AS total, currency
        FROM daily_costs
        WHERE usage_date >= %s
        GROUP BY service_name, currency
        ORDER BY total DESC
        LIMIT 10
    """, (since,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"No cost data found for the last {days} days. Run /sync/costs on the platform API to ingest data."
    result = f"Top Azure costs for last {days} days:\n"
    for service, cost, currency in rows:
        result += f"  - {service or 'Unknown'}: {float(cost):.4f} {currency}\n"
    return result


@tool
def get_cost_spike(threshold_percent: float = 20.0) -> str:
    """Detect days where total Azure spend increased by more than threshold_percent compared to previous day."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        WITH daily_totals AS (
            SELECT usage_date, SUM(cost_amount) AS total
            FROM daily_costs
            GROUP BY usage_date
            ORDER BY usage_date DESC
            LIMIT 14
        ),
        with_prev AS (
            SELECT usage_date, total,
                   LAG(total) OVER (ORDER BY usage_date) AS prev_total
            FROM daily_totals
        )
        SELECT usage_date, total, prev_total,
               ROUND(((total - prev_total) / NULLIF(prev_total, 0)) * 100, 2) AS pct_change
        FROM with_prev
        WHERE prev_total IS NOT NULL
          AND ((total - prev_total) / NULLIF(prev_total, 0)) * 100 > %s
        ORDER BY usage_date DESC
    """, (threshold_percent,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"No cost spikes detected above {threshold_percent}% threshold in the last 14 days. Spend looks stable."
    result = f"Cost spikes detected (>{threshold_percent}% increase):\n"
    for date, total, prev, pct in rows:
        result += f"  - {date}: ${float(total):.4f} vs ${float(prev):.4f} the day before (+{pct}%)\n"
    return result


@tool
def get_subscriptions() -> str:
    """List all Azure subscriptions currently tracked in the FinOps platform."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT subscription_id, display_name, state, last_synced_at FROM subscriptions ORDER BY display_name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return "No subscriptions found. Call POST /sync/subscriptions on the platform API first."
    result = f"Tracked Azure subscriptions ({len(rows)} total):\n"
    for sub_id, name, state, synced in rows:
        result += f"  - {name} | ID: {sub_id} | State: {state} | Synced: {synced}\n"
    return result


@tool
def get_total_spend(month: str = None) -> str:
    """Get total Azure spend. Optionally pass month in YYYY-MM format. Defaults to current month."""
    conn = get_db_connection()
    cur = conn.cursor()
    if month:
        cur.execute("""
            SELECT SUM(cost_amount), currency, COUNT(DISTINCT usage_date) AS days
            FROM daily_costs
            WHERE TO_CHAR(usage_date, 'YYYY-MM') = %s
            GROUP BY currency
        """, (month,))
        label = month
    else:
        cur.execute("""
            SELECT SUM(cost_amount), currency, COUNT(DISTINCT usage_date) AS days
            FROM daily_costs
            WHERE DATE_TRUNC('month', usage_date) = DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY currency
        """)
        label = datetime.now().strftime("%Y-%m")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"No spend data found for {label}."
    result = f"Total Azure spend for {label}:\n"
    for total, currency, days in rows:
        result += f"  {float(total):.4f} {currency} across {days} day(s) of data\n"
    return result


@tool
def get_cost_by_subscription(days: int = 30) -> str:
    """Break down Azure costs by subscription for the last N days."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT dc.subscription_id, s.display_name,
               SUM(dc.cost_amount) AS total, dc.currency
        FROM daily_costs dc
        LEFT JOIN subscriptions s ON dc.subscription_id = s.subscription_id
        WHERE dc.usage_date >= CURRENT_DATE - %s
        GROUP BY dc.subscription_id, s.display_name, dc.currency
        ORDER BY total DESC
    """, (days,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"No cost data by subscription for the last {days} days."
    result = f"Azure costs by subscription (last {days} days):\n"
    for sub_id, name, total, currency in rows:
        result += f"  - {name or sub_id}: {float(total):.4f} {currency}\n"
    return result
