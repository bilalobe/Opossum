"""Enumerations for Chat2SVG pipeline."""
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def to_metric_value(self) -> float:
        """Convert state to metric value for Prometheus."""
        return {"closed": 0, "half-open": 1, "open": 2}[self.value]