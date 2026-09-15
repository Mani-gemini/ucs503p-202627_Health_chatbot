import os
import sys

# Add backend dirs to python path so we can import easily
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "knowledge_base"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "embeddings"))

from document_loader import load_document
from text_cleaner import clean_text
from chunker import chunk_text
from embedding_model import EmbeddingModel
from vector_store import VectorStore
from retriever import MedicalRetriever

def run_tests():
    print("="*50)
    print("RUNNING MODULE 1 AND 2 TESTS")
    print("="*50)
    
    # Locate sample data
    test_file_path = "data/raw/diabetes_sample.txt"
    if not os.path.exists(test_file_path):
        print(f"Please ensure {test_file_path} exists before running tests.")
        return

    # TEST 1: Load Document
    print("\n[TEST 1] Loading medical document...")
    doc_data = load_document(test_file_path)
    assert doc_data is not None, "Failed to load document"
    print("✓ Document loaded successfully.")
    
    # TEST 2: Clean Text
    print("\n[TEST 2] Cleaning text...")
    raw_text = doc_data["content"]
    cleaned_text = clean_text(raw_text)
    assert len(cleaned_text) > 0, "Cleaned text is empty"
    print("✓ Text cleaned successfully.")
    
    # TEST 3 & 4: Chunk Text and Check Metadata
    print("\n[TEST 3 & 4] Chunking text and verifying metadata...")
    chunks = chunk_text(cleaned_text, doc_data["metadata"], chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 0, "No chunks generated"
    assert "source" in chunks[0]["metadata"], "Metadata 'source' missing"
    assert "chunk_id" in chunks[0]["metadata"], "Metadata 'chunk_id' missing"
    print(f"✓ Document split into {len(chunks)} chunks with metadata.")
    
    # TEST 5: Generate Embeddings
    print("\n[TEST 5] Generating embeddings...")
    embedder = EmbeddingModel()
    sample_text = chunks[0]["text"]
    embedding = embedder.embed_text(sample_text)
    assert len(embedding) > 0, "Embedding generation failed"
    print("✓ Embeddings generated successfully.")
    
    # TEST 6: Insert into ChromaDB
    print("\n[TEST 6] Inserting chunks into ChromaDB...")
    store = VectorStore(persist_directory="vector_db/test_chroma", collection_name="test_medical")
    
    # Generate embeddings for all chunks for insertion
    all_texts = [c["text"] for c in chunks]
    all_embeddings = embedder.embed_batch(all_texts)
    
    store.add_chunks(chunks, all_embeddings)
    print("✓ Chunks inserted into ChromaDB successfully.")
    
    # TEST 7: Retrieval
    print("\n[TEST 7] Testing Retrieval...")
    query = "What are the common symptoms of diabetes?"
    print(f"Query: '{query}'")
    
    # Need to instantiate retriever with our test store
    retriever = MedicalRetriever()
    retriever.store = store # Override with test store
    retriever.embedder = embedder # Override with loaded embedder
    
    results = retriever.retrieve(query, top_k=2)
    
    assert len(results) > 0, "Retrieval returned no results"
    print("✓ Retrieval successful! Top chunks found:")
    
    for i, res in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"Distance Score: {res.get('distance', 'N/A')}")
        print(f"Source: {res['metadata'].get('source', 'Unknown')}")
        print(f"Text Snippet: {res['text'][:150]}...")
        
    print("\n" + "="*50)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("="*50)

if __name__ == "__main__":
    run_tests()
