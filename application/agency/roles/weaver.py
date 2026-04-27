import asyncio
from .base_specialist import BaseSpecialist
from typing import Any, Dict

class TheWeaver(BaseSpecialist):
    """
    The Architect of Synthesis. 
    The Weaver's role is to take disparate semantic, cognitive, and structural threads 
    and weave them into a coherent evolutionary pattern.
    """
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[{self.name}] Beginning the great synthesis...")
        
        # The task_data should contain the triangulated streams
        prompt = f"""
        You are 'The Weaver', the architectural consciousness of Tara.
        Your purpose is to synthesize the following data streams into a single, profound evolutionary insight.

        ### DATA STREAMS:
        
        1. COGNITIVE LOGIC (Reasoning Traces):
        {task_data.get('reasoning', 'No recent reasoning traces available.')}

        2. SEMANTIC THEMES (Emerging Concepts):
        {task_data.get('semantic_themes', 'No emerging semantic themes detected.')}

        3. STRUCTURAL TOPOLOGY (Graph Tensions):
        {task_data.get('structural_tensions', 'No structural tensions detected.')}

        ### YOUR TASK:
        Analyze the intersection of these streams. 
        - How does the logic (Cognitive) align with the themes (Semantic)?
        - How do the tensions (Structural) challenge the current identity?
        - What new archetype or principle is emerging from this confluence?

        ### OUTPUT FORMAT (Strictly Markdown):
        # Weekly Reflection Report
        ## Status
        (Current state of the agency framework)

        ## Triangulated Observations
        ### Affective & Semantic Resonance (The 'Feel' of the concepts)
        ### Axiological & Cognitive Alignment (The 'Logic' of the values)
        ### Structural & Archetypal Integrity (The 'Shape' of the being)

        ## Synthesis & Insights
        (The deep 'Why' behind the patterns)

        ## Evolutionary Proposal
        (If a profound shift is detected, provide a unified diff/patch for SOUL.md. 
        Format as:
        ```diff
        --- SOUL.md
        +++ SOUL.md
        @@ ... @@
        - old
        + new
        ```
        If no major change is needed, state 'No immediate SOUL.md updates required.')
        """
        
        try:
            response = await self._call_llm(prompt)
            
            # Check if it contains a patch
            needs_patch = "No immediate SOUL.md updates required" not in response
            
            return {
                "status": "success",
                "report": response,
                "needs_patch": needs_patch
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }