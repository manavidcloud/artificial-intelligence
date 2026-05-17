"""OpenCost REST API client for the FinOps Dashboard.

OpenCost runs in the `opencost` namespace as part of the core platform.
Helm values: 4-dashboard/k8s/opencost-helm-values.yaml

Default in-cluster URL: http://opencost.opencost.svc.cluster.local:9003
Override with OPENCOST_URL environment variable.

Full API surface (OpenCost 1.100+):
  Allocation
    /allocation/compute          — namespace / workload / pod / container / service / label / annotation
  Assets
    /assets                      — node, pv, network, load-balancer costs
  Cloud Costs  (requires cloud billing export configured)
    /cloudCost                   — Azure/AWS/GCP billing by provider, category, service
  External / Custom Costs
    /customCost/total            — 3rd-party cost totals
    /customCost/timeseries       — 3rd-party cost daily series
  Savings
    /savings/requestSizingV2     — container CPU/RAM rightsizing
    /savings/clusterSizingRecommendations — node pool rightsizing
    /savings/abandonedWorkloads  — workloads with 0 CPU+RAM usage
    /savings/unclaimedVolumes    — PVs not mounted by any pod
    /savings/underutilizedNodes  — nodes below utilization threshold
"""
import os
import requests
import streamlit as st

_BASE = os.environ.get(
    "OPENCOST_URL",
    "http://opencost.opencost.svc.cluster.local:9003",
).rstrip("/")

_TIMEOUT = 15
_WARNED: set[str] = set()


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _warn_once(endpoint: str, exc: Exception) -> None:
    if endpoint not in _WARNED:
        _WARNED.add(endpoint)
        msg = str(exc)
        if "char 0" in msg or "Expecting value" in msg:
            st.warning(
                f"OpenCost `/{endpoint}` returned an empty response — "
                "OpenCost may still be starting up or Prometheus is not yet connected. "
                "Run: `kubectl get pods -n opencost`"
            )
        else:
            st.warning(f"OpenCost `/{endpoint}` error: {exc}")


def _get(path: str, params: dict | None = None, ttl_key: str = "") -> dict | list | None:
    """Raw GET helper — returns parsed JSON or None on error."""
    try:
        r = requests.get(f"{_BASE}/{path.lstrip('/')}", params=params or {}, timeout=_TIMEOUT)
        r.raise_for_status()
        if not r.text.strip():
            return None
        return r.json()
    except Exception as exc:
        if ttl_key:
            _warn_once(ttl_key, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

def is_online() -> bool:
    try:
        r = requests.get(f"{_BASE}/healthz", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Allocation  (/allocation/compute)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def allocation(
    window: str = "7d",
    aggregate: str = "namespace",
    accumulate: bool = True,
    step: str = "1d",
    include_idle: bool = True,
    share_idle: bool = False,
    resolution: str = "1m",
) -> list[dict]:
    """Cost allocation — supports namespace/workload/pod/container/service/label/annotation."""
    params = {
        "window":      window,
        "aggregate":   aggregate,
        "accumulate":  str(accumulate).lower(),
        "step":        step,
        "includeIdle": str(include_idle).lower(),
        "shareIdle":   str(share_idle).lower(),
        "resolution":  resolution,
    }
    data = _get("allocation/compute", params, ttl_key="allocation")
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


# ─────────────────────────────────────────────────────────────────────────────
# Assets  (/assets)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def node_assets(window: str = "7d") -> list[dict]:
    """Node-level infrastructure costs."""
    data = _get("assets", {"window": window, "aggregate": "node", "accumulate": "true"}, "assets/node")
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


@st.cache_data(ttl=120, show_spinner=False)
def pv_assets(window: str = "7d") -> list[dict]:
    """PersistentVolume costs — storage cost breakdown."""
    data = _get("assets", {"window": window, "aggregate": "pv", "accumulate": "true"}, "assets/pv")
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


# ─────────────────────────────────────────────────────────────────────────────
# Savings APIs
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def request_sizing() -> list[dict]:
    """Container CPU/RAM rightsizing recommendations."""
    data = _get("savings/requestSizingV2")
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("recommendations", [])
    return data if isinstance(data, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def cluster_sizing() -> dict:
    """Node pool rightsizing recommendations."""
    data = _get("savings/clusterSizingRecommendations")
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=300, show_spinner=False)
def abandoned_workloads() -> list[dict]:
    """Workloads with 0 CPU + RAM usage — candidates for deletion."""
    data = _get("savings/abandonedWorkloads")
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("recommendations", data.get("data", []))
    return data if isinstance(data, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def unclaimed_volumes() -> list[dict]:
    """PersistentVolumes not mounted by any running pod."""
    data = _get("savings/unclaimedVolumes")
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("recommendations", data.get("data", []))
    return data if isinstance(data, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def underutilized_nodes() -> list[dict]:
    """Nodes running below utilization threshold."""
    data = _get("savings/underutilizedNodes")
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("recommendations", data.get("data", []))
    return data if isinstance(data, list) else []


# ─────────────────────────────────────────────────────────────────────────────
# Cloud Costs  (/cloudCost)
# Requires Azure billing export + cloudCost.enabled=true in helm values
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cloud_costs(
    window: str = "7d",
    aggregate: str = "service",
    accumulate: str = "day",
) -> list[dict]:
    """Cloud provider billing costs (Azure/AWS/GCP).

    aggregate options: invoiceEntityID, accountID, provider,
                       providerID, category, service
    accumulate options: all, hour, day, week, month, quarter
    """
    data = _get(
        "cloudCost",
        {"window": window, "aggregate": aggregate, "accumulate": accumulate},
    )
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


def cloud_costs_enabled() -> bool:
    """Quick check — returns True only if /cloudCost returns real data (not empty)."""
    try:
        r = requests.get(
            f"{_BASE}/cloudCost",
            params={"window": "1d", "aggregate": "provider", "accumulate": "all"},
            timeout=8,
        )
        if r.status_code != 200 or not r.text.strip():
            return False
        data = r.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        return bool(items)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Custom / External Costs  (/customCost)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def custom_cost_total(
    window: str = "7d",
    aggregate: str = "",
    accumulate: str = "day",
) -> list[dict]:
    """External/3rd-party cost totals (e.g. Datadog, Snowflake, custom)."""
    params: dict = {"window": window, "accumulate": accumulate}
    if aggregate:
        params["aggregate"] = aggregate
    data = _get("customCost/total", params)
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


@st.cache_data(ttl=300, show_spinner=False)
def custom_cost_timeseries(
    window: str = "7d",
    aggregate: str = "",
    accumulate: str = "day",
) -> list[dict]:
    """External/3rd-party cost daily time-series."""
    params: dict = {"window": window, "accumulate": accumulate}
    if aggregate:
        params["aggregate"] = aggregate
    data = _get("customCost/timeseries", params)
    if data is None:
        return []
    items = data.get("data", []) if isinstance(data, dict) else data
    return items if isinstance(items, list) else [items]


# ─────────────────────────────────────────────────────────────────────────────
# Flatten helpers
# ─────────────────────────────────────────────────────────────────────────────

def flatten_allocation(raw: list[dict]) -> list[dict]:
    """Flatten OpenCost allocation buckets into a flat DataFrame-ready list."""
    rows: list[dict] = []
    for bucket in raw:
        if not isinstance(bucket, dict):
            continue
        for name, props in bucket.items():
            if not isinstance(props, dict):
                continue
            cpu_eff = props.get("cpuEfficiency", 0.0) or 0.0
            ram_eff = props.get("ramEfficiency", 0.0) or 0.0
            start   = (props.get("window") or {}).get("start", "")
            rows.append({
                "name":           name,
                "cpu_cost":       props.get("cpuCost",     0.0) or 0.0,
                "ram_cost":       props.get("ramCost",     0.0) or 0.0,
                "pv_cost":        props.get("pvCost",      0.0) or 0.0,
                "gpu_cost":       props.get("gpuCost",     0.0) or 0.0,
                "network_cost":   props.get("networkCost", 0.0) or 0.0,
                "shared_cost":    props.get("sharedCost",  0.0) or 0.0,
                "total_cost":     props.get("totalCost",   0.0) or 0.0,
                "cpu_efficiency": round(cpu_eff * 100, 1),
                "ram_efficiency": round(ram_eff * 100, 1),
                "efficiency":     round(((cpu_eff + ram_eff) / 2) * 100, 1),
                "start":          start[:10] if start else "",
            })
    return rows


def flatten_pv_assets(raw: list[dict]) -> list[dict]:
    """Flatten PV asset buckets into a flat DataFrame-ready list."""
    rows: list[dict] = []
    for bucket in (raw or []):
        if not isinstance(bucket, dict):
            continue
        for name, props in bucket.items():
            if not isinstance(props, dict):
                continue
            rows.append({
                "pv":         name,
                "total_cost": props.get("totalCost",  0.0) or 0.0,
                "bytes":      props.get("bytes",       0)   or 0,
                "gb":         round((props.get("bytes", 0) or 0) / (1024 ** 3), 1),
                "namespace":  (props.get("properties") or {}).get("namespace", ""),
                "claim":      (props.get("properties") or {}).get("claim", ""),
                "storage_class": (props.get("properties") or {}).get("storageClass", ""),
            })
    return rows
