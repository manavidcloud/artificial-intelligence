import os
from datetime import datetime, timedelta
from fastapi import FastAPI, BackgroundTasks
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.costmanagement import CostManagementClient
import psycopg2

app = FastAPI(title="FinOps Engine")
credential = DefaultAzureCredential()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database="finops-db",
        user="pgadmin",
        password=os.getenv("DB_PASSWORD")
    )

@app.get("/health")
def health(): return {"status": "online"}

# --- STEP 4 LOGIC: SUBSCRIPTION DISCOVERY ---
@app.post("/sync/subscriptions")
def sync_subscriptions(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_discovery)
    return {"status": "Subscription discovery started"}

def run_discovery():
    client = ResourceGraphClient(credential)
    # Query to find all subscriptions
    query = "resourcecontainers | where type == 'microsoft.resources/subscriptions' | project subscriptionId, name"
    response = client.resources(query={"query": query})
    
    conn = get_db_connection()
    cur = conn.cursor()
    for row in response.data:
        cur.execute(
            "INSERT INTO subscriptions (subscription_id, display_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (row['subscriptionId'], row['name'])
        )
    conn.commit()
    cur.close()
    conn.close()

# --- STEP 5 LOGIC: COST INGESTION ---
@app.post("/sync/costs")
def sync_costs(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_cost_ingestion)
    return {"status": "Cost ingestion started"}

def run_cost_ingestion():
    cost_client = CostManagementClient(credential)
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get subscriptions from our DB
    cur.execute("SELECT subscription_id FROM subscriptions")
    subs = cur.fetchall()

    # 2. Query yesterday's cost for each
    yesterday = datetime.now() - timedelta(days=1)
    
    for (sub_id,) in subs:
        scope = f"/subscriptions/{sub_id}"
        # Simplified query for demonstration
        # In production, you'd define grouping by ServiceName/ResourceGroup
        print(f"Fetching costs for {sub_id}...")
        # (Azure API call logic goes here)

    conn.close()