# OpenCost Troubleshooting

> **OPTIONAL COMPONENT**
> Runs in the `opencost` namespace on AKS. Pod name: `opencost-*`.

---

## Quick Diagnosis

```bash
# Check pod state
kubectl get pods -n opencost

# Check logs (live)
kubectl logs -n opencost -l app.kubernetes.io/name=opencost --tail=100 -f

# Test health (via port-forward)
kubectl port-forward svc/opencost 9090:9090 -n opencost &
curl http://localhost:9090/healthz

# Fetch allocation data directly
curl "http://localhost:9090/allocation/compute?window=1d&aggregate=namespace" | python3 -m json.tool | head -40
```

---

## Pod CrashLoopBackOff

### Prometheus not reachable

```
Error connecting to Prometheus: Get "http://prometheus-server.opencost.svc:80/api/v1/query": ...
```

Check if Prometheus is running in the `opencost` namespace:

```bash
kubectl get pods -n opencost -l app=prometheus-server
kubectl get svc  -n opencost prometheus-server
```

If Prometheus is in a different namespace, update the `helm-values.yaml`:

```yaml
opencost:
  prometheus:
    external:
      enabled: true
      url: "http://prometheus-server.<your-namespace>.svc:80"
```

Then:

```bash
helm upgrade opencost opencost/opencost \
  --namespace opencost \
  -f 5-opencost/k8s/helm-values.yaml
```

---

### `ImagePullBackOff`

```bash
# Re-assign AcrPull role (or ensure quay.io is reachable)
# OpenCost image is from quay.io — no ACR needed, no auth required.
# If blocked by firewall, whitelist: quay.io
```

---

## Dashboard — "OpenCost Offline"

The dashboard pings `https://opencost.manmas.online/healthz` to check status.
If it shows offline:

1. Check the ingress is applied: `kubectl get ingress -n opencost`
2. Check TLS certificate: `kubectl get certificate -n opencost`
3. Check DNS: `nslookup opencost.manmas.online` — should resolve to NGINX ingress IP
4. Port-forward and test locally:
   ```bash
   kubectl port-forward svc/opencost 9090:9090 -n opencost &
   curl http://localhost:9090/healthz
   ```

---

## "No Cost Data" in OpenCost UI

OpenCost needs ~5-10 minutes of Prometheus scrape data to show cost allocations.

```bash
# Check Prometheus is scraping kubelet metrics
kubectl port-forward svc/prometheus-server 9080:80 -n opencost &
curl "http://localhost:9080/api/v1/query?query=up{job='kubernetes-nodes'}" | python3 -m json.tool
```

If the kubelet scrape job is missing, Prometheus is not configured for K8s metrics.
Reinstall using the `helm-values.yaml` from this folder (it configures the correct scrape jobs).

---

## Dashboard iframe shows blank page / CORS error

OpenCost UI uses `X-Frame-Options: SAMEORIGIN` in some builds, which blocks iframe embedding.

```bash
# Check response headers
curl -I https://opencost.manmas.online/
# Look for: X-Frame-Options
```

If present, override at the NGINX ingress level by adding to `ingress.yaml` annotations:

```yaml
nginx.ingress.kubernetes.io/configuration-snippet: |
  more_set_headers "X-Frame-Options: ALLOWALL";
```

Then re-apply: `kubectl apply -f 5-opencost/k8s/ingress.yaml`

---

## Recovery Procedure

```bash
# Full reinstall
helm uninstall opencost   -n opencost
helm uninstall prometheus -n opencost

helm install prometheus prometheus-community/prometheus \
  --namespace opencost \
  --set alertmanager.enabled=false \
  --set pushgateway.enabled=false \
  --set server.persistentVolume.size=8Gi

helm install opencost opencost/opencost \
  --namespace opencost \
  -f 5-opencost/k8s/helm-values.yaml

kubectl apply -f 5-opencost/k8s/ingress.yaml
kubectl rollout status deployment/opencost -n opencost
```
