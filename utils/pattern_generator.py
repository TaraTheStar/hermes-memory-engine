import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple

# Add the repository to the path so imports work
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from domain.core.models import Milestone, Skill, RelationalEdge
from domain.supporting.ledger import StructuralLedger
from domain.core.semantic_memory import SemanticMemory

class PatternGenerator:
    """
    Generates structured 'stories' of events and edges to test the 
    SynthesisEngine's ability to detect motifs.
    """

    def __init__(self, ledger: StructuralLedger, semantic_memory: SemanticMemory):
        self.ledger = ledger
        self.semantic_memory = semantic_memory

    def create_story(self, template_name: str, noise_level: float = 0.0) -> str:
        """
        Generates a story based on a template and returns a summary.
        
        Args:
            template_name: The name of the motif template to use.
            noise_level: 0.0 to 1.0. Higher values add more random, disconnected events.
        """
        print(f"\n[PatternGenerator] Generating story: {template_name} (Noise: {noise_level})")
        
        if template_name == "LEARNING_LOOP":
            self._generate_learning_loop()
        elif template_name == "CONFLICT_RESOLUTION":
            self._generate_conflict_resolution()
        elif template_name == "DEEP_DIVE":
            self._generate_deep_dive()
        else:
            raise ValueError(f"Unknown template: {template_name}")

        if noise_level > 0:
            self._inject_noise(noise_level)
            
        return f"Story '{template_name}' generated successfully."

    def _generate_learning_loop(self):
        """
        Pattern: Milestone(Inquiry) --[temporal]--> Event(Research) --[semantic]--> Skill(Discovery)
        """
        with self.ledger.session_scope() as session:
            # 1. Create Milestone
            m_id = str(uuid.uuid4())
            ms = Milestone(
                id=m_id,
                title="The Great Inquiry",
                description="A period of intense investigation into unknown patterns.",
                timestamp=datetime.now(timezone.utc) - timedelta(days=1)
            )
            session.add(ms)

            # 2. Create Research Event
            e_id = f"evt_{uuid.uuid4().hex}"
            e_text = "The research process revealed deep connections between disparate nodes in the network."
            # We manually add to semantic memory to ensure we have the ID for edge creation
            self.semantic_memory.add_event(
                text=e_text,
                metadata={"timestamp": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()},
                structural_id=m_id
            )
            
            # Add the temporal edge
            self.ledger.add_edge(
                source_id=m_id,
                target_id=e_id,
                relationship_type="temporal_context",
                weight=1.0,
                session=session
            )

            # 3. Create Skill (Discovery)
            s_id = str(uuid.uuid4())
            skill = Skill(
                id=s_id,
                name="Pattern Synthesis",
                description="The ability to weave disparate semantic signals into coherent structures.",
                last_used=datetime.now(timezone.utc)
            )
            session.add(skill)

            # 4. Create the Semantic Edge (The Weaver's target)
            # Link Research Event to the Skill
            self.ledger.add_edge(
                source_id=e_id,
                target_id=s_id,
                relationship_type="semantic_similarity",
                weight=0.9,
                session=session
            )
            
            print(f"  [+] Injected Learning Loop: {m_id} -> {e_id} -> {s_id}")

    def _generate_conflict_resolution(self):
        """
        Pattern: Event(Disagreement) --[temporal]--> Event(Mediation) --[semantic]--> Milestone(Resolution)
        """
        with self.ledger.session_scope() as session:
            # 1. Create Resolution Milestone
            m_id = str(uuid.uuid4())
            ms = Milestone(
                id=m_id,
                title="Consensus Reached",
                description="The disparate views were synthesized into a unified perspective.",
                timestamp=datetime.now(timezone.utc)
            )
            session.add(ms)

            # 2. Create Mediation Event
            e_med_id = f"evt_{uuid.uuid4().hex}"
            e_med_text = "A mediation session was held to reconcile the conflicting viewpoints."
            self.semantic_memory.add_event(
                text=e_med_text,
                metadata={"timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()}
            )

            # 3. Create Disagreement Event
            e_dis_id = f"evt_{uuid.uuid4().hex}"
            e_dis_text = "Conflicting signals detected in the consensus layer."
            self.semantic_memory.add_event(
                text=e_dis_text,
                metadata={"timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()}
            )

            # 4. Connect the chain
            # Disagreement --[temporal]--> Mediation
            self.ledger.add_edge(
                source_id=e_dis_id,
                target_id=e_med_id,
                relationship_type="temporal_context",
                weight=0.8,
                session=session
            )
            # Mediation --[semantic]--> Resolution
            self.ledger.add_edge(
                source_id=e_med_id,
                target_id=m_id,
                relationship_type="semantic_similarity",
                weight=0.9,
                session=session
            )

            print(f"  [+] Injected Conflict Resolution: {e_dis_id} -> {e_med_id} -> {m_id}")

    def _generate_deep_dive(self):
        """
        Pattern: Skill(Foundation) --[semantic]--> Event(Exploration) --[temporal]--> Milestone(Insight)
        """
        with self.ledger.session_scope() as session:
            # 1. Create Foundation Skill
            s_id = str(uuid.uuid4())
            skill = Skill(
                id=s_id,
                name="Core Logic",
                description="Foundational principles of the system.",
                last_used=datetime.now(timezone.utc)
            )
            session.add(skill)

            # 2. Create Exploration Event
            e_id = f"evt_{uuid.uuid4().hex}"
            e_text = "Deep exploration of the core logic revealed underlying symmetries."
            self.semantic_memory.add_event(
                text=e_text,
                metadata={"timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
            )

            # Link Skill to Event (Semantic)
            self.ledger.add_edge(
                source_id=s_id,
                target_id=e_id,
                relationship_type="semantic_similarity",
                weight=0.8,
                session=session
            )

            # 3. Create Insight Milestone
            m_id = str(uuid.uuid4())
            ms = Milestone(
                id=m_id,
                title="The Great Insight",
                description="A breakthrough in understanding the system architecture.",
                timestamp=datetime.now(timezone.utc)
            )
            session.add(ms)

            # Link Event to Milestone (Temporal)
            self.ledger.add_edge(
                source_id=e_id,
                target_id=m_id,
                relationship_type="temporal_context",
                weight=0.9,
                session=session
            )
            
            print(f"  [+] Injected Deep Dive: {s_id} -> {e_id} -> {m_id}")

    def _inject_noise(self, level: float):
        """Injects random, disconnected events to test robustness."""
        num_noise_events = int(level * 50)
        print(f"[PatternGenerator] Injecting {num_noise_events} noise events...")
        for _ in range(num_noise_events):
            text = f"Random noise message {uuid.uuid4().hex[:8]}"
            self.semantic_memory.add_event(
                text=text,
                metadata={"timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1000))).isoformat()}
            )

if __name__ == "__main__":
    # Example usage
    import tempfile
    import shutil
    
    tmp = tempfile.mkdtemp()
    try:
        l = StructuralLedger(os.path.join(tmp, "test.db"))
        sm = SemanticMemory(tmp)
        pg = PatternGenerator(l, sm)
        print(pg.create_story("LEARNING_LOOP", noise_level=0.1))
    finally:
        shutil.rmtree(tmp)
