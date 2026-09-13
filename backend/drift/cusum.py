"""
CUSUM Drift Detection

Runs on the pre-multiplier fused daily score (self_score + peer_score combination).
This input is LOCKED so the drift signal stays stable regardless of later multiplier tuning.

The raw cumulative-sum path is stored per user for forensic timeline visualization.
"""

import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class CUSUMResult:
    """CUSUM detection result for a single user."""
    user_id: str
    drift_score: float  # Final drift score (0-1 normalized)
    raw_path: List[float]  # Day-by-day cumulative sum values
    drift_detected: bool  # Whether drift threshold was crossed
    days_to_detection: int  # Days until drift exceeded threshold
    max_cumsum: float  # Maximum cumulative sum value


class CUSUMDetector:
    """
    Cumulative Sum (CUSUM) control chart for drift detection.
    
    Classic statistical tool for detecting sustained mean shifts,
    as opposed to single outliers.
    
    Parameters:
        threshold: Control limit (default: 0.25, matches Section 7.3 & UI chart)
        slack: Slack parameter for CUSUM (default: 0.08)
        mean_est: Estimated mean of in-control process (default: 0.35)
    """
    
    def __init__(self, threshold: float = 0.25, slack: float = 0.08, mean_est: float = 0.35):
        self.threshold = threshold
        self.slack = slack
        self.mean_est = mean_est
    
    def compute_cumsum(self, scores: List[float]) -> List[float]:
        """
        Compute cumulative sum path for a sequence of scores.
        
        The CUSUM statistic is computed as:
        S_t = max(0, S_{t-1} + (x_t - mean_est) - slack)
        
        This detects when scores consistently exceed the expected mean.
        
        Args:
            scores: List of daily pre-multiplier fused scores
            
        Returns:
            List of cumulative sum values (raw path)
        """
        cumsum = [0.0]
        for score in scores:
            deviation = score - self.mean_est
            new_val = max(0.0, cumsum[-1] + deviation - self.slack)
            cumsum.append(round(float(new_val), 4))
        return cumsum[1:]  # Exclude initial 0
    
    def detect_drift(self, cumsum_path: List[float]) -> Dict[str, Any]:
        """
        Determine if drift was detected and when.
        
        Args:
            cumsum_path: Raw cumulative sum values
            
        Returns:
            Dictionary with drift detection information
        """
        max_val = max(cumsum_path) if cumsum_path else 0.0
        drift_detected = max_val >= self.threshold
        
        days_to_detection = -1
        if drift_detected:
            for i, val in enumerate(cumsum_path):
                if val >= self.threshold:
                    days_to_detection = i + 1  # 1-indexed
                    break
        
        return {
            "drift_detected": drift_detected,
            "max_cumsum": round(float(max_val), 4),
            "days_to_detection": days_to_detection,
            "raw_path": cumsum_path
        }
    
    def compute_drift_score(self, cumsum_path: List[float]) -> float:
        """
        Normalize the drift score to 0-1 range.
        
        Higher cumulative sum = higher drift = higher risk.
        
        Args:
            cumsum_path: Raw cumulative sum values
            
        Returns:
            Normalized drift score (0-1)
        """
        if not cumsum_path:
            return 0.0
        
        max_val = max(cumsum_path)
        # Scale smoothly: reaches ~0.625 at threshold 0.25, and 1.0 at 0.40
        normalized = min(1.0, max_val / (self.threshold * 1.6))
        return round(float(normalized), 4)
    
    def process_user(self, user_id: str, scores: List[float]) -> CUSUMResult:
        """
        Process a single user's daily scores through CUSUM.
        
        Args:
            user_id: User identifier
            scores: List of daily pre-multiplier fused scores
            
        Returns:
            CUSUMResult with drift analysis
        """
        if not scores:
            return CUSUMResult(
                user_id=user_id,
                drift_score=0.0,
                raw_path=[],
                drift_detected=False,
                days_to_detection=-1,
                max_cumsum=0.0
            )
        
        # Compute raw CUSUM path
        raw_path = self.compute_cumsum(scores)
        
        # Detect drift
        detection = self.detect_drift(raw_path)
        
        # Compute normalized drift score
        drift_score = self.compute_drift_score(raw_path)
        
        return CUSUMResult(
            user_id=user_id,
            drift_score=drift_score,
            raw_path=raw_path,
            drift_detected=detection["drift_detected"],
            days_to_detection=detection["days_to_detection"],
            max_cumsum=detection["max_cumsum"]
        )


# Default global detector instance
default_detector = CUSUMDetector(threshold=0.25, slack=0.08, mean_est=0.35)


def compute_cusum_for_user(user_id: str, scores: List[float]) -> CUSUMResult:
    """
    Convenience function to process a user with default detector.
    
    Args:
        user_id: User identifier
        scores: List of daily pre-multiplier fused scores
        
    Returns:
        CUSUMResult with drift analysis
    """
    return default_detector.process_user(user_id, scores)
