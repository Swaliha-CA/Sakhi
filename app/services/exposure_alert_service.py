"""
Exposure Alert Service for EDC Exposure Monitoring

Implements:
- Threshold-based alerting for weekly safe limits
- Personalized reduction strategies generation
- Exposure trend tracking over time
- Primary EDC source identification for users

Requirements: 2.5, 13.4
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    ExposureAlert, EDCExposureLog, ProductScan, User
)
from app.services.exposure_aggregation_service import (
    ExposureAggregationService,
    PeriodType,
    ExposureStatus
)


class AlertType(str, Enum):
    """Types of exposure alerts"""
    WEEKLY_LIMIT_EXCEEDED = "weekly_limit_exceeded"
    APPROACHING_LIMIT = "approaching_limit"
    TREND_INCREASING = "trend_increasing"
    HIGH_EDC_TYPE = "high_edc_type"
    CRITICAL_SOURCE = "critical_source"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertConfig:
    """Configuration for alert thresholds"""
    weekly_warning_threshold: float = 70.0  # % of EPA limit
    weekly_critical_threshold: float = 100.0  # % of EPA limit
    trend_increase_threshold: float = 20.0  # % increase
    high_edc_threshold: float = 30.0  # % of total exposure from single EDC type
    critical_source_threshold: float = 40.0  # % of total exposure from single product


class ExposureAlertService:
    """
    Service for monitoring EDC exposure and generating alerts
    
    Monitors:
    - Weekly exposure against safe limits
    - Exposure trends over time
    - High-risk EDC types
    - Critical exposure sources
    """
    
    def __init__(self, db_session: Session, config: Optional[AlertConfig] = None):
        """
        Initialize exposure alert service
        
        Args:
            db_session: SQLAlchemy database session
            config: Optional alert configuration (uses defaults if not provided)
        """
        self.db = db_session
        self.config = config or AlertConfig()
        self.aggregation_service = ExposureAggregationService(db_session)
    
    def check_and_create_alerts(self, user_id: int) -> List[ExposureAlert]:
        """
        Check exposure levels and create alerts if thresholds are exceeded
        
        This is the main entry point for alert generation. It should be called:
        - After each product scan
        - On a scheduled basis (e.g., weekly)
        - When user requests exposure report
        
        Args:
            user_id: User ID to check
        
        Returns:
            List of created alerts
        """
        logger.info(f"Checking exposure alerts for user {user_id}")
        
        created_alerts = []
        
        # Generate weekly exposure report
        weekly_report = self.aggregation_service.generate_exposure_report(
            user_id=user_id,
            period_type=PeriodType.WEEKLY
        )
        
        # Check weekly limit thresholds
        limit_alerts = self._check_weekly_limits(user_id, weekly_report)
        created_alerts.extend(limit_alerts)
        
        # Check exposure trends
        trend_alerts = self._check_exposure_trends(user_id, weekly_report)
        created_alerts.extend(trend_alerts)
        
        # Check high EDC type concentrations
        edc_alerts = self._check_high_edc_types(user_id, weekly_report)
        created_alerts.extend(edc_alerts)
        
        # Check critical sources
        source_alerts = self._check_critical_sources(user_id, weekly_report)
        created_alerts.extend(source_alerts)
        
        logger.info(
            f"Created {len(created_alerts)} alerts for user {user_id}"
        )
        
        return created_alerts
    
    def _check_weekly_limits(
        self,
        user_id: int,
        weekly_report
    ) -> List[ExposureAlert]:
        """
        Check if weekly exposure exceeds safe limits
        
        Args:
            user_id: User ID
            weekly_report: Weekly exposure report
        
        Returns:
            List of limit-based alerts
        """
        alerts = []
        percent_of_limit = weekly_report.percent_of_limit
        
        # Critical threshold exceeded
        if percent_of_limit >= self.config.weekly_critical_threshold:
            alert = self._create_alert(
                user_id=user_id,
                exposure_log_id=self._get_latest_log_id(user_id),
                alert_type=AlertType.WEEKLY_LIMIT_EXCEEDED,
                severity=AlertSeverity.CRITICAL,
                title="⚠️ CRITICAL: Weekly EDC Limit Exceeded",
                message=(
                    f"Your EDC exposure this week is {percent_of_limit:.0f}% of the safe limit. "
                    f"This exceeds recommended safety thresholds. "
                    f"Immediate action is recommended to reduce exposure."
                ),
                reduction_strategies=self._generate_reduction_strategies(weekly_report),
                primary_sources=self._identify_primary_sources(weekly_report)
            )
            alerts.append(alert)
        
        # Warning threshold exceeded
        elif percent_of_limit >= self.config.weekly_warning_threshold:
            alert = self._create_alert(
                user_id=user_id,
                exposure_log_id=self._get_latest_log_id(user_id),
                alert_type=AlertType.APPROACHING_LIMIT,
                severity=AlertSeverity.WARNING,
                title="⚠️ WARNING: Approaching Weekly EDC Limit",
                message=(
                    f"Your EDC exposure this week is {percent_of_limit:.0f}% of the safe limit. "
                    f"You're approaching the recommended safety threshold. "
                    f"Consider reducing exposure to stay within safe limits."
                ),
                reduction_strategies=self._generate_reduction_strategies(weekly_report),
                primary_sources=self._identify_primary_sources(weekly_report)
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_exposure_trends(
        self,
        user_id: int,
        weekly_report
    ) -> List[ExposureAlert]:
        """
        Check if exposure is trending upward
        
        Args:
            user_id: User ID
            weekly_report: Weekly exposure report
        
        Returns:
            List of trend-based alerts
        """
        alerts = []
        
        # Need at least 2 weeks of data to detect trends
        if len(weekly_report.trend_data) < 2:
            return alerts
        
        # Compare current week to previous week
        current_exposure = weekly_report.total_exposure
        previous_exposure = weekly_report.trend_data[-1]["total_exposure"]
        
        if previous_exposure > 0:
            percent_increase = (
                (current_exposure - previous_exposure) / previous_exposure * 100
            )
            
            if percent_increase >= self.config.trend_increase_threshold:
                alert = self._create_alert(
                    user_id=user_id,
                    exposure_log_id=self._get_latest_log_id(user_id),
                    alert_type=AlertType.TREND_INCREASING,
                    severity=AlertSeverity.WARNING,
                    title="📈 TREND ALERT: Exposure Increasing",
                    message=(
                        f"Your EDC exposure has increased by {percent_increase:.0f}% "
                        f"compared to last week. "
                        f"Review recent product changes and consider alternatives."
                    ),
                    reduction_strategies=self._generate_trend_strategies(
                        weekly_report,
                        percent_increase
                    ),
                    primary_sources=self._identify_primary_sources(weekly_report)
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_high_edc_types(
        self,
        user_id: int,
        weekly_report
    ) -> List[ExposureAlert]:
        """
        Check if specific EDC types contribute disproportionately to exposure
        
        Args:
            user_id: User ID
            weekly_report: Weekly exposure report
        
        Returns:
            List of EDC type-based alerts
        """
        alerts = []
        
        if not weekly_report.exposure_by_type:
            return alerts
        
        total_exposure = weekly_report.total_exposure
        if total_exposure == 0:
            return alerts
        
        # Check each EDC type
        for edc_type, exposure in weekly_report.exposure_by_type.items():
            percent_of_total = (exposure / total_exposure) * 100
            
            if percent_of_total >= self.config.high_edc_threshold:
                alert = self._create_alert(
                    user_id=user_id,
                    exposure_log_id=self._get_latest_log_id(user_id),
                    alert_type=AlertType.HIGH_EDC_TYPE,
                    severity=AlertSeverity.WARNING,
                    title=f"🔴 HIGH EXPOSURE: {edc_type.upper()}",
                    message=(
                        f"{edc_type.upper()} contributes {percent_of_total:.0f}% "
                        f"of your total EDC exposure. "
                        f"This is a primary concern for your health."
                    ),
                    reduction_strategies=self._generate_edc_specific_strategies(
                        edc_type,
                        percent_of_total
                    ),
                    primary_sources=self._identify_edc_sources(
                        weekly_report,
                        edc_type
                    )
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_critical_sources(
        self,
        user_id: int,
        weekly_report
    ) -> List[ExposureAlert]:
        """
        Check if single products contribute disproportionately to exposure
        
        Args:
            user_id: User ID
            weekly_report: Weekly exposure report
        
        Returns:
            List of source-based alerts
        """
        alerts = []
        
        if not weekly_report.top_sources:
            return alerts
        
        total_exposure = weekly_report.total_exposure
        if total_exposure == 0:
            return alerts
        
        # Check top source
        top_source = weekly_report.top_sources[0]
        source_contribution = top_source["exposure_contribution"]
        percent_of_total = (source_contribution / total_exposure) * 100
        
        if percent_of_total >= self.config.critical_source_threshold:
            alert = self._create_alert(
                user_id=user_id,
                exposure_log_id=self._get_latest_log_id(user_id),
                alert_type=AlertType.CRITICAL_SOURCE,
                severity=AlertSeverity.WARNING,
                title=f"🎯 CRITICAL SOURCE: {top_source['product_name']}",
                message=(
                    f"'{top_source['product_name']}' contributes {percent_of_total:.0f}% "
                    f"of your total EDC exposure. "
                    f"Replacing this product should be your top priority."
                ),
                reduction_strategies=self._generate_source_strategies(
                    top_source,
                    percent_of_total
                ),
                primary_sources=[top_source]
            )
            alerts.append(alert)
        
        return alerts
    
    def _create_alert(
        self,
        user_id: int,
        exposure_log_id: int,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        reduction_strategies: List[str],
        primary_sources: List[Dict[str, Any]]
    ) -> ExposureAlert:
        """
        Create and save an exposure alert
        
        Args:
            user_id: User ID
            exposure_log_id: Associated exposure log ID
            alert_type: Type of alert
            severity: Alert severity
            title: Alert title
            message: Alert message
            reduction_strategies: List of reduction strategies
            primary_sources: List of primary EDC sources
        
        Returns:
            Created ExposureAlert
        """
        alert = ExposureAlert(
            user_id=user_id,
            exposure_log_id=exposure_log_id,
            alert_type=alert_type.value,
            severity=severity.value,
            title=title,
            message=message,
            reduction_strategies=reduction_strategies,
            primary_edc_sources=primary_sources,
            sent=False,
            acknowledged=False
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(
            f"Created {severity.value} alert for user {user_id}: {alert_type.value}"
        )
        
        return alert
    
    def _get_latest_log_id(self, user_id: int) -> int:
        """
        Get the ID of the most recent exposure log for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Exposure log ID
        """
        log = self.db.query(EDCExposureLog).filter(
            EDCExposureLog.user_id == user_id
        ).order_by(desc(EDCExposureLog.created_at)).first()
        
        return log.id if log else 0
    
    def _generate_reduction_strategies(self, weekly_report) -> List[str]:
        """
        Generate personalized reduction strategies based on exposure data
        
        Args:
            weekly_report: Weekly exposure report
        
        Returns:
            List of reduction strategy strings
        """
        strategies = []
        
        # Category-based strategies
        if weekly_report.exposure_by_category:
            top_categories = sorted(
                weekly_report.exposure_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            for category, exposure in top_categories:
                if category == "cosmetic":
                    strategies.append(
                        "Switch to clean beauty products: Look for certified organic "
                        "and EDC-free cosmetics. Prioritize products with minimal ingredients."
                    )
                elif category == "food":
                    strategies.append(
                        "Reduce food packaging exposure: Choose fresh, unpackaged foods. "
                        "Avoid heating food in plastic containers. Use glass or stainless steel."
                    )
                elif category == "personal_care":
                    strategies.append(
                        "Choose natural personal care: Switch to fragrance-free, "
                        "paraben-free, and phthalate-free products."
                    )
                elif category == "household":
                    strategies.append(
                        "Use eco-friendly cleaning: Replace chemical cleaners with "
                        "natural alternatives like vinegar, baking soda, and castile soap."
                    )
        
        # EDC type-based strategies
        if weekly_report.exposure_by_type:
            top_edc_types = sorted(
                weekly_report.exposure_by_type.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            for edc_type, exposure in top_edc_types:
                if edc_type == "bpa":
                    strategies.append(
                        "Eliminate BPA: Use BPA-free water bottles and food containers. "
                        "Avoid canned foods with BPA linings. Never microwave plastic."
                    )
                elif edc_type == "phthalate":
                    strategies.append(
                        "Reduce phthalates: Avoid fragranced products (perfumes, air fresheners). "
                        "Choose phthalate-free nail polish and personal care items."
                    )
                elif edc_type == "paraben":
                    strategies.append(
                        "Go paraben-free: Read labels carefully and choose products "
                        "labeled 'paraben-free'. Focus on lotions, shampoos, and cosmetics."
                    )
        
        # Top source strategy
        if weekly_report.top_sources:
            top_source = weekly_report.top_sources[0]
            strategies.append(
                f"Priority replacement: '{top_source['product_name']}' is your "
                f"highest exposure source. Find a safer alternative immediately."
            )
        
        # General strategies
        strategies.append(
            "Scan before you buy: Use the app to scan all new products before purchasing "
            "to avoid high-risk items."
        )
        
        return strategies
    
    def _generate_trend_strategies(
        self,
        weekly_report,
        percent_increase: float
    ) -> List[str]:
        """
        Generate strategies specific to increasing exposure trends
        
        Args:
            weekly_report: Weekly exposure report
            percent_increase: Percentage increase in exposure
        
        Returns:
            List of strategy strings
        """
        strategies = [
            f"Your exposure increased {percent_increase:.0f}% this week. "
            "Review products you started using recently."
        ]
        
        # Add general reduction strategies
        strategies.extend(self._generate_reduction_strategies(weekly_report))
        
        return strategies
    
    def _generate_edc_specific_strategies(
        self,
        edc_type: str,
        percent_of_total: float
    ) -> List[str]:
        """
        Generate strategies specific to a high-risk EDC type
        
        Args:
            edc_type: EDC type (bpa, phthalate, etc.)
            percent_of_total: Percentage of total exposure
        
        Returns:
            List of strategy strings
        """
        strategies = []
        
        if edc_type == "bpa":
            strategies.extend([
                "BPA Reduction Plan:",
                "1. Replace all plastic food containers with glass or stainless steel",
                "2. Use BPA-free water bottles (look for #2, #4, #5 plastics)",
                "3. Avoid canned foods or choose BPA-free cans",
                "4. Never heat food in plastic containers or with plastic wrap",
                "5. Choose fresh or frozen foods over canned when possible"
            ])
        elif edc_type == "phthalate":
            strategies.extend([
                "Phthalate Reduction Plan:",
                "1. Avoid all fragranced products (perfumes, air fresheners, scented candles)",
                "2. Choose phthalate-free personal care products",
                "3. Use fragrance-free laundry detergent and cleaning products",
                "4. Avoid vinyl/PVC products (shower curtains, flooring)",
                "5. Choose natural fiber clothing and bedding"
            ])
        elif edc_type == "paraben":
            strategies.extend([
                "Paraben Reduction Plan:",
                "1. Read all cosmetic labels and choose paraben-free options",
                "2. Replace shampoos, conditioners, and body washes",
                "3. Switch to paraben-free lotions and moisturizers",
                "4. Choose natural deodorants without parabens",
                "5. Look for preservative-free or naturally preserved products"
            ])
        elif edc_type == "heavy_metal":
            strategies.extend([
                "Heavy Metal Reduction Plan:",
                "1. Avoid cosmetics with lead, mercury, or cadmium",
                "2. Check traditional/ayurvedic products for heavy metal content",
                "3. Use stainless steel or cast iron cookware instead of non-stick",
                "4. Filter drinking water to remove heavy metals",
                "5. Choose organic produce to reduce pesticide exposure"
            ])
        else:
            strategies.append(
                f"Focus on reducing {edc_type} exposure by choosing certified "
                f"organic and EDC-free products."
            )
        
        return strategies
    
    def _generate_source_strategies(
        self,
        top_source: Dict[str, Any],
        percent_of_total: float
    ) -> List[str]:
        """
        Generate strategies for replacing a critical source
        
        Args:
            top_source: Top exposure source
            percent_of_total: Percentage of total exposure
        
        Returns:
            List of strategy strings
        """
        strategies = [
            f"IMMEDIATE ACTION REQUIRED:",
            f"'{top_source['product_name']}' is responsible for {percent_of_total:.0f}% "
            f"of your EDC exposure.",
            "",
            "Steps to take:",
            "1. Stop using this product immediately",
            "2. Scan alternative products in the same category",
            "3. Choose a replacement with a Hormonal Health Score above 70",
            "4. Check the app's alternative recommendations for this product",
            "",
            f"Replacing just this one product could reduce your exposure by {percent_of_total:.0f}%!"
        ]
        
        return strategies
    
    def _identify_primary_sources(self, weekly_report) -> List[Dict[str, Any]]:
        """
        Identify primary EDC sources from exposure report
        
        Args:
            weekly_report: Weekly exposure report
        
        Returns:
            List of primary source dictionaries
        """
        return weekly_report.top_sources[:3]  # Top 3 sources
    
    def _identify_edc_sources(
        self,
        weekly_report,
        edc_type: str
    ) -> List[Dict[str, Any]]:
        """
        Identify sources contributing to a specific EDC type
        
        Args:
            weekly_report: Weekly exposure report
            edc_type: EDC type to filter by
        
        Returns:
            List of source dictionaries
        """
        # Filter top sources that contain the specified EDC type
        edc_sources = []
        
        for source in weekly_report.top_sources:
            # Would need to query the actual scan to check flagged chemicals
            # For now, include all top sources
            edc_sources.append(source)
        
        return edc_sources[:3]  # Top 3 sources
    
    def get_user_alerts(
        self,
        user_id: int,
        unacknowledged_only: bool = False,
        limit: int = 10
    ) -> List[ExposureAlert]:
        """
        Get alerts for a user
        
        Args:
            user_id: User ID
            unacknowledged_only: Only return unacknowledged alerts
            limit: Maximum number of alerts to return
        
        Returns:
            List of ExposureAlert objects
        """
        query = self.db.query(ExposureAlert).filter(
            ExposureAlert.user_id == user_id
        )
        
        if unacknowledged_only:
            query = query.filter(ExposureAlert.acknowledged == False)
        
        alerts = query.order_by(
            desc(ExposureAlert.created_at)
        ).limit(limit).all()
        
        return alerts
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Mark an alert as acknowledged
        
        Args:
            alert_id: Alert ID
        
        Returns:
            True if successful, False otherwise
        """
        alert = self.db.query(ExposureAlert).filter(
            ExposureAlert.id == alert_id
        ).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return False
        
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Alert {alert_id} acknowledged")
        return True
    
    def mark_alert_sent(self, alert_id: int) -> bool:
        """
        Mark an alert as sent (for notification tracking)
        
        Args:
            alert_id: Alert ID
        
        Returns:
            True if successful, False otherwise
        """
        alert = self.db.query(ExposureAlert).filter(
            ExposureAlert.id == alert_id
        ).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return False
        
        alert.sent = True
        alert.sent_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Alert {alert_id} marked as sent")
        return True
