"""
Performance metrics and observability.

Tracks performance, success rates, and error statistics.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """Single metric value."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and tracks performance metrics.
    
    Provides timing, counters, and statistics.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, int] = defaultdict(int)
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.errors: Dict[str, int] = defaultdict(int)
        self.metrics: List[Metric] = []
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Increment value
            tags: Optional tags
        """
        self.counters[name] += value
        self.metrics.append(Metric(name=f"{name}_count", value=value, tags=tags or {}))
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a timing metric.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            tags: Optional tags
        """
        self.timings[name].append(duration)
        self.metrics.append(Metric(name=f"{name}_duration", value=duration, tags=tags or {}))
    
    def record_error(self, name: str, error_type: str = "unknown"):
        """
        Record an error.
        
        Args:
            name: Operation name
            error_type: Type of error
        """
        self.errors[f"{name}:{error_type}"] += 1
        self.increment(f"{name}_errors", tags={"error_type": error_type})
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)
    
    def get_avg_timing(self, name: str) -> Optional[float]:
        """Get average timing for a metric."""
        timings = self.timings.get(name, [])
        if not timings:
            return None
        return sum(timings) / len(timings)
    
    def get_error_count(self, name: str) -> int:
        """Get error count for an operation."""
        return sum(count for key, count in self.errors.items() if key.startswith(f"{name}:"))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        return {
            'counters': dict(self.counters),
            'avg_timings': {
                name: self.get_avg_timing(name)
                for name in self.timings.keys()
            },
            'errors': dict(self.errors),
            'total_metrics': len(self.metrics)
        }
    
    def reset(self):
        """Reset all metrics."""
        self.counters.clear()
        self.timings.clear()
        self.errors.clear()
        self.metrics.clear()


class Timer:
    """
    Context manager for timing operations.
    
    Usage:
        with Timer("operation_name", metrics_collector):
            # do work
    """
    
    def __init__(self, name: str, collector: Optional[MetricsCollector] = None, tags: Optional[Dict[str, str]] = None):
        """
        Initialize timer.
        
        Args:
            name: Operation name
            collector: Optional metrics collector
            tags: Optional tags
        """
        self.name = name
        self.collector = collector
        self.tags = tags or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if self.start_time and self.collector:
            duration = time.time() - self.start_time
            self.collector.record_timing(self.name, duration, self.tags)
        return False
    
    def elapsed(self) -> float:
        """Get elapsed time."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def set_metrics(collector: MetricsCollector):
    """Set the global metrics collector (useful for testing)."""
    global _metrics_collector
    _metrics_collector = collector

