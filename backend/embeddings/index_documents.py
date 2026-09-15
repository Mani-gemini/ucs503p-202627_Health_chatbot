import os
import json
from dotenv import load_dotenv

from embedding_model import EmbeddingModel
from vector_store import VectorStore

load_dotenv()

DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR", "data/processed")
INPUT_FILE = os.path.join(DATA_PROCESSED_DIR, "medical_chunks.jsonl")

def main():
    print("Starting Document Indexing...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Processed chunks file '{INPUT_FILE}' not found. Please run build_knowledge_base.py first.")
        return
        
    # 1. Load chunks from JSONL
    print(f"Loading chunks from {INPUT_FILE}...")
    chunks = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    print(f"Loaded {len(chunks)} chunks.")
    if not chunks:
        return
        
    # 2. Initialize Models and Database
    embedder = EmbeddingModel()
    store = VectorStore()
    
    # 3. Generate Embeddings (batching can be added for huge datasets, processing all at once for now)
    print("Generating embeddings...")
    texts_to_embed = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_batch(texts_to_embed)
    
    # 4. Insert into ChromaDB
    print("Inserting into Vector Store...")
    store.add_chunks(chunks, embeddings)
    
    print(f"Successfully indexed {len(chunks)} chunks into ChromaDB.")

if __name__ == "__main__":
    main()
