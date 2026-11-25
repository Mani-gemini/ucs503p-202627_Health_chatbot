"""
server.py - Module E backend (FastAPI) for HealthBot AI.

Run (from the project folder, with your .venv active):
    export GROQ_API_KEY=gsk_...          # required for answers
    export ADMIN_TOKEN=choose-a-long-secret   # required to use the admin page
    uvicorn server:app --reload

Then open  http://127.0.0.1:8000        (chat)
           http://127.0.0.1:8000/admin  (admin)
           http://127.0.0.1:8000/docs   (auto-generated API docs)

This file is only the "delivery layer": all intelligence lives in pipeline.py.
"""

import hmac
import json
import os
import re
import shutil
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parent if BASE.name == "backend" else BASE
os.chdir(PROJECT_ROOT)   # pipeline.py uses relative paths (./chroma_db, query_log.db)
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from fastapi import Depends, FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware                     # noqa: E402
from fastapi.responses import FileResponse                             # noqa: E402
from fastapi.staticfiles import StaticFiles                            # noqa: E402
from pydantic import BaseModel, Field                                  # noqa: E402

import pipeline  # noqa: E402

KB_PATH = PROJECT_ROOT / "data" / "FINAL_DATASET.json"
if not KB_PATH.exists():
    KB_PATH = PROJECT_ROOT / "FINAL_DATASET.json"
STATIC_DIR = PROJECT_ROOT / "web"          # frontend lives in web/ (separate from any old static/ folder)
KEY_RE = re.compile(r"^[a-z0-9_]{2,40}$")
MAX_ENTRY_BYTES = 100_000

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "15"))   # /api/ask per IP per minute
_hits = defaultdict(deque)
_kb_lock = threading.Lock()


# ---------------------------------------------------------------- startup ---
@asynccontextmanager
async def lifespan(app):
    print("Loading embedding model and knowledge base (first start takes a little while) ...")
    try:
        pipeline.get_embed_model()
        col = pipeline.get_collection()
        n = col.count()
        if n == 0:
            print("Knowledge base is empty. Running initial ingestion from FINAL_DATASET.json...")
            try:
                from ingest import main as run_ingest
                run_ingest()
                pipeline._collection = None  # refresh collection
                n = pipeline.get_collection().count()
            except Exception as ie:
                print(f"Initial ingestion attempt encountered an issue: {ie}")
        print(f"Ready. {n} chunks in the knowledge base.")
    except Exception as e:  # server still starts, /api/health will show the problem
        print(f"WARNING: knowledge base not ready: {e}")
    # Self-check: make sure the chat page really talks to this server and is not an old mock-up copy.
    try:
        js = (STATIC_DIR / "healthbot.js").read_text(encoding="utf-8")
        if "/api/ask" in js and "mockDatabase" not in js:
            print(f"Frontend check: OK - chat page is connected to /api/ask (files served from {STATIC_DIR})")
        else:
            print("WARNING: web/healthbot.js is NOT the connected version (it looks like an old mock-up).")
    except Exception as e:
        print(f"WARNING: could not read web/healthbot.js - is the web/ folder complete? ({e})")
    print("Open http://127.0.0.1:8000 in your browser (not the index.html file directly).")
    if not os.environ.get("GROQ_API_KEY"):
        print("WARNING: GROQ_API_KEY is not set - normal answers will fail (emergency replies still work).")
    if not os.environ.get("ADMIN_TOKEN"):
        print("NOTE: ADMIN_TOKEN is not set - the admin page is disabled.")
    yield


app = FastAPI(title="HealthBot AI", version="1.0", lifespan=lifespan)

cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()] if cors_origins_raw != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    # No inline scripts anywhere, so the browser can be told to refuse them (blocks XSS).
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
        # Scripts only from this site (no CDN scripts, no inline scripts). Google Fonts for text only.
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'")
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"   # browser must re-check files, so edits show up immediately
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# ------------------------------------------------------------- public API ---
class HistoryTurn(BaseModel):
    role: str       # 'user' or 'assistant'
    content: str = Field(..., max_length=2000)


class Ask(BaseModel):
    question: str = Field(..., min_length=1, max_length=pipeline.MAX_QUERY_LEN)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=10)


def _rate_limit(ip):
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many questions too quickly. Please wait a minute and try again.")
    q.append(now)


@app.post("/api/ask")
def ask(body: Ask, request: Request):
    _rate_limit(request.client.host if request.client else "unknown")
    history = [{"role": t.role, "content": t.content} for t in body.history]
    r = pipeline.answer_question(body.question, history=history)
    if r["path"] == "error":
        print(f"[error] {r['error_detail']}")      # technical detail stays on the server
    return {"path": r["path"],
            "emergency": r["path"] == "emergency",
            "emergency_kind": r.get("emergency_kind"),
            "body": r["body"],
            "sources": r["sources"]}


def _load_kb():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/diseases")
def diseases():
    kb = _load_kb()
    return [{"key": k, "name": v.get("name", k)} for k, v in kb.items()]


@app.get("/api/health")
def health():
    info = {"status": "ok", "llm_configured": bool(os.environ.get("GROQ_API_KEY")),
            "threshold": pipeline.RELEVANCE_THRESHOLD}
    try:
        info["chunks"] = pipeline.get_collection().count()
    except Exception as e:
        info["status"] = "degraded"
        info["problem"] = f"knowledge base unavailable: {e}"
    return info


# -------------------------------------------------------------- admin API ---
def require_admin(x_admin_token: str = Header(default="")):
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Admin is disabled: set the ADMIN_TOKEN environment variable and restart.")
    if not hmac.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(401, "Wrong admin token.")


@app.get("/api/admin/check", dependencies=[Depends(require_admin)])
def admin_check():
    return {"ok": True}


@app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats():
    try:
        con = sqlite3.connect(pipeline.LOG_DB)
        by_path = dict(con.execute("SELECT path, COUNT(*) FROM interactions GROUP BY path").fetchall())
        rows = con.execute("SELECT id, timestamp, query, path, best_distance FROM interactions "
                           "ORDER BY id DESC LIMIT 50").fetchall()
        con.close()
    except sqlite3.OperationalError:    # table does not exist yet
        by_path, rows = {}, []
    return {"by_path": by_path, "total": sum(by_path.values()),
            "recent": [{"id": r[0], "time": r[1], "query": r[2], "path": r[3],
                        "distance": None if r[4] is None else round(r[4], 2)} for r in rows]}


@app.get("/api/admin/diseases/{key}", dependencies=[Depends(require_admin)])
def admin_get_disease(key: str):
    kb = _load_kb()
    if key not in kb:
        raise HTTPException(404, "No such disease key.")
    return kb[key]


class Entry(BaseModel):
    entry: dict


def _validate_entry(entry):
    if len(json.dumps(entry)) > MAX_ENTRY_BYTES:
        raise HTTPException(400, "Entry is too large.")
    for field in ("name", "source"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise HTTPException(400, f"Field '{field}' is required and must be non-empty text.")
    content = [k for k, v in entry.items() if k not in ("name", "source") and v]
    if not content:
        raise HTTPException(400, "Add at least one content field (for example key_facts or symptoms).")


@app.put("/api/admin/diseases/{key}", dependencies=[Depends(require_admin)])
def admin_upsert_disease(key: str, body: Entry):
    """Add or update one disease: save to the JSON file, then re-embed only that disease."""
    if not KEY_RE.match(key):
        raise HTTPException(400, "Key must be 2-40 characters: lowercase letters, digits, underscore.")
    _validate_entry(body.entry)
    from ingest import build_chunks   # imported here so the server starts fast

    chunks = build_chunks(key, body.entry)
    texts = [c["text"] for c in chunks]
    with _kb_lock:
        try:
            embeddings = pipeline.get_embed_model().encode(texts).tolist()   # can fail: do it first
        except Exception as e:
            raise HTTPException(500, f"Embedding failed, nothing was changed: {e}")

        kb = _load_kb()
        existed = key in kb
        shutil.copyfile(KB_PATH, str(KB_PATH) + ".bak")            # safety backup
        kb[key] = body.entry
        tmp = KB_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, KB_PATH)
        try:
            col = pipeline.get_collection()
            col.delete(where={"disease_key": key})
            col.add(ids=[f"{key}__{i}" for i in range(len(chunks))], embeddings=embeddings,
                    documents=texts, metadatas=[c["metadata"] for c in chunks])
        except Exception as e:
            shutil.copyfile(str(KB_PATH) + ".bak", KB_PATH)         # roll the file back
            raise HTTPException(500, f"Vector store update failed, file restored: {e}")
    return {"ok": True, "action": "updated" if existed else "added", "chunks": len(chunks)}


@app.delete("/api/admin/diseases/{key}", dependencies=[Depends(require_admin)])
def admin_delete_disease(key: str):
    with _kb_lock:
        kb = _load_kb()
        if key not in kb:
            raise HTTPException(404, "No such disease key.")
        shutil.copyfile(KB_PATH, str(KB_PATH) + ".bak")
        del kb[key]
        tmp = KB_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, KB_PATH)
        pipeline.get_collection().delete(where={"disease_key": key})
    return {"ok": True}


# ------------------------------------------------------------------ pages ---
@app.get("/admin")
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


# Admin assets live under /static/...; the public chat site (index.html, app.js, style.css)
# is served from the site root so its relative links work unchanged. Must be mounted LAST.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="site")
