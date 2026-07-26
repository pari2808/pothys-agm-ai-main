# Pothys AI Copilot

An intelligent executive assistant built for the Pothys Jewellery group, designed to help AGM-level management interact with business data through natural conversation. Built on a **FastAPI + React Native (Expo)** stack with **Groq** as the AI backbone.

---

## What It Does

Pothys AI Copilot is a chatbot that sits on top of your daily branch reports and lets you ask questions like you'd ask a real assistant — no SQL, no dashboards, just talk.

**Ask things like:**
- *"Who's our top performer today?"*
- *"Show me the Chromepet report"*
- *"Compare gold sales between Padi and Chromepet"*
- *"What's our total revenue today?"*
- *"Schedule a meeting tomorrow at 3pm with all branch managers"*
- *"Help"*

It understands context, remembers conversations, and routes your queries to the right place — whether that's pulling numbers from the database, searching internal documents, or creating a calendar event.

---

## Architecture

```
┌──────────────────────┐     ┌──────────────────────────────────────┐
│   React Native App   │────▶│           FastAPI Backend             │
│   (Expo / Frontend)  │◀────│                                      │
└──────────────────────┘     │  ┌──────────┐    ┌────────────────┐  │
                             │  │   Chat    │───▶│  Groq (LLaMA)  │  │
                             │  │  Handler  │◀───│  Tool Calling   │  │
                             │  └────┬─────┘    └───────┬────────┘  │
                             │       │                   │           │
                             │       ▼                   ▼           │
                             │  ┌──────────┐    ┌────────────────┐  │
                             │  │ Business  │    │  Intent        │  │
                             │  │  Query    │    │  Classifier    │  │
                             │  │ Executor  │    └────────────────┘  │
                             │  └────┬─────┘                         │
                             │       │                               │
                             │       ▼                               │
                             │  ┌──────────┐    ┌────────────────┐  │
                             │  │ SQLAlchemy│    │  RAG Engine     │  │
                             │  │ (Postgres)│    │  (Supabase +    │  │
                             │  └──────────┘    │   pgvector)     │  │
                             │                  └────────────────┘  │
                             └──────────────────────────────────────┘
```

---

## Core Features

### 1. Natural Language Business Queries
Ask anything about branch performance in plain English. The system classifies your intent, extracts parameters (branch, date, metrics), and fetches the data.

| Query | What Happens |
|-------|-------------|
| *"Who's the top performer today?"* | Queries employee performance rankings |
| *"Show me Chromepet's report"* | Fetches the full daily executive summary |
| *"Compare gold sales between Padi and Coimbatore"* | Runs a cross-branch comparison |
| *"What's today's revenue?"* | Aggregates revenue across all reporting branches |
| *"Which branches haven't submitted reports?"* | Lists pending submissions |

### 2. Meeting Management
Create, update, or delete meetings through conversational flow. The assistant guides you through each field (title, date, time, participants, branch) and confirms before saving.

**Example flow:**
```
User:  Schedule a meeting tomorrow at 3pm
Bot:   To schedule the meeting, I need a few details.
       Please provide the meeting title.
User:  Annual Business Plan Meet
Bot:   Who are the participants to invite?
User:  all branch managers
Bot:   Which branch is this meeting for?
User:  all
Bot:   Meeting Scheduled Successfully.
       Title: Annual Business Plan Meet
       Date: 27-Jul-2026 | Time: 03:00 PM
       Duration: 60 min | Branch: All
```

### 3. Smart Chat History
The copilot maintains conversation context. Ask a follow-up like *"what about Padi?"* after a comparison query, and it knows you're still talking about sales.

- Chat history is capped at 20 messages to stay within Groq's token limits
- Deduplication prevents repeated queries for the same branch
- Smart dedup skips sub-metrics (revenue, gold, silver) when a full branch report is already queried

### 4. Knowledge Base (RAG)
Upload internal documents (policies, SOPs, training material) and ask questions about them. Uses **Supabase pgvector** for semantic search and Groq for generating grounded responses.

### 5. Role-Based Access
- **AGM** — sees data across all branches
- **Manager** — sees only their own branch's data

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React Native + Expo (TypeScript) |
| Backend | Python 3.11+ / FastAPI |
| Database | PostgreSQL (SQLAlchemy async) |
| Vector Store | Supabase pgvector |
| AI / LLM | Groq API (LLaMA 3.1 8B Instant) |
| Authentication | JWT (FastAPI security) |
| Embeddings | OpenAI text-embedding-3-small (via Supabase) |

### Why Groq?
The original system used Google Gemini, but its per-model token limit (8,192 tokens) caused failures with multi-branch queries that return large JSON payloads. Groq provides:
- **6,000 TPM** free tier (sufficient for executive-level usage)
- **32,768 token context** — no truncation on branch reports
- **Fast inference** — sub-second response times
- **OpenAI-compatible API** — drop-in replacement

---

## Project Structure

```
pothys-ai-assistant-2-main/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── ai.py                  # Main chat endpoint (tool calling loop)
│   │   │   ├── auth.py                # Login / JWT
│   │   │   ├── reports.py             # Excel upload & report parsing
│   │   │   └── notifications.py       # Alerts & notifications
│   │   ├── models/
│   │   │   ├── user.py                # User model (AGM / Manager)
│   │   │   ├── report.py              # DailyReport model
│   │   │   ├── employee_performance.py # Per-employee sales data
│   │   │   ├── meeting.py             # Meeting model
│   │   │   └── ai_memory.py           # AIMemory (used for meeting state)
│   │   ├── services/
│   │   │   ├── gemini_service.py       # Groq API wrapper (tool calling + extraction)
│   │   │   ├── intent_classifier.py   # Local intent classification + slot extraction
│   │   │   ├── business_query_executor.py # Business query handlers (15+ intents)
│   │   │   ├── rag_engine.py          # RAG pipeline (embed + search + generate)
│   │   │   ├── pdf_generator.py       # PDF report generation
│   │   │   └── excel_engine/
│   │   │       ├── erp_excel_parser.py    # ERP Excel parsing
│   │   │       └── anchor_parser.py       # Anchor template parsing
│   │   ├── schemas/
│   │   ├── core/
│   │   └── main.py                    # FastAPI app entry point
│   ├── .env                           # Environment variables
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── screens/agm/
│   │   │   └── AICopilotScreen.tsx    # Chat UI (FlatList + message bubbles)
│   │   └── store/
│   │       └── authStore.ts           # Auth state + API base URL
│   └── package.json
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- A [Groq API key](https://console.groq.com)
- A [Supabase](https://supabase.com) project (for vector search)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env         # Then fill in your keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install
npx expo start
```

### Environment Variables (`backend/.env`)

```env
# Groq
GROQ_API_KEY=gsk_...

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pothys_agm_db

# Supabase (for RAG / vector search)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# JWT
JWT_SECRET=your-secret-key

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
```

---

## How the AI Pipeline Works

1. **User sends a message** → FastAPI receives it at `/api/v1/ai/query`

2. **Meeting flow intercept** — if an active meeting creation flow exists, short messages are routed directly to the meeting handler (bypassing Groq entirely)

3. **Groq tool calling** — the message + chat history + tool definitions are sent to Groq. Groq decides which business tool(s) to call (e.g., `GET_BRANCH_REPORT`, `CREATE_MEETING`)

4. **Intent guard** — before executing, the local classifier cross-checks. If Groq wants to call a business tool but the user said "help" or "tell me a joke", the tool call is blocked and the static/out-of-domain response is returned

5. **Handler execution** — the matched handler queries PostgreSQL and returns structured data

6. **Response formatting** — data is formatted into a human-readable executive response (deterministic, no LLM hallucination)

7. **Fallback path** — if Groq returns text instead of tool calls, the local classifier routes the query through the appropriate handler or knowledge base

### Intent Classification

The system uses a **dual-layer** approach:

| Layer | What It Does | Speed |
|-------|-------------|-------|
| **Local classifier** (keyword-based) | Fast first-pass classification into BUSINESS / STATIC / KNOWLEDGE / OUT_OF_DOMAIN | ~1ms |
| **Groq (LLaMA 3.1 8B)** | Deep intent classification + slot extraction + tool calling | ~200ms |

The local classifier also provides a safety net: if Groq misclassifies a query (e.g., calls `SHOW_TODAYS_AGENDA` when user said "add meeting"), the local classifier catches it and overrides.

---

## Supported Intents

| Category | Intent | Example Query |
|----------|--------|--------------|
| Business | `GET_BRANCH_REPORT` | "Show me the Chromepet report" |
| Business | `GET_TOP_EXECUTIVE` | "Who is the top performer?" |
| Business | `GET_TOP_BRANCH` | "Which branch did the best today?" |
| Business | `COMPARE_BRANCHES` | "Compare Padi and Coimbatore" |
| Business | `SHOW_TODAYS_AGENDA` | "What's on my agenda today?" |
| Business | `CREATE_MEETING` | "Schedule a meeting tomorrow at 3pm" |
| Business | `SHOW_ALERTS` | "Any operational issues today?" |
| Business | `SHOW_COMPLAINTS` | "Any customer complaints?" |
| Business | `GET_PENDING_REPORTS` | "Which branches haven't reported?" |
| Knowledge | `KNOWLEDGE_QUERY` | "What's our return policy?" |
| Static | `HELP` | "help" |
| Static | `ACKNOWLEDGMENT` | "ok", "done", "thanks" |
| Static | `OUT_OF_DOMAIN` | "Tell me a joke" |

---

## Data Flow for Excel Reports

Branch managers upload daily Excel reports through the frontend. The backend:

1. **Parses** the Excel file using column-aware template matching
2. **Extracts** metrics: revenue, gold/silver/platinum/diamond sales, attendance, complaints, operational issues, digigold/digisilver enrollments
3. **Stores** in PostgreSQL: `DailyReport` + `EmployeePerformance` tables
4. **Embeds** the report content into Supabase pgvector for RAG search
5. **Returns** the executive summary for display

---

## License

Internal use — Pothys Jewellery Group.
