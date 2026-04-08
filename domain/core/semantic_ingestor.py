import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from domain.core.ports.ingestor import IntelligenceIngestor
from domain.core.semantic_memory import SemanticMemory
from domain.core.ports import BaseLLMInterface
from domain.core.prompt_sanitizer import sanitize_field

logger = logging.getLogger(__name__)

class SemanticIngestor(IntelligenceIngestor):
    """
    A concrete implementation of IntelligenceIngestor that uses an LLM 
    to synthesize AgentResults into high-signal SemanticMemory events.
    """
    def __init__(self, 
                 semantic_memory: SemanticMemory, 
                 llm: BaseLLMInterface,
                 context_id: str = "system"):
        self.semantic_memory = semantic_memory
        self.llm = llm
        self.context_id = context_id

    async def ingest(self, result: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Synthesizes orchestration results into a single, meaningful semantic event.
        """
        try:
            goal = result.get("goal", "Unknown Goal")
            findings = result.get("agent_findings", [])
            summary = result.get("orchestration_summary", {})
            
            if not findings:
                logger.info("[SemanticIngestor] No findings to ingest.")
                return False

            # 1. Construct a prompt for the LLM to synthesize the intelligence
            # We want a single, high-density sentence that captures the essence.
            # Each finding is individually sanitized to prevent cross-finding injection.
            sanitized_findings = []
            for f in findings:
                safe_text = sanitize_field(str(f['finding']), 'finding')
                sanitized_findings.append(f"- {safe_text} (Confidence: {f['confidence']})")
            findings_str = "\n".join(sanitized_findings)

            prompt = (
                f"You are the Intelligence Synthesis engine for the Hermes Memory System. "
                f"Your task is to take a complex orchestration report and compress it into a single, "
                f"high-signal, professional sentence that can be stored in long-term memory.\n\n"
                f"GOAL: {sanitize_field(goal, 'goal')}\n"
                f"FINDINGS:\n{findings_str}\n\n"
                f"INSTRUCTION: Output ONLY the single sentence. No preamble. No commentary. "
                f"Focus on the 'what' and the 'why'. The sentence must be dense and descriptive.\n\n"
                f"SYNTHESIZED EVENT:"
            )

            logger.info(f"[SemanticIngestor] Synthesizing intelligence for goal: {goal}")
            
            synthesized_text = await asyncio.to_thread(
                self.llm.complete, prompt,
                "You are a master of linguistic compression and semantic density."
            )

            if not synthesized_text or len(synthesized_text) < 10:
                logger.warning("[SemanticIngestor] Synthesis failed or produced insufficient text.")
                return False

            # 2. Determine the context_id (prefer the one from context, fallback to default)
            target_context = context.get("context_id", self.context_id)

            # 3. Commit to Semantic Memory
            # We add metadata to ensure we can trace this back to the original orchestration
            metadata = {
                "type": "autonomous_learning",
                "original_goal": goal,
                "confidence": summary.get("aggregate_confidence", 0.0),
                "agents_involved": len(findings)
            }

            self.semantic_memory.add_event(
                synthesized_text.strip(),
                metadata,
                context_id=target_context
            )

            logger.info(f"[SemanticIngestor] Successfully ingested: {synthesized_text.strip()}")
            return True

        except Exception as e:
            logger.error(f"[SemanticIngestor] Error during ingestion: {e}")
            return False
