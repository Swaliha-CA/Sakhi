"""ASHA Dashboard API endpoints"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.sqlite_manager import get_db
from app.services.asha_service import (
    get_asha_service,
    ASHAService,
    Intervention,
    InterventionType
)
from app.core.logging import logger


router = APIRouter(prefix="/asha", tags=["ASHA Dashboard"])


# Request/Response Models
class InterventionRequest(BaseModel):
    """Request model for logging intervention"""
    asha_id: int = Field(..., description="ASHA worker ID")
    user_id: int = Field(..., description="User ID")
    intervention_type: str = Field(..., description="Type of intervention")
    notes: str = Field(..., description="Intervention notes")
    outcome: str = Field(..., description="Intervention outcome")
    follow_up_date: Optional[str] = Field(None, description="Follow-up date (ISO format)")
    conducted_at: Optional[str] = Field(None, description="Intervention date (ISO format)")


class CaseloadResponse(BaseModel):
    """Response model for caseload"""
    asha_id: int
    total_cases: int
    high_risk_cases: int
    critical_cases: int
    pending_screenings: int
    recent_alerts: List[dict]
    cases: List[dict]


class AlertAggregationResponse(BaseModel):
    """Response model for alert aggregation"""
    by_type: dict
    by_priority: dict
    stats: dict


class ReportResponse(BaseModel):
    """Response model for ASHA report"""
    asha_id: int
    asha_name: str
    report_period: str
    total_interventions: int
    home_visits: int
    phone_counseling: int
    referrals: int
    screenings_conducted: int
    high_risk_cases_identified: int
    successful_referrals: int
    ppd_cases_prevented: int
    total_assigned_users: int
    active_users: int
    generated_at: str


@router.get("/caseload/{asha_id}", response_model=CaseloadResponse)
async def get_caseload(
    asha_id: int,
    filter_risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    sort_by: str = Query("risk_level", description="Sort criteria"),
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Get ASHA worker's caseload with all assigned users
    
    **Query Parameters:**
    - filter_risk_level: Filter by risk level (critical, high, moderate, low)
    - sort_by: Sort criteria (risk_level, last_contact, name)
    
    **Returns:**
    - Caseload with health status indicators for all assigned users
    - Recent alerts with priority flagging
    - Pending screenings and upcoming tasks
    """
    try:
        logger.info(f"API: Getting caseload for ASHA {asha_id}")
        
        caseload = asha_service.get_caseload(
            db=db,
            asha_id=asha_id,
            filter_risk_level=filter_risk_level,
            sort_by=sort_by
        )
        
        # Convert to response format
        return CaseloadResponse(
            asha_id=caseload.asha_id,
            total_cases=caseload.total_cases,
            high_risk_cases=caseload.high_risk_cases,
            critical_cases=caseload.critical_cases,
            pending_screenings=caseload.pending_screenings,
            recent_alerts=[
                {
                    "alert_id": a.alert_id,
                    "user_id": a.user_id,
                    "user_name": a.user_name,
                    "alert_type": a.alert_type.value,
                    "priority": a.priority.value,
                    "title": a.title,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                    "acknowledged": a.acknowledged
                }
                for a in caseload.recent_alerts
            ],
            cases=[
                {
                    "user_id": c.user_id,
                    "user_name": c.user_name,
                    "age": c.age,
                    "location": c.location,
                    "risk_level": c.risk_level,
                    "last_contact": c.last_contact.isoformat() if c.last_contact else None,
                    "recent_screenings": c.recent_screenings,
                    "recent_lab_results": c.recent_lab_results,
                    "recent_product_scans": c.recent_product_scans,
                    "ppd_risk_score": c.ppd_risk_score,
                    "micronutrient_deficiencies": c.micronutrient_deficiencies,
                    "edc_exposure_level": c.edc_exposure_level,
                    "upcoming_tasks": c.upcoming_tasks,
                    "pending_screenings": c.pending_screenings
                }
                for c in caseload.cases
            ]
        )
    
    except Exception as e:
        logger.error(f"Error getting caseload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-risk-cases/{asha_id}")
async def get_high_risk_cases(
    asha_id: int,
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Get only high-risk and critical cases for quick triage
    
    **Returns:**
    - List of high-risk and critical cases requiring immediate attention
    """
    try:
        logger.info(f"API: Getting high-risk cases for ASHA {asha_id}")
        
        high_risk_cases = asha_service.get_high_risk_cases(db=db, asha_id=asha_id)
        
        return {
            "asha_id": asha_id,
            "high_risk_count": len(high_risk_cases),
            "cases": [
                {
                    "user_id": c.user_id,
                    "user_name": c.user_name,
                    "age": c.age,
                    "location": c.location,
                    "risk_level": c.risk_level,
                    "ppd_risk_score": c.ppd_risk_score,
                    "micronutrient_deficiencies": c.micronutrient_deficiencies,
                    "upcoming_tasks": c.upcoming_tasks,
                    "last_contact": c.last_contact.isoformat() if c.last_contact else None
                }
                for c in high_risk_cases
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting high-risk cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/case-summary/{user_id}")
async def get_case_summary(
    user_id: int,
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Get detailed case summary for a specific user
    
    **Returns:**
    - Comprehensive case summary with recent screenings, lab results, exposure logs
    - Risk trends and upcoming tasks
    """
    try:
        logger.info(f"API: Getting case summary for user {user_id}")
        
        from app.db.models import User
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        case_summary = asha_service._build_case_summary(db, user)
        
        return {
            "user_id": case_summary.user_id,
            "user_name": case_summary.user_name,
            "age": case_summary.age,
            "location": case_summary.location,
            "risk_level": case_summary.risk_level,
            "last_contact": case_summary.last_contact.isoformat() if case_summary.last_contact else None,
            "recent_screenings": case_summary.recent_screenings,
            "recent_lab_results": case_summary.recent_lab_results,
            "recent_product_scans": case_summary.recent_product_scans,
            "ppd_risk_score": case_summary.ppd_risk_score,
            "micronutrient_deficiencies": case_summary.micronutrient_deficiencies,
            "edc_exposure_level": case_summary.edc_exposure_level,
            "upcoming_tasks": case_summary.upcoming_tasks,
            "pending_screenings": case_summary.pending_screenings
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervention")
async def log_intervention(
    request: InterventionRequest,
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Log an ASHA intervention
    
    **Request Body:**
    - asha_id: ASHA worker ID
    - user_id: User ID
    - intervention_type: Type of intervention (home_visit, phone_counseling, etc.)
    - notes: Intervention notes
    - outcome: Intervention outcome
    - follow_up_date: Optional follow-up date
    - conducted_at: Optional intervention date (defaults to now)
    
    **Returns:**
    - Logged intervention with ID
    """
    try:
        logger.info(f"API: Logging intervention for user {request.user_id}")
        
        # Parse dates
        follow_up_date = None
        if request.follow_up_date:
            follow_up_date = datetime.fromisoformat(request.follow_up_date.replace('Z', '+00:00'))
        
        conducted_at = datetime.utcnow()
        if request.conducted_at:
            conducted_at = datetime.fromisoformat(request.conducted_at.replace('Z', '+00:00'))
        
        # Validate intervention type
        try:
            intervention_type = InterventionType(request.intervention_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid intervention type: {request.intervention_type}"
            )
        
        # Create intervention
        intervention = Intervention(
            intervention_id=None,
            asha_id=request.asha_id,
            user_id=request.user_id,
            intervention_type=intervention_type,
            notes=request.notes,
            outcome=request.outcome,
            follow_up_date=follow_up_date,
            conducted_at=conducted_at
        )
        
        result = asha_service.log_intervention(db=db, intervention=intervention)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging intervention: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{asha_id}", response_model=AlertAggregationResponse)
async def get_aggregated_alerts(
    asha_id: int,
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Get aggregated alerts by type and priority
    
    **Returns:**
    - Alerts grouped by type (PPD risk, nutritional deficiency, etc.)
    - Alerts grouped by priority (critical, high, moderate, low)
    - Alert statistics
    """
    try:
        logger.info(f"API: Getting aggregated alerts for ASHA {asha_id}")
        
        aggregation = asha_service.aggregate_alerts(db=db, asha_id=asha_id)
        
        return AlertAggregationResponse(
            by_type=aggregation["by_type"],
            by_priority=aggregation["by_priority"],
            stats=aggregation["stats"]
        )
    
    except Exception as e:
        logger.error(f"Error getting aggregated alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{asha_id}", response_model=ReportResponse)
async def generate_report(
    asha_id: int,
    days: int = Query(30, description="Report period in days"),
    db: Session = Depends(get_db),
    asha_service: ASHAService = Depends(get_asha_service)
):
    """
    Generate ASHA performance report
    
    **Query Parameters:**
    - days: Report period in days (default: 30)
    
    **Returns:**
    - Performance metrics (interventions, referrals, screenings)
    - Outcome metrics (high-risk cases identified, successful referrals)
    - Caseload metrics
    """
    try:
        logger.info(f"API: Generating report for ASHA {asha_id} ({days} days)")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        report = asha_service.generate_report(
            db=db,
            asha_id=asha_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return ReportResponse(
            asha_id=report.asha_id,
            asha_name=report.asha_name,
            report_period=report.report_period,
            total_interventions=report.total_interventions,
            home_visits=report.home_visits,
            phone_counseling=report.phone_counseling,
            referrals=report.referrals,
            screenings_conducted=report.screenings_conducted,
            high_risk_cases_identified=report.high_risk_cases_identified,
            successful_referrals=report.successful_referrals,
            ppd_cases_prevented=report.ppd_cases_prevented,
            total_assigned_users=report.total_assigned_users,
            active_users=report.active_users,
            generated_at=report.generated_at.isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for ASHA Dashboard API"""
    return {
        "status": "healthy",
        "service": "ASHA Dashboard API",
        "timestamp": datetime.utcnow().isoformat()
    }
