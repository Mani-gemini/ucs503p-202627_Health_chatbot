import os
import json
from dotenv import load_dotenv

from document_loader import load_document
from text_cleaner import clean_text
from chunker import chunk_text

# Load environment variables
load_dotenv()

DATA_RAW_DIR = os.getenv("DATA_RAW_DIR", "data/raw")
DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR", "data/processed")
OUTPUT_FILE = os.path.join(DATA_PROCESSED_DIR, "medical_chunks.jsonl")

def main():
    print("Starting Knowledge Base Builder...")
    
    # Ensure processed directory exists
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_RAW_DIR):
        print(f"Error: Raw data directory '{DATA_RAW_DIR}' does not exist.")
        return

    all_chunks = []
    
    # Process each file in the raw directory
    for filename in os.listdir(DATA_RAW_DIR):
        file_path = os.path.join(DATA_RAW_DIR, filename)
        
        # Skip directories
        if not os.path.isfile(file_path):
            continue
            
        print(f"Processing: {filename}")
        
        # 1. Load document
        doc_data = load_document(file_path)
        if not doc_data:
            print(f"Skipping {filename}: Could not extract text or unsupported format.")
            continue
            
        raw_text = doc_data["content"]
        metadata = doc_data["metadata"]
        
        # 2. Clean text
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text:
            print(f"Skipping {filename}: Text is empty after cleaning.")
            continue
            
        # 3. Chunk text (Sensible chunk size and overlap for medical RAG)
        chunks = chunk_text(cleaned_text, metadata, chunk_size=1000, chunk_overlap=200)
        
        all_chunks.extend(chunks)
        print(f"-> Generated {len(chunks)} chunks.")
        
    # 4. Save processed chunks to JSONL
    print(f"\nSaving {len(all_chunks)} chunks to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")
            
    print("Knowledge Base Builder complete.")

if __name__ == "__main__":
    main()
