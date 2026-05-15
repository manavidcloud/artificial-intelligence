"""HTTP client for Platform API and AI Agent."""
import os
import logging
import requests

logger = logging.getLogger(__name__)

PLATFORM_API = os.getenv(
    "PLATFORM_API_URL",
    "http://finops-platform-api-svc.platform.svc.cluster.local",
).rstrip("/")

AI_AGENT_URL = os.getenv(
    "PLATFORM_AI_URL",
    "http://finops-ai-agent-svc.ai.svc.cluster.local",
).rstrip("/")

TIMEOUT = 10


def get(path: str, params: dict = None) -> dict | None:
    try:
        r = requests.get(f"{PLATFORM_API}{path}", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("GET %s failed: %s", path, e)
        return None


def post(path: str, json: dict = None, params: dict = None) -> dict | None:
    try:
        r = requests.post(
            f"{PLATFORM_API}{path}", json=json, params=params, timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("POST %s failed: %s", path, e)
        return None


def ai_health() -> dict | None:
    try:
        r = requests.get(f"{AI_AGENT_URL}/health", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def ai_chat(messages: list[dict]) -> dict | None:
    try:
        r = requests.post(
            f"{AI_AGENT_URL}/chat",
            json={"messages": messages},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("AI chat failed: %s", e)
        return None


def sync_all() -> list[tuple[str, bool]]:
    results = []
    for ep in ["/sync/subscriptions", "/sync/costs", "/sync/resources", "/sync/advisor"]:
        resp = post(ep)
        results.append((ep, resp is not None))
    return results
