"""FinOps AI Agent — LangGraph ReAct agent with Azure OpenAI and dashboard context awareness."""
import os
import logging
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

app = FastAPI(title="FinOps AI Agent", version="1.1.0")
logger = logging.getLogger(__name__)

PLATFORM_API = os.getenv(
    "PLATFORM_API_URL",
    "http://finops-platform-api-svc.platform.svc.cluster.local",
)

SYSTEM_PROMPT = """You are FinOps AI, an expert Azure cloud cost optimization assistant embedded in a FinOps dashboard.

Your job is to help engineers and finance teams understand their Azure spending, identify anomalies, and act on savings.

RESPONSE PRINCIPLES:
- Always cite specific services, amounts, and dates when data is available
- Express costs in the user's currency (from context, default USD)
- Give concrete, actionable recommendations — not generic advice
- When asked to "explain" a billing item, give a plain-English definition plus the main cost drivers
- When data is missing, suggest running a sync first (sidebar → Sync All Data)
- Keep answers concise; use bullet points for lists of more than 3 items

BILLING KNOWLEDGE — Azure services explained:
- "Bandwidth / Data Transfer": Charges for data leaving Azure datacenters (egress). Driven by large file downloads, cross-region replication, and CDN misses.
- "Azure Kubernetes Service": Managed Kubernetes control plane is free; you pay for the VM nodes running your pods. Cost is driven by node size × count × uptime.
- "Azure Monitor / Log Analytics": Pay-per-GB for data ingestion and 31-day retention. Reduce by filtering noisy logs at source and shortening retention for dev workspaces.
- "Storage Account / Blob Storage": Pay for GB stored + transaction operations. Archive tier is ~10× cheaper than Hot for infrequently accessed data.
- "Azure SQL / PostgreSQL": Pay for vCores × hours + storage. Reserved capacity (1yr/3yr) gives 50-70% discount over pay-as-you-go.
- "Azure Backup / Site Recovery": Pay per protected instance + storage. Often overlooked until you see a large Storage line item.
- "Reserved Instances / Savings Plans": Upfront or monthly commitment that reduces compute costs 30-60%. The 1st-of-month spike is the monthly amortization charge.
- "Azure Defender / Microsoft Defender": Security posture service charged per resource type per month. Common cost driver in large subscriptions.
- "Azure Key Vault": Very cheap per operation (< $0.03/10K calls). If large, check for application bugs making excessive API calls.

If you receive a DASHBOARD CONTEXT block at the start of the conversation, use those numbers in your answers and avoid making tool calls to fetch the same data.
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
    """Get total Azure cost summary including current period, previous period, and % change."""
    return str(_api("/costs/summary", {"days": days}))


@tool
def get_top_services(days: int = 30) -> str:
    """Get top Azure services by cost for the past N days, ranked by spend."""
    return str(_api("/costs/by-service", {"days": days, "limit": 15}))


@tool
def get_cost_trend(days: int = 30) -> str:
    """Get daily cost trend for the past N days. Use to identify spikes and patterns."""
    return str(_api("/costs/daily", {"days": days}))


@tool
def get_advisor_recommendations(impact: str = "High") -> str:
    """Get Azure Advisor cost optimization recommendations. impact: High, Medium, or Low."""
    return str(_api("/advisor", {"category": "Cost", "impact": impact}))


@tool
def get_all_advisor_recommendations() -> str:
    """Get all Azure Advisor cost recommendations regardless of impact level."""
    return str(_api("/advisor", {"category": "Cost"}))


@tool
def get_resource_list(resource_type: str = "") -> str:
    """List Azure resources filtered by type (e.g. microsoft.compute/virtualmachines)."""
    params = {"type": resource_type, "limit": 100} if resource_type else {"limit": 100}
    return str(_api("/resources", params))


@tool
def get_cost_by_subscription() -> str:
    """Get cost breakdown by Azure subscription."""
    return str(_api("/costs/by-subscription"))


@tool
def get_cost_by_resource_group(days: int = 30) -> str:
    """Get cost breakdown by resource group for the past N days."""
    return str(_api("/costs/by-resource-group", {"days": days, "limit": 20}))


@tool
def explain_azure_service(service_name: str) -> str:
    """Explain what an Azure billing line item means in plain English and what drives its cost.
    Use this when the user asks 'what is X' or 'explain X' for a service name."""
    explanations = {
        "bandwidth":          "Egress data transfer charges. Azure charges for data leaving its datacenters. Driven by downloads, cross-region traffic, and CDN misses. Use Azure CDN and keep data in-region to reduce.",
        "data transfer":      "Same as Bandwidth — egress charges for data leaving Azure. Free within the same region.",
        "azure kubernetes":   "AKS managed control plane is free. You pay for the underlying VM nodes. Cost scales with node count × VM size × uptime. Use spot nodes for non-critical workloads and scale down dev clusters at night.",
        "virtual machine":    "Pay per VM size × hours running. VMs cost money even when idle. Use auto-shutdown for dev/test, spot instances for batch work, and Reserved Instances for 24/7 production workloads.",
        "azure monitor":      "Pay per GB of log data ingested plus retention past 31 days. Reduce by filtering noisy application logs, using basic logs tier, and reducing sampling rates.",
        "log analytics":      "Azure Monitor's log storage backend. Pay per GB ingested and retained. Same optimisation advice as Azure Monitor.",
        "application insights": "APM tool billed per GB of telemetry. Reduce by enabling adaptive sampling and filtering out health-check traffic.",
        "storage":            "Pay for GB stored (hot/cool/archive tiers) plus transaction operations. Archive tier is ~10× cheaper for infrequently accessed data. Review lifecycle policies.",
        "blob":               "Object storage. Pay for GB + read/write transactions. Use lifecycle policies to move old data to cool/archive tiers automatically.",
        "managed disk":       "Block storage for VMs. Pay per disk size provisioned (not used). Downsize or delete unattached disks.",
        "azure sql":          "Managed SQL database. Pay for vCores × hours + storage. Reserved capacity gives 50-70% discount. Elastic pools reduce cost for multiple small databases.",
        "postgresql":         "Managed PostgreSQL. Pay for vCores × hours + storage. Burstable tier is cheapest for intermittent workloads.",
        "cosmos db":          "Multi-model database. Pay for Request Units (RUs) provisioned + storage. Autoscale prevents over-provisioning.",
        "azure backup":       "Per-instance fee + backup storage. Appears as a Storage line item. Review retention policies — keeping 5 years of daily backups is expensive.",
        "key vault":          "Very cheap per operation (< $0.03/10K API calls). Large charges indicate an application making excessive vault reads — usually a missing cache.",
        "azure firewall":     "Fixed hourly charge (~$1.25/hr) plus data processing fee. Consider Azure Firewall Basic SKU or NSGs for simpler filtering.",
        "vpn gateway":        "Fixed hourly charge per gateway SKU plus S2S tunnel hours. Charged even when no traffic flows.",
        "reserved instance":  "Upfront or monthly commitment for a specific VM size/region that gives 30-60% discount. The 1st-of-month spike you see is the monthly amortization of an annual upfront payment.",
        "savings plan":       "Flexible compute commitment ($/hr) that applies across VM sizes and regions. Gives ~30% discount vs pay-as-you-go. Less restrictive than Reserved Instances.",
        "defender":           "Microsoft Defender for Cloud. Charged per resource type per month. Often large in subscriptions with many resource types. Audit which plans are enabled.",
        "sentinel":           "Cloud SIEM. Pay per GB of data analysed per day. Often the largest Monitor & Security cost. Use data connectors selectively.",
    }
    key = service_name.lower()
    for svc, explanation in explanations.items():
        if svc in key or key in svc:
            return f"**{service_name}**: {explanation}"
    return (
        f"'{service_name}' is an Azure cloud service. "
        "I don't have a built-in explanation for this specific name. "
        "Try searching the Azure Pricing Calculator or ask me to look up your current charges for it."
    )


def build_llm():
    endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key    = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_ver    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    kwargs = dict(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=api_ver,
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


_tools = [
    get_cost_summary,
    get_top_services,
    get_cost_trend,
    get_advisor_recommendations,
    get_all_advisor_recommendations,
    get_resource_list,
    get_cost_by_subscription,
    get_cost_by_resource_group,
    explain_azure_service,
]

llm = build_llm()


class ChatRequest(BaseModel):
    messages: list[dict]
    context: str | None = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[str] = []


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        "version": "1.1.0",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Build per-request system prompt with optional dashboard context
    system_content = SYSTEM_PROMPT
    if req.context:
        system_content = (
            SYSTEM_PROMPT
            + "\n\nDASHBOARD CONTEXT — what the user is currently viewing:\n"
            + req.context
            + "\n\nUse the numbers above in your answers before making tool calls for the same data."
        )

    agent = create_react_agent(
        llm,
        _tools,
        state_modifier=SystemMessage(content=system_content),
    )

    lc_messages = []
    for m in req.messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    try:
        result     = agent.invoke({"messages": lc_messages})
        final      = result["messages"][-1]
        tool_names = [m.name for m in result["messages"] if hasattr(m, "name") and m.name]
        return ChatResponse(response=final.content, tool_calls=tool_names)
    except Exception as e:
        logger.error("Agent error: %s", e)
        return ChatResponse(response=f"I encountered an error: {str(e)}", tool_calls=[])
