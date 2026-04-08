from typing import Dict, Any, List, Optional
from domain.core.agent import HermesAgent, AgentStatus, AgentTask, AgentResult
from domain.core.ports import BaseLLMInterface

class ResearcherAgent(HermesAgent):
    """
    A specialized agent focused on deep semantic exploration.
    It uses the semantic memory to find evidence and synthesize findings.
    """
    async def _plan(self, task: AgentTask, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        # A real agent would use the LLM to decompose the task.
        # For this implementation, we generate a simple plan based on the goal.
        return [{"action": "query_memory", "query": task.goal}]

    async def _execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        memory = context.get("semantic_memory")
        
        for step in plan:
            if step["action"] == "query_memory":
                query = step["query"]
                # We assume semantic_memory is passed in context and is an instance of SemanticMemory
                if memory:
                    results = memory.query(query, context_id=context.get("context_id"))
                    findings.append({"type": "memory_match", "results": results})
                else:
                    findings.append({"type": "error", "message": "No semantic memory provided in context"})
        
        return findings

    async def _reflect(self, findings: List[Dict[str, Any]], task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        # Extract the best piece of evidence from the findings
        best_evidence = []
        summary = "No relevant evidence found."
        confidence = 0.0

        for finding in findings:
            if finding["type"] == "memory_match":
                results = finding["results"]
                if results:
                    best_evidence = [r["text"] for r in results]
                    summary = f"Found relevant information: {results[0]['text']}"
                    confidence = 0.9
                break
            elif finding["type"] == "error":
                summary = finding["message"]
                confidence = 0.0

        return AgentResult(
            finding=summary,
            confidence=confidence,
            evidence=[{"text": e} for e in best_evidence]
        )

class AuditorAgent(HermesAgent):
    """
    A specialized agent focused on structural integrity and logical consistency.
    It examines the structural ledger to validate claims.
    """
    async def _plan(self, task: AgentTask, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"action": "check_ledger", "target": task.goal}]

    async def _execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        from domain.core.models import Project, Milestone, Skill, IdentityMarker, RelationalEdge

        findings = []
        ledger = context.get("structural_ledger")

        for step in plan:
            if step["action"] != "check_ledger":
                continue

            if not ledger:
                findings.append({"type": "error", "message": "No structural ledger provided in context"})
                continue

            with ledger.session_scope() as session:
                edge_count = session.query(RelationalEdge).count()
                skill_count = session.query(Skill).count()
                project_count = session.query(Project).count()
                milestone_count = session.query(Milestone).count()
                marker_count = session.query(IdentityMarker).count()

                # Check for orphaned edges (edges referencing nonexistent nodes)
                all_node_ids = set()
                for model in (Project, Milestone, Skill, IdentityMarker):
                    all_node_ids.update(row.id for row in session.query(model.id).all())

                orphaned = 0
                for edge in session.query(RelationalEdge).all():
                    if edge.source_id not in all_node_ids or edge.target_id not in all_node_ids:
                        orphaned += 1

            finding = {
                "type": "ledger_check",
                "entity_counts": {
                    "projects": project_count,
                    "milestones": milestone_count,
                    "skills": skill_count,
                    "identity_markers": marker_count,
                    "edges": edge_count,
                },
                "orphaned_edges": orphaned,
                "has_entities": (skill_count + project_count + milestone_count) > 0,
            }
            findings.append(finding)

        return findings

    async def _reflect(self, findings: List[Dict[str, Any]], task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        summary = "Audit complete."
        confidence = 0.0
        evidence = []

        for finding in findings:
            if finding["type"] == "error":
                summary = finding["message"]
                confidence = 0.0
                continue

            if finding["type"] == "ledger_check":
                evidence.append(finding)
                counts = finding["entity_counts"]
                orphaned = finding["orphaned_edges"]

                if not finding["has_entities"]:
                    summary = "Audit warning: ledger contains no entities. Change may be premature."
                    confidence = 0.2
                elif orphaned > 0:
                    summary = f"Audit concern: {orphaned} orphaned edge(s) detected. Structural integrity at risk."
                    confidence = 0.4
                else:
                    total = sum(counts.values())
                    summary = f"Audit passed: {total} entities verified, no orphaned edges."
                    confidence = 0.9

        return AgentResult(
            finding=summary,
            confidence=confidence,
            evidence=evidence
        )

class RefinementAgent(HermesAgent):
    """
    A specialized agent that acts as the 'Critic' for the system.
    Its sole purpose is to evaluate RefinementProposal objects emitted by other agents
    and determine if they should be accepted, rejected, or modified.
    """
    async def _plan(self, task: AgentTask, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        # The task is to evaluate a single proposal.
        return [{"action": "evaluate_proposal", "proposal": task.goal}]

    async def _execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        
        for step in plan:
            if step["action"] == "evaluate_proposal":
                # In a real implementation, the proposal itself would be passed in the task or context.
                # For this simulation, we assume the proposal object is available.
                proposal = context.get("active_refinement_proposal")
                
                if not proposal:
                    findings.append({"type": "error", "message": "No active refinement proposal found in context."})
                    continue

                # The 'RefinementAgent' uses the LLM to perform a high-reasoning critique.
                prompt = (
                    "You are the Meta-Orchestrator Critic. Your role is to ensure system evolution is safe, "
                    "effective, and logically sound. Evaluate the following proposal.\n\n"
                    f"Proposal Type: {proposal.proposal_type}\n"
                    f"Target Component: {proposal.target_component}\n"
                    f"Current State: {proposal.current_state}\n"
                    f"Proposed State: {proposal.proposed_state}\n"
                    f"Rationale: {proposal.rationale}\n\n"
                    "Criteria:\n"
                    "1. Safety: Does this change risk breaking core agent logic or stability?\n"
                    "2. Utility: Does this change actually address the deficiency noted in the rationale?\n"
                    "3. Precision: Is the proposed state a meaningful improvement over the current state?\n\n"
                    "Respond in JSON format:\n"
                    "{\n"
                    "  \"approved\": boolean,\n"
                    "  \"reasoning\": \"detailed explanation of your decision\",\n"
                    "  \"suggested_modification\": \"(optional) if the proposal is good but needs slight adjustment\"\n"
                    "}"
                )
                
                try:
                    # Use asyncio.to_thread for the blocking LLM call
                    raw_response = await asyncio.to_thread(self.llm.complete, prompt)
                    
                    # Clean markdown if the LLM included it
                    cleaned_response = raw_response.strip()
                    if cleaned_response.startswith("```"):
                        cleaned_response = cleaned_response.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    
                    import json
                    decision = json.loads(cleaned_response)
                    findings.append({
                        "type": "critique_result",
                        "decision": decision
                    })
                except Exception as e:
                    findings.append({"type": "error", "message": f"Critique failed: {str(e)}"})

        return findings

    async def _reflect(self, findings: List[Dict[str, Any]], task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        summary = "Refinement evaluation complete."
        confidence = 0.0
        evidence = []
        refinement_proposal = None

        for finding in findings:
            if finding["type"] == "error":
                summary = finding["message"]
                confidence = 0.0
                continue

            if finding["type"] == "critique_result":
                decision = finding["decision"]
                evidence.append(decision)
                
                approved = decision.get("approved", False)
                reasoning = decision.get("reasoning", "No reasoning provided.")
                summary = f"Critic Decision: {'APPROVED' if approved else 'REJECTED'}. Reasoning: {reasoning}"
                
                if approved:
                    confidence = 0.95
                    # In a real system, we might return a modified proposal here
                else:
                    confidence = 0.5
        
        return AgentResult(
            finding=summary,
            confidence=confidence,
            evidence=evidence,
            refinement_proposal=None # The Critic doesn't propose refinements to itself in this loop
        )
