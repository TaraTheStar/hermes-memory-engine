import unittest
import os
import sys

# Add the repo root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from application.engine import MemoryEngine
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Project, Milestone, Skill, IdentityMarker, Event

class TestStructuralBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a dedicated test database to avoid corrupting real memory
        cls.test_db = "/tmp/hermes_test_structure.db"
        cls.test_semantic_dir = "/tmp/hermes_test_semantic"
        
        # Clean up previous runs
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        if os.path.exists(cls.test_semantic_dir):
            import shutil
            shutil.rmtree(cls.test_semantic_dir)
        os.makedirs(cls.test_semantic_dir)

    def setUp(self):
        self.engine = MemoryEngine(
            semantic_dir=self.test_semantic_dir,
            structural_db_path=self.test_db
        )
        self.ledger = StructuralLedger(self.test_db)

    def test_bridge_enrichment(self):
        """Test that a semantic query returns enriched structural context for a linked entity."""
        # 1. Setup structural data
        proj_id = self.ledger.add_project("Test Project", "https://test.com")
        ms_id = self.ledger.add_milestone("Test Milestone", "Testing the bridge", project_id=proj_id)
        
        # 2. Setup semantic data with a link
        # We use the structural_id in the metadata to test the bridge
        self.engine.semantic_memory.add_event(
            text="This is a test event linked to the milestone.",
            metadata={"type": "test", "structural_id": ms_id}
        )
        
        # 3. Query
        results = self.engine.query("test event")
        
        # 4. Assertions
        self.assertEqual(len(results), 1, "Should find exactly one result.")
        self.assertIn('structural_context', results[0], "Result should be enriched with structural context.")
        
        context = results[0]['structural_context']
        self.assertEqual(context['type'], 'milestone')
        self.assertEqual(context['id'], ms_id)
        self.assertEqual(context['title'], "Test Milestone")
        self.assertEqual(context['project_id'], proj_id)

    def test_ingest_with_instructions(self):
        """Test that ingest_interaction correctly handles instructions with structural IDs."""
        # 1. Setup structural data
        proj_id = self.ledger.add_project("Linkage Test Project")
        ms_id = self.ledger.add_milestone("Linkage Test Milestone", "Testing the new linkage protocol", project_id=proj_id)
        
        # 2. Prepare instruction with a link
        test_event = Event("This event is explicitly linked to a milestone.", "test_event", {"importance": "high"})
        instructions = [
            {
                "event": test_event,
                "structural_id": ms_id
            }
        ]
        
        # 3. Ingest
        self.engine.ingest_interaction("User: I am testing linkage.", "Tara: I am recording it.", instructions=instructions)
        
        # 4. Query and verify enrichment
        results = self.engine.query("test event")
        self.assertGreaterEqual(len(results), 1)
        
        # Check that at least one result is our enriched target
        found_enriched = False
        for res in results:
            if res.get('structural_context') and res['structural_context'].get('id') == ms_id:
                found_enriched = True
                break
        
        self.assertTrue(found_enriched, f"Expected to find enriched result for {ms_id} in {results}")

    def test_unlinked_event(self):
        """Test that an unlinked semantic event does not crash the engine."""
        self.engine.semantic_memory.add_event(
            text="Just a random unlinked event.",
            metadata={"type": "noise"}
        )
        
        results = self.engine.query("random unlinked")
        self.assertGreaterEqual(len(results), 1)

if __name__ == '__main__':
    unittest.main()
