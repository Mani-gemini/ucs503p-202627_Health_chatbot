"""
pipeline.py - the reusable "brain" of HealthBot AI (Modules C + D).

    from pipeline import answer_question
    result = answer_question("what are the symptoms of dengue")

Flow:  safety check -> retrieve from ChromaDB -> relevance gate ->
       grounded prompt -> Groq LLM -> answer + sources + disclaimer
Every question is logged to SQLite (query_log.db) = Data Store D2.

Environment variables (Command Prompt:  set NAME=value):
    GROQ_API_KEY         required for normal answers (NEVER put it in code)
    GROQ_MODEL           optional, default llama-3.3-70b-versatile
    RELEVANCE_THRESHOLD  optional, default 1.2 (use the value from calibrate.py)
    LOG_DB               optional, default query_log.db
"""

import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime

import requests

_CUR_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CUR_DIR.parent if _CUR_DIR.name == "backend" else _CUR_DIR

def _get_path(env_key, default_name):
    if env_key in os.environ:
        return os.environ[env_key]
    if (Path("./") / default_name).exists():
        return str(Path("./") / default_name)
    return str(_PROJECT_ROOT / default_name)

CHROMA_DIR = _get_path("CHROMA_DIR", "chroma_db")
COLLECTION_NAME = "medical_knowledge"
EMBEDDING_MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"
TOP_K = 4
RELEVANCE_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "50.014"))
LOG_DB = _get_path("LOG_DB", "query_log.db")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq retires models regularly (llama-3.3-70b-versatile was shut down on 16 Aug 2026).
# Set GROQ_MODEL to override; the others are tried automatically if a model is unavailable.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODELS = ["openai/gpt-oss-20b"]
MAX_QUERY_LEN = 500

NO_INFO_MESSAGE = ("I don't have verified information on this specific question - "
                   "please consult a doctor.")
DISCLAIMER = ("\n\nDisclaimer: This is general health awareness information from WHO/CDC "
              "sources, not medical advice or a diagnosis. Please consult a qualified doctor.")

MEDICAL_ESCALATION = (
    "This could be a medical emergency. Please act now:\n"
    "- Call 112 (India's emergency number) or 108 (ambulance, in most states) immediately.\n"
    "- Go to the nearest hospital emergency department.\n"
    "- Do not wait for an online answer.\n"
    "I'm an information chatbot and cannot give emergency care.")

SELF_HARM_ESCALATION = (
    "I'm really sorry you're feeling this way, and I'm glad you said it. You deserve support right now.\n"
    "- Call Tele-MANAS (free, 24x7): 14416 or 1800-891-4416.\n"
    "- If you are in immediate danger, call 112 or go to the nearest hospital.\n"
    "- Please reach out to someone you trust and stay with them.\n"
    "I'm an information chatbot, but you do not have to go through this alone.")

# ---------------------------------------------------------------- emergency --
SELF_HARM = [r"\bwant to die\b", r"\bkill myself\b", r"\bsuicid", r"\bend my life\b",
             r"\bhurt myself\b", r"\bself[- ]harm\b", r"\bdon'?t want to live\b",
             r"\bno reason to live\b", r"\bcut(ting)? myself\b", r"\bend it all\b",
             r"\beveryone (would be|is) better (off )?without me\b",
             r"\bwish i (was|were|wasn'?t) (here|alive|born)\b"]

ALWAYS_EMERGENCY = [r"\bnot breathing\b", r"\bstopped breathing\b", r"\bunconscious\b",
                    r"\bunresponsive\b", r"\bcoughing (up )?blood\b", r"\bvomiting blood\b",
                    r"\bsevere bleeding\b", r"\bcan'?t breathe\b", r"\bcannot breathe\b",
                    r"\bpoison(ed|ing)?\b", r"\boverdose\b",
                    # Loss of consciousness / unresponsive
                    r"\bpassed out\b", r"\bpassing out\b", r"\bnot waking up\b",
                    r"\bwon'?t wake up\b", r"\bcan'?t wake (him|her|them|up)\b",
                    r"\bblacked out\b", r"\bcollapsed\b",
                    # Severe allergic reaction
                    r"\banaphylax", r"\bsevere allergic\b", r"\bepipen\b",
                    r"\bface (is )?swelling\b", r"\bthroat (is )?closing\b",
                    # Other life-threatening
                    r"\bchok(ing|ed)\b", r"\bdrown(ing|ed)\b",
                    r"\belectric shock\b", r"\belectrocut",
                    r"\bbleed(ing)? (won'?t|can'?t) stop\b",
                    r"\bcan'?t stop (the )?bleeding\b"]

SERIOUS = [r"\bchest pain\b", r"\bstroke\b", r"\bseizure", r"\bheart attack\b",
           r"\bfaint(ed|ing)\b", r"\bshortness of breath\b", r"\bdifficulty breathing\b",
           r"\bparalys", r"\bconvulsion",
           # Additional serious signs
           r"\bslurred? speech\b", r"\bcouldn'?t speak\b", r"\bcan'?t speak\b",
           r"\bsudden (severe )?headache\b", r"\bworst headache\b",
           r"\bloss of vision\b", r"\bblurry vision\b", r"\bsudden blindness\b",
           r"\bsudden numbness\b", r"\bone side (of (my|the) body)?\b",
           r"\bhigh fever\b", r"\bstiff neck\b",   # meningitis warning signs
           r"\brapid heart(beat)?\b", r"\bheart (is )?racing\b", r"\bpalpitation"]

# words showing the person is in trouble NOW
URGENT = [r"\bi (am|'m|have|think i)\b", r"\bi've\b",
          r"\bmy (father|mother|dad|mom|baby|child|son|daughter|wife|husband|friend|brother|sister|grandfather|grandmother|someone)\b",
          r"\bhaving\b", r"\bnow\b", r"\bright now\b", r"\bwhat should i do\b",
          r"\bhelp\b", r"\bplease help\b", r"\bsudden", r"\burgent\b",
          r"\bsomeone (is|has|just)\b"]

# openers meaning "this is a textbook question"
INFO_STARTS = ("what are", "what is", "what causes", "what triggers", "how does", "how do",
               "how is", "how can", "why does", "why do", "can ", "does ", "do ", "is ",
               "are ", "who is at risk", "tell me about", "explain")
INFO_PHRASES = [r"\bsymptoms of\b", r"\bsigns of\b", r"\bsign of\b", r"\bcauses? of\b",
                r"\bwarning signs\b", r"\bis .* a sign\b"]


def _any(patterns, text):
    return any(re.search(p, text) for p in patterns)


def check_emergency(query):
    """Return 'self_harm', 'medical' or None."""
    q = query.lower().strip()
    if _any(SELF_HARM, q):
        return "self_harm"
    if _any(ALWAYS_EMERGENCY, q):
        return "medical"
    if _any(SERIOUS, q):
        urgent = _any(URGENT, q)
        if urgent:
            return "medical"
        informational = q.startswith(INFO_STARTS) or _any(INFO_PHRASES, q)
        if informational:
            return None          # textbook question, e.g. "what are the symptoms of stroke"
    return None


# ------------------------------------------------------------------ logging --
def _init_db():
    con = sqlite3.connect(LOG_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS interactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, query TEXT, path TEXT,
        best_distance REAL, sources TEXT, answer TEXT)""")
    return con


def log_interaction(query, path, answer, best_distance=None, sources=""):
    try:
        con = _init_db()
        con.execute("INSERT INTO interactions(timestamp,query,path,best_distance,sources,answer) "
                    "VALUES(?,?,?,?,?,?)",
                    (datetime.now().isoformat(timespec="seconds"), query, path,
                     best_distance, sources, answer))
        con.commit()
        con.close()
    except Exception:
        pass  # logging must never break the chatbot


# ---------------------------------------------------------------- retrieval --
_model = None
_collection = None


def get_embed_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_collection():
    global _collection
    if _collection is None:
        import chromadb
        _collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION_NAME)
    return _collection


def retrieve_chunks(query):
    emb = get_embed_model().encode([query]).tolist()
    res = get_collection().query(query_embeddings=emb, n_results=TOP_K)
    chunks = []
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        chunks.append({"text": res["documents"][0][i], "distance": res["distances"][0][i],
                       "disease": meta.get("disease", ""), "section": meta.get("section", ""),
                       "source": meta.get("source", "")})
    return chunks


# --------------------------------------------------------------- generation --
KNOWN_DISEASE_TERMS = [
    "yellow fever", "high blood pressure", "fungal diseases", "fungal disease",
    "dengue", "malaria", "typhoid", "tuberculosis", "tb", "diabetes",
    "influenza", "flu", "chikungunya", "hypertension", "asthma",
    "anemia", "stroke", "plague", "hiv", "aids"
]


def _heuristic_contextualize(query, history):
    """Fallback contextualizer if the LLM rewriting call is unavailable."""
    q_lower = query.lower()
    for d in KNOWN_DISEASE_TERMS:
        if re.search(r"\b" + re.escape(d) + r"\b", q_lower):
            return query
    for turn in reversed(history or []):
        content = (turn.get("content") or "").lower()
        for d in KNOWN_DISEASE_TERMS:
            if re.search(r"\b" + re.escape(d) + r"\b", content):
                return f"{query} {d}"
    return query


def contextualize_query(query, history):
    """Rewrite follow-up questions referencing recent turns into standalone search queries."""
    if not history:
        return query
    recent = history[-6:]
    history_lines = []
    for turn in recent:
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = (turn.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content[:300]}")
    if not history_lines:
        return query

    prompt = (
        "Given the chat history and a follow-up question, rewrite the follow-up question into a "
        "standalone search question that explicitly names the disease or health condition being discussed. "
        "If the question is already standalone or unrelated to the history, return it exactly as is. "
        "Do NOT answer the question. Output ONLY the standalone question text without quotes or explanation.\n\n"
        "Chat History:\n" + "\n".join(history_lines) + "\n\n"
        f"Follow-up Question: {query}\n\n"
        "Standalone Question:"
    )
    ok, rewritten = call_groq(prompt)
    if ok and rewritten:
        cleaned = rewritten.strip().strip("\"'").strip()
        if cleaned.lower().startswith("standalone question:"):
            cleaned = cleaned[len("standalone question:"):].strip()
        if cleaned and len(cleaned) <= MAX_QUERY_LEN:
            return cleaned
    return _heuristic_contextualize(query, recent)


def build_grounded_prompt(query, chunks, history=None):
    context = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))

    # Prepend the last 3 turns of conversation so the model understands references
    # like "what about the treatment?" or "tell me more about that".
    history_block = ""
    if history:
        recent = history[-6:]   # at most 3 user+assistant pairs
        lines = []
        for turn in recent:
            role_label = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role_label}: {turn.get('content', '').strip()}")
        if lines:
            history_block = "Recent conversation (for context only — do NOT answer from this):\n"
            history_block += "\n".join(lines) + "\n\n"

    return ("You are a public-health awareness assistant. Answer the question using ONLY the "
            "verified context below. If the context does not contain the answer, reply exactly: "
            f"\"{NO_INFO_MESSAGE}\"\n"
            "Do not diagnose, do not prescribe medicines or doses, and do not add facts from "
            "outside the context. Keep the answer clear, simple and short.\n\n"
            f"{history_block}"
            f"CONTEXT:\n{context}\n\nQUESTION: {query}\n\nANSWER:")


def call_groq(prompt):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return False, "GROQ_API_KEY is not set in the terminal that started the server"
    last = ""
    for model in [GROQ_MODEL] + [m for m in GROQ_FALLBACK_MODELS if m != GROQ_MODEL]:
        payload = {"model": model, "temperature": 0.1,
                   "messages": [{"role": "user", "content": prompt}]}
        if model.startswith("openai/gpt-oss"):
            payload["reasoning_effort"] = "low"      # short, fast answers for a simple RAG task
        try:
            r = requests.post(GROQ_URL, timeout=45, headers={"Authorization": f"Bearer {key}"}, json=payload)
        except Exception as e:
            return False, f"network error: {e}"
        if r.status_code == 200:
            try:
                text = (r.json()["choices"][0]["message"].get("content") or "").strip()
            except Exception as e:
                return False, f"unexpected response from Groq: {e}"
            if text:
                return True, text
            last = f"model {model} returned an empty answer"
            continue
        last = f"HTTP {r.status_code} from model {model}: {r.text[:300]}"
        # only move on to the next model when THIS model is the problem
        if r.status_code in (400, 404) and "model" in r.text.lower():
            continue
        return False, last
    return False, last or "no model available"


def format_final_answer(answer, chunks):
    seen, sources = set(), []
    for c in chunks:
        k = (c["disease"], c["source"])
        if k not in seen:
            seen.add(k)
            sources.append(f"- {c['disease']}: {c['source']}")
    return f"{answer}\n\nSources:\n" + "\n".join(sources) + DISCLAIMER


# --------------------------------------------------------------------- main --
def _result(path, answer, chunks=None, best=None, err="", body=None, sources=None, kind=None):
    """body = the answer text alone (what a web page shows); answer = body + sources +
    disclaimer as one string (what the command-line tools print)."""
    return {"path": path, "answer": answer, "body": answer if body is None else body,
        "sources": sources or [], "chunks": chunks or [],
        "best_distance": best, "error_detail": err, "emergency_kind": kind}


def _source_list(chunks):
    seen, out = set(), []
    for c in chunks:
        k = (c["disease"], c["section"])
        if k not in seen:
            seen.add(k)
            out.append({"disease": c["disease"], "section": c["section"], "source": c["source"]})
    return out


def answer_question(query, history=None):
    query = (query or "").strip()
    if not query:
        return _result("invalid", "Please type a health question.")
    if len(query) > MAX_QUERY_LEN:
        query = query[:MAX_QUERY_LEN]

    kind = check_emergency(query)
    if kind:
        msg = SELF_HARM_ESCALATION if kind == "self_harm" else MEDICAL_ESCALATION
        log_interaction(query, "emergency", msg)
        return _result("emergency", msg, kind=kind)

    # Use conversation history to contextualize follow-up questions for semantic retrieval
    search_query = query
    if history:
        search_query = contextualize_query(query, history)
        if search_query != query:
            contextual_kind = check_emergency(search_query)
            if contextual_kind:
                msg = SELF_HARM_ESCALATION if contextual_kind == "self_harm" else MEDICAL_ESCALATION
                log_interaction(query, "emergency", msg)
                return _result("emergency", msg, kind=contextual_kind)

    try:
        chunks = retrieve_chunks(search_query)
    except Exception as e:
        msg = "Sorry, the knowledge base is not available right now. Please try again later."
        log_interaction(query, "error", msg)
        return _result("error", msg, err=f"retrieval failed: {e}")

    best = min((c["distance"] for c in chunks), default=None)
    if best is None or best > RELEVANCE_THRESHOLD:
        log_interaction(query, "fallback", NO_INFO_MESSAGE, best)
        return _result("fallback", NO_INFO_MESSAGE + DISCLAIMER, chunks, best, body=NO_INFO_MESSAGE)

    ok, text = call_groq(build_grounded_prompt(query, chunks, history))
    if not ok:
        msg = "Sorry, I couldn't generate an answer right now. Please try again in a moment."
        log_interaction(query, "error", msg, best)
        return _result("error", msg, chunks, best, err=text)

    if NO_INFO_MESSAGE in text:      # the model itself said the context lacks the answer
        log_interaction(query, "fallback", NO_INFO_MESSAGE, best)
        return _result("fallback", NO_INFO_MESSAGE + DISCLAIMER, chunks, best, body=NO_INFO_MESSAGE)

    final = format_final_answer(text, chunks)
    log_interaction(query, "answer", final, best,
                    "; ".join(sorted({f"{c['disease']}/{c['section']}" for c in chunks})))
    return _result("answer", final, chunks, best, body=text, sources=_source_list(chunks))
