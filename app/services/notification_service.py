"""Notification Service for health alerts

Provides notification functionality for:
- Health alerts (PPD risk, micronutrient deficiency, EDC exposure, heat stress)
- Dual notifications for buddy system (elder + digital helper)
- Privacy controls respecting buddy link permissions
- Notification preferences per user
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import User, BuddyLink, HealthRecord
from app.core.logging import logger


class AlertType(str, Enum):
    """Types of health alerts"""
    HIGH_PPD_RISK = "high_ppd_risk"
    MICRONUTRIENT_DEFICIENCY = "micronutrient_deficiency"
    HIGH_EDC_EXPOSURE = "high_edc_exposure"
    HEAT_STRESS = "heat_stress"
    SCREENING_DUE = "screening_due"
    CHRONIC_DEFICIENCY = "chronic_deficiency"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    PUSH = "push"
    SMS = "sms"
    VOICE_CALL = "voice_call"
    IN_APP = "in_app"


@dataclass
class NotificationPreferences:
    """User notification preferences"""
    user_id: int
    enabled_channels: List[str]
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None  # Hour (0-23)
    critical_only: bool = False


@dataclass
class HealthAlert:
    """Health alert information"""
    user_id: int
    alert_type: str
    severity: str
    title: str
    message: str
    data_category: Optional[str] = None  # For privacy filtering
    action_url: Optional[str] = None
    channels: Optional[List[str]] = None


class NotificationService:
    """
    Notification Service for health alerts
    
    Features:
    - Send health alerts to users
    - Dual notifications for buddy system (elder + helper)
    - Respect privacy controls (only notify for permitted data categories)
    - Notification preferences per user
    - Multiple delivery channels (push, SMS, voice, in-app)
    """
    
    def __init__(self):
        """Initialize notification service"""
        # In a real implementation, this would initialize:
        # - Firebase Cloud Messaging (FCM) for push notifications
        # - SMS gateway (Twilio or local provider)
        # - Voice call service (Bhashini TTS)
        # - WebSocket connections for in-app notifications
        logger.info("Notification service initialized")
    
    def send_health_alert(
        self,
        db: Session,
        alert: HealthAlert
    ) -> Dict[str, Any]:
        """
        Send a health alert to a user
        
        If the user has active buddy links, also sends to digital helpers
        who have RECEIVE_ALERTS permission and appropriate data category access.
        
        Args:
            db: Database session
            alert: HealthAlert to send
        
        Returns:
            Status dictionary with delivery information
        """
        logger.info(
            f"Sending health alert to user {alert.user_id}: "
            f"{alert.alert_type} ({alert.severity})"
        )
        
        # Get user
        user = db.query(User).filter(User.id == alert.user_id).first()
        if not user:
            raise ValueError(f"User {alert.user_id} not found")
        
        # Get user's notification preferences
        user_prefs = self._get_user_preferences(db, alert.user_id)
        
        # Send to primary user
        primary_result = self._send_to_user(
            db=db,
            user_id=alert.user_id,
            alert=alert,
            preferences=user_prefs
        )
        
        # Check for buddy links and send dual notifications
        helper_results = self._send_dual_notifications(
            db=db,
            elder_id=alert.user_id,
            alert=alert
        )
        
        return {
            "status": "sent",
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "primary_user": {
                "user_id": alert.user_id,
                "delivered": primary_result["delivered"],
                "channels": primary_result["channels"]
            },
            "helpers_notified": helper_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _send_dual_notifications(
        self,
        db: Session,
        elder_id: int,
        alert: HealthAlert
    ) -> List[Dict[str, Any]]:
        """
        Send notifications to digital helpers linked to an elder
        
        Respects:
        - RECEIVE_ALERTS permission
        - Privacy controls (data category permissions)
        - Helper's notification preferences
        
        Args:
            db: Database session
            elder_id: Elder user ID
            alert: HealthAlert to send
        
        Returns:
            List of helper notification results
        """
        logger.info(f"Checking for buddy links for elder {elder_id}")
        
        # Get all active buddy links where user is elder
        links = db.query(BuddyLink).filter(
            BuddyLink.elder_id == elder_id,
            BuddyLink.is_active == True
        ).all()
        
        if not links:
            logger.info(f"No active buddy links found for elder {elder_id}")
            return []
        
        helper_results = []
        
        for link in links:
            # Check if helper has RECEIVE_ALERTS permission
            permissions = link.permissions.split(",")
            if "receive_alerts" not in permissions:
                logger.info(
                    f"Helper {link.helper_id} does not have RECEIVE_ALERTS permission"
                )
                continue
            
            # Check privacy controls for data category
            if alert.data_category and not self._check_data_category_permission(
                permissions, alert.data_category
            ):
                logger.info(
                    f"Helper {link.helper_id} does not have permission for "
                    f"data category: {alert.data_category}"
                )
                continue
            
            # Get helper's notification preferences
            helper_prefs = self._get_user_preferences(db, link.helper_id)
            
            # Send to helper
            helper_result = self._send_to_user(
                db=db,
                user_id=link.helper_id,
                alert=alert,
                preferences=helper_prefs,
                is_helper_notification=True,
                elder_id=elder_id
            )
            
            helper_results.append({
                "helper_id": link.helper_id,
                "delivered": helper_result["delivered"],
                "channels": helper_result["channels"]
            })
            
            logger.info(
                f"Notification sent to helper {link.helper_id} for elder {elder_id}"
            )
        
        return helper_results
    
    def _check_data_category_permission(
        self,
        permissions: List[str],
        data_category: str
    ) -> bool:
        """
        Check if permissions include access to a specific data category
        
        Data categories map to permissions:
        - health_data -> view_health_data
        - lab_results -> view_lab_results
        - screenings -> view_screenings
        - product_scans -> view_product_scans
        
        Args:
            permissions: List of permission strings
            data_category: Data category to check
        
        Returns:
            True if permission granted, False otherwise
        """
        # Map data categories to required permissions
        category_permission_map = {
            "health_data": "view_health_data",
            "lab_results": "view_lab_results",
            "screenings": "view_screenings",
            "product_scans": "view_product_scans",
            "ppd_risk": "view_screenings",
            "micronutrients": "view_lab_results",
            "edc_exposure": "view_product_scans"
        }
        
        required_permission = category_permission_map.get(data_category)
        
        if not required_permission:
            # If no specific permission required, allow
            return True
        
        return required_permission in permissions
    
    def _send_to_user(
        self,
        db: Session,
        user_id: int,
        alert: HealthAlert,
        preferences: NotificationPreferences,
        is_helper_notification: bool = False,
        elder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send notification to a specific user
        
        Args:
            db: Database session
            user_id: User ID to send to
            alert: HealthAlert to send
            preferences: User's notification preferences
            is_helper_notification: Whether this is a helper notification
            elder_id: Elder ID if this is a helper notification
        
        Returns:
            Delivery status dictionary
        """
        # Check if notifications are enabled
        if not preferences.enabled_channels:
            logger.info(f"User {user_id} has no enabled notification channels")
            return {"delivered": False, "channels": [], "reason": "no_channels_enabled"}
        
        # Check quiet hours
        if self._is_quiet_hours(preferences) and alert.severity != AlertSeverity.CRITICAL.value:
            logger.info(f"User {user_id} is in quiet hours, skipping non-critical alert")
            return {"delivered": False, "channels": [], "reason": "quiet_hours"}
        
        # Check critical only preference
        if preferences.critical_only and alert.severity != AlertSeverity.CRITICAL.value:
            logger.info(f"User {user_id} has critical_only enabled, skipping non-critical alert")
            return {"delivered": False, "channels": [], "reason": "critical_only"}
        
        # Determine channels to use
        channels_to_use = alert.channels if alert.channels else preferences.enabled_channels
        channels_to_use = [ch for ch in channels_to_use if ch in preferences.enabled_channels]
        
        # Modify message for helper notifications
        message = alert.message
        title = alert.title
        if is_helper_notification and elder_id:
            elder = db.query(User).filter(User.id == elder_id).first()
            elder_name = elder.name if elder else f"User {elder_id}"
            title = f"Alert for {elder_name}: {title}"
            message = f"Health alert for {elder_name}: {message}"
        
        # Send via each channel
        delivered_channels = []
        for channel in channels_to_use:
            try:
                if channel == NotificationChannel.PUSH.value:
                    self._send_push_notification(user_id, title, message, alert.action_url)
                    delivered_channels.append(channel)
                elif channel == NotificationChannel.SMS.value:
                    self._send_sms(user_id, message)
                    delivered_channels.append(channel)
                elif channel == NotificationChannel.VOICE_CALL.value:
                    self._send_voice_call(user_id, message)
                    delivered_channels.append(channel)
                elif channel == NotificationChannel.IN_APP.value:
                    self._send_in_app_notification(user_id, title, message, alert.action_url)
                    delivered_channels.append(channel)
            except Exception as e:
                logger.error(f"Failed to send via {channel} to user {user_id}: {str(e)}")
        
        return {
            "delivered": len(delivered_channels) > 0,
            "channels": delivered_channels
        }
    
    def _get_user_preferences(
        self,
        db: Session,
        user_id: int
    ) -> NotificationPreferences:
        """
        Get user's notification preferences
        
        In a real implementation, this would query a user_preferences table.
        For now, returns default preferences.
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            NotificationPreferences
        """
        # Default preferences (in real implementation, query from database)
        return NotificationPreferences(
            user_id=user_id,
            enabled_channels=[
                NotificationChannel.PUSH.value,
                NotificationChannel.IN_APP.value
            ],
            quiet_hours_start=22,  # 10 PM
            quiet_hours_end=7,  # 7 AM
            critical_only=False
        )
    
    def _is_quiet_hours(self, preferences: NotificationPreferences) -> bool:
        """
        Check if current time is within user's quiet hours
        
        Args:
            preferences: User's notification preferences
        
        Returns:
            True if in quiet hours, False otherwise
        """
        if preferences.quiet_hours_start is None or preferences.quiet_hours_end is None:
            return False
        
        current_hour = datetime.utcnow().hour
        start = preferences.quiet_hours_start
        end = preferences.quiet_hours_end
        
        # Handle quiet hours that span midnight
        if start < end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end
    
    def _send_push_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ):
        """
        Send push notification via Firebase Cloud Messaging
        
        In a real implementation, this would use FCM SDK.
        """
        logger.info(f"[PUSH] Sending to user {user_id}: {title}")
        # TODO: Implement FCM integration
        pass
    
    def _send_sms(self, user_id: int, message: str):
        """
        Send SMS notification
        
        In a real implementation, this would use Twilio or local SMS gateway.
        """
        logger.info(f"[SMS] Sending to user {user_id}: {message[:50]}...")
        # TODO: Implement SMS gateway integration
        pass
    
    def _send_voice_call(self, user_id: int, message: str):
        """
        Send automated voice call notification
        
        In a real implementation, this would use Bhashini TTS for voice calls.
        """
        logger.info(f"[VOICE] Sending to user {user_id}: {message[:50]}...")
        # TODO: Implement voice call integration with Bhashini
        pass
    
    def _send_in_app_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ):
        """
        Send in-app notification via WebSocket
        
        In a real implementation, this would use WebSocket connections.
        """
        logger.info(f"[IN-APP] Sending to user {user_id}: {title}")
        # TODO: Implement WebSocket notification
        pass
    
    def update_notification_preferences(
        self,
        db: Session,
        user_id: int,
        enabled_channels: Optional[List[str]] = None,
        quiet_hours_start: Optional[int] = None,
        quiet_hours_end: Optional[int] = None,
        critical_only: Optional[bool] = None
    ) -> NotificationPreferences:
        """
        Update user's notification preferences
        
        Args:
            db: Database session
            user_id: User ID
            enabled_channels: List of enabled channels
            quiet_hours_start: Quiet hours start (hour 0-23)
            quiet_hours_end: Quiet hours end (hour 0-23)
            critical_only: Whether to only receive critical alerts
        
        Returns:
            Updated NotificationPreferences
        """
        logger.info(f"Updating notification preferences for user {user_id}")
        
        # In a real implementation, this would update a user_preferences table
        # For now, just return the new preferences
        
        # Validate channels
        if enabled_channels:
            valid_channels = [ch.value for ch in NotificationChannel]
            enabled_channels = [ch for ch in enabled_channels if ch in valid_channels]
        
        # Validate quiet hours
        if quiet_hours_start is not None and not (0 <= quiet_hours_start <= 23):
            raise ValueError("quiet_hours_start must be between 0 and 23")
        if quiet_hours_end is not None and not (0 <= quiet_hours_end <= 23):
            raise ValueError("quiet_hours_end must be between 0 and 23")
        
        return NotificationPreferences(
            user_id=user_id,
            enabled_channels=enabled_channels or [NotificationChannel.PUSH.value, NotificationChannel.IN_APP.value],
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            critical_only=critical_only if critical_only is not None else False
        )


# Global service instance
notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Get or create global notification service instance
    
    Returns:
        NotificationService instance
    """
    global notification_service
    
    if notification_service is None:
        notification_service = NotificationService()
        logger.info("Notification service initialized")
    
    return notification_service
