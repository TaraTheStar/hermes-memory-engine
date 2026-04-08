from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum, auto

class MetricType(Enum):
    NODE_DEGREE = auto()
    COMMUNITY_SIZE = auto()
    GRAPH_DENSITY = auto()
    EDGE_WEIGHT = auto()
    CONNECTION_RATE = auto()

@dataclass(frozen=True)
class ThresholdProfile:
    """
    A set of statistical thresholds and sensitivity settings
    tailored for a specific Bounded Context.
    """
    name: str
    # Absolute thresholds: flag when current_value > threshold (used in simple mode)
    thresholds: Dict[MetricType, float] = field(default_factory=dict)
    # Z-score sigma cutoffs: flag when z_score > cutoff (used in complex/statistical mode)
    z_score_thresholds: Dict[MetricType, float] = field(default_factory=dict)
    # Sensitivity multiplier: higher means more prone to triggering anomalies
    sensitivity_multiplier: float = 1.0
    # Minimum sample size required before statistics become valid
    min_sample_size: int = 5
    # Metadata for debugging
    metadata: Dict[str, Any] = field(default_factory=dict)
