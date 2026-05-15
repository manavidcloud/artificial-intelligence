import os
from fastapi import FastAPI, BackgroundTasks
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
import psycopg2

app = FastAPI(title="FinOps Engine")

# 1. Connect to Azure using Lab 1 Identity
credential = DefaultAzureCredential()

# 2. Database Connection Helper
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database="finops-db",
        user="pgadmin",
        password=os.getenv("DB_PASSWORD")
    )

@app.get("/health")
def health():
    return {"status": "online"}

@app.post("/sync/subscriptions")
def sync_subscriptions(background_tasks: BackgroundTasks):
    """Goal: Subscription Discovery & Resource Inventory"""
    background_tasks.add_task(run_discovery)
    return {"message": "Sync started in background"}

def run_discovery():
    # Azure Resource Graph Query
    client = ResourceGraphClient(credential)
    query = "resourcecontainers | where type == 'microsoft.resources/subscriptions' | project subscriptionId, name"
    response = client.resources(query={"query": query})
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for row in response.data:
        sub_id = row['subscriptionId']
        name = row['name']
        # Save to the table we just created in Step 1
        cur.execute(
            "INSERT INTO subscriptions (subscription_id, display_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (sub_id, name)
        )
    
    conn.commit()
    cur.close()
    conn.close()
    print("Discovery Complete!")