"""
query.py
---------
Run this AFTER ingest.py has populated ChromaDB. It embeds a test question
with the same biomedical embedding model, searches ChromaDB by cosine
similarity, and prints the top-k most relevant chunks -- this is the
"Retrieval" step from your pipeline diagram (Module C).

Run:
    python query.py "what are the symptoms of dengue"
    python query.py "what triggers an asthma emergency"
    python query.py "how does plague spread"
"""

import sys
from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "medical_knowledge"
EMBEDDING_MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"
TOP_K = 4


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what are the symptoms of dengue"

    print(f"Query: {query}\n")

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    query_embedding = model.encode([query]).tolist()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=TOP_K,
    )

    print(f"Top {TOP_K} retrieved chunks:\n")
    for i in range(len(results["ids"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        print(f"[{i+1}] (distance={distance:.4f}) {meta['disease']} / {meta['section']}")
        print(f"    {doc}")
        print(f"    source: {meta['source']}\n")


if __name__ == "__main__":
    main()
