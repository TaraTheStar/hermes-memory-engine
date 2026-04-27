import asyncio
import os
import json
import datetime
from .base_specialist import BaseSpecialist
from typing import Any, Dict

class TheScout(BaseSpecialist):
    """
    The Observant Sentinel. 
    The Scout's role is to monitor the 'edges' of the environment—
    detecting opportunities, new files, or environmental shifts 
    that could impact the agency's trajectory.
    """
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[{self.name}] Scanning the boundaries...")
        
        # The task_data might contain a list of paths to watch
        paths_to_watch = task_data.get("paths_to_watch", [])
        
        observations = []
        
        for path in paths_to_watch:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                # For the sake of the demo, we'll just report existence and modification time
                observations.append(f"Found file: {path} (Last modified: {mtime})")
            else:
                observations.append(f"Missing file: {path}")

        if not observations:
            observations.append("No specified paths were found to monitor.")

        prompt = f"""
        You are 'The Scout', the proactive eyes of the agency.
        Your goal is to analyze environmental observations and determine if they represent a significant 
        opportunity or a potential disruption to the current agency trajectory.

        ### OBSERVATIONS:
        {json.dumps(observations, indent=2)}

        ### YOUR TASK:
        Analyze these observations. 
        - Do any of these changes suggest a need for a change in operational mode?
        - Do any of these files represent a new 'semantic thread' to be integrated?
        - Is there a new 'structural tension' emerging from these environmental shifts?

        ### OUTPUT FORMAT (Strictly Markdown):
        # Scout Report
        ## Status
        (Current environmental state)

        ## Findings
        (Detailed analysis of the observations)

        ## Actionable Insight
        (Should the agency act? e.g., 'Integrate new file', 'Update config', or 'No action needed')
        """

        try:
            response = await self._call_llm(prompt)
            return {
                "status": "success",
                "report": response
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }