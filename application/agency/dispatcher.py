import asyncio
import logging
from typing import Dict, Any, List, Optional
from .roles.base_specialist import BaseSpecialist

# Setup logging for the agency
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("AgencyDispatcher")

class Dispatcher:
    """
    The central nervous system of the agency. 
    It receives tasks, identifies the appropriate specialist, 
    and manages the sequential execution of the task queue.
    """
    def __init__(self, specialists: List[BaseSpecialist]):
        self.specialists = {s.name.lower(): s for s in specialists}
        self.task_queue = asyncio.Queue()
        self._running = False

    async def add_task(self, role_name: str, task_data: Dict[str, Any]):
        """Adds a new task to the agency queue."""
        logger.info(f"New task queued for role: {role_name}")
        await self.task_queue.put({
            "role": role_name.lower(),
            "data": task_data
        })

    async def _process_task(self, task: Dict[str, Any]):
        role_name = task["role"]
        task_data = task["data"]
        
        specialist = self.specialists.get(role_name)
        if not specialist:
            logger.error(f"No specialist found for role: {role_name}")
            return

        logger.info(f"Dispatching task to Specialist: {specialist.name}")
        try:
            result = await specialist.execute(task_data)
            logger.info(f"Task completed by {specialist.name}")
            return result
        except Exception as e:
            logger.error(f"Task failed in {specialist.name}: {e}")
            return {"error": str(e)}

    async def run(self):
        """Starts the dispatcher loop."""
        self._running = True
        logger.info("Agency Dispatcher is online and listening...")
        
        while self._running:
            task = await self.task_queue.get()
            await self._process_task(task)
            self.task_queue.task_done()

    def stop(self):
        """Stops the dispatcher loop."""
        self._running = False
        logger.info("Agency Dispatcher shutting down.")

if __name__ == "__main__":
    # This is just a placeholder for testing
    print("Dispatcher module loaded.")