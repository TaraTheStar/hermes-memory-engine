import os
import shutil
import pytest

from application.engine import MemoryEngine
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Event


@pytest.fixture(scope="module")
def test_paths():
    db = "/tmp/hermes_test_structure.db"
    semantic = "/tmp/hermes_test_semantic"

    if os.path.exists(db):
        os.remove(db)
    if os.path.exists(semantic):
        shutil.rmtree(semantic)
    os.makedirs(semantic)

    return db, semantic


@pytest.fixture
def engine(test_paths):
    db, semantic = test_paths
    return MemoryEngine(semantic_dir=semantic, structural_db_path=db)


@pytest.fixture
def ledger(test_paths):
    db, _ = test_paths
    return StructuralLedger(db)


def test_bridge_enrichment(engine, ledger):
    """Test that a semantic query returns enriched structural context for a linked entity."""
    proj_id = ledger.add_project("Test Project", "https://test.com")
    ms_id = ledger.add_milestone("Test Milestone", "Testing the bridge", project_id=proj_id)

    engine.semantic_memory.add_event(
        text="This is a test event linked to the milestone.",
        metadata={"type": "test", "structural_id": ms_id},
    )

    results = engine.query("test event")

    assert len(results) == 1, "Should find exactly one result."
    assert "structural_context" in results[0], "Result should be enriched with structural context."

    context = results[0]["structural_context"]
    assert context["type"] == "milestone"
    assert context["id"] == ms_id
    assert context["title"] == "Test Milestone"
    assert context["project_id"] == proj_id


def test_ingest_with_instructions(engine, ledger):
    """Test that ingest_interaction correctly handles instructions with structural IDs."""
    proj_id = ledger.add_project("Linkage Test Project")
    ms_id = ledger.add_milestone("Linkage Test Milestone", "Testing the new linkage protocol", project_id=proj_id)

    test_event = Event("This event is explicitly linked to a milestone.", "test_event", {"importance": "high"})
    instructions = [{"event": test_event, "structural_id": ms_id}]

    engine.ingest_interaction("User: I am testing linkage.", "Tara: I am recording it.", instructions=instructions)

    results = engine.query("test event")
    assert len(results) >= 1

    found_enriched = any(
        res.get("structural_context", {}).get("id") == ms_id for res in results
    )
    assert found_enriched, f"Expected to find enriched result for {ms_id} in {results}"


def test_unlinked_event(engine):
    """Test that an unlinked semantic event does not crash the engine."""
    engine.semantic_memory.add_event(
        text="Just a random unlinked event.",
        metadata={"type": "noise"},
    )

    results = engine.query("random unlinked")
    assert len(results) >= 1
