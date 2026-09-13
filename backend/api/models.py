"""
API Data Models

Simple data containers (no pydantic dependency).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Contract A Input Model (read-only - for reference)
@dataclass
class DailyUserScore:
    """Represents one row of Contract A input data."""
    user_id: str
    date: str  # ISO format date
    self_score: float
    peer_score: float
    cohort_used: str
    cohort_size: int
    fallback_applied: bool
    role: str


# Contract B - Queue Response
@dataclass
class QueueItem:
    """Single item in the ranked queue (GET /queue response)."""
    user_id: str
    name: str
    role: str
    risk_score: float
    severity: str  # "low" | "medium" | "high" | "critical"
    last_updated: str  # ISO format date


@dataclass
class QueueResponse:
    """Response for GET /queue endpoint."""
    items: List[QueueItem]
    total_count: int
    timestamp: str


# Contract B - Case Detail Response
@dataclass
class EventTimelineItem:
    """Single item in the event timeline."""
    timestamp: str
    event: str
    score_contribution: Optional[float] = None


@dataclass
class CaseDetailResponse:
    """Response for GET /case/{user_id} endpoint."""
    user_id: str
    risk_score: float
    self_score: float
    peer_score: float
    drift_score: float
    pre_multiplier_score: float
    raw_fusion_score: float
    adjusted_fusion_score: float
    cohort_used: str
    cohort_size: int
    fallback_applied: bool
    explanation_text: str
    cusum_path: List[float]
    event_timeline: List[EventTimelineItem]
    severity: str
    multipliers_applied: Dict[str, float]
    score_components: Dict[str, float]
    last_updated: str


# Contract B - Feedback Request/Response
@dataclass
class FeedbackRequest:
    """Request body for POST /feedback endpoint."""
    user_id: str
    is_false_positive: bool
    reason: Optional[str] = None


@dataclass
class FeedbackResponse:
    """Response for POST /feedback endpoint."""
    timestamp: str
    status: str  # "success" | "error"
    message: str
    feedback_id: Optional[str] = None


# API Error Responses
@dataclass
class ErrorResponse:
    """Standard error response."""
    error: str
    message: str
    timestamp: str


@dataclass
class ValidationErrorResponse:
    """Validation error response."""
    error: str
    details: List[Dict[str, Any]]
    timestamp: str
