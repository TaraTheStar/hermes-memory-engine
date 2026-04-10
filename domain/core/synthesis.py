import logging
import re
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from domain.core.semantic_memory import SemanticMemory
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Project, Milestone, Skill, IdentityMarker, RelationalEdge

logger = logging.getLogger(__name__)

DEFAULT_SYMMETRY_KEYWORDS: Set[str] = {'python', 'javascript', 'rust', 'coding'}

# Pruning defaults
DEFAULT_MAX_EDGE_AGE_DAYS = 90
DEFAULT_MIN_EDGE_WEIGHT = 0.5
DEFAULT_MAX_EDGES = 10000

class SynthesisEngine:
    _TEMPORAL_WATERMARK_KEY = "_synthesis_last_temporal_scan"
    _COOCCURRENCE_WATERMARK_KEY = "_synthesis_last_cooccurrence_scan"
    _SYMMETRY_KEYWORDS_KEY = "_synthesis_symmetry_keywords"
    _MOTIF_WATERMARK_KEY = "_synthesis_last_motif_scan"
    _MOTIF_PATTERN_KEY = "_synthesis_discovered_motifs"
    def __init__(self, semantic_dir: str, structural_db_path_or_ledger,
                 symmetry_keywords: Optional[Set[str]] = None,
                 max_edge_age_days: int = DEFAULT_MAX_EDGE_AGE_DAYS,
                 min_edge_weight: float = DEFAULT_MIN_EDGE_WEIGHT,
                 max_edges: int = DEFAULT_MAX_EDGES):
        self.semantic_memory = SemanticMemory(semantic_dir)
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        
        # Load symmetry keywords from persistent storage, fallback to provided or defaults
        self.symmetry_keywords = self._load_keywords()
        if not self.symmetry_keywords:
            if symmetry_keywords is not None:
                self.symmetry_keywords = symmetry_keywords
            else:
                self.symmetry_keywords = DEFAULT_SYMMETRY_KEYWORDS
                self._save_keywords(self.symmetry_keywords)

        # Pruning configuration
        self._max_edge_age_days = max_edge_age_days
        self._min_edge_weight = min_edge_weight
        self._max_edges = max_edges

        # High-water marks for incremental scanning (per scan type).
        self._last_temporal_scan: Optional[datetime] = self._load_watermark(self._TEMPORAL_WATERMARK_KEY)
        self._last_cooccurrence_scan: Optional[datetime] = self._load_watermark(self._COOCCURRENCE_WATERMARK_KEY)
        self._last_motif_scan: Optional[datetime] = self._load_watermark(self._MOTIF_WATERMARK_KEY)

        # Load discovered motifs
        self.discovered_motifs = self._load_motifs()

    def _load_keywords(self) -> Optional[Set[str]]:
        """Load symmetry keywords from the structural ledger."""
        with self.ledger.session_scope() as session:
            marker = session.query(IdentityMarker).filter_by(key=self._SYMMETRY_KEYWORDS_KEY).first()
            if marker and marker.value:
                try:
                    keywords = json.loads(marker.value)
                    return set(keywords)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Failed to parse symmetry keywords from ledger: %s", e)
        return None

    def _save_keywords(self, keywords: Set[str]) -> None:
        """Persist symmetry keywords to the structural ledger."""
        self.ledger.set_identity_marker(self._SYMMETRY_KEYWORDS_KEY, json.dumps(list(keywords)), confidence=1.0)

    def add_symmetry_keywords(self, new_keywords: Set[str]) -> None:
        """Dynamically add new discovered motifs to the symmetry engine."""
        if not new_keywords:
            return
        self.symmetry_keywords.update(new_keywords)
        self._save_keywords(self.symmetry_keywords)
        logger.info("Promoted new symmetry keywords: %s", new_keywords)

    def _load_motifs(self) -> List[Dict[str, Any]]:
        """Load discovered structural motifs from the ledger."""
        with self.ledger.session_scope() as session:
            marker = session.query(IdentityMarker).filter_by(key=self._MOTIF_PATTERN_KEY).first()
            if marker and marker.value:
                try:
                    return json.loads(marker.value)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Failed to parse discovered motifs: %s", e)
        return []

    def _save_motifs(self, motifs: List[Dict[str, Any]]) -> None:
        """Persist discovered structural motifs to the ledger."""
        self.ledger.set_identity_marker(self._MOTIF_PATTERN_KEY, json.dumps(motifs), confidence=1.0)

    def _load_watermark(self, key: str) -> Optional[datetime]:
        """Load a scan watermark from the structural ledger."""
        with self.ledger.session_scope() as session:
            marker = session.query(IdentityMarker).filter_by(key=key).first()
            if marker and marker.value:
                try:
                    ts = datetime.fromisoformat(marker.value)
                    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    return None
        return None

    def _save_watermark(self, key: str, value: datetime) -> None:
        """Persist a scan watermark to the structural ledger."""
        self.ledger.set_identity_marker(key, value.isoformat(), confidence=1.0)

    def run_temporal_correlation_scan(self, window_minutes: int = 60, similarity_threshold: float = 0.6) -> int:
        """
        Scans for entities that appear close together in time.
        If a semantic event occurs near a structural entity, we infer a relationship.
        Only processes events newer than the last scan (incremental).
        
        Phase A: Temporal Semantic Correlation
        We check if the event and the milestone are semantically similar AND temporally close.
        """
        new_edges_count = 0
        window_delta = timedelta(minutes=window_minutes)

        scan_start = datetime.now(timezone.utc)

        with self.ledger.session_scope() as session:
            milestones = session.query(Milestone).all()
            skills = session.query(Skill).all()
            events = self.semantic_memory.list_events(limit=100)

            # Pre-load existing temporal_context edges into a set for O(1) lookup.
            existing_edges: set = set()
            for e in session.query(
                RelationalEdge.source_id, RelationalEdge.target_id
            ).filter_by(relationship_type="temporal_context").all():
                existing_edges.add((e.source_id, e.target_id))
                existing_edges.add((e.target_id, e.source_id))

            for event in events:
                try:
                    ts_raw = event.get('metadata', {}).get('timestamp')
                    if not ts_raw:
                        continue
                    event_time_raw = datetime.fromisoformat(ts_raw)
                except (ValueError, TypeError) as e:
                    logger.warning("Skipping event with invalid timestamp: %s", e)
                    continue
                
                event_time = event_time_raw if event_time_raw.tzinfo else event_time_raw.replace(tzinfo=timezone.utc)

                # Skip events already processed in a previous scan
                if self._last_temporal_scan and event_time < self._last_temporal_scan:
                    continue
                
                event_text = event.get('text', '')
                event_id = event['id']

                # Check against milestones
                for ms in milestones:
                    ms_time = ms.timestamp if ms.timestamp.tzinfo else ms.timestamp.replace(tzinfo=timezone.utc)
                    
                    # 1. Temporal Check
                    if abs((event_time - ms_time).total_seconds()) <= window_delta.total_seconds():
                        
                        # 2. Semantic Check (The Bridge)
                        # We check similarity between the event text and the milestone title/description
                        # Instead of just string matching, we use the semantic memory to compare.
                        # We'll create a temporary query or use the embedding-based similarity.
                        # Since get_similarity requires two event IDs, we'll perform a quick query 
                        # or use the text-to-embedding similarity if available.
                        # For now, we use the event_text against the milestone context.
                        
                        # Optimization: If string match exists, it's a high-confidence semantic match.
                        if ms.title.lower() in event_text.lower() or (ms.description and ms.description.lower() in event_text.lower()):
                            similarity = 1.0
                        else:
                            # Perform a semantic similarity check
                            # We simulate a milestone as a virtual event to use get_similarity logic
                            # or more simply, query the semantic memory with the milestone title.
                            query_results = self.semantic_memory.query(ms.title, n_results=1, min_similarity=similarity_threshold)
                            
                            # If the event is one of the top semantic matches for the milestone, it's a hit.
                            # (This is a slightly indirect way but works well with the current API)
                            is_semantic_match = any(res['id'] == event_id for res in query_results)
                            similarity = 1.0 if is_semantic_match else 0.0

                        if similarity >= similarity_threshold:
                            edge_key = (ms.id, event_id)
                            if edge_key not in existing_edges:
                                try:
                                    nested = session.begin_nested()
                                    self.ledger.add_edge(
                                        source_id=ms.id,
                                        target_id=event_id,
                                        relationship_type="temporal_context",
                                        weight=similarity,
                                        session=session
                                    )
                                    nested.commit()
                                    existing_edges.add(edge_key)
                                    new_edges_count += 1
                                except Exception as e:
                                    nested.rollback()
                                    logger.warning("Failed to add temporal edge %s->%s: %s", ms.id, event_id, e)

                # Check against skills
                for sk in skills:
                    if sk.last_used is None:
                        continue 
                    sk_time = sk.last_used
                    sk_time = sk_time if sk_time.tzinfo else sk_time.replace(tzinfo=timezone.utc)
                    
                    if abs((event_time - sk_time).total_seconds()) <= window_delta.total_seconds():
                        # Semantic check for skills
                        if sk.name.lower() in event_text.lower():
                            similarity = 1.0
                        else:
                            query_results = self.semantic_memory.query(sk.name, n_results=1, min_similarity=similarity_threshold)
                            is_semantic_match = any(res['id'] == event_id for res in query_results)
                            similarity = 1.0 if is_semantic_match else 0.0

                        if similarity >= similarity_threshold:
                            edge_key = (sk.id, event_id)
                            if edge_key not in existing_edges:
                                try:
                                    nested = session.begin_nested()
                                    self.ledger.add_edge(
                                        source_id=sk.id,
                                        target_id=event_id,
                                        relationship_type="temporal_context",
                                        weight=similarity,
                                        session=session
                                    )
                                    nested.commit()
                                    existing_edges.add(edge_key)
                                    new_edges_count += 1
                                except Exception as e:
                                    nested.rollback()
                                    logger.warning("Failed to add temporal edge %s->%s: %s", sk.id, event_id, e)

            self._save_watermark(self._TEMPORAL_WATERMARK_KEY, scan_start)
            self._last_temporal_scan = scan_start
        return new_edges_count

    def run_semantic_cooccurrence_scan(self, similarity_threshold: float = 0.7) -> int:
        """
        Scans for entities that are semantically similar.
        If two events are very similar, we infer a relationship between them.
        Only compares pairs where at least one event is newer than the last scan.
        """
        new_edges_count = 0
        scan_start = datetime.now(timezone.utc)
        events = self.semantic_memory.list_events(limit=50)
        
        if len(events) < 2:
            return 0

        with self.ledger.session_scope() as session:
            # Pre-load existing semantic_similarity edges for O(1) lookup.
            # Store both directions so (A,B) and (B,A) are treated as the same edge.
            existing_edges: set = set()
            for e in session.query(
                RelationalEdge.source_id, RelationalEdge.target_id
            ).filter_by(relationship_type="semantic_similarity").all():
                existing_edges.add((e.source_id, e.target_id))
                existing_edges.add((e.target_id, e.source_id))

            for i in range(len(events)):
                for j in range(i + 1, len(events)):
                    # Skip pairs where both events were already scanned
                    if self._last_cooccurrence_scan:
                        try:
                            ts_i = events[i].get('metadata', {}).get('timestamp')
                            ts_j = events[j].get('metadata', {}).get('timestamp')
                            if ts_i and ts_j:
                                t_i = datetime.fromisoformat(ts_i)
                                t_j = datetime.fromisoformat(ts_j)
                                t_i = t_i if t_i.tzinfo else t_i.replace(tzinfo=timezone.utc)
                                t_j = t_j if t_j.tzinfo else t_j.replace(tzinfo=timezone.utc)
                                if t_i < self._last_cooccurrence_scan and t_j < self._last_cooccurrence_scan:
                                    continue
                        except (ValueError, TypeError) as e:
                            logger.warning("Skipping cooccurrence pair due to bad timestamp: %s", e)
                            continue

                    e1, e2 = events[i], events[j]
                    try:
                        similarity = self.semantic_memory.get_similarity(e1['id'], e2['id'])
                    except Exception as e:
                        logger.warning("Failed to compute similarity for %s <-> %s: %s", e1['id'], e2['id'], e)
                        continue

                    if similarity >= similarity_threshold:
                        edge_key = (e1['id'], e2['id'])
                        if edge_key not in existing_edges:
                            try:
                                nested = session.begin_nested()
                                self.ledger.add_edge(
                                    source_id=e1['id'],
                                    target_id=e2['id'],
                                    relationship_type="semantic_similarity",
                                    weight=similarity,
                                    session=session
                                )
                                nested.commit()
                                existing_edges.add(edge_key)
                                new_edges_count += 1
                            except Exception as e:
                                nested.rollback()
                                logger.warning("Failed to add similarity edge %s->%s: %s", e1['id'], e2['id'], e)

            self._save_watermark(self._COOCCURRENCE_WATERMARK_KEY, scan_start)
            self._last_cooccurrence_scan = scan_start
        return new_edges_count

    def run_attribute_symmetry_scan(self) -> int:
        """
        Scans skills for attribute-level similarity using symmetry keywords
        and substring containment. Creates edges between related skills.

        Phase B: Attribute Symmetry
        Two skills are linked when they share a symmetry keyword or one name
        is a substring of the other.
        """
        new_edges_count = 0

        with self.ledger.session_scope() as session:
            skills = session.query(Skill).all()
            if len(skills) < 2:
                return 0

            # Pre-load existing attribute_symmetry edges for dedup
            existing_edges: set = set()
            for e in session.query(
                RelationalEdge.source_id, RelationalEdge.target_id
            ).filter_by(relationship_type="attribute_symmetry").all():
                existing_edges.add((e.source_id, e.target_id))
                existing_edges.add((e.target_id, e.source_id))

            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    s1, s2 = skills[i], skills[j]
                    edge_key = (s1.id, s2.id)
                    if edge_key in existing_edges:
                        continue

                    name1 = s1.name.lower()
                    name2 = s2.name.lower()

                    # Check substring containment
                    matched = name1 in name2 or name2 in name1

                    # Check symmetry keyword overlap
                    if not matched:
                        words1 = set(name1.split())
                        words2 = set(name2.split())
                        shared = (words1 | words2) & {kw.lower() for kw in self.symmetry_keywords}
                        matched = bool(words1 & shared and words2 & shared)

                    if matched:
                        try:
                            nested = session.begin_nested()
                            self.ledger.add_edge(
                                source_id=s1.id,
                                target_id=s2.id,
                                relationship_type="attribute_symmetry",
                                weight=0.8,
                                session=session,
                            )
                            nested.commit()
                            existing_edges.add(edge_key)
                            new_edges_count += 1
                        except Exception as e:
                            nested.rollback()
                            logger.warning("Failed to add symmetry edge %s->%s: %s", s1.id, s2.id, e)

        return new_edges_count

    def run_motif_detection_scan(self) -> int:
        """
        Scans for recurring structural patterns (motifs) in the relational graph.
        
        Phase C: The Weaver's Intelligence
        Identifies chains of relationships that appear with high frequency.
        """
        new_motifs_count = 0
        scan_start = datetime.now(timezone.utc)

        with self.ledger.session_scope() as session:
            # 1. Fetch all recent edges to analyze local graph structure
            edges = session.query(RelationalEdge).all()
            if len(edges) < 3:
                return 0

            # 2. Build an adjacency list for path traversal
            adj = {}
            for e in edges:
                if e.source_id not in adj:
                    adj[e.source_id] = []
                adj[e.source_id].append({
                    "target": e.target_id,
                    "type": e.relationship_type,
                    "weight": e.weight
                })

            # 3. Identify "Chains" (e.g., A -> B -> C)
            # We look for common paths of relationship types.
            # Example path: ["temporal_context", "semantic_similarity"]
            path_counts = {}

            for start_node in adj:
                for step1 in adj[start_node]:
                    target_b = step1["target"]
                    type1 = step1["type"]
                    
                    if target_b in adj:
                        for step2 in adj[target_b]:
                            type2 = step2["type"]
                            target_c = step2["target"]
                            
                            # We found a chain: start_node -> target_b -> target_c
                            # The pattern is (type1, type2)
                            pattern = (type1, type2)
                            path_counts[pattern] = path_counts.get(pattern, 0) + 1

            # 4. Promote high-frequency paths to Motifs
            # If a pattern appears more than 5 times, it's a structural motif.
            MOTIF_THRESHOLD = 5
            for pattern, count in path_counts.items():
                if count >= MOTIF_THRESHOLD:
                    pattern_str = " -> ".join(pattern)
                    # Check if we already know this motif
                    if not any(m['pattern'] == pattern_str for m in self.discovered_motifs):
                        new_motif = {
                            "pattern": pattern_str,
                            "frequency": count,
                            "discovered_at": datetime.now(timezone.utc).isoformat()
                        }
                        self.discovered_motifs.append(new_motif)
                        self._save_motifs(self.discovered_motifs)
                        new_motifs_count += 1
                        logger.info("Discovered new structural motif: %s", pattern_str)

            self._save_watermark(self._MOTIF_WATERMARK_KEY, scan_start)
            self._last_motif_scan = scan_start

        return new_motifs_count

    def prune(self) -> int:
        """Run edge pruning using the configured limits."""
        return self.ledger.prune_stale_edges(
            max_age_days=self._max_edge_age_days,
            min_weight=self._min_edge_weight,
            max_edges=self._max_edges,
        )

    def run_full_cycle(self, window_minutes: int = 60,
                       temporal_threshold: float = 0.6,
                       cooccurrence_threshold: float = 0.7) -> Dict[str, int]:
        """Run all synthesis scans followed by pruning. Returns per-phase counts."""
        results = {
            "temporal_edges": self.run_temporal_correlation_scan(window_minutes, temporal_threshold),
            "cooccurrence_edges": self.run_semantic_cooccurrence_scan(cooccurrence_threshold),
            "motifs": self.run_motif_detection_scan(),
            "pruned": self.prune(),
        }
        logger.info("Synthesis cycle complete: %s", results)
        return results
