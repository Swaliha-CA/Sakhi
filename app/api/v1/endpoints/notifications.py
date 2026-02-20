"""Notification API endpoints

Provides REST API for health alert notifications:
- Send health alerts
- Update notification preferences
- Get notification history
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.sqlite_manager import get_db
from app.services.notification_service import (
    get_notification_service,
    NotificationService,
    HealthAlert,
    AlertType,
    AlertSeverity,
    NotificationChannel,
    NotificationPreferences
)
from app.core.logging import logger


router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response Models

class SendAlertRequest(BaseModel):
    """Request to send a health alert"""
    user_id: int = Field(..., description="User ID to send alert to")
    alert_type: str = Field(..., description="Type of alert (high_ppd_risk, micronutrient_deficiency, etc.)")
    severity: str = Field(..., description="Alert severity (info, warning, critical)")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    data_category: Optional[str] = Field(None, description="Data category for privacy filtering")
    action_url: Optional[str] = Field(None, description="Optional action URL")
    channels: Optional[List[str]] = Field(None, description="Optional list of channels to use")


class UpdatePreferencesRequest(BaseModel):
    """Request to update notification preferences"""
    enabled_channels: Optional[List[str]] = Field(None, description="List of enabled channels")
    quiet_hours_start: Optional[int] = Field(None, description="Quiet hours start (hour 0-23)")
    quiet_hours_end: Optional[int] = Field(None, description="Quiet hours end (hour 0-23)")
    critical_only: Optional[bool] = Field(None, description="Whether to only receive critical alerts")


class AlertResponse(BaseModel):
    """Response for alert sending"""
    status: str
    alert_type: str
    severity: str
    primary_user: dict
    helpers_notified: List[dict]
    timestamp: str


class PreferencesResponse(BaseModel):
    """Response for notification preferences"""
    user_id: int
    enabled_channels: List[str]
    quiet_hours_start: Optional[int]
    quiet_hours_end: Optional[int]
    critical_only: bool


# Endpoints

@router.post("/send-alert", response_model=AlertResponse)
async def send_health_alert(
    request: SendAlertRequest,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send a health alert to a user
    
    If the user has active buddy links, also sends to digital helpers
    who have RECEIVE_ALERTS permission and appropriate data category access.
    
    Respects:
    - Buddy link permissions
    - Privacy controls (data category permissions)
    - User notification preferences
    - Quiet hours (except for critical alerts)
    """
    try:
        # Validate alert type
        try:
            AlertType(request.alert_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert type: {request.alert_type}"
            )
        
        # Validate severity
        try:
            AlertSeverity(request.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {request.severity}"
            )
        
        # Validate channels if provided
        if request.channels:
            valid_channels = [ch.value for ch in NotificationChannel]
            invalid_channels = [ch for ch in request.channels if ch not in valid_channels]
            if invalid_channels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid channels: {invalid_channels}"
                )
        
        # Create alert
        alert = HealthAlert(
            user_id=request.user_id,
            alert_type=request.alert_type,
            severity=request.severity,
            title=request.title,
            message=request.message,
            data_category=request.data_category,
            action_url=request.action_url,
            channels=request.channels
        )
        
        # Send alert
        result = service.send_health_alert(db=db, alert=alert)
        
        return AlertResponse(**result)
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending health alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/preferences/{user_id}", response_model=PreferencesResponse)
async def update_notification_preferences(
    user_id: int,
    request: UpdatePreferencesRequest,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Update user's notification preferences
    
    Allows users to:
    - Enable/disable notification channels (push, SMS, voice, in-app)
    - Set quiet hours (no non-critical notifications during this time)
    - Enable critical-only mode (only receive critical alerts)
    """
    try:
        # Validate channels if provided
        if request.enabled_channels:
            valid_channels = [ch.value for ch in NotificationChannel]
            invalid_channels = [ch for ch in request.enabled_channels if ch not in valid_channels]
            if invalid_channels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid channels: {invalid_channels}"
                )
        
        # Update preferences
        preferences = service.update_notification_preferences(
            db=db,
            user_id=user_id,
            enabled_channels=request.enabled_channels,
            quiet_hours_start=request.quiet_hours_start,
            quiet_hours_end=request.quiet_hours_end,
            critical_only=request.critical_only
        )
        
        return PreferencesResponse(
            user_id=preferences.user_id,
            enabled_channels=preferences.enabled_channels,
            quiet_hours_start=preferences.quiet_hours_start,
            quiet_hours_end=preferences.quiet_hours_end,
            critical_only=preferences.critical_only
        )
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/preferences/{user_id}", response_model=PreferencesResponse)
async def get_notification_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Get user's notification preferences
    
    Returns current notification settings including:
    - Enabled channels
    - Quiet hours
    - Critical-only mode
    """
    try:
        # Get preferences
        preferences = service._get_user_preferences(db=db, user_id=user_id)
        
        return PreferencesResponse(
            user_id=preferences.user_id,
            enabled_channels=preferences.enabled_channels,
            quiet_hours_start=preferences.quiet_hours_start,
            quiet_hours_end=preferences.quiet_hours_end,
            critical_only=preferences.critical_only
        )
    
    except Exception as e:
        logger.error(f"Error getting notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Helper endpoints for common alert types

@router.post("/alert/ppd-risk/{user_id}")
async def send_ppd_risk_alert(
    user_id: int,
    risk_score: float,
    risk_level: str,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send PPD risk alert to user and their digital helpers
    
    Automatically determines severity based on risk level.
    """
    try:
        # Determine severity
        severity = AlertSeverity.CRITICAL.value if risk_level == "critical" else AlertSeverity.WARNING.value
        
        # Create alert
        alert = HealthAlert(
            user_id=user_id,
            alert_type=AlertType.HIGH_PPD_RISK.value,
            severity=severity,
            title="Postpartum Depression Risk Alert",
            message=f"Your PPD risk score is {risk_score:.1f} ({risk_level}). Please consult with your healthcare provider.",
            data_category="ppd_risk"
        )
        
        # Send alert
        result = service.send_health_alert(db=db, alert=alert)
        
        return result
    
    except Exception as e:
        logger.error(f"Error sending PPD risk alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/alert/micronutrient-deficiency/{user_id}")
async def send_micronutrient_deficiency_alert(
    user_id: int,
    nutrient: str,
    level: float,
    threshold: float,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send micronutrient deficiency alert to user and their digital helpers
    """
    try:
        # Create alert
        alert = HealthAlert(
            user_id=user_id,
            alert_type=AlertType.MICRONUTRIENT_DEFICIENCY.value,
            severity=AlertSeverity.WARNING.value,
            title=f"{nutrient} Deficiency Detected",
            message=f"Your {nutrient} level ({level}) is below the recommended threshold ({threshold}). Consider dietary changes or supplements.",
            data_category="micronutrients"
        )
        
        # Send alert
        result = service.send_health_alert(db=db, alert=alert)
        
        return result
    
    except Exception as e:
        logger.error(f"Error sending micronutrient deficiency alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/alert/edc-exposure/{user_id}")
async def send_edc_exposure_alert(
    user_id: int,
    exposure_level: float,
    epa_limit: float,
    percent_of_limit: float,
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send EDC exposure alert to user and their digital helpers
    """
    try:
        # Determine severity
        if percent_of_limit >= 100:
            severity = AlertSeverity.CRITICAL.value
        elif percent_of_limit >= 80:
            severity = AlertSeverity.WARNING.value
        else:
            severity = AlertSeverity.INFO.value
        
        # Create alert
        alert = HealthAlert(
            user_id=user_id,
            alert_type=AlertType.HIGH_EDC_EXPOSURE.value,
            severity=severity,
            title="EDC Exposure Alert",
            message=f"Your cumulative EDC exposure is at {percent_of_limit:.1f}% of EPA safe limits. Consider reducing exposure to high-risk products.",
            data_category="edc_exposure"
        )
        
        # Send alert
        result = service.send_health_alert(db=db, alert=alert)
        
        return result
    
    except Exception as e:
        logger.error(f"Error sending EDC exposure alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
