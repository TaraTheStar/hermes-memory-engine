import asyncio
import os
import sys
from typing import List, Dict, Any, Set, Optional

# Add parent directory to sys.path to allow absolute imports from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.supporting.ledger import StructuralLedger
from application.orchestrator import Orchestrator
from domain.core.refinement_engine import RefinementEngine, RefinementProposal
from domain.core.agents_impl import ResearcherAgent, AuditorAgent
from infrastructure.llm_implementations import LocalLLMImplementation
from domain.core.models import Skill, RelationalEdge

class RefinementOrchestrator:
    """
    Manages the lifecycle of a refinement proposal: 
    Detection -> Audit -> Execution.
    """
    def __init__(self, structural_db_path: str, registry: Dict[str, Any], llm_interface=None):
        self.ledger = StructuralLedger(structural_db_path)
        self.engine = RefinementEngine(structural_db_path)
        self.orchestrator = Orchestrator(registry, llm_interface)
        self.llm = llm_interface

    async def process_refinements(self) -> int:
        """
        Scans for proposals and runs the audit/execution loop.
        """
        proposals = self.engine.analyze_for_refinement()
        if not proposals:
            print("[RefinementOrchestrator] No refinement opportunities detected.")
            return 0

        print(f"[RefinementOrchestrator] Found {len(proposals)} proposals. Starting audit cycle...")
        executed_count = 0

        for proposal in proposals:
            print(f"\n[RefinementOrchestrator] Processing: {proposal.proposal_type} ({proposal.description})")
            
            # 1. Audit Phase: Delegate to an Auditor to ensure we don't break the graph
            audit_goal = f"Audit the following proposed graph change for structural integrity: {proposal.description}. Data: {proposal.data}"
            audit_result = await self.orchestrator.run_goal(audit_goal)
            
            # Check if the Auditor approved (Simulated logic for prototype)
            # In a real system, we'd parse the Auditor's finding for a 'CONFIRMED' signal
            if self._is_approved(audit_result):
                print(f"[RefinementOrchestrator] Proposal APPROVED by Auditor.")
                # 2. Execution Phase
                await self._execute_proposal(proposal)
                executed_count += 1
            else:
                print(f"[RefinementOrchestrator] Proposal REJECTED by Auditor. Skipping.")

        return executed_count

    def _is_approved(self, audit_result: Dict[str, Any]) -> bool:
        # Prototype logic: assume success if no explicit error found in findings
        for finding in audit_result.get('findings', []):
            if "REJECT" in str(finding).upper() or "DANGEROUS" in str(finding).upper():
                return False
        return True

    async def _execute_proposal(self, proposal: RefinementProposal):
        """
        Applies the change to the Structural Ledger.
        """
        print(f"[RefinementOrchestrator] Executing {proposal.proposal_type}...")
        session = self.ledger.Session()
        try:
            if proposal.proposal_type == "PRUNE_EDGE":
                # Parse target_id: "source->target"
                u, v = proposal.target_id.split("->")
                session.query(RelationalEdge).filter(
                    (RelationalEdge.source_id == u) & (RelationalEdge.target_id == v)
                ).delete()
                print(f"  -> Edge {u} <-> {v} pruned.")

            elif proposal.proposal_type == "MERGE_COMMUNITY":
                # Prototype logic: We don't actually implement the complex merge logic yet,
                # we just log that the intention was captured.
                print(f"  -> [SIMULATED] Community condensation triggered for {proposal.target_id}.")

            elif proposal.proposal_type == "GLOBAL_REBALANCE":
                print(f"  -> [SIMULATED] Global rebalancing triggered.")

            session.commit()
        except Exception as e:
            print(f"[RefinementOrchestrator] Execution failed: {e}")
            session.rollback()
        finally:
            session.close()

if __name__ == "__main__":
    # Simple test runner
    async def test():
        import os
        db = '/tmp/hermes_refinement_test_v2.db'
        if os.path.exists(db):
            os.remove(db)
            
        registry = {"researcher": ResearcherAgent, "auditor": AuditorAgent}
        llm = LocalLLMImplementation()
        orch = RefinementOrchestrator(db, registry, llm)
        
        # 1. Create a "Bloated Community" to trigger MERGE_COMMUNITY
        print("\n[Test] Creating a bloated community of 25 nodes...")
        session = orch.ledger.Session()
        try:
            hub_skill = Skill(name="Cluster_Nexus", description="The center of a massive cluster.")
            session.add(hub_skill)
            session.commit()
            
            cluster_nodes = []
            for i in range(25):
                s = Skill(name=f"Cluster_Node_{i}", description="Part of a dense cluster.")
                session.add(s)
                cluster_nodes.append(s)
            session.commit()
            
            # Connect all nodes to the hub to create a dense community
            for node in cluster_nodes:
                edge = RelationalEdge(
                    source_id=hub_skill.id,
                    target_id=node.id,
                    relationship_type="cluster_member",
                    weight=0.8
                )
                session.add(edge)
            session.commit()
            print(f"[Test] Cluster created with {len(cluster_nodes)} nodes.")
        finally:
            session.close()

        # 2. Run the refinement cycle
        print("\n[Test] Running Refinement Cycle...")
        executed = await orch.process_refinements()
        print(f"\n[Test] Results: {executed} refinement(s) executed.")

    asyncio.run(test())
