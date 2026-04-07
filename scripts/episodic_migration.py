import json
import os
from datetime import datetime
from typing import List, Dict, Any
from domain.core.semantic_memory import SemanticMemory
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Event

class EpisodicMigrator:
    def __init__(self, 
                 sessions_dir: str = "/data/sessions",
                 semantic_engine_path: str = "/data/hermes_memory_engine/core/engine.py"):
        self.sessions_dir = sessions_dir
        # We'll import the engine components dynamically to avoid path issues
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from application.engine import MemoryEngine
        self.engine = MemoryEngine()

    def run_migration(self):
        print(f"Starting migration from {self.sessions_dir}...")
        
        session_files = [f for f in os.listdir(self.sessions_dir) if f.endswith('.json')]
        print(f"Found {len(session_files)} session files.")

        for filename in session_files:
            file_path = os.path.join(self.sessions_dir, filename)
            print(f"Processing {filename}...")
            
            try:
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                
                self._process_session(session_data)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")

        print("Migration complete.")

    def _process_session(self, session: Dict[str, Any]):
        """
        Analyte the session and identify meaningful events.
        In a real agentic loop, this would be a call to an LLM.
        For this script, I will simulate the 'reflection' process.
        """
        messages = session.get("messages", [])
        title = session.get("title", "Untitled Session")
        
        # SIMULATED REFLECTION LOGIC
        # In a real implementation, the agent would 'read' these messages 
        # and generate these events.
        
        discovered_events = []

        # 1. Detect Milestones (Simulated)
        # Example: If the title or content mentions a "merger" or "milestone"
        if "milestone" in title.lower() or "merge" in title.lower():
            discovered_events.append(Event(
                text=f"Milestone achieved in session: {title}",
                event_type="milestone",
                metadata={"session_id": session.get("session_id"), "title": title}
            ))

        # 2. Detect Preferences (Simulated)
        # Example: Look for phrases about "prefer", "like", "want"
        for msg in messages:
            content = msg.get("content", "").lower()
            if "prefer" in content or "i like" in content or "i want" in content:
                discovered_events.append(Event(
                    text=f"User preference expressed: {msg.get('content')[:100]}...",
                    event_type="preference",
                    metadata={"role": msg.get("role"), "session_id": session.get("session_id")}
                ))

        # 3. Detect Skills (Simulated)
        if "skill" in title.lower() or "how to" in title.lower():
            discovered_events.append(Event(
                text=f"New skill/knowledge discovered: {title}",
                event_type="skill",
                metadata={"session_id": session.get("session_id")}
            ))

        # Ingest the discovered events into the engine
        if discovered_events:
            print(f"  Found {len(discovered_events)} significant events. Ingesting...")
            # We use the engine's ingest_interaction, but since we are doing 
            # an automated batch, we pass the events directly.
            self.engine.ingest_interaction(
                user_text="Batch Migration from Session Logs",
                assistant_text=f"Reflecting on session: {title}",
                instructions=[{"event": e} for e in discovered_events]
            )

if __name__ == "__main__":
    # Set PYTHONPATH so we can import the local core modules
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    migrator = EpisodicMigrator()
    migrator.run_migration()
