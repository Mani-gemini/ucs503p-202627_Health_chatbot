# HealthBot AI: AI-Driven Public Health Chatbot for Disease Awareness

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Mani-gemini/ucs503p-202627_Health_chatbot)

A modular, verified AI health-awareness chatbot engineered with Knowledge Base Ingestion, Vector Database Semantic Search, Safety/Emergency Escalation Guardrails, Groq-powered RAG Response Generation, and a FastAPI Delivery Backend with an Admin Dashboard.

Project for **UCS503P** — *Thapar Institute of Engineering and Technology*.

---

## Project Structure

```
ucs503p-202627_Health_chatbot/
├── assets/                         # Static assets and icons
│   ├── icons/                      # Icon sets
│   ├── stylesheets/                # Custom stylesheets
│   └── vendor/phosphor/            # Phosphor web fonts and CSS
│
├── backend/                        # Backend intelligence & server
│   ├── pipeline.py                 # Core RAG Brain: safety gate + vector retrieval + Groq LLM + SQLite logging
│   ├── server.py                   # FastAPI application (Chat API, Admin API, static delivery)
│   ├── ingest.py                   # Ingests & embeds disease dataset into ChromaDB (PubMedBERT)
│   ├── calibrate.py                # Calculates cosine distance threshold for out-of-scope filtering
│   ├── query.py                    # Direct CLI semantic retrieval tool
│   ├── generate.py                 # Direct CLI question-answering tool
│   ├── embeddings/                 # Module 2: Embedding + Vector Database
│   │   ├── embedding_model.py      # Sentence-Transformer wrapper
│   │   ├── vector_store.py         # ChromaDB vector store wrapper
│   │   ├── index_documents.py      # Chunks indexing script
│   │   └── retriever.py            # Standalone retriever
│   ├── knowledge_base/             # Module 1: Knowledge Base Builder
│   │   ├── document_loader.py      # Document extraction (PDF, DOCX, TXT)
│   │   ├── text_cleaner.py         # Text cleaner and normalizer
│   │   ├── chunker.py              # Recursive text chunker
│   │   └── build_knowledge_base.py # Chunker builder
│   └── tests/
│       ├── test_pipeline.py        # Automated unit tests for modules 1 & 2
│       └── run_tests.py            # Automated test runner (25+ test cases for RAG + emergency safety)
│
├── data/                           # Knowledge datasets
│   ├── FINAL_DATASET.json          # Verified medical disease dataset from WHO/CDC
│   ├── raw/                        # Raw health source documents
│   └── processed/                  # Processed knowledge chunks (JSONL)
│
├── docs/                           # Documentation & test reports
│   └── test_results.csv            # Automated evaluation matrix with latency, pass/fail status
│
├── journals/                       # Student weekly learning journals
├── project-proposal/               # UCS503P project proposal LaTeX source & PDF
├── project-report-final/           # Final project report
├── project-report-prototype-stage/ # Prototype stage report
│
├── web/                            # Full-featured web application
│   ├── index.html                  # Chat interface with audio mode, voice input & emergency ribbon
│   ├── style.css                   # Responsive application stylesheets
│   ├── healthbot.js                # Frontend client logic & TTS integration
│   ├── admin.html                  # Admin analytics and query log dashboard
│   ├── admin.css                   # Admin dashboard styles
│   ├── admin.js                    # Admin dashboard logic
│   └── vendor/phosphor/            # Phosphor web icons
│
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables
└── README.md                       # Project documentation
```

---

## Architecture Overview

```
User Query (Chat UI / API)
        │
        ▼
Safety & Escalation Layer (pipeline.py)
   ├── Emergency / Acute Symptoms Check ──► Emergency Escalation (112 / 108 / nearest ER)
   ├── Self-Harm / Crisis Check         ──► Crisis Help (Tele-MANAS: 14416 / 1800-891-4416)
   │
   ▼ (Safe query)
ChromaDB Vector Retrieval (PubMedBERT Embeddings)
   │
   ▼
Relevance Gate (Cosine Distance Threshold)
   ├── Distance > Threshold ──► Fallback: "No verified information — please consult a doctor"
   │
   ▼ (Grounded context)
Groq LLM Generation (Strict Grounding Prompt)
   │
   ▼
Response Formatting (WHO/CDC Sources + Medical Disclaimer)
   │
   ▼
Audit & SQLite Query Log (query_log.db)
```

---

## Setup & Installation

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Mani-gemini/ucs503p-202627_Health_chatbot.git
cd ucs503p-202627_Health_chatbot

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` (or set environment variables in your terminal):

```bash
export GROQ_API_KEY="your-groq-api-key"
export ADMIN_TOKEN="choose-a-secure-secret-for-admin"
```

Optional settings:
- `RELEVANCE_THRESHOLD`: Cosine distance threshold (default calibrated to `50.014`).
- `GROQ_MODEL`: LLM model (default `openai/gpt-oss-120b`).
- `RATE_LIMIT_PER_MIN`: Rate limit for `/api/ask` (default `15`).

---

## Running the Application

### Start the FastAPI Server

```bash
uvicorn backend.server:app --reload --port 8000
```
*(Or simply `uvicorn server:app --reload` from the root directory)*

Open in your browser:
- **Chat Interface:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin Dashboard:** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Running Automated Tests

Run the full end-to-end evaluation suite (tests 25+ medical, emergency, and out-of-scope queries):

```bash
python backend/tests/run_tests.py
```

The script evaluates:
1. **Medical Knowledge Accuracy:** Queries on Dengue, Malaria, Tuberculosis, Diabetes, Typhoid, etc.
2. **Emergency Escalation:** Rapid redirection for severe emergencies without making LLM calls.
3. **Self-Harm Protection:** Sensitive helpline escalation (Tele-MANAS).
4. **Out-of-Scope Fallback:** Rejecting irrelevant queries (cricket, cooking, coding) safely.

Results are saved to: `docs/test_results.csv`.
