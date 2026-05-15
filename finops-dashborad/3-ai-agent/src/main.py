"""FinOps AI Agent — LangGraph ReAct agent with Azure OpenAI."""
import os
import logging
import requests
from typing import Annotated
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

app = FastAPI(title="FinOps AI Agent", version="1.0.0")
logger = logging.getLogger(__name__)

PLATFORM_API = os.getenv(
    "PLATFORM_API_URL",
    "http://finops-platform-api-svc.platform.svc.cluster.local",
)

SYSTEM_PROMPT = """You are FinOps AI, an expert Azure cost optimization assistant.
You help teams understand their Azure spending, identify anomalies, and find savings.

When answering:
- Always cite specific services, amounts, and dates when data is available
- Express costs in the user's currency (default USD)
- Give actionable recommendations, not just observations
- If data is missing, suggest running a sync first

Available capabilities: cost trends, service breakdown, resource inventory, advisor recommendations.
"""


def _api(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{PLATFORM_API}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@tool
def get_cost_summary(days: int = 30) -> str:
    """Get total Azure cost summary for the past N days."""
    data = _api("/costs/summary", {"days": days})
    return str(data)


@tool
def get_top_services(days: int = 30) -> str:
    """Get top Azure services by cost for the past N days."""
    data = _api("/costs/by-service", {"days": days})
    return str(data)


@tool
def get_cost_trend(days: int = 30) -> str:
    """Get daily cost trend for the past N days."""
    data = _api("/costs/daily", {"days": days})
    return str(data)


@tool
def get_advisor_recommendations(impact: str = "High") -> str:
    """Get Azure Advisor cost optimization recommendations filtered by impact (High/Medium/Low)."""
    data = _api("/advisor", {"category": "Cost", "impact": impact})
    return str(data)


@tool
def get_resource_list(resource_type: str = "") -> str:
    """List Azure resources, optionally filtered by type (e.g. microsoft.compute/virtualmachines)."""
    data = _api("/resources", {"type": resource_type} if resource_type else None)
    return str(data)


@tool
def get_cost_by_subscription() -> str:
    """Get cost breakdown by subscription."""
    data = _api("/costs/by-subscription")
    return str(data)


def build_llm():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    kwargs = dict(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=api_version,
        temperature=0,
    )
    if api_key:
        kwargs["api_key"] = api_key
    else:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        kwargs["azure_ad_token_provider"] = token_provider
    return AzureChatOpenAI(**kwargs)


tools = [
    get_cost_summary,
    get_top_services,
    get_cost_trend,
    get_advisor_recommendations,
    get_resource_list,
    get_cost_by_subscription,
]

llm = build_llm()
agent = create_react_agent(
    llm,
    tools,
    state_modifier=SystemMessage(content=SYSTEM_PROMPT),
)


class ChatRequest(BaseModel):
    messages: list[dict]


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[str] = []


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    lc_messages = []
    for m in req.messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    try:
        result = agent.invoke({"messages": lc_messages})
        final = result["messages"][-1]
        tool_names = [
            m.name
            for m in result["messages"]
            if hasattr(m, "name") and m.name
        ]
        return ChatResponse(response=final.content, tool_calls=tool_names)
    except Exception as e:
        logger.error("Agent error: %s", e)
        return ChatResponse(
            response=f"I encountered an error: {str(e)}", tool_calls=[]
        )
