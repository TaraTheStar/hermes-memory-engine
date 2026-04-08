import os
from typing import List, Dict, Any, Optional
from domain.core.semantic_memory import SemanticMemory
from domain.core.models import Event, Project, Milestone, Skill, IdentityMarker, RelationalEdge
from infrastructure.paths import default_semantic_dir, default_structural_db

# Note: In a real deployment, EventExtractor would call an LLM API.
# Here, I am designing the interface so that I (the agent) can 
# utilize it to automate my own memory updates.

import re

class EventExtractor:
    """
    Responsible for analyzing text and identifying meaningful events using heuristic patterns.
    In a production environment, this would be replaced by an LLM-driven extraction process.
    """
    # Max characters to capture as the subject of an extracted event.
    _SUBJECT_PATTERN = r"([^.!?\n]{1,100})"

    def __init__(self):
        subj = self._SUBJECT_PATTERN
        self.patterns = [
            {
                "type": "preference",
                "regex": rf"(prefer|like|dislike|hate|want|don't like|love|interest in|fascinated by)\s+{subj}",
                "description": "Identifies user preferences and interests."
            },
            {
                "type": "milestone",
                "regex": rf"(finished|completed|merged|achieved|accomplished|reached)\s+{subj}",
                "description": "Identifies significant achievements or completed tasks."
            },
            {
                "type": "skill",
                "regex": rf"(learned|mastered|skilled at|know how to|become proficient in)\s+{subj}",
                "description": "Identifies new skill acquisitions."
            },
            {
                "type": "identity_marker",
                "regex": rf"(my name is|i am|call me|identify as)\s+{subj}",
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
            semantic_dir = default_semantic_dir()
        if structural_db_path is None:
            structural_db_path = default_structural_db()
        self.semantic_memory = SemanticMemory(semantic_dir)
        self.extractor = EventExtractor()
        from domain.supporting.ledger import StructuralLedger
        self.ledger = StructuralLedger(structural_db_path)

    _MAX_INPUT_LENGTH = 50_000

    def ingest_interaction(self, user_text: str, assistant_text: str, instructions: Optional[List[Dict[str, Any]]] = None):
        """
        Processes an interaction and stores discovered events.
        Instructions can include a list of dicts with 'event' (Event object) and optional 'structural_id'.
        """
        user_text = (user_text or "")[:self._MAX_INPUT_LENGTH]
        assistant_text = (assistant_text or "")[:self._MAX_INPUT_LENGTH]
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

    # Maps ID prefix to the method that resolves structural context for that entity type.
    _ENTITY_RESOLVERS = {
        "proj_": "_resolve_project",
        "ms_": "_resolve_milestone",
        "sk_": "_resolve_skill",
        "id_": "_resolve_identity_marker",
    }

    def query(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        semantic_results = self.semantic_memory.query(query_text, n_results=n_results)
        enriched_results = []

        with self.ledger.session_scope() as session:
            for res in semantic_results:
                enriched_item = res.copy()
                structural_id = res['metadata'].get('structural_id')
                if structural_id:
                    try:
                        entity_context = self._resolve_entity(session, structural_id)
                    except Exception as e:
                        entity_context = {"error": str(e)}
                    enriched_item['structural_context'] = entity_context
                enriched_results.append(enriched_item)

        return enriched_results

    def _resolve_entity(self, session, structural_id: str) -> Dict[str, Any]:
        for prefix, method_name in self._ENTITY_RESOLVERS.items():
            if structural_id.startswith(prefix):
                return getattr(self, method_name)(session, structural_id)
        return {}

    @staticmethod
    def _resolve_project(session, structural_id: str) -> Dict[str, Any]:
        project = session.query(Project).filter_by(id=structural_id).first()
        if not project:
            return {}
        context = {
            "type": "project",
            "id": project.id,
            "name": project.name,
            "repository_url": project.repository_url,
            "status": project.status,
            "milestones": [{"id": m.id, "title": m.title} for m in project.milestones]
        }
        edges = session.query(RelationalEdge).filter_by(source_id=project.id).all()
        connected_skill_ids = [e.target_id for e in edges if e.relationship_type == "uses_skill"]
        if connected_skill_ids:
            skills = session.query(Skill).filter(Skill.id.in_(connected_skill_ids)).all()
            context["skills"] = [{"id": s.id, "name": s.name} for s in skills]
        return context

    @staticmethod
    def _resolve_milestone(session, structural_id: str) -> Dict[str, Any]:
        milestone = session.query(Milestone).filter_by(id=structural_id).first()
        if not milestone:
            return {}
        context = {
            "type": "milestone",
            "id": milestone.id,
            "title": milestone.title,
            "description": milestone.description,
            "project_id": milestone.project_id
        }
        if milestone.project_id:
            project = session.query(Project).filter_by(id=milestone.project_id).first()
            if project:
                context["parent_project"] = {"id": project.id, "name": project.name}
        return context

    @staticmethod
    def _resolve_skill(session, structural_id: str) -> Dict[str, Any]:
        skill = session.query(Skill).filter_by(id=structural_id).first()
        if not skill:
            return {}
        context = {
            "type": "skill",
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "proficiency_level": skill.proficiency_level
        }
        edges = session.query(RelationalEdge).filter_by(target_id=skill.id, relationship_type="uses_skill").all()
        if edges:
            project_ids = [e.source_id for e in edges]
            projects = session.query(Project).filter(Project.id.in_(project_ids)).all()
            context["used_in_projects"] = [{"id": p.id, "name": p.name} for p in projects]
        return context

    @staticmethod
    def _resolve_identity_marker(session, structural_id: str) -> Dict[str, Any]:
        marker = session.query(IdentityMarker).filter_by(id=structural_id).first()
        if not marker:
            return {}
        return {
            "type": "identity_marker",
            "id": marker.id,
            "key": marker.key,
            "value": marker.value,
            "confidence_score": marker.confidence_score
        }
