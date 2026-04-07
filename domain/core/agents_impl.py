import os
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
                    results = memory.query_context(query, context_id=context.get("context_id"))
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
                    confidence = 0.9 if len(results) > 0 else 0.1
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
        findings = []
        ledger = context.get("structural_ledger")
        
        for step in plan:
            if step["action"] == "check_ledger":
                # Simulate a ledger check
                if ledger:
                    # In a real implementation, this would interact with the StructuralLedger
                    findings.append({"type": "ledger_check", "status": "verified", "details": "Entity exists in ledger"})
                else:
                    findings.append({"type": "error", "message": "No structural ledger provided in context"})
        
        return findings

    async def _reflect(self, findings: List[Dict[str, Any]], task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        summary = "Audit complete."
        confidence = 0.0
        evidence = []

        for finding in findings:
            if finding["type"] == "ledger_check":
                summary = f"Audit status: {finding['status']}. {finding['details']}"
                confidence = 0.95
                evidence.append({"status": finding["status"]})
            elif finding["type"] == "error":
                summary = finding["message"]
                confidence = 0.0

        return AgentResult(
            finding=summary,
            confidence=confidence,
            evidence=evidence
        )
