# What Comes In LAB 2

Next lab will build:

# Core Platform API Layer

Including:

✅ FastAPI platform service
✅ subscription discovery
✅ Azure Resource Graph integration
✅ Cost Management API integration
✅ PostgreSQL schemas
✅ background workers
✅ cost ingestion pipeline (cip)
✅ resource inventory engine
✅ initial REST APIs


LAB 2: The Core Platform API Layer
Sequence of Steps
Step 1: Create Tables (The Schema) — Initialize the structure inside finops-db.

Step 2: API Code (FastAPI) — Write the Python code to discover subscriptions and costs.

Step 3: Containerize — Push the code to your ACR.

Step 4: Deployment — Run the API in AKS using your Managed Identity.


Step 1: Initialize the Database Tables
Since your database is inside a private subnet, your laptop cannot "see" it. We use a Kubernetes Job as a temporary bridge to run the setup commands.

1. Create a file named db-init.yaml and paste this:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: finops-db-init
  namespace: platform
spec:
  template:
    spec:
      containers:
      - name: psql-client
        image: postgres:16-alpine
        env:
        - name: PGPASSWORD
          value: "YourStr0ngPass!"  # The password you set in Lab 1
        command: ["sh", "-c"]
        args:
        - |
          psql -h finops-pgflex.postgres.database.azure.com -U pgadmin -d finops-db <<EOF
          CREATE TABLE IF NOT EXISTS subscriptions (
              subscription_id VARCHAR(50) PRIMARY KEY,
              display_name VARCHAR(255),
              state VARCHAR(50),
              last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
          );
          CREATE TABLE IF NOT EXISTS daily_costs (
              id SERIAL PRIMARY KEY,
              usage_date DATE NOT NULL,
              subscription_id VARCHAR(50) REFERENCES subscriptions(subscription_id),
              service_name VARCHAR(100),
              cost_amount DECIMAL(18, 4),
              currency VARCHAR(10) DEFAULT 'USD'
          );
          EOF
      restartPolicy: OnFailure
```

kubectl get pods -n platform
NAME                   READY   STATUS      RESTARTS   AGE
finops-db-init-whtld   0/1     Completed   0          16s


Step 2: The FastAPI Platform Service (Code)
We are going to build the "Brain." This service will do three things:

Subscription Discovery: Use Azure Resource Graph to find all subscriptions.

Resource Inventory: Identify the Resource Groups.

Cost Ingestion: Pull the actual spending data.

1. The Project Structure
Create a folder for your app. Inside, you need three files: kindly refer fast-api folder

main.py (The Python code)
```py
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

```
requirements.txt (The libraries)
```py
fastapi
uvicorn
azure-identity
azure-mgmt-resourcegraph
azure-mgmt-costmanagement
psycopg2-binary

```

# Dockerfile (To build the container)

```py
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

```



2. The Code (main.py)
This script uses the Workload Identity from Lab 1 to talk to Azure without needing a password.


# 3.1 start docker desktop if its not running you can't proceed to az acr login
az acr login --name finopsacrmanmas

# 3.2 build fastapi image 
/artificial-intelligence/azure-cost/gpt/lab2-application-logic/fast-api

docker build -t finopsacrmanmas.azurecr.io/finops-api:v1 .
docker push finopsacrmanmas.azurecr.io/finops-api:v1

az acr repository list --name finopsacrmanmas --output table
- output must show: finops-api


# Step 4 — The Deployment (Identity & Orchestration)
This is where all your Lab 1 work with Workload Identity pays off. Your code doesn't have an Azure password inside it; instead, it will "borrow" the identity of the cost-platform-sa Service Account to talk to Azure.

1. Create the Deployment YAML
Create a file named api-deployment.yaml. This file tells AKS how to run your app.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: finops-api
  namespace: platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: finops-api
  template:
    metadata:
      labels:
        app: finops-api
        azure.workload.identity/use: "true" # Critical for Lab 1 Identity
    spec:
      serviceAccountName: cost-platform-sa # The SA you created in Lab 1
      containers:
      - name: finops-api
        image: finopsacrmanmas.azurecr.io/finops-api:v1
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: "finops-pgflex.postgres.database.azure.com"
        - name: DB_PASSWORD
          value: "YourStr0ngPass!" # Use the password from Lab 1
---
apiVersion: v1
kind: Service
metadata:
  name: finops-api-svc
  namespace: platform
spec:
  type: ClusterIP
  selector:
    app: finops-api
  ports:
  - port: 80
    targetPort: 8000
    ```
``
kubectl apply -f api-deployment.yaml

kubectl get pods -n platform
- if fast-api failed for image then run this command again

az aks update ^
  --name finops-aks ^
  --resource-group rg-finops-prod-core ^
  --attach-acr finopsacrmanmas


Test the Internal Health Check:
kubectl port-forward svc/finops-api-svc 8080:80 -n platform

Now, open your browser and go to http://localhost:8080/health
- on broswer it will show online

- now in another cmd run
curl -X POST http://localhost:8080/sync/subscriptions
- this will show as backgroud 
---

# Step  5  The Cost Ingestion Pipeline
We need to add the logic to pull costs from the Azure Cost Management API. This API is complex because it requires a "Query" definition.

Action: Update your main.py (locally) with this ingestion function:
- I have created another folder called 3.cip and with main.py your Dockerfile and requirements file should be there before build new image version
- why we haven't did early - it will be heavy and it might failed the fast api so we fisrt build the fast-api image

```py
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
    ```

docker build -t finopsacrmanmas.azurecr.io/finops-api:v2 .
docker push finopsacrmanmas.azurecr.io/finops-api:v2

Update your Deployment to use :v2 instead of :v1.
kubectl set image deployment/finops-api finops-api=finopsacrmanmas.azurecr.io/finops-api:v2 -n platform


# Keep port-forward running: kubectl port-forward svc/finops-api-svc 8080:80 -n platform
curl -X POST http://localhost:8080/sync/subscriptions
curl -X POST http://localhost:8080/sync/costs

###########################################################


Moving to LAB 3 — The AI & Visualization Layer
This is where we turn "raw data" into "intelligent insights." In Lab 3, we will:

Setup LangGraph: To create an AI agent that can answer questions like "Why did my cost spike yesterday?"

Deploy Streamlit/Dash: To create the "Executive Dashboard" for your FinOps data.

Semantic Search: Using PostgreSQL pgvector to allow the AI to search through your resource tags.