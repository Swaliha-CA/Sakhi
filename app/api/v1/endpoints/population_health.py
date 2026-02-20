"""
Population Health Dashboard API Endpoints

Provides endpoints for public health authorities to access population health
dashboards, aggregate metrics, risk patterns, and generate reports.

Requirements: 15.4, 15.5
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.services.population_health_dashboard_service import PopulationHealthDashboardService


router = APIRouter()
dashboard_service = PopulationHealthDashboardService()


# Request/Response Models

class TimeRangeRequest(BaseModel):
    """Time range for filtering data"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class DashboardMetricsRequest(BaseModel):
    """Request for dashboard metrics"""
    group_by: Optional[List[str]] = None
    time_range: Optional[TimeRangeRequest] = None


class ReportRequest(BaseModel):
    """Request for generating health authority report"""
    report_type: str = 'comprehensive'  # comprehensive, summary, trends
    time_range: Optional[TimeRangeRequest] = None


# Endpoints

@router.get("/metrics")
async def get_aggregate_metrics(
    group_by: Optional[str] = Query(None, description="Comma-separated list of fields to group by"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering")
):
    """
    Get aggregate health metrics for population health dashboard
    
    Returns aggregate metrics grouped by demographics (age_group, region, etc.)
    """
    try:
        # Parse group_by parameter
        group_by_list = group_by.split(',') if group_by else None
        
        # Parse time range
        time_range = None
        if start_date or end_date:
            time_range = {
                'start_date': start_date,
                'end_date': end_date
            }
        
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        metrics = dashboard_service.get_aggregate_metrics(
            user_records,
            group_by=group_by_list,
            time_range=time_range
        )
        
        return {
            "success": True,
            "data": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edc-exposure-patterns")
async def get_edc_exposure_patterns(
    group_by: Optional[str] = Query(None, description="Comma-separated list of fields to group by")
):
    """
    Get EDC exposure patterns across demographics
    
    Returns patterns of EDC exposure (BPA, phthalates, etc.) by demographic groups
    """
    try:
        # Parse group_by parameter
        group_by_list = group_by.split(',') if group_by else None
        
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        patterns = dashboard_service.get_edc_exposure_patterns(
            user_records,
            group_by=group_by_list
        )
        
        return {
            "success": True,
            "data": patterns
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/condition-prevalence")
async def get_condition_prevalence(
    conditions: Optional[str] = Query(None, description="Comma-separated list of conditions to analyze")
):
    """
    Get prevalence rates for specific health conditions
    
    Returns prevalence rates for PCOS, PPD, anemia, etc. by demographic groups
    """
    try:
        # Parse conditions parameter
        conditions_list = conditions.split(',') if conditions else None
        
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        prevalence = dashboard_service.get_condition_prevalence(
            user_records,
            conditions=conditions_list
        )
        
        return {
            "success": True,
            "data": prevalence
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anemia-rates")
async def get_anemia_rates(
    group_by: Optional[str] = Query(None, description="Comma-separated list of fields to group by")
):
    """
    Get anemia prevalence rates across demographics
    
    Returns anemia rates by age group, region, and reproductive stage
    """
    try:
        # Parse group_by parameter
        group_by_list = group_by.split(',') if group_by else None
        
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        anemia_data = dashboard_service.get_anemia_rates(
            user_records,
            group_by=group_by_list
        )
        
        return {
            "success": True,
            "data": anemia_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-patterns")
async def detect_risk_patterns():
    """
    Detect emerging risk patterns in population health data
    
    Returns detected risk patterns including:
    - EDC-PCOS correlations
    - High prevalence rates
    - Regional patterns
    - Occupational health risks
    """
    try:
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        risk_patterns = dashboard_service.detect_risk_patterns(user_records)
        
        return {
            "success": True,
            "data": risk_patterns
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-report")
async def generate_health_authority_report(request: ReportRequest):
    """
    Generate comprehensive report for health authorities
    
    Report types:
    - comprehensive: Full report with all metrics and analysis
    - summary: Executive summary with key findings
    - trends: Trend analysis over time
    """
    try:
        # Parse time range
        time_range = None
        if request.time_range:
            time_range = {
                'start_date': request.time_range.start_date,
                'end_date': request.time_range.end_date
            }
        
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        report = dashboard_service.generate_health_authority_report(
            user_records,
            report_type=request.report_type,
            time_range=time_range
        )
        
        return {
            "success": True,
            "data": report
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard-summary")
async def get_dashboard_summary():
    """
    Get a quick summary of all key population health metrics
    
    Returns a consolidated view of:
    - Total users
    - Condition prevalence rates
    - Risk pattern counts
    - Average health scores
    """
    try:
        # For demo purposes, using empty list (in production, fetch from database)
        user_records = []
        
        # Get all key metrics
        aggregate_metrics = dashboard_service.get_aggregate_metrics(user_records)
        prevalence_data = dashboard_service.get_condition_prevalence(user_records)
        risk_patterns = dashboard_service.detect_risk_patterns(user_records)
        anemia_data = dashboard_service.get_anemia_rates(user_records)
        
        # Build summary
        summary = {
            'total_users': aggregate_metrics.get('population_metrics', {}).get('total_users', 0),
            'condition_prevalence': prevalence_data.get('overall_prevalence', {}),
            'anemia_rate': anemia_data.get('overall_anemia_rate', 0),
            'risk_patterns_detected': risk_patterns.get('total_patterns_detected', 0),
            'average_scores': {
                'toxicity': aggregate_metrics.get('population_metrics', {}).get('average_toxicity_score', 0),
                'hormonal': aggregate_metrics.get('population_metrics', {}).get('average_hormonal_score', 0)
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "data": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
