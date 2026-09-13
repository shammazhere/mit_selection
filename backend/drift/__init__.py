"""
CUSUM Drift Detection Module

Provides drift detection using cumulative sum control charts.
"""

from .cusum import (
    CUSUMDetector,
    CUSUMResult,
    compute_cusum_for_user,
    default_detector
)

__all__ = [
    "CUSUMDetector",
    "CUSUMResult",
    "compute_cusum_for_user",
    "default_detector"
]
