"""
API endpoints for EDC exposure tracking and reporting

Endpoints:
- GET /exposure/report: Generate exposure report for a user
- GET /exposure/trends: Get exposure trends over time
- GET /exposure/alerts: Get exposure alerts for a user
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.sqlite_manager import get_db
from app.services.exposure_aggregation_service import (
    ExposureAggregationService,
    PeriodType,
    ExposureReport
)
from app.services.exposure_alert_service import (
    ExposureAlertService,
    AlertConfig
)


router = APIRouter()


@router.get("/report")
async def get_exposure_report(
    user_id: int = Query(..., description="User ID"),
    period_type: str = Query("monthly", description="Period type: daily, weekly, or monthly"),
    period_start: Optional[str] = Query(None, description="Period start date (ISO format)"),
    period_end: Optional[str] = Query(None, description="Period end date (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive EDC exposure report for a user
    
    Returns:
    - Total exposure score
    - Exposure breakdown by EDC type and product category
    - Comparison to EPA safe limits
    - Top contributing products
    - Trend data
    - Personalized recommendations
    """
    try:
        # Validate period type
        try:
            period_type_enum = PeriodType(period_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period_type. Must be one of: daily, weekly, monthly"
            )
        
        # Parse dates if provided
        period_start_dt = None
        period_end_dt = None
        
        if period_start:
            try:
                period_start_dt = datetime.fromisoformat(period_start)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid period_start format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        if period_end:
            try:
                period_end_dt = datetime.fromisoformat(period_end)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid period_end format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Create service and generate report
        service = ExposureAggregationService(db)
        report = service.generate_exposure_report(
            user_id=user_id,
            period_type=period_type_enum,
            period_start=period_start_dt,
            period_end=period_end_dt
        )
        
        logger.info(f"Generated exposure report for user {user_id}")
        
        return {
            "success": True,
            "report": report.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate exposure report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate exposure report: {str(e)}"
        )


@router.get("/trends")
async def get_exposure_trends(
    user_id: int = Query(..., description="User ID"),
    period_type: str = Query("monthly", description="Period type: daily, weekly, or monthly"),
    num_periods: int = Query(6, description="Number of periods to include", ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Get exposure trends over multiple time periods
    
    Returns historical exposure data for trend analysis and visualization
    """
    try:
        # Validate period type
        try:
            period_type_enum = PeriodType(period_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period_type. Must be one of: daily, weekly, monthly"
            )
        
        # Create service
        service = ExposureAggregationService(db)
        
        # Calculate trend data
        current_time = datetime.utcnow()
        trend_data = service._calculate_trend_data(
            user_id=user_id,
            period_type=period_type_enum,
            current_period_start=current_time,
            num_periods=num_periods
        )
        
        logger.info(f"Retrieved exposure trends for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "period_type": period_type,
            "num_periods": num_periods,
            "trends": trend_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exposure trends: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exposure trends: {str(e)}"
        )


@router.get("/current")
async def get_current_exposure(
    user_id: int = Query(..., description="User ID"),
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get current cumulative exposure for a user
    
    Quick endpoint for checking current exposure status without full report generation
    """
    try:
        from datetime import timedelta
        
        # Create service
        service = ExposureAggregationService(db)
        
        # Calculate exposure for the specified period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        
        exposure_data = service.calculate_cumulative_exposure(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end
        )
        
        # Determine appropriate period type for EPA comparison
        if days <= 1:
            period_type = PeriodType.DAILY
        elif days <= 7:
            period_type = PeriodType.WEEKLY
        else:
            period_type = PeriodType.MONTHLY
        
        # Compare to EPA limits
        epa_limit, percent_of_limit, status = service.compare_to_epa_limits(
            exposure_data.total_exposure,
            period_type
        )
        
        logger.info(f"Retrieved current exposure for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "period_days": days,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_exposure": exposure_data.total_exposure,
            "exposure_by_type": exposure_data.exposure_by_type,
            "exposure_by_category": exposure_data.exposure_by_category,
            "scan_count": exposure_data.scan_count,
            "epa_limit": epa_limit,
            "percent_of_limit": percent_of_limit,
            "status": status.value,
            "top_sources": exposure_data.top_sources
        }
    
    except Exception as e:
        logger.error(f"Failed to get current exposure: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current exposure: {str(e)}"
        )


@router.get("/visualization-data")
async def get_visualization_data(
    user_id: int = Query(..., description="User ID"),
    period_type: str = Query("monthly", description="Period type: daily, weekly, or monthly"),
    db: Session = Depends(get_db)
):
    """
    Get data formatted for visualization (charts, graphs)
    
    Returns data optimized for frontend visualization libraries
    """
    try:
        # Validate period type
        try:
            period_type_enum = PeriodType(period_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period_type. Must be one of: daily, weekly, monthly"
            )
        
        # Generate full report
        service = ExposureAggregationService(db)
        report = service.generate_exposure_report(
            user_id=user_id,
            period_type=period_type_enum
        )
        
        # Format for visualization
        visualization_data = {
            "exposure_by_type_chart": {
                "labels": list(report.exposure_by_type.keys()),
                "values": list(report.exposure_by_type.values()),
                "chart_type": "pie"
            },
            "exposure_by_category_chart": {
                "labels": list(report.exposure_by_category.keys()),
                "values": list(report.exposure_by_category.values()),
                "chart_type": "bar"
            },
            "trend_chart": {
                "labels": [t["period_start"][:10] for t in report.trend_data],
                "values": [t["total_exposure"] for t in report.trend_data],
                "chart_type": "line"
            },
            "epa_limit_gauge": {
                "current": report.total_exposure,
                "limit": report.epa_limit,
                "percent": report.percent_of_limit,
                "status": report.status,
                "chart_type": "gauge"
            },
            "top_sources_table": report.top_sources
        }
        
        logger.info(f"Generated visualization data for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "period_type": period_type,
            "visualization_data": visualization_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get visualization data: {str(e)}"
        )



@router.get("/alerts")
async def get_exposure_alerts(
    user_id: int = Query(..., description="User ID"),
    unacknowledged_only: bool = Query(False, description="Only return unacknowledged alerts"),
    limit: int = Query(10, description="Maximum number of alerts to return", ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get exposure alerts for a user
    
    Returns alerts for:
    - Weekly limit exceeded
    - Approaching safe limits
    - Increasing exposure trends
    - High EDC type concentrations
    - Critical exposure sources
    """
    try:
        # Create alert service
        alert_service = ExposureAlertService(db)
        
        # Get alerts
        alerts = alert_service.get_user_alerts(
            user_id=user_id,
            unacknowledged_only=unacknowledged_only,
            limit=limit
        )
        
        # Format alerts for response
        alert_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "reduction_strategies": alert.reduction_strategies,
                "primary_edc_sources": alert.primary_edc_sources,
                "sent": alert.sent,
                "acknowledged": alert.acknowledged,
                "created_at": alert.created_at.isoformat(),
                "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
            }
            for alert in alerts
        ]
        
        logger.info(f"Retrieved {len(alerts)} alerts for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "alert_count": len(alerts),
            "alerts": alert_data
        }
    
    except Exception as e:
        logger.error(f"Failed to get exposure alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exposure alerts: {str(e)}"
        )


@router.post("/alerts/check")
async def check_exposure_alerts(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Check exposure levels and create alerts if thresholds are exceeded
    
    This endpoint should be called:
    - After each product scan
    - On a scheduled basis (e.g., weekly)
    - When user requests exposure report
    
    Returns newly created alerts
    """
    try:
        # Create alert service
        alert_service = ExposureAlertService(db)
        
        # Check and create alerts
        new_alerts = alert_service.check_and_create_alerts(user_id)
        
        # Format alerts for response
        alert_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "reduction_strategies": alert.reduction_strategies,
                "primary_edc_sources": alert.primary_edc_sources,
                "created_at": alert.created_at.isoformat()
            }
            for alert in new_alerts
        ]
        
        logger.info(f"Created {len(new_alerts)} new alerts for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "new_alert_count": len(new_alerts),
            "alerts": alert_data
        }
    
    except Exception as e:
        logger.error(f"Failed to check exposure alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check exposure alerts: {str(e)}"
        )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as acknowledged by the user
    """
    try:
        # Create alert service
        alert_service = ExposureAlertService(db)
        
        # Acknowledge alert
        success = alert_service.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found"
            )
        
        logger.info(f"Alert {alert_id} acknowledged")
        
        return {
            "success": True,
            "alert_id": alert_id,
            "message": "Alert acknowledged successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post("/alerts/{alert_id}/mark-sent")
async def mark_alert_sent(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as sent (for notification tracking)
    
    This endpoint is typically called by the notification service
    after successfully sending an alert notification
    """
    try:
        # Create alert service
        alert_service = ExposureAlertService(db)
        
        # Mark as sent
        success = alert_service.mark_alert_sent(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found"
            )
        
        logger.info(f"Alert {alert_id} marked as sent")
        
        return {
            "success": True,
            "alert_id": alert_id,
            "message": "Alert marked as sent successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark alert as sent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark alert as sent: {str(e)}"
        )
