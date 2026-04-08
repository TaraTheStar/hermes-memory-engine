import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from domain.core.semantic_memory import SemanticMemory
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Project, Milestone, Skill, IdentityMarker, RelationalEdge

logger = logging.getLogger(__name__)

DEFAULT_SYMMETRY_KEYWORDS: Set[str] = {'python', 'javascript', 'rust', 'coding'}

class SynthesisEngine:
    def __init__(self, semantic_dir: str, structural_db_path_or_ledger,
                 symmetry_keywords: Optional[Set[str]] = None):
        self.semantic_memory = SemanticMemory(semantic_dir)
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        self.symmetry_keywords = symmetry_keywords if symmetry_keywords is not None else DEFAULT_SYMMETRY_KEYWORDS
        # High-water marks for incremental scanning (per scan type)
        self._last_temporal_scan: Optional[datetime] = None
        self._last_cooccurrence_scan: Optional[datetime] = None
 
    def run_temporal_correlation_scan(self, window_minutes: int = 60) -> int:
        """
        Scans for entities that appear close together in time.
        If a semantic event occurs near a structural entity, we infer a relationship.
        Only processes events newer than the last scan (incremental).
        """
        new_edges_count = 0
        window_delta = timedelta(minutes=window_minutes)

        scan_start = datetime.now(timezone.utc)

        with self.ledger.session_scope() as session:
            milestones = session.query(Milestone).all()
            skills = session.query(Skill).all()
            events = self.semantic_memory.list_events(limit=100)

            # Pre-load existing temporal_context edges into a set for O(1) lookup.
            # Store both directions so (A,B) and (B,A) are treated as the same edge.
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
                # Normalize to UTC-aware datetime for consistent comparison
                event_time = event_time_raw if event_time_raw.tzinfo else event_time_raw.replace(tzinfo=timezone.utc)

                # Skip events already processed in a previous scan
                if self._last_temporal_scan and event_time <= self._last_temporal_scan:
                    continue
                event_text = event.get('text', '').lower()

                # Check against milestones
                for ms in milestones:
                    ms_time = ms.timestamp if ms.timestamp.tzinfo else ms.timestamp.replace(tzinfo=timezone.utc)
                    if abs((event_time - ms_time).total_seconds()) <= window_delta.total_seconds():
                        if ms.title.lower() in event_text or (ms.description and ms.description.lower() in event_text):
                            edge_key = (ms.id, event['id'])
                            if edge_key not in existing_edges:
                                self.ledger.add_edge(
                                    source_id=ms.id,
                                    target_id=event['id'],
                                    relationship_type="temporal_context",
                                    weight=0.5,
                                    session=session
                                )
                                existing_edges.add(edge_key)
                                new_edges_count += 1

                # Check against skills
                for sk in skills:
                    if sk.last_used is None:
                        continue  # Skip skills that have never been used
                    sk_time = sk.last_used
                    sk_time = sk_time if sk_time.tzinfo else sk_time.replace(tzinfo=timezone.utc)
                    if abs((event_time - sk_time).total_seconds()) <= window_delta.total_seconds():
                        if sk.name.lower() in event_text:
                            edge_key = (sk.id, event['id'])
                            if edge_key not in existing_edges:
                                self.ledger.add_edge(
                                    source_id=sk.id,
                                    target_id=event['id'],
                                    relationship_type="temporal_context",
                                    weight=0.5,
                                    session=session
                                )
                                existing_edges.add(edge_key)
                                new_edges_count += 1

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
                                if t_i <= self._last_cooccurrence_scan and t_j <= self._last_cooccurrence_scan:
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
                            self.ledger.add_edge(
                                source_id=e1['id'],
                                target_id=e2['id'],
                                relationship_type="semantic_similarity",
                                weight=similarity,
                                session=session
                            )
                            existing_edges.add(edge_key)
                            new_edges_count += 1

        self._last_cooccurrence_scan = scan_start
        return new_edges_count

    def run_attribute_symmetry_scan(self) -> int:
        """
        Scans for entities that share similar metadata attributes.
        """
        new_edges_count = 0
        with self.ledger.session_scope() as session:
            skills = session.query(Skill).all()

            # Pre-load existing attribute_symmetry edges for O(1) lookup.
            # Store both directions so (A,B) and (B,A) are treated as the same edge.
            existing_edges: set = set()
            for e in session.query(
                RelationalEdge.source_id, RelationalEdge.target_id
            ).filter_by(relationship_type="attribute_symmetry").all():
                existing_edges.add((e.source_id, e.target_id))
                existing_edges.add((e.target_id, e.source_id))

            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    s1, s2 = skills[i], skills[j]
                    name1, name2 = s1.name.lower(), s2.name.lower()
                    words1 = set(re.findall(r'\w+', name1))
                    words2 = set(re.findall(r'\w+', name2))
                    common_words = words1.intersection(words2)

                    if common_words.intersection(self.symmetry_keywords) or \
                       name1 in name2 or name2 in name1:
                        edge_key = (s1.id, s2.id)
                        if edge_key not in existing_edges:
                            self.ledger.add_edge(
                                source_id=s1.id,
                                target_id=s2.id,
                                relationship_type="attribute_symmetry",
                                weight=0.8,
                                session=session
                            )
                            existing_edges.add(edge_key)
                            new_edges_count += 1

        return new_edges_count
