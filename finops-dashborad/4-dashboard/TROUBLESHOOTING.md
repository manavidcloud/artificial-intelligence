# Dashboard Troubleshooting

> Streamlit multi-page dashboard running in the `frontend` namespace.
> Pod name: `finops-dashboard-*`.

---

## Quick Diagnosis

```bash
# Check pod state
kubectl get pods -n frontend
kubectl describe pod -n frontend -l app=finops-dashboard

# Check logs (live)
kubectl logs -n frontend -l app=finops-dashboard --tail=100 -f

# Check logs of previous crashed pod
kubectl logs -n frontend -l app=finops-dashboard --previous

# Port-forward for local access
kubectl port-forward -n frontend svc/finops-dashboard-svc 8501:80
# Open: http://localhost:8501
```

---

## Authentication Issues

### "Invalid credentials" — using the wrong username field

The `name:` field in `users.yaml` is the display name shown in the sidebar. The **login username** is the YAML key above it:

```yaml
users:
  admin:              # ← type THIS in the Username field
    name: "finaiadmin"   # ← this is NOT the login username
    password: "..."
```

Always use the key (`admin`, `viewer`, etc.).

---

### "Invalid credentials" after `kubectl rollout restart`

`kubectl port-forward` tunnels to a specific pod. After a restart, the tunnel points at the old terminated pod.

```bash
# Kill the old tunnel and restart it
pkill -f "port-forward"
kubectl port-forward -n frontend svc/finops-dashboard-svc 8501:80
```

Then open `http://localhost:8501` in an **incognito window** to clear stale Streamlit WebSocket state.

---

### "Invalid credentials" — bcrypt hash mismatch

The pod may be reading a stale or wrong `users.yaml`. Verify:

```bash
kubectl exec -n frontend \
  $(kubectl get pod -n frontend -l app=finops-dashboard -o jsonpath='{.items[0].metadata.name}') \
  -- python3 -c "
import yaml
from pathlib import Path
data = yaml.safe_load(Path('/app/src/users.yaml').read_text())
for u, info in data.get('users', {}).items():
    pw = info.get('password', '')
    print(u, '→', pw[:20], '...' if len(pw) > 20 else '')
"
```

If the password shows as a bcrypt hash (`$2b$...`), it was auto-upgraded on first login. If it shows as plaintext but you've forgotten it, reset via:

```bash
# Regenerate users.yaml from the template, set a new password
cp 4-dashboard/src/users.yaml.template 4-dashboard/src/users.yaml
nano 4-dashboard/src/users.yaml   # set new password

# Update the K8s secret
kubectl delete secret finops-dashboard-users -n frontend
kubectl create secret generic finops-dashboard-users \
  --from-file=users.yaml=4-dashboard/src/users.yaml \
  -n frontend
kubectl rollout restart deployment/finops-dashboard -n frontend
```

---

### Login page loops or shows blank screen

Usually a Streamlit state issue. Clear browser cache and cookies, or use incognito mode. If the loop persists:

```bash
kubectl logs -n frontend -l app=finops-dashboard --tail=50 | grep -i "error\|exception"
```

---

## Data Not Showing

### "No cost data — Run a sync"

1. Click **🔄 Sync All Data** in the sidebar (or go to Settings → Manual Sync)
2. Wait 1-3 minutes — the sync pulls 30 days from Azure Cost Management
3. If sync completes but no data appears:

```bash
# Check Platform API received the sync call
kubectl logs -n platform -l app=finops-platform-api --tail=50 | grep -i "sync\|cost"

# Check DB has data
kubectl port-forward -n platform svc/finops-platform-api-svc 8080:80 &
curl 'http://localhost:8080/costs/summary?days=30'
```

---

### Charts show zeros but API returns data

Currency conversion may be failing. Check the currency setting in `Settings → Currency`:

```bash
# Test currency utility
kubectl exec -n frontend -l app=finops-dashboard -- \
  python3 -c "
from utils.currency import convert, fmt
print(convert(100, 'USD', 'USD'))   # should print 100.0
print(fmt(100.0, 'USD'))            # should print \$100.00
"
```

---

### Savings Summary shows "No savings data" but Advisor shows recommendations

This happens when Azure Advisor returns recommendations with `potential_savings = 0` or `null`. It's an Azure API limitation — Advisor sometimes doesn't include savings amounts for all recommendation types.

The Savings Summary now shows the count prominently even when savings amount is $0. If you see "X recommendations found but no savings data", this is expected behavior for some recommendation types (e.g., security and reliability recommendations that have no direct cost saving).

---

### Sankey / Plotly chart shows `ValueError: Invalid element(s) for color`

This was caused by 8-digit hex colors (`#rrggbbAA`) which Plotly doesn't support. Fixed in the current `Home.py` using `_rgba()` helper function. If you see it on a custom chart, use `rgba(r,g,b,alpha)` format instead of appending alpha hex digits to a hex color string.

---

## Docker Build Issues

### Build fails — wrong directory

Always run Docker builds from inside `finops-dashborad/` and reference the subdirectory:

```bash
# Wrong (if already inside finops-dashborad/)
docker buildx build ... finops-dashborad/4-dashboard/

# Correct
docker buildx build --platform linux/amd64 --push \
  -t $ACR/finops-dashboard:latest \
  4-dashboard/
```

---

### `ENV AUTH_MODE` warning from BuildKit

```
Do not use ENV instructions for sensitive data (ENV "AUTH_MODE")
```

Docker BuildKit lints variables named `AUTH*` as potentially sensitive. The `AUTH_MODE` variable must be injected at runtime via Kubernetes Secret — **not** baked into the Dockerfile. The current `Dockerfile` has no `ENV AUTH_MODE` line. If you accidentally added one, remove it and rebuild.

---

### `users.yaml` not found — pod starts but login always fails

The pod reads `/app/src/users.yaml`. It must be mounted from a Kubernetes Secret. If the secret is missing, the pod falls back to the template (no real passwords).

```bash
# Check if the secret exists
kubectl get secret finops-dashboard-users -n frontend

# Create it if missing
kubectl create secret generic finops-dashboard-users \
  --from-file=users.yaml=4-dashboard/src/users.yaml \
  -n frontend
kubectl rollout restart deployment/finops-dashboard -n frontend
```

---

## AI Chat Issues

### AI Chat shows "Agent: Offline"

```bash
# Check AI agent pod
kubectl get pods -n ai

# Test AI agent from inside the dashboard pod
kubectl exec -n frontend -l app=finops-dashboard -- \
  curl -s http://finops-ai-agent-svc.ai.svc.cluster.local/health
```

If the AI agent is not responding, see `3-ai-agent/TROUBLESHOOTING.md`.

---

### AI Chat gives answers about wrong data / ignores context

1. Verify **Dashboard Context** toggle is ON in the sidebar (AI Chat page)
2. Expand the "📡 Context being sent to AI" section to confirm the context contains your actual spend data
3. If context shows "Total spend: $0.00", the dashboard couldn't fetch cost data — run a sync first

---

## Ingress / TLS Issues

### Dashboard not accessible at `https://app.manmas.online`

```bash
# Check ingress exists
kubectl get ingress -n frontend

# Check TLS certificate status
kubectl get certificate -n frontend
kubectl describe certificate finops-dashboard-tls -n frontend

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=30
```

Common causes:
- DNS A record not pointing to the correct NGINX ingress IP
- Port 80 blocked (cert-manager HTTP-01 challenge fails)
- Still using `letsencrypt-staging` issuer (shows "Not Secure" in browser)

Switch to production TLS:

```bash
sed -i 's/letsencrypt-staging/letsencrypt-prod/g' k8s/ingress.yaml
kubectl delete secret finops-dashboard-tls -n frontend
kubectl apply -f k8s/ingress.yaml
kubectl get certificate -n frontend --watch   # wait for READY=True
```

---

### `curl: (60) SSL certificate problem` — staging certificate

You're on the staging issuer. Staging certs are functional but not trusted by browsers. Follow the "Switch to production TLS" steps above.

---

## Recovery Procedures

### Full dashboard redeploy

```bash
# Set real user passwords first
cp 4-dashboard/src/users.yaml.template 4-dashboard/src/users.yaml
nano 4-dashboard/src/users.yaml

# Recreate the users secret
kubectl delete secret finops-dashboard-users -n frontend 2>/dev/null || true
kubectl create secret generic finops-dashboard-users \
  --from-file=users.yaml=4-dashboard/src/users.yaml \
  -n frontend

# Rebuild and push
docker buildx build --platform linux/amd64 --push \
  -t $ACR/finops-dashboard:latest \
  4-dashboard/

# Apply manifest and wait
kubectl apply -f 4-dashboard/k8s/deployment.yaml
kubectl rollout status deployment/finops-dashboard -n frontend
```

### Check all dashboard env vars

```bash
kubectl get secret finops-frontend-secret -n frontend \
  -o jsonpath='{.data}' | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
for k in ['PLATFORM_API_URL', 'PLATFORM_AI_URL']:
    if k in d:
        print(f'{k} = {base64.b64decode(d[k]).decode()}')
    else:
        print(f'{k} = MISSING')
"
```
