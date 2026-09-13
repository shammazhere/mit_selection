"""
Explanation Generator

Creates templated natural-language explanations from fusion inputs.
Explicitly discloses when department-level cohort fallback was used.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class ExplanationResult:
    """Generated explanation for a risk alert."""
    user_id: str
    explanation_text: str
    fallback_disclosed: bool
    explanation_components: Dict[str, Any]


class ExplanationGenerator:
    """
    Generates plain-English explanations from fusion inputs.
    
    The explanation includes:
    - Self-baseline indication
    - Peer-cohort indication with fallback disclosure
    - Drift trend indication
    - Severity assessment
    
    Follows the specification's "explanation-first" design philosophy.
    """
    
    def __init__(self):
        self.min_cohort_size_for_role = 5
        self.min_cohort_size_for_department = 3
    
    def generate_explanation(
        self,
        self_score: float,
        peer_score: float,
        drift_score: float,
        cohort_used: Optional[str] = None,
        cohort_size: Optional[int] = None,
        fallback_applied: bool = False,
        days_of_drift: Optional[int] = None,
        max_drift_path_value: Optional[float] = None,
        role: Optional[str] = None
    ) -> ExplanationResult:
        """
        Generate a plain-English explanation from fusion inputs.
        
        Args:
            self_score: Self-baseline anomaly score (0-1)
            peer_score: Peer-cohort deviation score (0-1)
            drift_score: CUSUM drift score (0-1)
            cohort_used: "role" or "department" - which cohort was used
            cohort_size: Number of peers in the cohort
            fallback_applied: Whether department fallback was used
            days_of_drift: Number of consecutive days of drift
            max_drift_path_value: Maximum value in CUSUM path
            role: User's role for context
            
        Returns:
            ExplanationResult with full explanation text
        """
        components = {
            "self_baseline": {},
            "peer_baseline": {},
            "drift": {},
            "severity": {}
        }
        
        # Generate self-baseline component
        self_component = self._generate_self_baseline_component(self_score)
        components["self_baseline"] = self_component
        
        # Generate peer-baseline component
        peer_component = self._generate_peer_baseline_component(
            peer_score, cohort_used, cohort_size, fallback_applied
        )
        components["peer_baseline"] = peer_component
        
        # Generate drift component
        drift_component = self._generate_drift_component(
            drift_score, days_of_drift, max_drift_path_value
        )
        components["drift"] = drift_component
        
        # Determine severity and store as dict
        severity = self._assess_severity(self_score, peer_score, drift_score)
        components["severity"] = {"severity": severity}
        
        # Build final explanation text
        explanation_text = self._build_explanation_text(components, role)
        
        return ExplanationResult(
            user_id="unknown",  # Will be set by caller
            explanation_text=explanation_text,
            fallback_disclosed=fallback_applied,
            explanation_components=components
        )
    
    def _generate_self_baseline_component(self, self_score: float) -> Dict[str, Any]:
        """Generate self-baseline explanation component."""
        if self_score >= 0.8:
            text = f"activity is unlike this user's own {self._describe_history_period()} history"
            severity = "high"
        elif self_score >= 0.6:
            text = f"activity shows moderate deviation from this user's normal pattern"
            severity = "medium"
        else:
            text = f"activity shows slight deviation from normal pattern"
            severity = "low"
        
        return {
            "text": text,
            "raw_score": self_score,
            "severity": severity,
            "indicator": "self_baseline"
        }
    
    def _generate_peer_baseline_component(
        self,
        peer_score: float,
        cohort_used: Optional[str],
        cohort_size: Optional[int],
        fallback_applied: bool
    ) -> Dict[str, Any]:
        """Generate peer-baseline explanation component."""
        if peer_score >= 0.8:
            text = f"unlike their {self._describe_cohort_type(cohort_used)} cohort's typical pattern"
            severity = "high"
        elif peer_score >= 0.6:
            text = f"deviates moderately from {self._describe_cohort_type(cohort_used)} peers"
            severity = "medium"
        else:
            text = f"slight deviation from peer cohort norms"
            severity = "low"
        
        # Add fallback disclosure if applicable
        if fallback_applied:
            text = f"Compared against {self._describe_cohort_type(cohort_used)} peers; fell back to department-level comparison because the role cohort had only {cohort_size} members"
        
        return {
            "text": text,
            "raw_score": peer_score,
            "severity": severity,
            "indicator": "peer_baseline",
            "fallback_applied": fallback_applied
        }
    
    def _generate_drift_component(
        self,
        drift_score: float,
        days_of_drift: Optional[int],
        max_drift_path_value: Optional[float]
    ) -> Dict[str, Any]:
        """Generate drift explanation component."""
        if drift_score >= 0.7:
            if days_of_drift and days_of_drift >= 5:
                text = f"has trended upward for {days_of_drift} consecutive days"
            else:
                text = f"shows sustained upward drift pattern"
            severity = "high"
        elif drift_score >= 0.4:
            text = f"shows moderate drift trend"
            severity = "medium"
        else:
            text = f"slight drift trend observed"
            severity = "low"
        
        return {
            "text": text,
            "raw_score": drift_score,
            "days_of_drift": days_of_drift,
            "max_path_value": max_drift_path_value,
            "severity": severity,
            "indicator": "drift"
        }
    
    def _assess_severity(
        self,
        self_score: float,
        peer_score: float,
        drift_score: float
    ) -> str:
        """Assess overall severity level."""
        # Weighted combination for severity assessment
        weighted_sum = self_score * 0.3 + peer_score * 0.3 + drift_score * 0.4
        
        if weighted_sum >= 0.7:
            return "critical"
        elif weighted_sum >= 0.5:
            return "high"
        elif weighted_sum >= 0.3:
            return "medium"
        else:
            return "low"
    
    def _describe_history_period(self) -> str:
        """Describe the historical period used for self-baseline."""
        return "90-day"
    
    def _describe_cohort_type(self, cohort_used: Optional[str]) -> str:
        """Describe the cohort type in plain language."""
        if cohort_used == "role":
            return "role"
        elif cohort_used == "department":
            return "department"
        return "peer"
    
    def _build_explanation_text(self, components: Dict[str, Any], role: Optional[str]) -> str:
        """Build final explanation text from components."""
        parts = []
        
        # Start with severity header
        severity = components["severity"]["severity"]
        if severity == "critical":
            parts.append("HIGH ALERT")
        elif severity == "high":
            parts.append("Elevated Risk")
        elif severity == "medium":
            parts.append("Moderate Risk")
        else:
            parts.append("Low Risk")
        
        parts.append(f"Flagged: {components['self_baseline']['text']}")
        
        # Add peer component
        parts.append(components['peer_baseline']['text'])
        
        # Add drift component
        parts.append(f"and {components['drift']['text']}.")
        
        return " ".join(parts)


# Default generator instance
default_explanation_generator = ExplanationGenerator()
