# Designing an Enterprise Agentic AI System — Notes
### Case study: bank customer support chatbot (simple → production architecture)

---

## 1. The business problem

- A bank's customer support team received **4.2 lakh (420,000) calls last month**.
- **65% of calls** are repetitive: account balance, recent debit explanation, checkbook requests.
- Average handle time: **4 minutes/call**, all on **toll-free numbers** → the bank pays the telecom provider, costing **millions of dollars/year**.
- All this information already exists in the bank's net banking app, but:
  - Net banking has **14+ screens** — hard to navigate.
  - Many customers don't know how to log in or find what they need.
- **Business goals:**
  1. Don't compromise customer experience — deliver info conversationally.
  2. Reduce telephony cost.
- **Proposed solution:** a secure, AI-powered customer support chatbot.

---

## 2. Architecture evolution — step by step

### Step 1 — Basic chatbot (no data access)
- We will build simple chatbot 
- UI → Backend API → Agent → LLM → response → UI.
    - UI: Build front end user interface, using that customer will ask the question.
    - API: API is in backend to recived all the questions asked by the user. this API receives all the request and pass to agent
    - Agent: Agent will communicate with LARGET language module(LLM) AS Soon as it generate correct answer, we will send responde back to user interface, it will be deplayed on chatboad 
- Agent talks to the LLM only; no access to bank data.
- Demo result: asked "What's my account balance?" → bot says it has no access to bank accounts.


### Step 2 — Tool-based AI agent (single agent, many tools) - connecting the agent to bank
- 
- Bank already exposes internal APIs: balance inquiry, transaction details, statement requests, change of address, etc. (this is literally how net banking works — every screen = an API call).
- Agent is given access to these APIs as **tools**.
- Flow: user question + list of available tools → LLM picks the right tool → agent calls the tool/API → result → LLM → natural-language answer → UI.
- **Problem:** a real banking app easily needs 30–40 tools. Attaching them all to one agent causes **tool confusion / tool overload** — the LLM struggles to pick the right tool.

### Step 3 — Domain-specific sub-agents
- Split one overloaded agent into specialized agents, e.g.:
  - **Accounts agent** (balance-related tools)
  - **Transaction agent** (transaction-related tools)
  - **Service agent** (service requests: checkbook, address change, etc.)
- Each agent only sees tools relevant to its domain → less confusion, cleaner reasoning.
- **New problem:** a single user question can span multiple domains, e.g. *"What's my balance and also get me my latest transactions?"* No single sub-agent can answer this alone.

### Step 4 — Coordinator (orchestrator) agent
- Add a **coordinator agent** on top of the sub-agents.
- The coordinator uses the LLM to build a **plan**: e.g., call accounts agent → call transaction agent → merge results → generate final answer.
- All sub-agents + coordinator each independently talk to the LLM to decide which of their own tools to use.
- This is the first appearance of a proper **multi-agent system**.

### Step 5 — Introduce MCP (Model Context Protocol) servers
- Problem: tools were tightly coupled directly into each agent's codebase (API schema, error handling, request/response mapping all baked into agent code). Agents should focus on **reasoning**, not **API plumbing**.
- Solution: create one **MCP server per domain** — Accounts MCP server, Transaction MCP server, Service MCP server.
- MCP servers own all tool/API integration detail (schema, required fields, error handling).
- Agents now just talk to the relevant MCP server — **loose coupling** between reasoning (agent) and integration (MCP server).
- (Referenced: the channel's separate "MCP Explained" video for full MCP architecture detail.)

### Step 6 — Security issue discovered (no authentication)
- Demo: asking for "account balance" → bot asks for a **customer ID**.
- Problem: *any* customer ID typed in returns that customer's data — there's no verification that the requester owns that ID.
- This is a **major security flaw**: any user could pull any other customer's account info.

### Step 7 — Authentication (identity provider integration)
- Integrate with the bank's existing **internal Identity Provider (IdP)**.
- Flow: user opens chatbot → redirected to IdP login → enters username/password → IdP authenticates → redirects back to chatbot.
- From then on, every API request carries the authenticated customer's identity (typically **token-based auth**, e.g. JWT/OAuth-style tokens) — the chatbot never has to ask "what's your customer ID."

### Step 8 — Authorization (role/entitlement checks)
- Authentication = *who* the user is. Authorization = *what they're allowed to do*.
- Example: two customers ask to raise their credit limit to ₹5 lakh.
  - **Privileged customer** → allowed (with OTP confirmation).
  - **Standard customer** → denied ("no permission to increase credit limit").
- Before a sensitive tool (e.g. "increase credit limit") is called, the system checks the user's role/tier (privileged / premium / standard) against policy.

> **AI engineering vs. software engineering (recurring theme in the video):**
> Auth/authZ, observability infra, cost tracking infra, edge security are **general software engineering** (blue) — they existed before AI. Agent design, sub-agent/coordinator patterns, MCP integration, PII-aware LLM routing, and non-deterministic evaluation suites are **AI engineering** (green). Enterprise agentic systems need both.

### Step 9 — Memory / session store (conversation + shared state)
- Problem demo: user says "I flagged a transaction as suspicious last week," then asks "was that the one?" — the agent has no memory of the earlier statement or the current session's earlier turn, and asks the user to repeat themselves.
- Root cause: **LLMs are stateless** — each call is independent; the LLM has no memory of prior turns unless you resend the history.
- Solution: add a **session store** (data layer) that holds:
  1. **Conversation history** per customer (what was said, and when).
  2. **Inter-agent shared state** — e.g., if the transaction agent derives something useful, it can persist it so other agents (accounts/service/coordinator) can access it too.
- This is a **software engineering** concern, not an AI-specific one.

### Step 10 — PII protection + hybrid LLM strategy
- Problem: user provides sensitive data in-chat (e.g., full credit card number). If sent straight to a **third-party LLM** (Claude/Gemini/OpenAI via API), the bank has effectively leaked customer PII to an external party — a major compliance/security risk.
- Two mitigations, used together:
  1. **PII redaction service** — scans every inbound user message; if PII is detected, it's masked/redacted before the message moves further down the pipeline.
  2. **Hybrid LLM hosting**:
     - Deploy a **self-hosted / open-weight LLM** inside the bank's own cloud/security boundary for general reasoning — data never leaves the bank's environment.
     - Use a **third-party LLM** only for cases needing advanced/complex reasoning.
     - PII detection/redaction is applied even before hitting the self-hosted model.

### Step 11 — Agent evaluation suite (regression protection)
- Scenario: a developer edits the system prompt (e.g., changes "always confirm delivery address before submitting a checkbook request" to "just use the customer's registered address") — this silently breaks correctness if the address on file is outdated, and the checkbook goes to the wrong place.
- Need a way to catch regressions before they reach production.
- Solution: an **agent evaluation suite** — a curated "golden dataset" of edge cases and expected behaviors, tested against every change.
- Important distinction: these are **not classic unit tests**. AI agent behavior is **non-deterministic** (natural-language, LLM-generated responses vary), so evaluation needs different mechanisms than traditional deterministic software testing. This is **AI engineering** work.

### Step 12 — Observability
- Scenario: a customer disputes a balance the bot reported (bot said ₹18,200; net banking shows ₹52,340). Support team checks logs and finds only: *request received at 3:42*, *response sent at 3:42* — no way to trace what went wrong.
- **Never productionize without observability.**
- General software observability (blue): CPU/memory/disk monitoring, standard app logging.
- **AI-specific observability additions (green):**
  - What prompt came in for a given interaction.
  - Which agent/sub-agent handled it.
  - Which tool that agent called, and with what parameters.
  - What was exchanged with the LLM at each step.
- This full trace is what lets you actually diagnose and fix failures — no production software works perfectly 100% of the time, so this is core to ongoing maintenance.

### Step 13 — Cost tracking
- Every layer of this system talks to an LLM → every layer incurs **cost**.
- Unlike traditional software, this cost is **non-deterministic** — it scales with how much users actually use the system (token usage, call volume).
- Must track cost per interaction/agent/model so you know where spend is going and can apply cost controls before bills balloon.

### Step 14 — Edge layer security (networking / infra)
- Everything above is internal application design. Before going live, you also need **infrastructure/network-layer** protections in front of the app:
  - **Web Application Firewall (WAF)** — blocks common web attack patterns.
  - **DoS/DDoS protection policies.**
  - **Rate limiting** — e.g., cap a single user to N requests/second, to blunt flood-style attacks.
  - **API Gateway** — sits in front of the backend API; enforces security policy and can integrate directly with the bank's authentication provider before a request ever reaches the backend.
- The video notes there's more networking/infra depth beyond this, but stops here to keep scope manageable.

---

## 3. Full production architecture — component summary

| Layer | Component | Type |
|---|---|---|
| Client | Chat UI | Software |
| Edge | WAF, DoS protection, rate limiting, API Gateway | Software |
| Identity | Identity Provider (auth) | Software |
| Access control | Authorization / role checks (privileged, premium, standard) | Software |
| Orchestration | Coordinator agent | AI |
| Domain agents | Accounts agent, Transaction agent, Service agent | AI |
| Tool integration | Accounts / Transaction / Service MCP servers | AI (protocol) / Software (impl.) |
| Data layer | Session store (conversation history + inter-agent shared state) | Software |
| Privacy | PII redaction service | Software |
| Model layer | Self-hosted LLM (default) + third-party LLM (complex reasoning only) | AI |
| Quality | Agent evaluation suite (golden dataset, non-deterministic testing) | AI |
| Ops | Observability (prompts, agent/tool traces, LLM I/O) | AI + Software |
| Finance | Cost tracking | Software |

---

## 4. Key takeaways

1. **Start simple, scale deliberately** — chatbot → tool agent → sub-agents → coordinator/multi-agent → MCP-based decoupling → security → memory → privacy → evaluation → observability → cost → edge security.
2. **Single-agent-with-many-tools breaks down fast** (tool confusion/overload) — domain-specific sub-agents plus a coordinator solve multi-domain questions.
3. **MCP decouples reasoning from integration** — agents reason about *which* tool to use; MCP servers handle *how* to call it (schema, errors, auth to the underlying API).
4. **AuthN ≠ AuthZ** — knowing who someone is doesn't mean they're allowed to do everything.
5. **LLMs are stateless** — memory/session state must be engineered explicitly, both for conversation history and for inter-agent coordination.
6. **PII must never leak to third-party LLMs** — redact first, and prefer a self-hosted model in your own security boundary for anything routine; reserve third-party LLMs for complex reasoning only.
7. **AI systems need non-deterministic evaluation** — traditional unit tests don't capture natural-language variability.
8. **Observability must be AI-aware** — trace prompts, agent routing, tool calls, and LLM I/O, not just infra metrics.
9. **Cost is variable and must be actively tracked**, unlike traditional fixed infra cost.
10. **Edge/network security (WAF, rate limiting, API gateway) is still required** even after the AI system itself is solid.