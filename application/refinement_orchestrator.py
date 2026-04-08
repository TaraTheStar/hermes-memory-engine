import logging
import re
from typing import List, Dict, Any, Optional
from domain.supporting.ledger import StructuralLedger
from application.orchestrator import Orchestrator
from domain.core.refinement_engine import RefinementEngine, GraphRefinementProposal
from domain.core.refinement_registry import RefinementRegistry
from domain.core.models import Skill, RelationalEdge
from domain.core.anomaly_detector import ContextualAnomalyDetector

logger = logging.getLogger(__name__)

class RefinementOrchestrator:
    """
    Manages the lifecycle of a refinement proposal:
    Detection -> Audit -> Execution.
    """
    def __init__(self, structural_db_path: str, registry: Dict[str, Any], llm_interface=None):
        self.ledger = StructuralLedger(structural_db_path)
        detector = ContextualAnomalyDetector()
        self.engine = RefinementEngine(self.ledger, detector)
        refinement_registry = RefinementRegistry(self.ledger)
        self.orchestrator = Orchestrator(registry, llm_interface,
                                         refinement_registry=refinement_registry)
        self.llm = llm_interface

    async def process_refinements(self) -> int:
        """
        Scans for proposals and runs the audit/execution loop.
        """
        proposals = self.engine.analyze_for_refinement()
        if not proposals:
            logger.info("No refinement opportunities detected.")
            return 0

        logger.info("Found %d proposals. Starting audit cycle...", len(proposals))
        executed_count = 0

        for proposal in proposals:
            logger.info("Processing: %s (%s)", proposal.proposal_type, proposal.description)
            
            # 1. Audit Phase: Delegate to an Auditor to ensure we don't break the graph
            audit_goal = f"Audit the following proposed graph change for structural integrity: {proposal.description}. Data: {proposal.data}"
            audit_result = await self.orchestrator.run_goal(audit_goal, {})
            
            # Check if the Auditor approved (Simulated logic for prototype)
            if self._is_approved(audit_result):
                logger.info("Proposal APPROVED by Auditor.")
                # 2. Execution Phase
                await self._execute_proposal(proposal)
                executed_count += 1
            else:
                logger.info("Proposal REJECTED by Auditor. Skipping.")

        return executed_count

    # Minimum aggregate confidence from agents to approve a proposal.
    APPROVAL_CONFIDENCE_THRESHOLD = 0.5

    # Phrases that veto approval regardless of confidence.
    _VETO_PHRASES = re.compile(
        r'\b(reject|dangerous|unsafe|do not proceed|abort)\b',
        re.IGNORECASE
    )
    # Negation prefixes that neutralize a veto phrase.
    _NEGATION_PREFIX = re.compile(
        r'\b(not|no|neither|never|isn\'t|aren\'t|wasn\'t|doesn\'t|don\'t)\b',
        re.IGNORECASE
    )

    def _is_approved(self, audit_result: Dict[str, Any]) -> bool:
        summary = audit_result.get('orchestration_summary', {})
        confidence = summary.get('aggregate_confidence', 0.0)

        if confidence < self.APPROVAL_CONFIDENCE_THRESHOLD:
            logger.info("Approval denied: confidence %.2f below threshold %.2f",
                        confidence, self.APPROVAL_CONFIDENCE_THRESHOLD)
            return False

        for finding in audit_result.get('agent_findings', []):
            text = str(finding.get('finding', ''))
            if self._contains_unmitigated_veto(text):
                logger.info("Approval denied: veto phrase found in finding")
                return False

        return True

    def _contains_unmitigated_veto(self, text: str) -> bool:
        """Returns True if text contains a veto phrase NOT preceded by a negation."""
        for match in self._VETO_PHRASES.finditer(text):
            # Check the 30 characters before the match for a negation word
            start = max(0, match.start() - 30)
            preceding = text[start:match.start()]
            if not self._NEGATION_PREFIX.search(preceding):
                return True
        return False

    async def _execute_proposal(self, proposal: GraphRefinementProposal) -> bool:
        """
        Applies the change to the Structural Ledger.
        Returns True on success, False if the proposal could not be executed.
        """
        logger.info("Executing %s...", proposal.proposal_type)
        with self.ledger.session_scope() as session:
            if proposal.proposal_type == "PRUNE_EDGE":
                parts = proposal.target_id.split("->", 1)
                if len(parts) != 2:
                    logger.warning("Malformed edge target_id: %s", proposal.target_id)
                    return False
                u, v = parts
                session.query(RelationalEdge).filter(
                    (RelationalEdge.source_id == u) & (RelationalEdge.target_id == v)
                ).delete()
                logger.info("Edge %s <-> %s pruned.", u, v)
                return True

            elif proposal.proposal_type == "MERGE_COMMUNITY":
                logger.info("[SIMULATED] Community condensation triggered for %s.", proposal.target_id)
                return True

            elif proposal.proposal_type == "GLOBAL_REBALANCE":
                logger.info("[SIMULATED] Global rebalancing triggered.")
                return True

            else:
                logger.warning("Unknown proposal type: %s", proposal.proposal_type)
                return False

