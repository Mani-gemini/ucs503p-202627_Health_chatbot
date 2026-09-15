from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid

def chunk_text(text, metadata, chunk_size=1000, chunk_overlap=200):
    """
    Splits text into chunks of specified size and overlap.
    Assigns metadata and a unique ID to each chunk.
    """
    if not text:
        return []
        
    # RecursiveCharacterTextSplitter tries to split on paragraphs, then sentences, then words
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    raw_chunks = splitter.split_text(text)
    
    processed_chunks = []
    for i, chunk_content in enumerate(raw_chunks):
        chunk_id = str(uuid.uuid4())
        
        # Copy original document metadata and add chunk-specific metadata
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = i
        chunk_metadata["chunk_id"] = chunk_id
        
        processed_chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_content,
            "metadata": chunk_metadata
        })
        
    return processed_chunks
