# AI Agent Troubleshooting

> LangGraph ReAct agent backed by Azure OpenAI.
> Runs in the `ai` namespace on AKS. Pod name: `finops-ai-agent-*`.

---

## Quick Diagnosis

```bash
# Check pod state
kubectl get pods -n ai
kubectl describe pod -n ai -l app=finops-ai-agent

# Check logs (live)
kubectl logs -n ai -l app=finops-ai-agent --tail=100 -f

# Test health
kubectl port-forward -n ai svc/finops-ai-agent-svc 8000:80 &
curl http://localhost:8000/health

# Send a test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is my total spend?"}]}'
```

---

## CrashLoopBackOff Causes

### `pydantic.v1.error_wrappers.ValidationError: Client.__init__() got an unexpected keyword argument 'proxies'`

LangChain version conflict. Fixed in current `requirements.txt`:
- `langchain-openai==0.1.23`
- `openai>=1.40.0,<2.0.0`

```bash
# Rebuild with current requirements
docker buildx build --platform linux/amd64,linux/arm64 --push \
  -t $ACR/finops-ai-agent:latest 3-ai-agent/
kubectl rollout restart deployment/finops-ai-agent -n ai
```

---

### `openai.AuthenticationError` / `401 Unauthorized`

**Option A — API key mode:** Verify `AZURE_OPENAI_API_KEY` is set in the secret:

```bash
kubectl get secret finops-ai-secret -n ai \
  -o jsonpath='{.data.AZURE_OPENAI_API_KEY}' | base64 -d && echo
```

**Option B — Workload Identity mode (no API key):** Verify managed identity has the OpenAI role:

```bash
MI_OID=$(az identity show --name mi-finops-prod --resource-group rg-finops-prod-core \
  --query principalId -o tsv)
OPENAI_ID=$(az cognitiveservices account show --name finops-ai-brain \
  --resource-group rg-finops-prod-ai --query id -o tsv)
az role assignment list --assignee "$MI_OID" --scope "$OPENAI_ID" -o table
# Should show: Cognitive Services OpenAI User
```

If missing:

```bash
az role assignment create \
  --role "Cognitive Services OpenAI User" \
  --assignee-object-id "$MI_OID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$OPENAI_ID"
```

---

### `openai.NotFoundError` — deployment not found

```bash
# Check the deployment name in the secret
kubectl get secret finops-ai-secret -n ai \
  -o jsonpath='{.data.AZURE_OPENAI_DEPLOYMENT}' | base64 -d && echo

# List actual deployments in Azure OpenAI
az cognitiveservices account deployment list \
  --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --query "[].{name:name, model:properties.model.name}" -o table
```

The deployment name in the secret must exactly match what's listed in Azure. Common mismatch: secret says `gpt-4.1-nano` but deployment name is `gpt-4o-mini`.

---

### `ResourceNotFoundError` — Azure OpenAI endpoint wrong

```bash
# Check endpoint in the secret
kubectl get secret finops-ai-secret -n ai \
  -o jsonpath='{.data.AZURE_OPENAI_ENDPOINT}' | base64 -d && echo

# Get the correct endpoint
az cognitiveservices account show --name finops-ai-brain \
  --resource-group rg-finops-prod-ai \
  --query properties.endpoint -o tsv
```

The endpoint must end with a `/` (e.g., `https://finops-ai-brain.openai.azure.com/`).

---

### Pod `Pending` — architecture mismatch

The AI Agent must be built for both `linux/amd64` and `linux/arm64` since it can land on either node pool:

```bash
# Rebuild as multi-arch
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t $ACR/finops-ai-agent:latest \
  3-ai-agent/
kubectl rollout restart deployment/finops-ai-agent -n ai
```

---

## Chat Failures (Pod Running but Chat Fails)

### Chat returns empty response or `tool error`

The agent calls the Platform API internally. If the Platform API is down, tool calls fail silently.

```bash
# Check Platform API from inside the AI agent pod
kubectl exec -n ai -l app=finops-ai-agent -- \
  curl -s http://finops-platform-api-svc.platform.svc.cluster.local/health

# Check the Platform API URL env var
kubectl get secret finops-ai-secret -n ai \
  -o jsonpath='{.data.PLATFORM_API_URL}' | base64 -d 2>/dev/null || \
  kubectl set env deployment/finops-ai-agent -n ai --list | grep PLATFORM_API
```

---

### Chat times out after 60 seconds

LangGraph ReAct agents can make multiple tool calls. If the Platform API is slow (DB queries taking > 10s), the agent chain times out.

```bash
# Check Platform API response times
time curl -s http://localhost:8080/costs/by-service | python3 -m json.tool | head -5
```

If consistently > 5s, check PostgreSQL performance (see `2-platform-api/TROUBLESHOOTING.md`).

The dashboard's `ai_chat()` function has a 60s timeout. To increase:

```python
# In 4-dashboard/src/utils/api.py — change TIMEOUT
def ai_chat(messages, context=None):
    ...
    r = requests.post(..., timeout=120)   # increase to 2 minutes
```

---

### Agent loops infinitely (tool call storm)

The ReAct agent is set to `temperature=0`. If the LLM enters a loop:

1. The API will timeout at 60s (dashboard side) and return an error
2. Check if the Azure OpenAI service has rate limiting (`429 TooManyRequests` in logs)

```bash
kubectl logs -n ai -l app=finops-ai-agent --tail=100 | grep -i "429\|rate\|error"
```

If rate limited, reduce the deployment capacity allocation in Azure Portal → Azure OpenAI → Deployments or request a quota increase.

---

## Context-Aware Chat Issues (v1.1+)

### Context not being passed

The dashboard sends `context` as a JSON field alongside `messages`. Verify the AI agent is running v1.1.0:

```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", "model": "...", "version": "1.1.0"}
```

If it returns version `1.0.0`, the new image hasn't been deployed:

```bash
docker buildx build --platform linux/amd64,linux/arm64 --push \
  -t $ACR/finops-ai-agent:latest 3-ai-agent/
kubectl rollout restart deployment/finops-ai-agent -n ai
```

### AI ignores the context I sent

The context is injected into the system prompt before the conversation starts. If the AI still makes tool calls for data that's in the context, it means the context didn't arrive correctly. Test directly:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is my total spend?"}],
    "context": "Total spend: $1,234.56 USD\nTime range: Last 30 days"
  }'
# AI should answer with $1,234.56 without making a tool call
```

---

## Build Issues

### `pip install` conflict during build

```
ERROR: Cannot install langchain-openai==0.1.23 and openai>=2.0.0 together
```

The `3-ai-agent/requirements.txt` pins `openai>=1.40.0,<2.0.0`. If this conflict appears:

```bash
cat 3-ai-agent/requirements.txt | grep openai
# Should show: openai>=1.40.0,<2.0.0
```

If the file has a broader pin, pin it explicitly:

```bash
sed -i 's/^openai.*/openai>=1.40.0,<2.0.0/' 3-ai-agent/requirements.txt
```

---

## Recovery Procedures

### Full AI agent redeploy

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t $ACR/finops-ai-agent:latest \
  3-ai-agent/

kubectl apply -f 3-ai-agent/k8s/deployment.yaml
kubectl rollout status deployment/finops-ai-agent -n ai
```

### Check all AI secrets are present

```bash
kubectl get secret finops-ai-secret -n ai \
  -o jsonpath='{.data}' | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
for k in ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_DEPLOYMENT', 'PLATFORM_API_URL']:
    if k in d:
        print(f'{k} = {base64.b64decode(d[k]).decode()[:60]}...')
    else:
        print(f'{k} = MISSING')
"
```
