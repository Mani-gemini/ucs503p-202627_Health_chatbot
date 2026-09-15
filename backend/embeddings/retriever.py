from embedding_model import EmbeddingModel
from vector_store import VectorStore

class MedicalRetriever:
    def __init__(self):
        """
        Initializes the retriever which combines the embedding model and vector store.
        """
        self.embedder = EmbeddingModel()
        self.store = VectorStore()
        
    def retrieve(self, query, top_k=3):
        """
        Embeds the query and fetches the top_k most relevant medical chunks.
        Returns a formatted list of results including relevance/distance scores if available.
        """
        query_embedding = self.embedder.embed_text(query)
        results = self.store.search(query_embedding, top_k=top_k)
        
        retrieved_chunks = []
        
        # ChromaDB results are returned as lists of lists (since we can query multiple embeddings at once)
        if not results or not results['documents'] or len(results['documents']) == 0:
            return retrieved_chunks
            
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0] if 'distances' in results and results['distances'] else [None] * len(documents)
        
        for doc, meta, dist in zip(documents, metadatas, distances):
            retrieved_chunks.append({
                "text": doc,
                "metadata": meta,
                "distance": dist  # Lower distance usually means higher similarity (L2 by default)
            })
            
        return retrieved_chunks
