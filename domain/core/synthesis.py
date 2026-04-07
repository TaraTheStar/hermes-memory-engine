import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from domain.core.semantic_memory import SemanticMemory
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Project, Milestone, Skill, IdentityMarker, RelationalEdge

class SynthesisEngine:
    def __init__(self, semantic_dir: str, structural_db_path: str):
        self.semantic_memory = SemanticMemory(semantic_dir)
        self.ledger = StructuralLedger(structural_db_path)

    def run_temporal_correlation_scan(self, window_minutes: int = 60) -> int:
        """
        Scans for entities that appear close together in time.
        If a semantic event occurs near a structural entity, we infer a relationship.
        """
        new_edges_count = 0
        window_delta = timedelta(minutes=window_minutes)
        
        session = self.ledger.Session()
        try:
            milestones = session.query(Milestone).all()
            skills = session.query(Skill).all()
            events = self.semantic_memory.list_events(limit=100)
            
            for event in events:
                event_time_raw = datetime.fromisoformat(event['metadata']['timestamp'])
                # Normalize to UTC-aware datetime for consistent comparison
                event_time = event_time_raw if event_time_raw.tzinfo else event_time_raw.replace(tzinfo=timezone.utc)
                event_text = event['text'].lower()
                
                # Check against milestones
                for ms in milestones:
                    ms_time = ms.timestamp if ms.timestamp.tzinfo else ms.timestamp.replace(tzinfo=timezone.utc)
                    if abs((event_time - ms_time).total_seconds()) <= window_delta.total_seconds():
                        if ms.title.lower() in event_text or ms.description.lower() in event_text:
                            existing = session.query(RelationalEdge).filter_by(
                                source_id=ms.id, 
                                target_id=event['id'], 
                                relationship_type="temporal_context"
                            ).first()
                            
                            if not existing:
                                self.ledger.add_edge(
                                    source_id=ms.id,
                                    target_id=event['id'],
                                    relationship_type="temporal_context",
                                    weight=0.5
                                )
                                new_edges_count += 1
                
                # Check against skills
                for sk in skills:
                    sk_time = sk.last_used if sk.last_used else datetime.now(timezone.utc)
                    sk_time = sk_time if sk_time.tzinfo else sk_time.replace(tzinfo=timezone.utc)
                    if abs((event_time - sk_time).total_seconds()) <= window_delta.total_seconds():
                        if sk.name.lower() in event_text:
                            existing = session.query(RelationalEdge).filter_by(
                                source_id=sk.id, 
                                target_id=event['id'], 
                                relationship_type="temporal_context"
                            ).first()
                            
                            if not existing:
                                self.ledger.add_edge(
                                    source_id=sk.id,
                                    target_id=event['id'],
                                    relationship_type="temporal_context",
                                    weight=0.5
                                )
                                new_edges_count += 1
        finally:
            session.close()
            
        return new_edges_count

    def run_semantic_cooccurrence_scan(self, similarity_threshold: float = 0.7) -> int:
        """
        Scans for entities that are semantically similar.
        If two events are very similar, we infer a relationship between them.
        """
        new_edges_count = 0
        events = self.semantic_memory.list_events(limit=50)
        
        if len(events) < 2:
            return 0

        session = self.ledger.Session()
        try:
            for i in range(len(events)):
                for j in range(i + 1, len(events)):
                    e1, e2 = events[i], events[j]
                    similarity = self.semantic_memory.get_similarity(e1['id'], e2['id'])
                    
                    if similarity >= similarity_threshold:
                        existing = session.query(RelationalEdge).filter_by(
                            source_id=e1['id'],
                            target_id=e2['id'],
                            relationship_type="semantic_similarity"
                        ).first()
                        
                        if not existing:
                            self.ledger.add_edge(
                                source_id=e1['id'],
                                target_id=e2['id'],
                                relationship_type="semantic_similarity",
                                weight=similarity
                            )
                            new_edges_count += 1
        finally:
            session.close()
            
        return new_edges_count

    def run_attribute_symmetry_scan(self) -> int:
        """
        Scans for entities that share similar metadata attributes.
        """
        new_edges_count = 0
        session = self.ledger.Session()
        try:
            skills = session.query(Skill).all()
            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    s1, s2 = skills[i], skills[j]
                    name1, name2 = s1.name.lower(), s2.name.lower()
                    words1 = set(re.findall(r'\w+', name1))
                    words2 = set(re.findall(r'\w+', name2))
                    common_words = words1.intersection(words2)
                    
                    if common_words.intersection({'python', 'javascript', 'rust', 'coding'}) or \
                       name1 in name2 or name2 in name1 or \
                       (len(name1) >= 4 and len(name2) >= 4 and name1[:4] == name2[:4]):
                        existing = session.query(RelationalEdge).filter_by(
                            source_id=s1.id,
                            target_id=s2.id,
                            relationship_type="attribute_symmetry"
                        ).first()
                        
                        if not existing:
                            self.ledger.add_edge(
                                source_id=s1.id,
                                target_id=s2.id,
                                relationship_type="attribute_symmetry",
                                weight=0.8
                            )
                            new_edges_count += 1
        finally:
            session.close()
            
        return new_edges_count
