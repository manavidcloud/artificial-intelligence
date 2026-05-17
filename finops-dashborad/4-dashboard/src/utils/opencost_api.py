"""OpenCost REST API client for the FinOps Dashboard.

OpenCost runs in the `opencost` namespace as part of the core platform.
Helm values: 4-dashboard/k8s/opencost-helm-values.yaml

Default in-cluster URL: http://opencost.opencost.svc.cluster.local:9090
Override with OPENCOST_URL environment variable.
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


def _warn_once(endpoint: str, exc: Exception) -> None:
    """Show a warning once per endpoint per Streamlit session to avoid flooding."""
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


def is_online() -> bool:
    """Quick health check — returns True if OpenCost is reachable."""
    try:
        r = requests.get(f"{_BASE}/healthz", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


@st.cache_data(ttl=120, show_spinner=False)
def allocation(
    window: str = "7d",
    aggregate: str = "namespace",
    accumulate: bool = True,
    step: str = "1d",
) -> list[dict]:
    """GET /allocation/compute — cost allocation by namespace / workload / pod / label."""
    try:
        r = requests.get(
            f"{_BASE}/allocation/compute",
            params={
                "window":     window,
                "aggregate":  aggregate,
                "accumulate": str(accumulate).lower(),
                "step":       step,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        if not r.text.strip():
            return []
        data = r.json().get("data", [])
        return data if isinstance(data, list) else [data]
    except Exception as exc:
        _warn_once("allocation", exc)
        return []


@st.cache_data(ttl=120, show_spinner=False)
def node_assets(window: str = "7d") -> list[dict]:
    """GET /assets?aggregate=node — node-level cost (OpenCost 1.100+)."""
    try:
        r = requests.get(
            f"{_BASE}/assets",
            params={"window": window, "aggregate": "node", "accumulate": "true"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        if not r.text.strip():
            return []
        data = r.json().get("data", [])
        return data if isinstance(data, list) else [data]
    except Exception as exc:
        _warn_once("assets", exc)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def request_sizing() -> list[dict]:
    """GET /savings/requestSizingV2 — container request rightsizing recs."""
    try:
        r = requests.get(f"{_BASE}/savings/requestSizingV2", timeout=_TIMEOUT)
        r.raise_for_status()
        if not r.text.strip():
            return []
        result = r.json()
        if isinstance(result, dict):
            return result.get("recommendations", [])
        return result if isinstance(result, list) else []
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def cluster_sizing() -> dict:
    """GET /savings/clusterSizingRecommendations — node pool rightsizing."""
    try:
        r = requests.get(
            f"{_BASE}/savings/clusterSizingRecommendations", timeout=_TIMEOUT
        )
        r.raise_for_status()
        if not r.text.strip():
            return {}
        return r.json()
    except Exception:
        return {}


def flatten_allocation(raw: list[dict]) -> list[dict]:
    """
    Flatten OpenCost allocation response (list of time-bucket dicts) into
    a flat list of rows suitable for a Pandas DataFrame.
    """
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
                "cpu_cost":       props.get("cpuCost", 0.0) or 0.0,
                "ram_cost":       props.get("ramCost", 0.0) or 0.0,
                "pv_cost":        props.get("pvCost", 0.0) or 0.0,
                "gpu_cost":       props.get("gpuCost", 0.0) or 0.0,
                "network_cost":   props.get("networkCost", 0.0) or 0.0,
                "shared_cost":    props.get("sharedCost", 0.0) or 0.0,
                "total_cost":     props.get("totalCost", 0.0) or 0.0,
                "cpu_efficiency": round(cpu_eff * 100, 1),
                "ram_efficiency": round(ram_eff * 100, 1),
                "efficiency":     round(((cpu_eff + ram_eff) / 2) * 100, 1),
                "start":          start[:10] if start else "",
            })
    return rows
