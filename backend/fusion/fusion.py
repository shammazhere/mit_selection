"""
Risk Fusion Engine

Combines self_score, peer_score, and CUSUM drift into a unified 0-100 risk score.
Applies role/time/data-sensitivity multipliers and score decay.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class MultiplierConfig:
    """Configuration for contextual multipliers."""
    role_admin_weight: float = 1.5  # Higher weight for admin accounts
    role_privileged_weight: float = 1.3
    role_regular_weight: float = 1.0
    
    time_before_7am_weight: float = 1.4  # Higher weight for before 7am
    time_after_8pm_weight: float = 1.3
    time_normal_weight: float = 1.0
    
    data_confidential_weight: float = 1.4  # Higher weight for confidential data
    data_removable_media_weight: float = 1.3
    data_normal_weight: float = 1.0


@dataclass
class FusionResult:
    """Result of risk fusion computation."""
    user_id: str
    risk_score: float  # Final 0-100 risk score
    self_score: float
    peer_score: float
    drift_score: float
    pre_multiplier_score: float  # Locked input to CUSUM
    raw_fusion_score: float  # Fusion before multipliers
    adjusted_fusion_score: float  # Fusion after multipliers
    multipliers_applied: Dict[str, float]
    score_components: Dict[str, float]

class RiskFusionEngine:
    """
    Fuses self_score, peer_score, and drift into a unified risk score.
    
    The fusion formula is:
    raw_fusion = (self_score * self_weight + peer_score * peer_weight + drift * drift_weight) / total_weight
    
    Then contextual multipliers and score decay are applied.
    
    Parameters:
        self_weight: Weight for self_score (default: 0.35)
        peer_weight: Weight for peer_score (default: 0.35)
        drift_weight: Weight for drift_score (default: 0.30)
    """
    
    def __init__(
        self,
        self_weight: float = 0.35,
        peer_weight: float = 0.35,
        drift_weight: float = 0.30,
        multiplier_config: Optional[MultiplierConfig] = None
    ):
        self.self_weight = self_weight
        self.peer_weight = peer_weight
        self.drift_weight = drift_weight
        self.multiplier_config = multiplier_config or MultiplierConfig()
        
        # Verify weights sum to 1
        total = self.self_weight + self.peer_weight + self.drift_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
    
    def compute_pre_multiplier_score(self, self_score: float, peer_score: float) -> float:
        """
        Compute the pre-multiplier fused score (LOCKED input to CUSUM).
        
        This exact score is what CUSUM watches - it must remain stable
        regardless of later multiplier tuning.
        
        Args:
            self_score: Isolation Forest anomaly score (0-1)
            peer_score: Z-score deviation vs peer cohort (0-1)
            
        Returns:
            Pre-multiplier fused score (0-1)
        """
        # Simple weighted combination - this is the LOCKED CUSUM input
        pre_score = (
            self_score * self.self_weight +
            peer_score * self.peer_weight
        ) / (self.self_weight + self.peer_weight)
        return round(pre_score, 4)
    
    def compute_raw_fusion(
        self,
        self_score: float,
        peer_score: float,
        drift_score: float
    ) -> float:
        """
        Compute raw fusion score before multipliers.
        
        Args:
            self_score: Isolation Forest anomaly score (0-1)
            peer_score: Z-score deviation vs peer cohort (0-1)
            drift_score: CUSUM drift score (0-1)
            
        Returns:
            Raw fusion score (0-1)
        """
        raw = (
            self_score * self.self_weight +
            peer_score * self.peer_weight +
            drift_score * self.drift_weight
        )
        return round(raw, 4)
    
    def apply_role_multiplier(self, role: Optional[str]) -> float:
        """Apply role sensitivity multiplier."""
        if not role:
            return self.multiplier_config.role_regular_weight
        
        role_lower = role.lower()
        
        if any(kw in role_lower for kw in ["admin", "administrator", "root", "superuser"]):
            return self.multiplier_config.role_admin_weight
        elif any(kw in role_lower for kw in ["privileged", "manager", "director", "lead"]):
            return self.multiplier_config.role_privileged_weight
        else:
            return self.multiplier_config.role_regular_weight
    
    def apply_time_multiplier(self, timestamp: Optional[datetime]) -> float:
        """Apply time of access multiplier."""
        if not timestamp:
            return self.multiplier_config.time_normal_weight
        
        hour = timestamp.hour
        
        # Before 7am
        if hour < 7:
            return self.multiplier_config.time_before_7am_weight
        # After 8pm
        elif hour >= 20:
            return self.multiplier_config.time_after_8pm_weight
        else:
            return self.multiplier_config.time_normal_weight
    
    def apply_data_sensitivity_multiplier(self, data_flags: Optional[List[str]]) -> float:
        """Apply data sensitivity multiplier."""
        if not data_flags:
            return self.multiplier_config.data_normal_weight
        
        flags_lower = [f.lower() for f in data_flags]
        
        if "confidential" in flags_lower:
            return self.multiplier_config.data_confidential_weight
        elif any(f in flags_lower for f in ["removable_media", "removable media", "usb", "external"]):
            return self.multiplier_config.data_removable_media_weight
        else:
            return self.multiplier_config.data_normal_weight
    
    def apply_score_decay(self, days_since_last_anomaly: int, max_decay_days: int = 30) -> float:
        """
        Apply score decay - gradual weight reduction for each day without new anomalous activity.
        
        Args:
            days_since_last_anomaly: Number of days since last anomalous activity
            max_decay_days: Days after which score is fully decayed
            
        Returns:
            Decay factor (0-1)
        """
        if days_since_last_anomaly <= 0:
            return 1.0
        
        # Linear decay: 1.0 at day 0, 0.0 at max_decay_days
        decay = max(0, 1.0 - (days_since_last_anomaly / max_decay_days))
        return round(decay, 4)
    
    def compute_risk_score(
        self,
        self_score: float,
        peer_score: float,
        drift_score: float,
        role: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        data_flags: Optional[List[str]] = None,
        days_since_last_anomaly: int = 0,
        fallback_applied: bool = False
    ) -> FusionResult:
        """
        Compute the full 0-100 risk score with all adjustments.
        
        Args:
            self_score: Isolation Forest anomaly score (0-1)
            peer_score: Z-score deviation vs peer cohort (0-1)
            drift_score: CUSUM drift score (0-1)
            role: User's role (for role multiplier)
            timestamp: Timestamp of activity (for time multiplier)
            data_flags: Data sensitivity flags (for data sensitivity multiplier)
            days_since_last_anomaly: Days since last anomalous activity
            fallback_applied: Whether department fallback was used
            
        Returns:
            FusionResult with complete score breakdown
        """
        # Step 1: Compute pre-multiplier score (LOCKED for CUSUM)
        pre_multiplier_score = self.compute_pre_multiplier_score(self_score, peer_score)
        
        # Step 2: Compute raw fusion (before multipliers)
        raw_fusion = self.compute_raw_fusion(self_score, peer_score, drift_score)
        
        # Step 3: Apply multipliers
        role_mult = self.apply_role_multiplier(role)
        time_mult = self.apply_time_multiplier(timestamp)
        data_mult = self.apply_data_sensitivity_multiplier(data_flags)
        
        # Combined multiplier (product of all applicable)
        combined_multiplier = role_mult * time_mult * data_mult
        
        # Step 4: Apply score decay
        decay_factor = self.apply_score_decay(days_since_last_anomaly)
        
        # Step 5: Compute adjusted fusion score
        adjusted_fusion = raw_fusion * combined_multiplier * decay_factor
        
        # Step 6: Normalize to 0-100 range
        # Clamp to valid range and scale
        normalized = np.clip(adjusted_fusion, 0, 1) * 100
        
        return FusionResult(
            user_id="unknown",  # Will be set by caller
            risk_score=round(normalized, 1),
            self_score=self_score,
            peer_score=peer_score,
            drift_score=drift_score,
            pre_multiplier_score=pre_multiplier_score,
            raw_fusion_score=raw_fusion,
            adjusted_fusion_score=adjusted_fusion,
            multipliers_applied={
                "role": role_mult,
                "time": time_mult,
                "data_sensitivity": data_mult,
                "decay": decay_factor
            },
            score_components={
                "self": self_score,
                "peer": peer_score,
                "drift": drift_score,
                "raw_fusion": raw_fusion,
                "adjusted_fusion": adjusted_fusion
            }
        )


# Default engine instance
default_fusion_engine = RiskFusionEngine()
