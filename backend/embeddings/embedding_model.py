import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# We default to 'all-MiniLM-L6-v2' as it is fast and runs locally well.
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

class EmbeddingModel:
    def __init__(self, model_name=MODEL_NAME):
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully.")
        
    def embed_text(self, text):
        """Generates an embedding for a single string."""
        return self.model.encode(text).tolist()
        
    def embed_batch(self, texts):
        """Generates embeddings for a list of strings."""
        return self.model.encode(texts).tolist()
