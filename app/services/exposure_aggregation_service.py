"""
Exposure Aggregation Service for Cumulative EDC Tracking

Implements:
- Cumulative exposure aggregation weighted by frequency and concentration
- Exposure calculation by EDC type (BPA, phthalates, organochlorines, etc.)
- Comparison against EPA safe limits
- Monthly exposure report generation with visualizations
- Trend analysis and personalized reduction strategies

Requirements: 2.4, 13.1, 13.2, 13.3, 13.5
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    ProductScan, EDCExposureLog, ExposureAlert, User
)


class PeriodType(str, Enum):
    """Time period types for exposure aggregation"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ExposureStatus(str, Enum):
    """Exposure status relative to EPA safe limits"""
    SAFE = "safe"
    APPROACHING_LIMIT = "approaching_limit"
    EXCEEDS_LIMIT = "exceeds_limit"


@dataclass
class ExposureData:
    """Aggregated exposure data for a time period"""
    total_exposure: float
    exposure_by_type: Dict[str, float]
    exposure_by_category: Dict[str, float]
    top_sources: List[Dict[str, Any]]
    scan_count: int
    period_start: datetime
    period_end: datetime


@dataclass
class ExposureReport:
    """Comprehensive exposure report"""
    user_id: int
    period_type: str
    period_start: datetime
    period_end: datetime
    total_exposure: float
    exposure_by_type: Dict[str, float]
    exposure_by_category: Dict[str, float]
    top_sources: List[Dict[str, Any]]
    epa_limit: float
    percent_of_limit: float
    status: str
    scan_count: int
    trend_data: List[Dict[str, Any]]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_exposure": self.total_exposure,
            "exposure_by_type": self.exposure_by_type,
            "exposure_by_category": self.exposure_by_category,
            "top_sources": self.top_sources,
            "epa_limit": self.epa_limit,
            "percent_of_limit": self.percent_of_limit,
            "status": self.status,
            "scan_count": self.scan_count,
            "trend_data": self.trend_data,
            "recommendations": self.recommendations
        }


class ExposureAggregationService:
    """
    Service for aggregating and analyzing cumulative EDC exposure
    
    Implements weighted aggregation by:
    - Frequency of use (estimated from scan frequency)
    - Concentration (when available from product data)
    - EDC risk scores from toxicity analysis
    """
    
    # EPA safe limits (placeholder values - should be configured based on actual EPA guidelines)
    # These are relative exposure scores, not absolute chemical concentrations
    EPA_SAFE_LIMITS = {
        PeriodType.DAILY: 10.0,
        PeriodType.WEEKLY: 50.0,
        PeriodType.MONTHLY: 200.0
    }
    
    # Thresholds for status classification (percentage of EPA limit)
    STATUS_THRESHOLDS = {
        ExposureStatus.SAFE: 70.0,  # < 70% of limit
        ExposureStatus.APPROACHING_LIMIT: 100.0,  # 70-100% of limit
        ExposureStatus.EXCEEDS_LIMIT: float('inf')  # > 100% of limit
    }
    
    # Frequency weights based on product category (estimated daily use)
    CATEGORY_FREQUENCY_WEIGHTS = {
        "cosmetic": 1.0,  # Daily use
        "personal_care": 1.5,  # Multiple times daily
        "food": 2.0,  # Multiple times daily
        "household": 0.3,  # Occasional use
    }
    
    def __init__(self, db_session: Session):
        """
        Initialize exposure aggregation service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def calculate_cumulative_exposure(
        self,
        user_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> ExposureData:
        """
        Calculate cumulative EDC exposure for a user over a time period
        
        Aggregation algorithm:
        1. Retrieve all product scans in the period
        2. Weight each scan by:
           - Product category frequency (how often product is typically used)
           - EDC risk scores from flagged chemicals
           - Scan recency (more recent scans weighted higher)
        3. Aggregate by EDC type and product category
        4. Identify top contributing sources
        
        Args:
            user_id: User ID
            period_start: Start of time period
            period_end: End of time period
        
        Returns:
            ExposureData with aggregated exposure information
        """
        logger.info(
            f"Calculating cumulative exposure for user {user_id} "
            f"from {period_start} to {period_end}"
        )
        
        # Retrieve product scans in the period
        scans = self.db.query(ProductScan).filter(
            and_(
                ProductScan.user_id == user_id,
                ProductScan.scanned_at >= period_start,
                ProductScan.scanned_at <= period_end
            )
        ).order_by(ProductScan.scanned_at.desc()).all()
        
        if not scans:
            logger.info(f"No scans found for user {user_id} in period")
            return ExposureData(
                total_exposure=0.0,
                exposure_by_type={},
                exposure_by_category={},
                top_sources=[],
                scan_count=0,
                period_start=period_start,
                period_end=period_end
            )
        
        # Initialize aggregation structures
        exposure_by_type: Dict[str, float] = {}
        exposure_by_category: Dict[str, float] = {}
        scan_contributions: List[Tuple[ProductScan, float]] = []
        
        total_exposure = 0.0
        period_days = (period_end - period_start).days + 1
        
        # Process each scan
        for scan in scans:
            # Calculate weighted exposure for this scan
            scan_exposure = self._calculate_scan_exposure(
                scan,
                period_start,
                period_end,
                period_days
            )
            
            total_exposure += scan_exposure
            scan_contributions.append((scan, scan_exposure))
            
            # Aggregate by EDC type
            if scan.flagged_chemicals:
                for chemical in scan.flagged_chemicals:
                    for edc_type in chemical.get("edc_types", []):
                        if edc_type not in exposure_by_type:
                            exposure_by_type[edc_type] = 0.0
                        
                        # Weight by chemical risk score and confidence
                        chemical_exposure = (
                            chemical.get("risk_score", 0.0) *
                            chemical.get("confidence", 1.0) *
                            self._get_frequency_weight(scan.product_category)
                        )
                        exposure_by_type[edc_type] += chemical_exposure
            
            # Aggregate by product category
            category = scan.product_category or "unknown"
            if category not in exposure_by_category:
                exposure_by_category[category] = 0.0
            exposure_by_category[category] += scan_exposure
        
        # Identify top sources (top 5 contributors)
        scan_contributions.sort(key=lambda x: x[1], reverse=True)
        top_sources = [
            {
                "scan_id": scan.id,
                "product_name": scan.product_name,
                "category": scan.product_category,
                "exposure_contribution": contribution,
                "scanned_at": scan.scanned_at.isoformat(),
                "risk_level": scan.risk_level
            }
            for scan, contribution in scan_contributions[:5]
        ]
        
        logger.info(
            f"Calculated exposure for user {user_id}: "
            f"total={total_exposure:.2f}, scans={len(scans)}, "
            f"types={len(exposure_by_type)}"
        )
        
        return ExposureData(
            total_exposure=round(total_exposure, 2),
            exposure_by_type=exposure_by_type,
            exposure_by_category=exposure_by_category,
            top_sources=top_sources,
            scan_count=len(scans),
            period_start=period_start,
            period_end=period_end
        )
    
    def _calculate_scan_exposure(
        self,
        scan: ProductScan,
        period_start: datetime,
        period_end: datetime,
        period_days: int
    ) -> float:
        """
        Calculate weighted exposure contribution from a single scan
        
        Weighting factors:
        1. Base risk: Overall score (inverted - lower score = higher exposure)
        2. Frequency: Product category frequency weight
        3. Recency: More recent scans weighted higher (decay over time)
        
        Args:
            scan: ProductScan object
            period_start: Start of period
            period_end: End of period
            period_days: Number of days in period
        
        Returns:
            Weighted exposure score
        """
        # Base exposure from overall score (invert: 100 - score)
        # Lower safety score = higher exposure
        base_exposure = 100.0 - (scan.overall_score or 50.0)
        
        # Frequency weight based on product category
        frequency_weight = self._get_frequency_weight(scan.product_category)
        
        # Recency weight (exponential decay)
        # More recent scans have higher weight (assume continued use)
        days_since_scan = (period_end - scan.scanned_at).days
        recency_weight = self._calculate_recency_weight(days_since_scan, period_days)
        
        # Combined weighted exposure
        weighted_exposure = base_exposure * frequency_weight * recency_weight
        
        return weighted_exposure
    
    def _get_frequency_weight(self, category: Optional[str]) -> float:
        """
        Get frequency weight for product category
        
        Args:
            category: Product category
        
        Returns:
            Frequency weight multiplier
        """
        if not category:
            return 0.5  # Default for unknown category
        
        return self.CATEGORY_FREQUENCY_WEIGHTS.get(
            category.lower(),
            0.5  # Default for unrecognized categories
        )
    
    def _calculate_recency_weight(self, days_since_scan: int, period_days: int) -> float:
        """
        Calculate recency weight with exponential decay
        
        Assumes products scanned more recently are still in use.
        Weight decays exponentially over the period.
        
        Args:
            days_since_scan: Days since the scan
            period_days: Total days in the period
        
        Returns:
            Recency weight (0.0 to 1.0)
        """
        if days_since_scan < 0:
            days_since_scan = 0
        
        # Exponential decay: weight = e^(-k * days)
        # k chosen so weight = 0.5 at half the period
        k = 0.693 / max(period_days / 2, 1)  # ln(2) / half_period
        
        import math
        weight = math.exp(-k * days_since_scan)
        
        return weight
    
    def compare_to_epa_limits(
        self,
        total_exposure: float,
        period_type: PeriodType
    ) -> Tuple[float, float, ExposureStatus]:
        """
        Compare exposure to EPA safe limits
        
        Args:
            total_exposure: Total exposure score
            period_type: Type of time period
        
        Returns:
            Tuple of (EPA limit, percent of limit, status)
        """
        epa_limit = self.EPA_SAFE_LIMITS[period_type]
        percent_of_limit = (total_exposure / epa_limit) * 100.0
        
        # Determine status
        if percent_of_limit < self.STATUS_THRESHOLDS[ExposureStatus.SAFE]:
            status = ExposureStatus.SAFE
        elif percent_of_limit < self.STATUS_THRESHOLDS[ExposureStatus.APPROACHING_LIMIT]:
            status = ExposureStatus.APPROACHING_LIMIT
        else:
            status = ExposureStatus.EXCEEDS_LIMIT
        
        return epa_limit, round(percent_of_limit, 1), status
    
    def generate_exposure_report(
        self,
        user_id: int,
        period_type: PeriodType = PeriodType.MONTHLY,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> ExposureReport:
        """
        Generate comprehensive exposure report with trends and recommendations
        
        Args:
            user_id: User ID
            period_type: Type of period (daily, weekly, monthly)
            period_start: Optional start date (defaults to start of current period)
            period_end: Optional end date (defaults to now)
        
        Returns:
            ExposureReport with complete analysis
        """
        # Determine period boundaries if not provided
        if period_end is None:
            period_end = datetime.utcnow()
        
        if period_start is None:
            if period_type == PeriodType.DAILY:
                period_start = period_end.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period_type == PeriodType.WEEKLY:
                period_start = period_end - timedelta(days=7)
            else:  # MONTHLY
                period_start = period_end - timedelta(days=30)
        
        logger.info(
            f"Generating {period_type.value} exposure report for user {user_id}"
        )
        
        # Calculate current period exposure
        exposure_data = self.calculate_cumulative_exposure(
            user_id,
            period_start,
            period_end
        )
        
        # Compare to EPA limits
        epa_limit, percent_of_limit, status = self.compare_to_epa_limits(
            exposure_data.total_exposure,
            period_type
        )
        
        # Get trend data (previous periods)
        trend_data = self._calculate_trend_data(
            user_id,
            period_type,
            period_start,
            num_periods=6
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            exposure_data,
            status,
            percent_of_limit,
            trend_data
        )
        
        # Create and save exposure log
        exposure_log = EDCExposureLog(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type.value,
            total_exposure_score=exposure_data.total_exposure,
            exposure_by_type=exposure_data.exposure_by_type,
            exposure_by_category=exposure_data.exposure_by_category,
            epa_limit=epa_limit,
            percent_of_limit=percent_of_limit,
            status=status.value,
            top_sources=[source for source in exposure_data.top_sources],
            scan_count=exposure_data.scan_count
        )
        
        self.db.add(exposure_log)
        self.db.commit()
        self.db.refresh(exposure_log)
        
        logger.info(
            f"Exposure report generated: status={status.value}, "
            f"percent_of_limit={percent_of_limit:.1f}%"
        )
        
        return ExposureReport(
            user_id=user_id,
            period_type=period_type.value,
            period_start=period_start,
            period_end=period_end,
            total_exposure=exposure_data.total_exposure,
            exposure_by_type=exposure_data.exposure_by_type,
            exposure_by_category=exposure_data.exposure_by_category,
            top_sources=exposure_data.top_sources,
            epa_limit=epa_limit,
            percent_of_limit=percent_of_limit,
            status=status.value,
            scan_count=exposure_data.scan_count,
            trend_data=trend_data,
            recommendations=recommendations
        )
    
    def _calculate_trend_data(
        self,
        user_id: int,
        period_type: PeriodType,
        current_period_start: datetime,
        num_periods: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Calculate exposure trends over previous periods
        
        Args:
            user_id: User ID
            period_type: Type of period
            current_period_start: Start of current period
            num_periods: Number of previous periods to include
        
        Returns:
            List of trend data points
        """
        trend_data = []
        
        # Calculate period duration
        if period_type == PeriodType.DAILY:
            period_delta = timedelta(days=1)
        elif period_type == PeriodType.WEEKLY:
            period_delta = timedelta(days=7)
        else:  # MONTHLY
            period_delta = timedelta(days=30)
        
        # Calculate exposure for each previous period
        for i in range(num_periods, 0, -1):
            period_end = current_period_start - (period_delta * (i - 1))
            period_start = period_end - period_delta
            
            exposure_data = self.calculate_cumulative_exposure(
                user_id,
                period_start,
                period_end
            )
            
            trend_data.append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "total_exposure": exposure_data.total_exposure,
                "scan_count": exposure_data.scan_count
            })
        
        return trend_data
    
    def _generate_recommendations(
        self,
        exposure_data: ExposureData,
        status: ExposureStatus,
        percent_of_limit: float,
        trend_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate personalized reduction strategies
        
        Args:
            exposure_data: Current exposure data
            status: Exposure status
            percent_of_limit: Percentage of EPA limit
            trend_data: Historical trend data
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Status-based recommendations
        if status == ExposureStatus.EXCEEDS_LIMIT:
            recommendations.append(
                f"⚠️ CRITICAL: Your EDC exposure is {percent_of_limit:.0f}% of the safe limit. "
                "Immediate action recommended to reduce exposure."
            )
        elif status == ExposureStatus.APPROACHING_LIMIT:
            recommendations.append(
                f"⚠️ WARNING: Your EDC exposure is {percent_of_limit:.0f}% of the safe limit. "
                "Consider reducing exposure to stay within safe limits."
            )
        else:
            recommendations.append(
                f"✓ SAFE: Your EDC exposure is {percent_of_limit:.0f}% of the safe limit. "
                "Continue monitoring to maintain safe levels."
            )
        
        # Trend-based recommendations
        if len(trend_data) >= 2:
            recent_trend = trend_data[-1]["total_exposure"]
            previous_trend = trend_data[-2]["total_exposure"]
            
            if recent_trend > previous_trend * 1.2:  # 20% increase
                recommendations.append(
                    "📈 TREND ALERT: Your exposure is increasing. "
                    "Review recent product changes and consider alternatives."
                )
        
        # EDC type-specific recommendations
        if exposure_data.exposure_by_type:
            top_edc_types = sorted(
                exposure_data.exposure_by_type.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            for edc_type, exposure in top_edc_types:
                if edc_type == "bpa":
                    recommendations.append(
                        "🔴 PRIMARY SOURCE - BPA: Switch to BPA-free products. "
                        "Avoid heating plastic containers."
                    )
                elif edc_type == "phthalate":
                    recommendations.append(
                        "🔴 PRIMARY SOURCE - Phthalates: Choose phthalate-free personal care products. "
                        "Avoid fragranced products."
                    )
                elif edc_type == "paraben":
                    recommendations.append(
                        "🟡 PRIMARY SOURCE - Parabens: Look for paraben-free cosmetics and lotions."
                    )
                elif edc_type == "heavy_metal":
                    recommendations.append(
                        "🔴 PRIMARY SOURCE - Heavy Metals: Avoid products with lead, mercury, or cadmium. "
                        "Check cosmetics and traditional products."
                    )
        
        # Category-specific recommendations
        if exposure_data.exposure_by_category:
            top_categories = sorted(
                exposure_data.exposure_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            for category, exposure in top_categories:
                if category == "cosmetic":
                    recommendations.append(
                        "💄 FOCUS AREA - Cosmetics: This is your highest exposure category. "
                        "Prioritize switching to clean beauty products."
                    )
                elif category == "food":
                    recommendations.append(
                        "🍽️ FOCUS AREA - Food: This is your highest exposure category. "
                        "Choose organic when possible and avoid plastic packaging."
                    )
                elif category == "personal_care":
                    recommendations.append(
                        "🧴 FOCUS AREA - Personal Care: This is your highest exposure category. "
                        "Switch to natural, EDC-free products."
                    )
        
        # Top sources recommendations
        if exposure_data.top_sources:
            top_source = exposure_data.top_sources[0]
            recommendations.append(
                f"🎯 TOP PRIORITY: Replace '{top_source['product_name']}' - "
                f"it contributes {(top_source['exposure_contribution'] / exposure_data.total_exposure * 100):.0f}% "
                "of your total exposure."
            )
        
        return recommendations
