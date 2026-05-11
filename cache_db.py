import chromadb
from chromadb.utils import embedding_functions
import os

# Initialize ChromaDB client. It will save data locally in the ./local_db folder.
db_path = os.path.join(os.path.dirname(__file__), "local_db")
chroma_client = chromadb.PersistentClient(path=db_path)

# We use the default SentenceTransformer embedding function (all-MiniLM-L6-v2)
sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()

# Create or get the collection for our Q&A cache
collection = chroma_client.get_or_create_collection(
    name="qa_cache",
    embedding_function=sentence_transformer_ef
)

def search_cache(question: str, threshold: float = 0.3) -> dict:
    """
    Searches the ChromaDB for a semantically similar question.
    Returns the cached response if the distance is BELOW the threshold.
    """
    try:
        results = collection.query(
            query_texts=[question],
            n_results=1
        )
        
        # Check if we got any results
        if results['distances'] and len(results['distances'][0]) > 0:
            distance = results['distances'][0][0]
            
            if distance < threshold:
                metadata = results['metadatas'][0][0]
                answer = metadata.get("answer", "")
                
                return {
                    "difficulty": metadata.get("difficulty", "UNKNOWN"),
                    "model_name": metadata.get("model_name", "cached_model"),
                    "model_description": "Served from Local Semantic DB (0 API Calls)",
                    "compute_level": "Zero (Cached)",
                    "answer": answer,
                    "cached": True,
                    "distance": distance,
                    "doc_id": results['ids'][0][0]
                }
    except Exception as e:
        print(f"Cache search error: {e}")
        
    return None

def save_to_cache(question: str, answer: str, metadata: dict):
    """
    Saves a new Q&A pair into the local database.
    Embeds the QUESTION so we can search against it later.
    """
    try:
        doc_id = str(hash(question))
        
        clean_metadata = {
            "answer": str(answer),
            "difficulty": str(metadata.get("difficulty", "")),
            "model_name": str(metadata.get("model_name", "")),
            "compute_level": str(metadata.get("compute_level", "")),
            "feedback": "0"
        }
        
        collection.add(
            documents=[question],
            metadatas=[clean_metadata],
            ids=[doc_id]
        )
        return doc_id
    except Exception as e:
        print(f"Cache save error: {e}")
        return None

def update_feedback(doc_id: str, score: int):
    """
    Updates the feedback score for a specific cached answer.
    """
    try:
        results = collection.get(ids=[doc_id])
        if results and results['metadatas']:
            meta = results['metadatas'][0]
            meta['feedback'] = str(score)
            collection.update(ids=[doc_id], metadatas=[meta])
    except Exception as e:
        print(f"Feedback update error: {e}")
