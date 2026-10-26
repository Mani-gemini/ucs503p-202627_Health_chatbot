"""
ingest.py (v2 - field-agnostic)
--------------------------------
Fixes a real bug in the v1 script: that version only chunked a fixed list of
known field names (key_facts, overview, symptoms, ...). Since the final
dataset has grown organically -- different diseases now carry different
extra fields (cdc_key_points, symptom_details, risk_factors_detailed, etc.)
-- the old script silently dropped most of that content instead of erroring,
which is the most dangerous kind of bug in a RAG pipeline: the system runs
fine, it just quietly knows less than you think it does.

This version chunks EVERY field except pure metadata (name, source), no
matter what it's called, and turns each field name into a readable section
label automatically (e.g. "cdc_key_points" -> "Cdc Key Points").

Run:
    python3 ingest.py
"""

import os
import json
from sentence_transformers import SentenceTransformer
import chromadb

from pathlib import Path
_CUR_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CUR_DIR.parent if _CUR_DIR.name == "backend" else _CUR_DIR
JSON_PATH = str(_PROJECT_ROOT / "data" / "FINAL_DATASET.json" if (_PROJECT_ROOT / "data" / "FINAL_DATASET.json").exists() else _PROJECT_ROOT / "FINAL_DATASET.json")
CHROMA_DIR = os.environ.get("CHROMA_DIR", str(_PROJECT_ROOT / "chroma_db"))
COLLECTION_NAME = "medical_knowledge"
EMBEDDING_MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"

# Fields that are structural metadata, not content to chunk/embed
METADATA_FIELDS = {"name", "source"}


def field_to_label(field_name: str) -> str:
    """Turns a snake_case field name into a readable section label."""
    return field_name.replace("_", " ").replace("cdc", "CDC").title()


def flatten_value(value) -> str:
    """
    Turns a field's value -- which might be a string, a list of strings, or
    a nested dict (like risk_factors: {modifiable: [...], non_modifiable: [...]}
    or form_specific_symptoms: {bubonic: "...", pneumonic: "..."}) -- into a
    single clean text block for chunking.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, dict):
        parts = []
        for sub_key, sub_val in value.items():
            sub_label = field_to_label(sub_key)
            sub_text = flatten_value(sub_val)
            parts.append(f"{sub_label}: {sub_text}")
        return " ".join(parts)
    return str(value)


def build_chunks(disease_key: str, entry: dict) -> list[dict]:
    """
    Field-agnostic chunk builder. Every field in the entry becomes its own
    chunk (one field = one semantically self-contained unit), except the
    pure metadata fields. This guarantees nothing gets silently dropped,
    no matter what a field happens to be named.
    """
    name = entry.get("name", disease_key)
    source = entry.get("source", "Unknown source")
    chunks = []

    for field_name, value in entry.items():
        if field_name in METADATA_FIELDS:
            continue
        text = flatten_value(value)
        if not text or not text.strip():
            continue
        label = field_to_label(field_name)
        chunks.append({
            "text": f"{name} - {label}: {text.strip()}",
            "metadata": {
                "disease": name,
                "disease_key": disease_key,
                "section": label,
                "source": source,
            }
        })

    return chunks


def main():
    print(f"Loading knowledge base from {JSON_PATH} ...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        kb = json.load(f)

    print(f"Found {len(kb)} disease entries. Building chunks ...")
    all_chunks = []
    for disease_key, entry in kb.items():
        disease_chunks = build_chunks(disease_key, entry)
        all_chunks.extend(disease_chunks)
        print(f"  - {entry.get('name', disease_key)}: {len(disease_chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    print(f"\nLoading embedding model '{EMBEDDING_MODEL_NAME}' "
          f"(downloads on first run) ...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Generating embeddings ...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    print(f"\nConnecting to persistent ChromaDB store at '{CHROMA_DIR}' ...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "WHO/CDC-sourced disease awareness knowledge base"}
    )

    ids = [f"{c['metadata']['disease_key']}_{c['metadata']['section'].replace(' ', '_')}_{i}"
           for i, c in enumerate(all_chunks)]
    metadatas = [c["metadata"] for c in all_chunks]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    print(f"\nDone. {collection.count()} chunks stored in ChromaDB "
          f"collection '{COLLECTION_NAME}' at '{CHROMA_DIR}'.")


if __name__ == "__main__":
    main()
