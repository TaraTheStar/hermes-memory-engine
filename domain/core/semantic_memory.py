import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

class SemanticMemory:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.environ.get("HERMES_SEMANTIC_DIR", "/data/hermes_memory_engine/semantic/chroma_db")
        self.persist_directory = os.path.expanduser(persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="hermes_semantic_memory")

    def add_event(self, text: str, metadata: Dict[str, Any], structural_id: Optional[str] = None):
        """
        Embeds and stores a new event in the semantic layer, with an optional link to a structural entity.
        """
        event_id = f"evt_{int(datetime.now().timestamp() * 1000)}"
        metadata["timestamp"] = datetime.now().isoformat()
        
        if structural_id:
            metadata["structural_id"] = structural_id
            
        self.collection.add(
            ids=[event_id],
            documents=[text],
            metadatas=[metadata]
        )
        return event_id

    def query_context(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Performs semantic search to retrieve relevant past events.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
        return formatted_results

    def list_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lists the most recent events.
        """
        results = self.collection.get(limit=limit)
        formatted_results = []
        for i in range(len(results['ids'])):
            formatted_results.append({
                "id": results['ids'][i],
                "text": results['documents'][i],
                "metadata": results['metadatas'][i]
            })
        return formatted_results

    def get_similarity(self, id1: str, id2: str) -> float:
        """
        Calculates the similarity between two events using their embeddings.
        Note: ChromaDB distance is L2 by default, so similarity = 1 / (1 + distance).
        """
        # Get embeddings for both IDs
        res1 = self.collection.get(ids=[id1], include=['embeddings'])
        res2 = self.collection.get(ids=[id2], include=['embeddings'])
        
        if len(res1['embeddings']) == 0 or len(res2['embeddings']) == 0:
            return 0.0
            
        import numpy as np
        emb1 = np.array(res1['embeddings'][0])
        emb2 = np.array(res2['embeddings'][0])
        
        # Cosine similarity
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

if __name__ == "__main__":
    # Quick Test
    sm = SemanticMemory()
    print("Testing SemanticMemory...")
    
    test_id = sm.add_event("The user and Tara achieved a major milestone: merging the first PR.", {"type": "milestone", "project": "hermes-webui"})
    print(f"Added event: {test_id}")
    
    query = "What was the major achievement regarding the PR?"
    print(f"Querying: '{query}'")
    matches = sm.query_context(query)
    
    for match in matches:
        print(f"Found: {match['text']} (Dist: {match.get('distance')})")
        print(f"Metadata: {match['metadata']}")
