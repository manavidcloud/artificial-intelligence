"""OpenCost REST API client."""
import os
import requests
import streamlit as st

_BASE = os.environ.get("OPENCOST_URL", "http://opencost.opencost.svc.cluster.local:9090")
_TIMEOUT = 15


@st.cache_data(ttl=120, show_spinner=False)
def allocation(
    window: str = "1d",
    aggregate: str = "namespace",
    accumulate: bool = False,
    step: str = "1d",
) -> list[dict]:
    """GET /allocation/compute — cost allocation by namespace/workload/pod/label."""
    try:
        r = requests.get(
            f"{_BASE}/allocation/compute",
            params={
                "window": window,
                "aggregate": aggregate,
                "accumulate": str(accumulate).lower(),
                "step": step,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if isinstance(data, list):
            return data
        return [data]
    except Exception as exc:
        st.warning(f"OpenCost API error (allocation): {exc}")
        return []


@st.cache_data(ttl=120, show_spinner=False)
def assets(window: str = "1d", aggregate: str = "node") -> list[dict]:
    """GET /assets/compute — node / disk / network asset costs."""
    try:
        r = requests.get(
            f"{_BASE}/assets/compute",
            params={"window": window, "aggregate": aggregate, "accumulate": "false"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if isinstance(data, list):
            return data
        return [data]
    except Exception as exc:
        st.warning(f"OpenCost API error (assets): {exc}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def savings_request_sizing() -> dict:
    """GET /savings/requestSizingV2 — rightsizing recommendations."""
    try:
        r = requests.get(f"{_BASE}/savings/requestSizingV2", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.warning(f"OpenCost API error (savings): {exc}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def savings_cluster_sizing() -> dict:
    """GET /savings/clusterSizingRecommendations — node pool rightsizing."""
    try:
        r = requests.get(
            f"{_BASE}/savings/clusterSizingRecommendations", timeout=_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.warning(f"OpenCost API error (cluster sizing): {exc}")
        return {}


def health() -> bool:
    """Returns True if OpenCost /healthz responds 200."""
    try:
        r = requests.get(f"{_BASE}/healthz", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def flatten_allocation(raw: list[dict]) -> list[dict]:
    """
    Flatten OpenCost allocation response into a flat list of dicts.
    Each bucket in `raw` is a dict of {name: AllocationProperties}.
    We merge all buckets into one flat list for easier DataFrame construction.
    """
    rows: list[dict] = []
    for bucket in raw:
        if not isinstance(bucket, dict):
            continue
        for name, props in bucket.items():
            if not isinstance(props, dict):
                continue
            row = {"name": name}
            row["cpu_cost"]     = props.get("cpuCost", 0.0)
            row["gpu_cost"]     = props.get("gpuCost", 0.0)
            row["ram_cost"]     = props.get("ramCost", 0.0)
            row["pv_cost"]      = props.get("pvCost", 0.0)
            row["network_cost"] = props.get("networkCost", 0.0)
            row["shared_cost"]  = props.get("sharedCost", 0.0)
            row["total_cost"]   = props.get("totalCost", 0.0)
            row["idle_cost"]    = props.get("cpuCostAdjustment", 0.0)
            # Efficiency
            cpuEff = props.get("cpuEfficiency", 0.0)
            ramEff = props.get("ramEfficiency", 0.0)
            row["cpu_efficiency"] = round(cpuEff * 100, 1)
            row["ram_efficiency"] = round(ramEff * 100, 1)
            row["efficiency"]     = round(((cpuEff + ramEff) / 2) * 100, 1)
            # Window
            start = (props.get("window") or {}).get("start", "")
            row["start"] = start[:10] if start else ""
            rows.append(row)
    return rows
