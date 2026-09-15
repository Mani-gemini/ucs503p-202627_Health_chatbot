import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "vector_db/chroma")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "medical_knowledge")

class VectorStore:
    def __init__(self, persist_directory=CHROMA_PATH, collection_name=COLLECTION_NAME):
        # Ensure the directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        print(f"Initializing ChromaDB at {persist_directory}...")
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(name=collection_name)
        print(f"Collection '{collection_name}' ready.")
        
    def add_chunks(self, chunks, embeddings):
        """
        Adds chunks and their embeddings to the vector store.
        Uses upsert to avoid duplicating chunks with the same ID.
        """
        if not chunks:
            return
            
        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
    def search(self, query_embedding, top_k=5):
        """
        Searches the vector database using the provided query embedding.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results
