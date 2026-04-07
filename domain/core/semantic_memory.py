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

    def add_event(self, text: str, metadata: Dict[str, Any], structural_id: Optional[str] = None, context_id: Optional[str] = None):
        """
        Embeds and stores a new event in the semantic layer, with an optional link to a structural entity
        and a bounded context identifier.
        """
        event_id = f"evt_{int(datetime.now().timestamp() * 1000)}"
        metadata["timestamp"] = datetime.now().isoformat()
        
        if structural_id:
            metadata["structural_id"] = structural_id
        
        if context_id:
            metadata["context_id"] = context_id
            
        self.collection.add(
            ids=[event_id],
            documents=[text],
            metadatas=[metadata]
        )
        return event_id

    def query(self, query_text: str, n_results: int = 3, context_id: Optional[str] = None, min_similarity: float = 0.4) -> List[Dict[str, Any]]:
        """
        Performs semantic search to retrieve relevant past events, optionally scoped to a bounded context.
        Includes a strict manual filter and a similarity threshold to prevent context leakage 
        and semantic noise.
        """
        # We perform a wider semantic search to get candidates,
        # but we do NOT rely on ChromaDB's 'where' clause as the sole source of truth.
        search_limit = n_results * 5
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=search_limit
        )
        
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i] if 'distances' in results else None
            
            # STAGE 1: Strict Context Validation
            if context_id and metadata.get("context_id") != context_id:
                continue

            # STAGE 2: Semantic Relevance Guard
            if distance is not None:
                similarity = 1 / (1 + distance)
                if similarity < min_similarity:
                    continue

            formatted_results.append({
                "id": results['ids'][0][i],
                "text": results['documents'][0][i],
                "metadata": metadata,
                "distance": distance
            })
            
            if len(formatted_results) >= n_results:
                break
                
        return formatted_results

    def query_context(self, query_text: str, n_results: int = 3, context_id: Optional[str] = None, min_similarity: float = 0.4) -> List[Dict[str, Any]]:
        """
        Alias for query to maintain compatibility.
        """
        return self.query(query_text, n_results=n_results, context_id=context_id, min_similarity=min_similarity)

    def list_events(self, limit: int = 10, context_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists the most recent events, optionally scoped to a bounded context.
        """
        # Note: We do not use the 'where' clause here to ensure we get the absolute latest,
        # then we manually filter.
        results = self.collection.get(limit=limit)
        formatted_results = []
        for i in range(len(results['ids'])):
            metadata = results['metadatas'][i]
            if context_id and metadata.get("context_id") != context_id:
                continue
                
            formatted_results.append({
                "id": results['ids'][i],
                "text": results['documents'][i],
                "metadata": metadata
            })
        return formatted_results

    def list_events_by_context(self, context_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lists the most recent events specifically within a given bounded context.
        """
        return self.list_events(limit=limit, context_id=context_id)

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
    
    # Test with context
    test_id = sm.add_event(
        "The user and Tara achieved a major milestone: merging the first PR.", 
        {"type": "milestone", "project": "hermes-webui"},
        context_id="collaboration"
    )
    print(f"Added event: {test_id}")
    
    query = "What was the major achievement regarding the PR?"
    print(f"Querying: '{query}'")
    matches = sm.query_context(query, context_id="collaboration")
    
    for match in matches:
        print(f"Found: {match['text']} (Dist: {match.get('distance')})")
        print(f"Metadata: {match['metadata']}")
