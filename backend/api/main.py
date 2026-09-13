"""
Main FastAPI Application

Implements the Contract B endpoints:
- GET /queue - Ranked risk queue
- GET /case/{user_id} - Case detail view
- POST /feedback - Record false positive feedback
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
import os
import sys
import json

# Add parent directory to path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

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

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
DB_PATH = os.environ.get("SILENT_SHIFT_DB", os.path.join(BASE_DIR, "data", "scores.db"))
db = Database(DB_PATH)


def _build_event_timeline(risk_score: dict) -> list:
    """Build simulated event timeline if concrete events not present."""
    timeline = []
    
    # Add events based on score components
    if risk_score.get("self_score", 0) >= 0.5:
        timeline.append({
            "timestamp": f"{risk_score.get('date', '2011-05-02')}T09:00:00",
            "event": f"Self-baseline anomaly detected ({risk_score.get('self_score', 0):.2f})"
        })
    
    if risk_score.get("peer_score", 0) >= 0.5:
        timeline.append({
            "timestamp": f"{risk_score.get('date', '2011-05-02')}T12:00:00",
            "event": f"Peer-cohort deviation elevated ({risk_score.get('peer_score', 0):.2f})"
        })
    
    if risk_score.get("drift_score", 0) >= 0.25:
        timeline.append({
            "timestamp": f"{risk_score.get('date', '2011-05-02')}T16:00:00",
            "event": f"CUSUM drift threshold crossed ({risk_score.get('drift_score', 0):.2f})"
        })
    
    # Add fallback disclosure if applicable
    if risk_score.get("fallback_applied", False):
        timeline.append({
            "timestamp": f"{risk_score.get('date', '2011-05-02')}T08:00:00",
            "event": f"Department-level fallback used (role cohort had only {risk_score.get('cohort_size', 2)} peers)"
        })
    
    return timeline


def _assess_severity(risk_score: float) -> str:
    """Assess severity level based on risk score."""
    if risk_score >= 80:
        return "critical"
    elif risk_score >= 65:
        return "high"
    elif risk_score >= 50:
        return "medium"
    else:
        return "low"


@app.get("/queue")
async def get_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_risk_score: float = Query(0, ge=0, le=100),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$")
):
    """
    Returns the ranked list for the dashboard's main view.
    
    Conforms directly to Contract B:
    [{ "user_id": "...", "name": "...", "role": "...", "risk_score": 78, "severity": "high", "last_updated": "..." }, ...]
    """
    try:
        # Get all risk scores from database
        risk_scores = db.get_all_risk_scores(limit=limit, offset=offset)
        
        if not risk_scores:
            return []
        
        # Filter by minimum risk score
        if min_risk_score > 0:
            risk_scores = [r for r in risk_scores if r.get("risk_score", 0) >= min_risk_score]
        
        # Filter by severity if specified
        if severity:
            risk_scores = [r for r in risk_scores if r.get("severity") == severity]
        
        # Build queue items matching Contract B JSON shape
        queue_items = []
        for score in risk_scores:
            risk = score.get("risk_score", 0)
            is_fp = bool(score.get("is_false_positive", False))
            
            queue_items.append({
                "user_id": score.get("user_id", ""),
                "name": score.get("name") or f"User {score.get('user_id', '')}",
                "role": score.get("role", "Unknown"),
                "team": score.get("team", ""),
                "risk_score": risk,
                "severity": score.get("severity", "low"),
                "last_updated": score.get("date") or score.get("last_updated", ""),
                "fallback_applied": score.get("fallback_applied", False),
                "is_false_positive": is_fp,
                "feedback_reason": score.get("feedback_reason", "")
            })
        
        # Sort descending by risk score
        queue_items.sort(key=lambda x: x["risk_score"], reverse=True)
        return queue_items
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching queue: {str(e)}")


@app.get("/case/{user_id}")
async def get_case(user_id: str):
    """
    Returns everything the case detail view needs.
    
    Includes score breakdown, explanation, and forensic details.
    """
    try:
        # Query latest risk score for user (no hardcoded date)
        risk_score = db.get_risk_score(user_id)
        
        if not risk_score:
            raise HTTPException(status_code=404, detail=f"Risk score not found for user {user_id}")
        
        # Extract or build event timeline
        event_timeline = risk_score.get("event_timeline")
        if not event_timeline or not isinstance(event_timeline, list) or len(event_timeline) == 0:
            event_timeline = _build_event_timeline(risk_score)
        
        # Ensure cusum_path is a list of floats
        cusum_path = risk_score.get("cusum_path", [])
        if isinstance(cusum_path, str):
            try:
                cusum_path = json.loads(cusum_path)
            except Exception:
                cusum_path = []
        
        # Build response matching CaseDetail
        return {
            "user_id": risk_score.get("user_id", ""),
            "name": risk_score.get("name") or f"User {risk_score.get('user_id', '')}",
            "role": risk_score.get("role", "Unknown"),
            "team": risk_score.get("team", ""),
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
            "cusum_path": cusum_path,
            "event_timeline": event_timeline,
            "severity": risk_score.get("severity", "low"),
            "multipliers_applied": risk_score.get("multipliers_applied", {}),
            "score_components": risk_score.get("score_components", {}),
            "is_false_positive": risk_score.get("is_false_positive", False),
            "feedback_reason": risk_score.get("feedback_reason", ""),
            "last_updated": risk_score.get("date") or risk_score.get("last_updated", "")
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
        
        # Record feedback in database and recalibrate risk score
        feedback_result = db.record_feedback(
            user_id=user_id,
            is_false_positive=is_false_positive,
            reason=reason
        )
        
        return {
            "ok": True,
            "status": "success",
            "message": "Feedback recorded successfully",
            "feedback_id": str(feedback_result.get("feedback_id")),
            "down_weight": feedback_result.get("down_weight", 1.0),
            "timestamp": feedback_result.get("timestamp", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")


@app.post("/simulate_threat")
async def simulate_threat_endpoint(req: dict):
    """
    Inject live custom threat activity for ANY user/actions and execute the full detection pipeline.
    """
    try:
        from simulator import inject_custom_threat
        
        name = req.get("name", "Mohammed Shamaz")
        role = req.get("role", "Engineer")
        department = req.get("department", "Engineering")
        team = req.get("team", "Platform")
        site = req.get("site", "https://wetransfer.com/upload")
        file_name = req.get("file", "confidential_customer_db.sql")
        email = req.get("email", "personal_leak@gmail.com")
        
        result = inject_custom_threat(
            name=name,
            role=role,
            department=department,
            team=team,
            site_visited=site,
            file_copied=file_name,
            external_email=email,
            include_after_hours=req.get("after_hours", True),
            include_usb=req.get("usb", True),
            include_removable_media=req.get("removable_media", True),
            include_cloud_upload=req.get("cloud_upload", True),
            include_external_email=req.get("external_email", True)
        )
        
        return {
            "ok": True,
            "status": "success",
            "user_id": result.get("user_id"),
            "name": result.get("name"),
            "role": result.get("role"),
            "risk_score": result.get("risk_score"),
            "severity": result.get("severity"),
            "explanation_text": result.get("explanation_text")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


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
