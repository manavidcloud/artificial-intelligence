# Step 1 — Basic Chatbot (no data access)

> Reference: [`../details-with-diagram.md`](../details-with-diagram.md) and
> [`../Demo to Production. Architect a Real Agentic AI System (Step by Step).md`](<../Demo to Production. Architect a Real Agentic AI System (Step by Step).md>)

**Flow:** UI → Backend API → Agent → LLM → response → UI.
The agent talks to the LLM only — it has no tools and no access to bank data.
Ask it *"What's my account balance?"* and it should correctly say it can't help
with that yet. See [`diagram.md`](diagram.md) for the architecture diagram.

```
step1/
├── backend/
│   ├── main.py            # FastAPI app: /api/chat endpoint + serves the UI
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html          # minimal vanilla-JS chat UI
├── Dockerfile
├── .dockerignore
└── diagram.md
```

---

## 1. Build & run locally

**Prerequisites:** Python 3.12+, an Anthropic API key ([console.anthropic.com](https://console.anthropic.com)).

```bash
cd step1
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# edit backend/.env and paste your real ANTHROPIC_API_KEY

uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** — the chat UI is served directly by the backend.

**Docker (optional, mirrors what you'll ship to the cloud):**

```bash
cd step1
docker build -t step1-chatbot .
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-xxxx step1-chatbot
```

---

## 2. Deploy to Azure (Container Apps)

```bash
az login
az group create -n rg-step1-chatbot -l eastus

# Container registry
az acr create -n step1chatbotacr -g rg-step1-chatbot --sku Basic
az acr login -n step1chatbotacr

docker build -t step1chatbotacr.azurecr.io/step1-chatbot:v1 .
docker push step1chatbotacr.azurecr.io/step1-chatbot:v1

# Container Apps environment + app
az containerapp env create -n step1-env -g rg-step1-chatbot -l eastus

az containerapp create \
  -n step1-chatbot -g rg-step1-chatbot \
  --environment step1-env \
  --image step1chatbotacr.azurecr.io/step1-chatbot:v1 \
  --registry-server step1chatbotacr.azurecr.io \
  --target-port 8000 --ingress external \
  --secrets anthropic-key=sk-ant-xxxx \
  --env-vars ANTHROPIC_API_KEY=secretref:anthropic-key \
  --min-replicas 1 --max-replicas 3
```

Grab the public URL:

```bash
az containerapp show -n step1-chatbot -g rg-step1-chatbot \
  --query properties.configuration.ingress.fqdn -o tsv
```

*Alternative:* **Azure App Service (Web App for Containers)** works the same way if you'd rather not use Container Apps — `az webapp create --deployment-container-image-name ...` pointed at the same ACR image.

---

## 3. Deploy to AWS (App Runner)

App Runner is the simplest path for a single container — no cluster/VPC to manage.

```bash
aws configure   # or use an existing profile

# Push the image to ECR
aws ecr create-repository --repository-name step1-chatbot
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/step1-chatbot:v1 .
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/step1-chatbot:v1

# Store the API key securely
aws secretsmanager create-secret \
  --name step1/anthropic-api-key \
  --secret-string '{"ANTHROPIC_API_KEY":"sk-ant-xxxx"}'

# Create the App Runner service
aws apprunner create-service \
  --service-name step1-chatbot \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "<account-id>.dkr.ecr.<region>.amazonaws.com/step1-chatbot:v1",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": { "Port": "8000" }
    },
    "AuthenticationConfiguration": { "AccessRoleArn": "<ecr-access-role-arn>" }
  }'
```

Then wire the `ANTHROPIC_API_KEY` env var to the Secrets Manager secret from the
App Runner console (Configuration → Environment variables → "Reference a secret"),
or pass it inline via `RuntimeEnvironmentSecrets` in the same `create-service` call.

*Alternative:* **ECS Fargate** if you already have a VPC/cluster and want more control over networking, autoscaling, and a load balancer.

---

## 4. Deploy to GCP (Cloud Run)

```bash
gcloud auth login
gcloud config set project <your-project-id>

# Store the API key
echo -n "sk-ant-xxxx" | gcloud secrets create anthropic-api-key --data-file=-

# Build & push with Cloud Build, then deploy
gcloud builds submit --tag gcr.io/<your-project-id>/step1-chatbot

gcloud run deploy step1-chatbot \
  --image gcr.io/<your-project-id>/step1-chatbot \
  --platform managed --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest
```

Cloud Run prints the public HTTPS URL when the deploy finishes.

---

## Notes

- All three cloud paths deploy the **same Docker image** — build once, ship anywhere.
- None of these expose the API key in the image or in source control; each uses
  the platform's native secret store (ACR/Container Apps secrets, Secrets Manager,
  Secret Manager).
- This is intentionally **Step 1 only**: no auth, no tools, no bank data, no
  observability. Don't point it at anything production-sensitive — the next
  steps in the video (and companion notes) progressively add tools (Step 2),
  sub-agents + coordinator (Steps 3–4), MCP servers (Step 5), authN/authZ
  (Steps 6–8), memory (Step 9), PII redaction (Step 10), evaluation (Step 11),
  observability (Step 12), cost tracking (Step 13), and edge security (Step 14).
