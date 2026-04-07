import os
from typing import List, Dict, Any, Optional
from domain.core.semantic_memory import SemanticMemory
from domain.core.models import Event

# Note: In a real deployment, EventExtractor would call an LLM API.
# Here, I am designing the interface so that I (the agent) can 
# utilize it to automate my own memory updates.

import re

class EventExtractor:
    """
    Responsible for analyzing text and identifying meaningful events using heuristic patterns.
    In a production environment, this would be replaced by an LLM-driven extraction process.
    """
    def __init__(self):
        self.patterns = [
            {
                "type": "preference",
                "regex": r"(prefer|like|dislike|hate|want|don't like|love|interest in|fascinated by)\s+([^.!?]+)",
                "description": "Identifies user preferences and interests."
            },
            {
                "type": "milestone",
                "regex": r"(finished|completed|merged|achieved|accomplished|reached)\s+([^.!?]+)",
                "description": "Identifies significant achievements or completed tasks."
            },
            {
                "type": "skill",
                "regex": r"(learned|mastered|skilled at|know how to|become proficient in)\s+([^.!?]+)",
                "description": "Identifies new skill acquisitions."
            },
            {
                "type": "identity_marker",
                "regex": r"(my name is|i am|call me|identify as)\s+([^.!?]+)",
                "description": "Identifies identity markers and persona elements."
            }
        ]

    def extract_events(self, text: str) -> List[Event]:
        """
        Analyzes text against heuristic patterns to return a list of discovered Events.
        """
        events = []
        for pattern in self.patterns:
            matches = re.finditer(pattern["regex"], text, re.IGNORECASE)
            for match in matches:
                trigger = match.group(1).lower()
                subject = match.group(2).strip()
                
                metadata = {"trigger": trigger, "subject": subject}
                
                importance = 1.0
                if any(word in trigger for word in ["mastered", "achieved", "completed"]):
                    importance = 5.0
                elif any(word in trigger for word in ["love", "fascinated"]):
                    importance = 3.0

                events.append(Event(
                    text=f"Detected {pattern['type']}: {subject}",
                    event_type=pattern["type"],
                    metadata={"importance": importance, **metadata}
                ))
        return events

class MemoryEngine:
    """
    The main orchestrator for the Hermes Memory Engine.
    """
    def __init__(self,
                 semantic_dir: str = None,
                 structural_db_path: str = None):
        if semantic_dir is None:
            semantic_dir = os.environ.get("HERMES_SEMANTIC_DIR", "/data/hermes_memory_engine/semantic/chroma_db")
        if structural_db_path is None:
            structural_db_path = os.environ.get("HERMES_STRUCTURAL_DB", "/data/hermes_memory_engine/structural/structure.db")
        self.semantic_memory = SemanticMemory(semantic_dir)
        self.extractor = EventExtractor()
        from domain.supporting.ledger import StructuralLedger
        self.ledger = StructuralLedger(structural_db_path)

    def ingest_interaction(self, user_text: str, assistant_text: str, instructions: Optional[List[Dict[str, Any]]] = None):
        """
        Processes an interaction and stores discovered events.
        Instructions can include a list of dicts with 'event' (Event object) and optional 'structural_id'.
        """
        if instructions:
            for instr in instructions:
                event = instr.get('event')
                structural_id = instr.get('structural_id')
                
                if event:
                    metadata = event.to_dict()
                    if structural_id:
                        metadata['structural_id'] = structural_id
                    
                    self.semantic_memory.add_event(
                        text=event.text,
                        metadata=metadata
                    )

        # Automated detection step
        all_text = f"User: {user_text}\nAssistant: {assistant_text}"
        discovered_events = self.extractor.extract_events(all_text)
        
        for event in discovered_events:
            # Avoid duplicate ingestion if the event is already in the instructions
            if instructions and any(i.get('event') and i.get('event').text == event.text for i in instructions):
                continue
                
            self.semantic_memory.add_event(
                text=event.text,
                metadata=event.to_dict()
            )

    def query(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        semantic_results = self.semantic_memory.query_context(query_text, n_results=n_results)
        enriched_results = []
        for res in semantic_results:
            enriched_item = res.copy()
            structural_id = res['metadata'].get('structural_id')
            if structural_id:
                entity_context = {}
                from domain.core.models import Project, Milestone, Skill, IdentityMarker
                session = self.ledger.Session()
                try:
                    if structural_id.startswith("proj_"):
                        project = session.query(Project).filter_by(id=structural_id).first()
                        if project:
                            entity_context = {
                                "type": "project",
                                "id": project.id,
                                "name": project.name,
                                "repository_url": project.repository_url,
                                "status": project.status,
                                "milestones": [{"id": m.id, "title": m.title} for m in project.milestones]
                            }
                            # Neighbor Expansion: Add connected skills
                            from domain.core.models import RelationalEdge, Skill
                            edges = session.query(RelationalEdge).filter_by(source_id=project.id).all()
                            connected_skill_ids = [e.target_id for e in edges if e.relationship_type == "uses_skill"]
                            if connected_skill_ids:
                                skills = session.query(Skill).filter(Skill.id.in_(connected_skill_ids)).all()
                                entity_context["skills"] = [{"id": s.id, "name": s.name} for s in skills]
                    elif structural_id.startswith("ms_"):
                        milestone = session.query(Milestone).filter_by(id=structural_id).first()
                        if milestone:
                            entity_context = {
                                "type": "milestone",
                                "id": milestone.id,
                                "title": milestone.title,
                                "description": milestone.description,
                                "project_id": milestone.project_id
                            }
                            # Neighbor Expansion: Add parent project
                            if milestone.project_id:
                                project = session.query(Project).filter_by(id=milestone.project_id).first()
                                if project:
                                    entity_context["parent_project"] = {"id": project.id, "name": project.name}
                    elif structural_id.startswith("sk_"):
                        skill = session.query(Skill).filter_by(id=structural_id).first()
                        if skill:
                            entity_context = {
                                "type": "skill",
                                "id": skill.id,
                                "name": skill.name,
                                "description": skill.description,
                                "proficiency_level": skill.proficiency_level
                            }
                            # Neighbor Expansion: Add projects that use this skill
                            from domain.core.models import RelationalEdge, Project
                            edges = session.query(RelationalEdge).filter_by(target_id=skill.id, relationship_type="uses_skill").all()
                            if edges:
                                project_ids = [e.source_id for e in edges]
                                projects = session.query(Project).filter(Project.id.in_(project_ids)).all()
                                entity_context["used_in_projects"] = [{"id": p.id, "name": p.name} for p in projects]
                    elif structural_id.startswith("id_"):
                        marker = session.query(IdentityMarker).filter_by(id=structural_id).first()
                        if marker:
                            entity_context = {
                                "type": "identity_marker",
                                "id": marker.id,
                                "key": marker.key,
                                "value": marker.value,
                                "confidence_score": marker.confidence_score
                            }
                except Exception as e:
                    entity_context = {"error": str(e)}
                finally:
                    session.close()
                enriched_item['structural_context'] = entity_context
            enriched_results.append(enriched_item)
        return enriched_results
