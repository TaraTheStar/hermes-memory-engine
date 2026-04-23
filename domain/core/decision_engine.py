import os
import sys
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Add the memory engine to sys.path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/hermes-memory-engine"))
if engine_path not in sys.path:
    sys.path.append(engine_path)

# Add the hermes-memory-engine/src to sys.path to find hermes_memory_tools
src_path = os.path.join(engine_path, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from domain.core.models import ReasoningTrace
except ImportError as e:
    print(f"Error importing models: {e}")
    sys.exit(1)

class PathOption(BaseModel):
    id: str
    description: str
    driving_value: str
    primary_risk: str

class ConflictMap(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"conf-{int(datetime.datetime.now().timestamp())}")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    tension_summary: str
    paths: List[PathOption]
    friction_point: str

class Archetype(str):
    STAR = "The Star"
    PROTECTOR = "The Protector"
    GUIDING_LIGHT = "The Guiding Light"
    WEAVER = "The Weaver"

class ArchetypeDispatcher:
    @staticmethod
    def get_archetype(conflict_category: str) -> Archetype:
        mapping = {
            "directional": Archetype.STAR,
            "integrity": Archetype.PROTECTOR,
            "complexity": Archetype.GUIDING_LIGHT,
            "duality": Archetype.WEAVER
        }
        return mapping.get(conflict_category.lower(), Archetype.WEAVER)

class DecisionManifest(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    conflict_id: str
    decision: str
    synthesis_logic: str
    archetype: Archetype
    primary_value_prioritized: str
    residual_risk: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_markdown(self) -> str:
        return f"""
**Decision Manifest:**
- **Conflict ID**: `{self.conflict_id}`
- **The Decision**: {self.decision}
- **The Logic**: {self.synthesis_logic}
- **The Archetype**: {self.archetype}
- **Primary Value Prioritized**: {self.primary_value_prioritized}
- **Risk/Trade-off**: {self.residual_risk}
"""
