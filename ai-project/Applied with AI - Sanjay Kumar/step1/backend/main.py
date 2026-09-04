"""
Step 1 — Basic chatbot (no data access)

Flow: UI -> Backend API -> Agent -> LLM -> response -> UI
The agent only talks to the LLM. It has no tools, no bank APIs, no data access.
Ask it "what's my account balance?" and it will correctly say it can't help with that.
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

MODEL = "claude-opus-5"
SYSTEM_PROMPT = (
    "You are a helpful customer support assistant for a bank. "
    "You do NOT have access to any customer account data, balances, or transactions "
    "at this stage — that integration comes in a later step. "
    "If asked for account-specific information, politely explain that you can't "
    "access account data yet and offer general help instead."
)

app = FastAPI(title="Step 1 - Basic Chatbot")

# Allow the static frontend (or a separately-hosted one) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The Anthropic client resolves credentials from the environment
# (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN) — nothing hardcoded here.
client = anthropic.Anthropic()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": m.role, "content": m.content} for m in req.messages],
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="Invalid or missing ANTHROPIC_API_KEY on the server.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by the LLM provider. Try again shortly.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {e.message}")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=502, detail="Could not reach the LLM provider.")

    reply_text = next((b.text for b in response.content if b.type == "text"), "")
    return ChatResponse(reply=reply_text)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# Serve the static chat UI at "/" (built for local/container use — see frontend/index.html).
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
