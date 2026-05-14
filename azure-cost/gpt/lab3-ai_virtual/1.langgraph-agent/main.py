import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.messages import SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from tools import (
    get_cost_summary,
    get_cost_spike,
    get_subscriptions,
    get_total_spend,
    get_cost_by_subscription,
)

app = FastAPI(title="FinOps AI Agent", version="1.0")

SYSTEM_PROMPT = """You are a FinOps Expert AI assistant for Azure cloud cost management.
You have access to real-time tools that query live Azure cost data from the database.

Your responsibilities:
- Analyze Azure spending patterns and detect anomalies
- Identify cost spikes and explain likely causes
- Provide actionable cost optimization recommendations
- Generate executive-level summaries of cloud spend
- Answer questions about subscriptions, services, and budgets

Rules:
- Always call a tool to get real data before answering cost questions
- Be specific with numbers, percentages, and dates
- Keep answers concise, structured, and actionable
- If no data is available, tell the user to run the sync endpoints first
"""

# Supports both:
#   Personal account  -> set AZURE_OPENAI_API_KEY in env/secret
#   Office account    -> leave AZURE_OPENAI_API_KEY empty, uses Workload Identity
_api_key = os.getenv("AZURE_OPENAI_API_KEY")

if _api_key:
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        api_key=_api_key,
        temperature=0,
    )
else:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_ad_token_provider=token_provider,
        temperature=0,
    )

tools = [
    get_cost_summary,
    get_cost_spike,
    get_subscriptions,
    get_total_spend,
    get_cost_by_subscription,
]

agent = create_react_agent(llm, tools, state_modifier=SystemMessage(content=SYSTEM_PROMPT))


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    thread_id: str


@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "finops-ai-agent",
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        "auth": "api-key" if os.getenv("AZURE_OPENAI_API_KEY") else "workload-identity",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        raise HTTPException(status_code=500, detail="AZURE_OPENAI_ENDPOINT not configured")
    try:
        result = agent.invoke({"messages": [("user", request.message)]})
        response_text = result["messages"][-1].content
        return ChatResponse(response=response_text, thread_id=request.thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
