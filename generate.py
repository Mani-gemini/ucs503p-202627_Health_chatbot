"""
generate.py - ask ONE question from the command line.

    python generate.py "what are the symptoms of dengue"
    python generate.py "I have chest pain and can't breathe"

All the real work is in pipeline.py (keep both files in the same folder).
"""

import sys
from pipeline import answer_question, RELEVANCE_THRESHOLD


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what are the symptoms of dengue"
    print(f"Question: {query}\n")

    result = answer_question(query)

    if result["chunks"]:
        print(f"[retrieval] best distance = {result['best_distance']:.4f} "
              f"(threshold = {RELEVANCE_THRESHOLD})")
        for c in result["chunks"]:
            print(f"   {c['distance']:.4f}  {c['disease']} / {c['section']}")
        print()

    print(f"[path taken] {result['path']}\n")
    print(result["answer"])

    if result["path"] == "error":
        print(f"\n[technical detail for you, not shown to users] {result['error_detail']}")


if __name__ == "__main__":
    main()
