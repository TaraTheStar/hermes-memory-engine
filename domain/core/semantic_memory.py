import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings


class SemanticMemory:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            from infrastructure.paths import default_semantic_dir
            persist_directory = default_semantic_dir()
        self.persist_directory = os.path.expanduser(persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="hermes_semantic_memory")

    def add_event(self, text: str, metadata: Dict[str, Any], structural_id: Optional[str] = None, context_id: Optional[str] = None):
        """
        Embeds and stores a new event in the semantic layer, with an optional link to a structural entity
        and a bounded context identifier.

        A shallow copy of *metadata* is made so the caller's dict is never mutated.
        """
        event_id = f"evt_{uuid.uuid4().hex}"
        metadata = {**metadata, "timestamp": datetime.now(timezone.utc).isoformat()}

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

    _MAX_QUERY_RESULTS = 500

    def query(self, query_text: str, n_results: int = 3, context_id: Optional[str] = None, min_similarity: float = 0.4) -> List[Dict[str, Any]]:
        """
        Performs semantic search to retrieve relevant past events, optionally scoped to a bounded context.
        Includes a strict manual filter and a similarity threshold to prevent context leakage
        and semantic noise.
        """
        if n_results <= 0:
            return []

        n_results = min(n_results, self._MAX_QUERY_RESULTS)

        # We perform a wider semantic search to get candidates,
        # but we do NOT rely on ChromaDB's 'where' clause as the sole source of truth.
        search_limit = min(n_results * 5, self._MAX_QUERY_RESULTS * 5)

        # ChromaDB raises if n_results exceeds collection size; clamp to what's stored.
        collection_count = self.collection.count()
        if collection_count == 0:
            return []
        search_limit = min(search_limit, collection_count)

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

    _MAX_LIST_FETCH = 5000

    def list_events(self, limit: int = 10, context_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists the most recent events, optionally scoped to a bounded context.
        Results are sorted by timestamp descending (most recent first).

        ChromaDB's ``get()`` does not guarantee ordering, so we fetch up to
        ``_MAX_LIST_FETCH`` events and sort in Python.  This caps memory usage
        while still being correct for typical collection sizes.
        """
        total = self.collection.count()
        if total == 0:
            return []

        fetch_count = min(total, self._MAX_LIST_FETCH)
        results = self.collection.get(limit=fetch_count, include=['documents', 'metadatas'])
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

        # Sort by timestamp descending so callers get the most recent events.
        formatted_results.sort(
            key=lambda e: e["metadata"].get("timestamp", ""),
            reverse=True
        )
        return formatted_results[:limit]

    def list_events_by_context(self, context_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lists the most recent events specifically within a given bounded context.
        """
        return self.list_events(limit=limit, context_id=context_id)

    def get_similarity(self, id1: str, id2: str) -> float:
        """
        Calculates the similarity between two events using their embeddings.
        Uses L2 distance converted to similarity via 1 / (1 + distance),
        consistent with the metric used in query().
        """
        import numpy as np

        res1 = self.collection.get(ids=[id1], include=['embeddings'])
        res2 = self.collection.get(ids=[id2], include=['embeddings'])

        if res1['embeddings'] is None or res2['embeddings'] is None:
            return 0.0
        if len(res1['embeddings']) == 0 or len(res2['embeddings']) == 0:
            return 0.0
        if res1['embeddings'][0] is None or res2['embeddings'][0] is None:
            return 0.0

        emb1 = np.array(res1['embeddings'][0])
        emb2 = np.array(res2['embeddings'][0])

        # ChromaDB's default 'l2' metric returns squared L2 distance.
        # Use the same here so similarity scores are consistent with query().
        distance = float(np.sum((emb1 - emb2) ** 2))
        return 1.0 / (1.0 + distance)
