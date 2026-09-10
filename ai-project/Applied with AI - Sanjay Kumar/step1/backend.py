# backend.py
from fastapi import FastAPI
from pydantic import BaseModel
import json
from typing import Dict, Any, List

app = FastAPI(title="Banking AI Agent API")

# --- 1. BANK APIs (TOOLS) ---
def execute_get_account_balance(account_id: str) -> Dict[str, Any]:
    return {"account_id": account_id, "balance": 24345.00, "currency": "USD"}

def execute_get_recent_transactions(account_id: str, limit: int = 2) -> Dict[str, Any]:
    return {
        "account_id": account_id,
        "transactions": [
            {"merchant": "Amazon", "amount": -120.00},
            {"merchant": "Payroll", "amount": 2500.00}
        ][:limit]
    }

TOOL_REGISTRY = {
    "get_account_balance": execute_get_account_balance,
    "get_recent_transactions": execute_get_recent_transactions
}

# --- 2. LLM REASONING ENGINE ---
class SimulatedLLM:
    def decide_tool(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        if "balance" in query_lower:
            return {
                "needs_tool": True,
                "tool_name": "get_account_balance",
                "args": {"account_id": "acc_78910"}
            }
        elif "transaction" in query_lower or "spent" in query_lower:
            return {
                "needs_tool": True,
                "tool_name": "get_recent_transactions",
                "args": {"account_id": "acc_78910", "limit": 2}
            }
        return {"needs_tool": False, "reply": "I can help you check your account balance or view recent transactions."}

    def format_final_reply(self, tool_name: str, result: Dict[str, Any]) -> str:
        if tool_name == "get_account_balance":
            return f"Your current account balance is ${result['balance']:,.2f} {result['currency']}."
        elif tool_name == "get_recent_transactions":
            txs = ", ".join([f"{t['merchant']} (${t['amount']})" for t in result['transactions']])
            return f"Here are your recent transactions: {txs}."
        return "Done."

# --- 3. AI AGENT ---
class AIAgent:
    def __init__(self):
        self.llm = SimulatedLLM()

    def process(self, user_message: str) -> str:
        # Step A: Ask LLM for Tool Choice
        decision = self.llm.decide_tool(user_message)
        
        if decision["needs_tool"]:
            tool_name = decision["tool_name"]
            args = decision["args"]
            
            # Step B: Execute Bank API Tool
            tool_func = TOOL_REGISTRY.get(tool_name)
            if tool_func:
                raw_data = tool_func(**args)
                # Step C: Ask LLM to format final response
                return self.llm.format_final_reply(tool_name, raw_data)
        
        return decision["reply"]

agent = AIAgent()

# --- 4. BACKEND API ENDPOINT ---
class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    reply = agent.process(request.message)
    return {"status": "success", "reply": reply}