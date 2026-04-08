import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum, auto

class EventSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all events within a Bounded Context."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: EventSeverity = EventSeverity.INFO
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class InfrastructureErrorEvent(DomainEvent):
    """Triggered when an external system (LLM, DB, API) fails."""
    original_exception: Optional[str] = None
    error_code: Optional[str] = None


class LLMInfrastructureError(Exception):
    """Raised when an LLM infrastructure call fails. Carries the domain event."""
    def __init__(self, event: "InfrastructureErrorEvent"):
        self.event = event
        super().__init__(f"[{event.error_code}] {event.original_exception}")

@dataclass(frozen=True)
class PatternDetectedEvent(DomainEvent):
    """Triggered when the intelligence engine identifies a new semantic pattern."""
    pattern_type: str = "general"
    confidence: float = 0.0

@dataclass(frozen=True)
class ContextShiftEvent(DomainEvent):
    """Triggered when the active Bounded Context changes."""
    old_context: str = ""
    new_context: str = ""

@dataclass(frozen=True)
class DataIntegrityEvent(DomainEvent):
    """Triggered when data consistency or validation issues are detected."""
    entity_type: str = ""
    violation_detail: str = ""
