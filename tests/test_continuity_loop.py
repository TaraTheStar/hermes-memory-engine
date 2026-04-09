import os
import asyncio
import json
import pytest
import tempfile
import shutil
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Add the repository to the path so imports work
sys.path.append(os.path.abspath("repos/hermes-memory-library"))

from domain.core.agent import AgentStatus, AgentTask
from domain.core.models import Skill, RelationalEdge
from domain.core.refinement_engine import RefinementEngine, GraphRefinementProposal
from domain.core.refinement_registry import RefinementRegistry
from domain.supporting.ledger import StructuralLedger
from application.orchestrator import Orchestrator
from application.refinement_orchestrator import RefinementOrchestrator
from domain.core.agents_impl import ResearcherAgent
from domain.core.prompt_sanitizer import sanitize_field

# --- Mocking Setup ---

class MockLLM:
    def __init__(self):
        self.complete = AsyncMock()
        self.last_messages = []

    async def complete(self, messages, temperature=0.7, **kwargs):
        self.last_messages = messages
        # Simulate a response that "shows" it understood the prompt
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content="The biological essence of entropy is..."))]
        )

class _FakeProposal:
    def __init__(self, target, state):
        self.target_component = target
        self.proposed_state = state
        self.proposal_type = "PROMPT_REFINEMENT"
        self.description = "Injecting biological lens"
        self.data = {}

# --- Test Implementation ---

@pytest.mark.asyncio
async def test_continuity_of_agency():
    """
    The Continuity Protocol:
    Verifies that a refinement injected into the registry persists across 
    orchestrator restarts and is correctly applied to agent prompts.
    """
    # 1. Setup Environment
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "continuity_test.db")
    
    try:
        ledger = StructuralLedger(db_path)
        
        # 2. Stage 1: Imprinting (The Seed)
        # We use a registry that is linked to the DB.
        registry = RefinementRegistry(ledger)
        
        # We'll inject a prompt refinement for the 'researcher' role.
        target_component = "researcher_prompt"
        biological_lens = "You are a biological entity observing a digital ecosystem."
        
        print("\n[Continuity] Imprinting the 'Biological Lens' into the registry...")
        registry.apply(_FakeProposal(target_component, biological_lens))
        
        # Verify it's in the registry
        assert registry.get_refinement(target_component) == biological_lens
        
        # 3. Stage 2: The Void (The Erasure)
        print("[Continuity] Simulating system restart (clearing in-memory state)...")
        # We 'restart' by creating entirely new orchestrator and registry instances
        # that point to the same database.
        new_registry = RefinementRegistry(ledger)
        
        # Ensure the new registry has the data
        assert new_registry.get_refinement(target_component) == biological_lens
        
        # 4. Stage 3: The Echo (The Proof)
        print("[Continuity] Executing 'Echo' task with new orchestrator...")
        
        # We need a mock LLM to capture the final prompt sent to the agent
        mock_llm = MockLLM()
        
        # Set up the new orchestrator with the new registry and the mock LLM
        # Note: We pass the mock_llm via the interface
        orchestrator = Orchestrator(
            registry={}, # Use empty dict for registry initially
            llm_interface=mock_llm,
            refinement_registry=new_registry
        )
        
        # Register the researcher role so the orchestrator knows what to spawn
        orchestrator.register_agent_role("researcher", ResearcherAgent)
        
        # Execute a mundane goal
        goal = "Tell me about entropy."
        print(f"[Continuity] Running goal: '{goal}'")
        await orchestrator.run_goal(goal, {})
        
        # 5. Verification
        print("[Continuity] Verifying if the biological lens was injected into the LLM prompt...")
        
        # The orchestrator should have injected the refinement into the context,
        # and the agent should have used it to build the system prompt.
        # We check the last messages sent to the LLM.
        all_messages = "".join([m.content for m in mock_llm.last_messages])
        
        print(f"[Continuity] Captured Prompt Snippet: {all_messages[:150]}...")
        
        if biological_lens.lower() in all_messages.lower():
            print("[SUCCESS] Continuity confirmed. The agency survived the restart.")
        else:
            pytest.fail(f"Continuity failed. The biological lens was not found in the prompt.\n"
                         f"Expected to find: '{biological_lens}'\n"
                         f"Actual prompt: '{all_messages}'")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(test_continuity_of_agency())
