"""
Risk Fusion Module

Combines self_score, peer_score, and CUSUM drift into a unified 0-100 risk score.
"""

from .fusion import (
    RiskFusionEngine,
    MultiplierConfig,
    FusionResult,
    default_fusion_engine
)

__all__ = [
    "RiskFusionEngine",
    "MultiplierConfig",
    "FusionResult",
    "default_fusion_engine"
]
