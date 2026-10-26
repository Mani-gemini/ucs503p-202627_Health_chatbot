"""
calibrate.py
-------------
Finds a sensible RELEVANCE_THRESHOLD for your data instead of guessing.

It runs questions your chatbot SHOULD answer (in scope) and questions it should
refuse (out of scope), records the best retrieval distance for each, and suggests
a threshold between the two groups.

Run (after ingest.py has built chroma_db):
    python calibrate.py
"""

from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "medical_knowledge"
EMBEDDING_MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"

IN_SCOPE = [
    "what are the symptoms of dengue",
    "how does malaria spread",
    "how can typhoid be prevented",
    "what are the warning signs of severe dengue",
    "is there a vaccine for yellow fever",
    "what triggers asthma",
    "what are the warning signs of a stroke",
    "who is at risk of high blood pressure",
    "how is tuberculosis treated",
    "how is HIV transmitted",
    "what causes plague",
    "what is anemia",
]

OUT_OF_SCOPE = [
    "best pizza recipe",
    "who won the cricket world cup",
    "how to learn python programming",
    "what is the capital of France",
    "how to repair a bike tyre",
    "latest smartphone prices",
    "explain quantum computing",
    "write me a poem about rain",
]


def best_distance(model, collection, query):
    emb = model.encode([query]).tolist()
    res = collection.query(query_embeddings=emb, n_results=1)
    return res["distances"][0][0], res["metadatas"][0][0]["disease"], res["metadatas"][0][0]["section"]


def main():
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION_NAME)

    print("IN-SCOPE questions (should be answered)")
    in_vals = []
    for q in IN_SCOPE:
        d, disease, section = best_distance(model, collection, q)
        in_vals.append(d)
        print(f"  {d:8.4f}  {q}   -> {disease} / {section}")

    print("\nOUT-OF-SCOPE questions (should be refused)")
    out_vals = []
    for q in OUT_OF_SCOPE:
        d, disease, section = best_distance(model, collection, q)
        out_vals.append(d)
        print(f"  {d:8.4f}  {q}   -> {disease} / {section}")

    worst_in = max(in_vals)
    best_out = min(out_vals)
    print("\nSUMMARY")
    print(f"  largest in-scope distance  : {worst_in:.4f}")
    print(f"  smallest out-of-scope dist.: {best_out:.4f}")

    if worst_in < best_out:
        suggested = (worst_in + best_out) / 2
        print(f"\n  Clean gap found. Suggested threshold: {suggested:.4f}")
        print(f"  Windows:  set RELEVANCE_THRESHOLD={suggested:.4f}")
    else:
        print("\n  No clean gap: some out-of-scope questions look as close as in-scope ones.")
        print("  Pick a threshold slightly above the largest in-scope distance you are")
        print("  comfortable answering, and expect a few borderline cases.")
        print("  Note this in your report as a known limitation of similarity thresholds.")


if __name__ == "__main__":
    main()
