"""
Main FastAPI Application

Implements the Contract B endpoints:
- GET /queue - Ranked risk queue
- GET /case/{user_id} - Case detail view
- POST /feedback - Record false positive feedback
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime, timedelta
import os
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drift.cusum import compute_cusum_for_user, default_detector
from fusion.fusion import default_fusion_engine, FusionResult
from fusion.fusion import MultiplierConfig
from explain.generator import default_explanation_generator
from api.models import (
    QueueItem,
    QueueResponse,
    CaseDetailResponse,
    FeedbackRequest,
    FeedbackResponse,
    ErrorResponse
)
from api.database import Database

# Initialize FastAPI app
app = FastAPI(
    title="Silent Shift API",
    description="Backend API for insider threat detection",
    version="1.0.0"
)

# Initialize database
db = Database("data/scores.db")

# Mock user data for demo purposes
MOCK_USER_DATA = {
    "u001": {"name": "Alice Chen", "role": "Senior Engineer"},
    "u002": {"name": "Bob Smith", "role": "IT Administrator"},
    "u003": {"name": "Carol Johnson", "role": "Financial Analyst"},
    "u004": {"name": "David Williams", "role": "HR Manager"},
    "u005": {"name": "Eve Davis", "role": "System Administrator"},
    "u006": {"name": "Frank Miller", "role": "Software Developer"},
    "u007": {"name": "Grace Lee", "role": "Project Lead"},
    "u008": {"name": "Henry Wilson", "role": "Data Scientist"},
    "u009": {"name": "Ivy Taylor", "role": "Marketing Manager"},
    "u010": {"name": "Jack Brown", "role": "Network Engineer"}
}


def _build_event_timeline(risk_score: dict) -> list:
    """Build simulated event timeline for demo purposes."""
    timeline = []
    
    # Add events based on score components
    if risk_score.get("self_score", 0) > 0.7:
        timeline.append({
            "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "event": "Self-baseline anomaly detected - unusual activity pattern",
            "score_contribution": risk_score.get("self_score")
        })
    
    if risk_score.get("peer_score", 0) > 0.7:
        timeline.append({
            "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "event": "Peer-cohort deviation - behavior differs from role peers",
            "score_contribution": risk_score.get("peer_score")
        })
    
    if risk_score.get("drift_score", 0) > 0.5:
        timeline.append({
            "timestamp": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "event": "CUSUM drift detected - sustained upward trend",
            "score_contribution": risk_score.get("drift_score")
        })
    
    # Add fallback disclosure if applicable
    if risk_score.get("fallback_applied", False):
        timeline.append({
            "timestamp": (datetime.utcnow() - timedelta(days=0)).isoformat(),
            "event": "Department-level fallback used (role cohort too small)",
            "score_contribution": None
        })
    
    return timeline


def _assess_severity(risk_score: float) -> str:
    """Assess severity level based on risk score."""
    if risk_score >= 80:
        return "critical"
    elif risk_score >= 60:
        return "high"
    elif risk_score >= 40:
        return "medium"
    else:
        return "low"


@app.get("/queue")
async def get_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_risk_score: float = Query(0, ge=0, le=100),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$")
):
    """
    Returns the ranked list for the dashboard's main view.
    
    Users are sorted by risk_score in descending order.
    """
    try:
        # Get all risk scores from database
        risk_scores = db.get_all_risk_scores(limit=limit, offset=offset)
        
        if not risk_scores:
            return {
                "items": [],
                "total_count": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Filter by minimum risk score
        if min_risk_score > 0:
            risk_scores = [r for r in risk_scores if r.get("risk_score", 0) >= min_risk_score]
        
        # Filter by severity if specified
        if severity:
            risk_scores = [r for r in risk_scores if r.get("severity") == severity]
        
        # Build queue items
        queue_items = []
        for score in risk_scores:
            queue_items.append({
                "user_id": score.get("user_id", ""),
                "name": score.get("name", "Unknown"),
                "role": score.get("role", "Unknown"),
                "risk_score": score.get("risk_score", 0),
                "severity": score.get("severity", "low"),
                "last_updated": score.get("last_updated", "")
            })
        
        return {
            "items": queue_items,
            "total_count": len(queue_items),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching queue: {str(e)}")


@app.get("/case/{user_id}")
async def get_case(user_id: str):
    """
    Returns everything the case detail view needs.
    
    Includes score breakdown, explanation, and forensic details.
    """
    try:
        # Get today's date
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Get risk score from database
        risk_score = db.get_risk_score(user_id, today)
        
        if not risk_score:
            raise HTTPException(status_code=404, detail=f"Risk score not found for user {user_id}")
        
        # Build event timeline (simulated for demo)
        event_timeline = _build_event_timeline(risk_score)
        
        # Build response
        return {
            "user_id": risk_score.get("user_id", ""),
            "risk_score": risk_score.get("risk_score", 0),
            "self_score": risk_score.get("self_score", 0),
            "peer_score": risk_score.get("peer_score", 0),
            "drift_score": risk_score.get("drift_score", 0),
            "pre_multiplier_score": risk_score.get("pre_multiplier_score", 0),
            "raw_fusion_score": risk_score.get("raw_fusion_score", 0),
            "adjusted_fusion_score": risk_score.get("adjusted_fusion_score", 0),
            "cohort_used": risk_score.get("cohort_used", "department"),
            "cohort_size": risk_score.get("cohort_size", 10),
            "fallback_applied": risk_score.get("fallback_applied", False),
            "explanation_text": risk_score.get("explanation_text", ""),
            "cusum_path": risk_score.get("cusum_path", []),
            "event_timeline": event_timeline,
            "severity": risk_score.get("severity", "low"),
            "multipliers_applied": risk_score.get("multipliers_applied", {}),
            "score_components": risk_score.get("score_components", {}),
            "last_updated": risk_score.get("last_updated", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching case: {str(e)}")


@app.post("/feedback")
async def post_feedback(feedback: dict):
    """
    Records an investigator's false-positive decision.
    
    The fusion engine uses this to down-weight that signal combination going forward.
    """
    try:
        user_id = feedback.get("user_id")
        is_false_positive = feedback.get("is_false_positive", False)
        reason = feedback.get("reason")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Record feedback in database
        feedback_result = db.record_feedback(
            user_id=user_id,
            is_false_positive=is_false_positive,
            reason=reason
        )
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully",
            "feedback_id": str(feedback_result.get("feedback_id")),
            "timestamp": feedback_result.get("timestamp", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Error handlers

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": str(exc.detail),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
