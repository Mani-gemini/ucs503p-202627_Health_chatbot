# AI Medical Chatbot

A modular AI medical chatbot with a Knowledge Base Builder and Embedding + Vector Database backend.

---

## Project Structure

```
ai chatbot/
├── index.html                      # Frontend UI
├── style.css                       # Frontend styles
├── app.js                          # Frontend logic
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment config
│
├── data/
│   ├── raw/                        # Place raw medical documents here (PDF, DOCX, TXT)
│   └── processed/                  # Auto-generated chunked data (JSONL)
│
├── vector_db/
│   └── chroma/                     # Persisted ChromaDB vector database
│
└── backend/
    ├── knowledge_base/             # Module 1: Knowledge Base Builder
    │   ├── document_loader.py      # Load PDF, DOCX, TXT files
    │   ├── text_cleaner.py         # Clean and normalize extracted text
    │   ├── chunker.py              # Split text into RAG-friendly chunks
    │   └── build_knowledge_base.py # ← Run this for Module 1
    │
    ├── embeddings/                 # Module 2: Embedding + Vector Database
    │   ├── embedding_model.py      # Sentence-Transformer wrapper
    │   ├── vector_store.py         # ChromaDB interface
    │   ├── index_documents.py      # ← Run this for Module 2
    │   └── retriever.py            # Standalone search/retrieval function
    │
    └── tests/
        └── test_pipeline.py        # Automated tests for both modules
```

---

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and customize:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PATH=vector_db/chroma
COLLECTION_NAME=medical_knowledge
DATA_RAW_DIR=data/raw
DATA_PROCESSED_DIR=data/processed
```

---

## Module 1 — Knowledge Base Builder

**Purpose:** Load medical documents → clean text → split into chunks → save as JSONL.

### Step 1: Add your medical documents

Place your PDF, DOCX, or TXT files in:

```
data/raw/
```

### Step 2: Run the pipeline

```bash
python3 backend/knowledge_base/build_knowledge_base.py
```

**Output:** `data/processed/medical_chunks.jsonl`

Each chunk contains:
- `chunk_id` — Unique UUID
- `text` — The chunk content
- `metadata.source` — Source filename
- `metadata.extension` — File extension
- `metadata.chunk_index` — Position within the document

---

## Module 2 — Embedding + Vector Database

**Purpose:** Embed chunks → store in ChromaDB → enable semantic search.

### Step 1: Ensure Module 1 has been run first

```bash
# Check that this file exists:
data/processed/medical_chunks.jsonl
```

### Step 2: Index the chunks

```bash
python3 backend/embeddings/index_documents.py
```

**Output:** Chunks are stored in `vector_db/chroma/` (persisted locally).

Running this script again is safe — it uses upsert to avoid duplicates.

---

## Running Tests

Run all 7 automated tests (from the project root):

```bash
python3 backend/tests/test_pipeline.py
```

Tests verify:
1. A medical document can be loaded
2. Text is cleaned correctly
3. Document is split into chunks
4. Chunks contain correct metadata
5. Embeddings are generated successfully
6. Chunks are inserted into ChromaDB
7. Query `"What are the common symptoms of diabetes?"` returns relevant results

---

## Example Retrieval

You can use the retriever directly in Python:

```python
import sys
sys.path.append("backend/embeddings")

from retriever import MedicalRetriever

retriever = MedicalRetriever()
results = retriever.retrieve("What are the symptoms of diabetes?", top_k=3)

for i, res in enumerate(results):
    print(f"Result {i+1}: {res['text'][:200]}")
    print(f"Source: {res['metadata']['source']}")
    print(f"Distance: {res['distance']}")
```

---

## Architecture

```
Medical PDFs/DOCS/TXTs
        ↓
Module 1: Knowledge Base Builder
  (document_loader → text_cleaner → chunker)
        ↓
data/processed/medical_chunks.jsonl
        ↓
Module 2: Embedding + Vector Database
  (embedding_model → vector_store)
        ↓
ChromaDB (vector_db/chroma/)
        ↓
retriever.py  ← Module 4 (RAG + LLM) will connect here
```

---

## Connecting Module 4 (RAG + LLM) Later

When you are ready to implement the RAG pipeline:

1. Import `MedicalRetriever` from `backend/embeddings/retriever.py`
2. Call `retriever.retrieve(user_query, top_k=3)` to get relevant chunks
3. Pass the retrieved chunk texts as context to your LLM prompt
4. The LLM generates a grounded medical response

```python
# Future Module 4 example:
context_chunks = retriever.retrieve(user_query, top_k=3)
context = "\n\n".join([c["text"] for c in context_chunks])
prompt = f"Using this medical context:\n{context}\n\nAnswer: {user_query}"
# → send prompt to LLM
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyMuPDF` | Extract text from PDF files |
| `python-docx` | Extract text from DOCX files |
| `langchain-text-splitters` | Recursive text chunking |
| `sentence-transformers` | Local embedding model (`all-MiniLM-L6-v2`) |
| `chromadb` | Local vector database |
| `python-dotenv` | Environment variable management |
