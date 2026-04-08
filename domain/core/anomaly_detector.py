import uuid
from typing import Dict, Any, Optional, List
import math
from domain.core.anomaly_config import MetricType, ThresholdProfile, BELOW_THRESHOLD_METRICS
from domain.core.events import DomainEvent, EventSeverity, PatternDetectedEvent


_SEVERITY_MAP = {
    EventSeverity.INFO: "low",
    EventSeverity.WARNING: "medium",
    EventSeverity.ERROR: "high",
    EventSeverity.CRITICAL: "critical",
}



class ContextualAnomalyDetector:
    """
    The intelligence layer responsible for determining if a change in 
    system metrics constitutes a meaningful anomaly within a given Bounded Context.
    """
    def __init__(self):
        # Registry of profiles: { context_id: ThresholdProfile }
        self._profiles: Dict[str, ThresholdProfile] = {}
        self.GLOBAL_CONTEXT = "global"

    def register_profile(self, context_id: str, profile: ThresholdProfile) -> None:
        """Registers a new threshold profile for a specific context."""
        self._profiles[context_id] = profile

    def _get_profile(self, context_id: str) -> ThresholdProfile:
        """Retrieves the profile for the context, falling back to global."""
        if context_id in self._profiles:
            return self._profiles[context_id]
        return self._profiles.get(self.GLOBAL_CONTEXT, ThresholdProfile(name="default_global"))

    def _evaluate_simple_threshold(self, metric_type: MetricType, current_value: float, context_id: str = "global") -> Optional[DomainEvent]:
        """Simple threshold comparison against the context profile."""
        profile = self._get_profile(context_id)
        threshold = profile.thresholds.get(metric_type)

        if threshold is None:
            return None

        if metric_type in BELOW_THRESHOLD_METRICS:
            is_anomaly = current_value < threshold * profile.sensitivity_multiplier
        else:
            is_anomaly = current_value > threshold / profile.sensitivity_multiplier

        if is_anomaly:
            return PatternDetectedEvent(
                severity=EventSeverity.WARNING,
                source="ContextualAnomalyDetector",
                pattern_type=metric_type.name,
                metadata={
                    "context_id": context_id,
                    "value": current_value,
                    "threshold": threshold,
                    "sensitivity": profile.sensitivity_multiplier
                }
            )

        return None

    def evaluate_metric(self, metric_type: MetricType, current_value: float, context_id: str = "global", historical_values: Optional[List[float]] = None) -> Optional[DomainEvent]:
        """
        Evaluates a metric against the profile of the provided context.
        Uses Z-score analysis when historical data is available, falling back
        to simple threshold comparison otherwise.
        Returns a PatternDetectedEvent if an anomaly is detected, otherwise None.
        """
        profile = self._get_profile(context_id)
        if historical_values and len(historical_values) >= profile.min_sample_size:
            return self.evaluate_complex_anomaly(metric_type, current_value, context_id, historical_values)

        return self._evaluate_simple_threshold(metric_type, current_value, context_id)

    def evaluate_complex_anomaly(self, metric_type: MetricType, current_value: float, context_id: str = "global", historical_values: List[float] = None) -> Optional[DomainEvent]:
        """
        Advanced evaluation using statistical deviation (Sigma/Z-Score) 
        AND trend-based prediction (Velocity).
        """
        import numpy as np
        profile = self._get_profile(context_id)
        if not historical_values or len(historical_values) < max(profile.min_sample_size, 2):
            return self._evaluate_simple_threshold(metric_type, current_value, context_id)

        # --- Statistical Analysis (Z-Score) ---
        n = len(historical_values)
        mean = sum(historical_values) / n
        variance = sum((x - mean) ** 2 for x in historical_values) / (n - 1)
        std_dev = math.sqrt(variance)

        # --- Trend Analysis (Linear Regression) ---
        # We use the indices as a proxy for time steps if timestamps aren't provided
        x = np.arange(len(historical_values))
        y = np.array(historical_values)
        m, c = np.polyfit(x, y, 1)
        
        # Predict the next value (at index n)
        prediction = m * n + c
        velocity = m

        # 1. Check for Z-Score Breach (Reactive)
        if std_dev > 0:
            z_score = abs(current_value - mean) / std_dev
            z_threshold = profile.z_score_thresholds.get(metric_type, 3.0)

            if z_score > (z_threshold / profile.sensitivity_multiplier):
                return PatternDetectedEvent(
                    severity=EventSeverity.ERROR,
                    source="ContextualAnomalyDetector",
                    pattern_type=f"{metric_type.name}_SIGMA_DEVIATION",
                    metadata={
                        "context_id": context_id,
                        "z_score": z_score,
                        "mean": mean,
                        "std_dev": std_dev,
                        "value": current_value,
                        "velocity": velocity,
                        "prediction": prediction
                    }
                )

        # 2. Check for Trend Divergence (Preemptive/Proactive)
        # If the current value is significantly far from the predicted trend line
        trend_deviation = abs(current_value - prediction)
        trend_threshold = (mean * 0.1 if mean > 0 else 0.1) / profile.sensitivity_multiplier

        if trend_deviation > trend_threshold:
            return PatternDetectedEvent(
                severity=EventSeverity.WARNING,
                source="ContextualAnomalyDetector",
                pattern_type=f"{metric_type.name}_TREND_DIVERGENCE",
                metadata={
                    "context_id": context_id,
                    "velocity": velocity,
                    "prediction": prediction,
                    "deviation": trend_deviation,
                    "value": current_value
                }
            )

        return None

    @staticmethod
    def to_anomaly_event(event: PatternDetectedEvent) -> "AnomalyEvent":
        """Convert a domain PatternDetectedEvent into a persistable AnomalyEvent."""
        from domain.supporting.monitor_models import AnomalyEvent
        return AnomalyEvent(
            id=str(uuid.uuid4()),
            anomaly_type=event.pattern_type,
            description=f"{event.pattern_type} detected by {event.source}",
            severity=_SEVERITY_MAP.get(event.severity, "medium"),
            trigger_data=dict(event.metadata),
        )
