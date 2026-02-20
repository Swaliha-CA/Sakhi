"""ASHA Dashboard Service for case management and intervention tracking

Provides frontline health workers with:
- Caseload management with health status indicators
- High-risk case filtering and prioritization
- Real-time alert aggregation
- Intervention logging and tracking
- Performance reporting
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.db.models import User, HealthRecord, Screening, ProductScan, SutikaCheckIn
from app.services.ppd_prediction_service import get_ppd_model, RiskFactors, RiskLevel
from app.services.micronutrient_service import get_micronutrient_service, NutrientType, LabResult
from app.core.logging import logger


class AlertType(str, Enum):
    """Types of health alerts"""
    HIGH_PPD_RISK = "high_ppd_risk"
    MICRONUTRIENT_DEFICIENCY = "micronutrient_deficiency"
    HIGH_EDC_EXPOSURE = "high_edc_exposure"
    HEAT_STRESS = "heat_stress"
    SCREENING_DUE = "screening_due"
    CHRONIC_DEFICIENCY = "chronic_deficiency"


class AlertPriority(str, Enum):
    """Alert priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class InterventionType(str, Enum):
    """Types of ASHA interventions"""
    HOME_VISIT = "home_visit"
    PHONE_COUNSELING = "phone_counseling"
    REFERRAL = "referral"
    NUTRITION_EDUCATION = "nutrition_education"
    MENTAL_HEALTH_SUPPORT = "mental_health_support"
    IFA_DISTRIBUTION = "ifa_distribution"
    SCREENING_CONDUCTED = "screening_conducted"


@dataclass
class Alert:
    """Health alert for ASHA dashboard"""
    alert_id: str
    user_id: int
    user_name: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


@dataclass
class CaseSummary:
    """Summary of a user's health case"""
    user_id: int
    user_name: str
    age: int
    location: str
    risk_level: str
    last_contact: Optional[datetime]
    
    # Recent health data
    recent_screenings: List[Dict[str, Any]] = field(default_factory=list)
    recent_lab_results: List[Dict[str, Any]] = field(default_factory=list)
    recent_product_scans: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk indicators
    ppd_risk_score: Optional[float] = None
    micronutrient_deficiencies: List[str] = field(default_factory=list)
    edc_exposure_level: Optional[str] = None
    
    # Upcoming tasks
    upcoming_tasks: List[Dict[str, Any]] = field(default_factory=list)
    pending_screenings: List[str] = field(default_factory=list)


@dataclass
class Intervention:
    """ASHA intervention record"""
    intervention_id: Optional[int]
    asha_id: int
    user_id: int
    intervention_type: InterventionType
    notes: str
    outcome: str
    follow_up_date: Optional[datetime]
    conducted_at: datetime


@dataclass
class Caseload:
    """ASHA worker's caseload"""
    asha_id: int
    total_cases: int
    high_risk_cases: int
    critical_cases: int
    pending_screenings: int
    recent_alerts: List[Alert]
    cases: List[CaseSummary]


@dataclass
class ASHAReport:
    """ASHA performance report"""
    asha_id: int
    asha_name: str
    report_period: str
    
    # Activity metrics
    total_interventions: int
    home_visits: int
    phone_counseling: int
    referrals: int
    screenings_conducted: int
    
    # Outcome metrics
    high_risk_cases_identified: int
    successful_referrals: int
    ppd_cases_prevented: int
    
    # Caseload metrics
    total_assigned_users: int
    active_users: int
    
    generated_at: datetime


class ASHAService:
    """
    ASHA Dashboard Service for case management
    
    Features:
    - Caseload retrieval with health status indicators
    - High-risk case filtering and sorting
    - Alert aggregation by type and priority
    - Intervention logging and tracking
    - Performance report generation
    - Real-time updates support
    """
    
    def __init__(self):
        """Initialize ASHA service"""
        self.ppd_model = get_ppd_model()
        self.micronutrient_service = get_micronutrient_service()
    
    def get_caseload(
        self,
        db: Session,
        asha_id: int,
        filter_risk_level: Optional[str] = None,
        sort_by: str = "risk_level"
    ) -> Caseload:
        """
        Get ASHA worker's caseload with filtering and sorting
        
        Args:
            db: Database session
            asha_id: ASHA worker ID
            filter_risk_level: Filter by risk level (critical, high, moderate, low)
            sort_by: Sort criteria (risk_level, last_contact, name)
        
        Returns:
            Caseload with all assigned users and alerts
        """
        logger.info(f"Retrieving caseload for ASHA {asha_id}")
        
        # Get all assigned users (in real system, would have ASHA assignment table)
        # For now, we'll get all users in the same district
        users = db.query(User).all()
        
        # Build case summaries
        cases = []
        high_risk_count = 0
        critical_count = 0
        pending_screenings_count = 0
        
        for user in users:
            case_summary = self._build_case_summary(db, user)
            
            # Apply risk level filter
            if filter_risk_level and case_summary.risk_level != filter_risk_level:
                continue
            
            cases.append(case_summary)
            
            # Count metrics
            if case_summary.risk_level == "critical":
                critical_count += 1
            elif case_summary.risk_level == "high":
                high_risk_count += 1
            
            pending_screenings_count += len(case_summary.pending_screenings)
        
        # Sort cases
        cases = self._sort_cases(cases, sort_by)
        
        # Get recent alerts
        recent_alerts = self._get_recent_alerts(db, asha_id, limit=20)
        
        logger.info(
            f"Caseload retrieved: {len(cases)} cases, "
            f"{critical_count} critical, {high_risk_count} high-risk"
        )
        
        return Caseload(
            asha_id=asha_id,
            total_cases=len(cases),
            high_risk_cases=high_risk_count,
            critical_cases=critical_count,
            pending_screenings=pending_screenings_count,
            recent_alerts=recent_alerts,
            cases=cases
        )
    
    def _build_case_summary(self, db: Session, user: User) -> CaseSummary:
        """Build comprehensive case summary for a user"""
        # Get recent screenings
        recent_screenings = db.query(Screening).filter(
            Screening.user_id == user.id
        ).order_by(desc(Screening.conducted_at)).limit(5).all()
        
        screenings_data = [
            {
                "type": s.screening_type,
                "score": s.total_score,
                "risk_level": s.risk_level,
                "date": s.conducted_at.isoformat()
            }
            for s in recent_screenings
        ]
        
        # Get recent lab results from health records
        lab_records = db.query(HealthRecord).filter(
            and_(
                HealthRecord.user_id == user.id,
                HealthRecord.event_type == "lab_result"
            )
        ).order_by(desc(HealthRecord.recorded_at)).limit(5).all()
        
        lab_results_data = [
            {
                "test_type": lr.event_data.get("test_type"),
                "results": lr.event_data.get("results"),
                "date": lr.recorded_at.isoformat()
            }
            for lr in lab_records
        ]
        
        # Get recent product scans
        recent_scans = db.query(ProductScan).filter(
            ProductScan.user_id == user.id
        ).order_by(desc(ProductScan.scanned_at)).limit(5).all()
        
        scans_data = [
            {
                "product_name": ps.product_name,
                "risk_level": ps.risk_level,
                "score": ps.overall_score,
                "date": ps.scanned_at.isoformat()
            }
            for ps in recent_scans
        ]
        
        # Calculate PPD risk if screening data available
        ppd_risk_score = None
        risk_level = "low"
        
        if recent_screenings:
            latest_screening = recent_screenings[0]
            risk_factors = RiskFactors(
                epds_score=latest_screening.total_score if latest_screening.screening_type == "epds" else None,
                phq9_score=latest_screening.total_score if latest_screening.screening_type == "phq9" else None
            )
            
            # Add lab data if available
            if lab_records:
                latest_lab = lab_records[0]
                lab_data = latest_lab.event_data.get("results", [])
                for result in lab_data:
                    param = result.get("parameter", "").lower()
                    value = result.get("value")
                    
                    if "hemoglobin" in param:
                        risk_factors.hemoglobin = value
                    elif "ferritin" in param:
                        risk_factors.ferritin = value
                    elif "b12" in param or "vitamin b12" in param:
                        risk_factors.vitamin_b12 = value
                    elif "folate" in param:
                        risk_factors.folate = value
            
            # Calculate PPD risk
            prediction = self.ppd_model.predict(risk_factors)
            ppd_risk_score = prediction.risk_score
            risk_level = prediction.risk_level.value
        
        # Identify micronutrient deficiencies
        deficiencies = []
        if lab_records:
            latest_lab = lab_records[0]
            lab_data = latest_lab.event_data.get("results", [])
            for result in lab_data:
                if result.get("flag") in ["low", "critical"]:
                    deficiencies.append(result.get("parameter"))
        
        # Determine EDC exposure level
        edc_exposure_level = None
        if recent_scans:
            avg_score = sum(s.overall_score or 0 for s in recent_scans) / len(recent_scans)
            if avg_score < 40:
                edc_exposure_level = "high"
            elif avg_score < 60:
                edc_exposure_level = "moderate"
            else:
                edc_exposure_level = "low"
        
        # Determine pending screenings
        pending_screenings = []
        if not recent_screenings or (datetime.utcnow() - recent_screenings[0].conducted_at).days > 30:
            pending_screenings.append("EPDS screening overdue")
        
        # Determine upcoming tasks
        upcoming_tasks = []
        if ppd_risk_score and ppd_risk_score >= 70:
            upcoming_tasks.append({
                "task": "High-risk PPD follow-up",
                "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "priority": "critical"
            })
        
        if deficiencies:
            upcoming_tasks.append({
                "task": f"Micronutrient counseling ({', '.join(deficiencies)})",
                "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "priority": "high"
            })
        
        # Get last contact (last intervention or screening)
        last_contact = None
        if recent_screenings:
            last_contact = recent_screenings[0].conducted_at
        
        return CaseSummary(
            user_id=user.id,
            user_name=user.name or "Unknown",
            age=user.age or 0,
            location=f"{user.district}, {user.state}" if user.district and user.state else "Unknown",
            risk_level=risk_level,
            last_contact=last_contact,
            recent_screenings=screenings_data,
            recent_lab_results=lab_results_data,
            recent_product_scans=scans_data,
            ppd_risk_score=ppd_risk_score,
            micronutrient_deficiencies=deficiencies,
            edc_exposure_level=edc_exposure_level,
            upcoming_tasks=upcoming_tasks,
            pending_screenings=pending_screenings
        )
    
    def _sort_cases(self, cases: List[CaseSummary], sort_by: str) -> List[CaseSummary]:
        """Sort cases by specified criteria"""
        risk_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        
        if sort_by == "risk_level":
            return sorted(cases, key=lambda c: risk_order.get(c.risk_level, 4))
        elif sort_by == "last_contact":
            return sorted(cases, key=lambda c: c.last_contact or datetime.min)
        elif sort_by == "name":
            return sorted(cases, key=lambda c: c.user_name)
        else:
            return cases
    
    def _get_recent_alerts(
        self,
        db: Session,
        asha_id: int,
        limit: int = 20
    ) -> List[Alert]:
        """Get recent alerts for ASHA's caseload"""
        alerts = []
        
        # Get all users (in real system, would filter by ASHA assignment)
        users = db.query(User).all()
        
        for user in users:
            # Check for high PPD risk
            recent_screenings = db.query(Screening).filter(
                Screening.user_id == user.id
            ).order_by(desc(Screening.conducted_at)).limit(1).all()
            
            if recent_screenings:
                screening = recent_screenings[0]
                if screening.risk_level in ["high", "critical"]:
                    alerts.append(Alert(
                        alert_id=f"ppd_{user.id}_{screening.id}",
                        user_id=user.id,
                        user_name=user.name or "Unknown",
                        alert_type=AlertType.HIGH_PPD_RISK,
                        priority=AlertPriority.CRITICAL if screening.risk_level == "critical" else AlertPriority.HIGH,
                        title=f"High PPD Risk: {user.name}",
                        message=f"PPD risk score: {screening.total_score}. Immediate follow-up required.",
                        created_at=screening.conducted_at
                    ))
            
            # Check for micronutrient deficiencies
            lab_records = db.query(HealthRecord).filter(
                and_(
                    HealthRecord.user_id == user.id,
                    HealthRecord.event_type == "lab_result"
                )
            ).order_by(desc(HealthRecord.recorded_at)).limit(1).all()
            
            if lab_records:
                lab = lab_records[0]
                lab_data = lab.event_data.get("results", [])
                for result in lab_data:
                    if result.get("flag") in ["low", "critical"]:
                        alerts.append(Alert(
                            alert_id=f"deficiency_{user.id}_{lab.id}_{result.get('parameter')}",
                            user_id=user.id,
                            user_name=user.name or "Unknown",
                            alert_type=AlertType.MICRONUTRIENT_DEFICIENCY,
                            priority=AlertPriority.HIGH if result.get("flag") == "critical" else AlertPriority.MODERATE,
                            title=f"Micronutrient Deficiency: {user.name}",
                            message=f"{result.get('parameter')}: {result.get('value')} {result.get('unit')} (Low)",
                            created_at=lab.recorded_at
                        ))
        
        # Sort by priority and date
        priority_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        alerts.sort(key=lambda a: (priority_order[a.priority.value], a.created_at), reverse=True)
        
        return alerts[:limit]
    
    def get_high_risk_cases(
        self,
        db: Session,
        asha_id: int
    ) -> List[CaseSummary]:
        """Get only high-risk and critical cases"""
        caseload = self.get_caseload(db, asha_id)
        return [
            case for case in caseload.cases
            if case.risk_level in ["high", "critical"]
        ]
    
    def log_intervention(
        self,
        db: Session,
        intervention: Intervention
    ) -> Dict[str, Any]:
        """
        Log an ASHA intervention
        
        Args:
            db: Database session
            intervention: Intervention details
        
        Returns:
            Logged intervention with ID
        """
        logger.info(
            f"Logging intervention: ASHA {intervention.asha_id} -> "
            f"User {intervention.user_id} ({intervention.intervention_type.value})"
        )
        
        # Create health record for intervention
        intervention_record = HealthRecord(
            user_id=intervention.user_id,
            event_type="intervention",
            event_data={
                "asha_id": intervention.asha_id,
                "intervention_type": intervention.intervention_type.value,
                "notes": intervention.notes,
                "outcome": intervention.outcome,
                "follow_up_date": intervention.follow_up_date.isoformat() if intervention.follow_up_date else None
            },
            recorded_at=intervention.conducted_at,
            device_id=f"asha_{intervention.asha_id}",
            synced_to_cloud=False
        )
        
        db.add(intervention_record)
        db.commit()
        db.refresh(intervention_record)
        
        logger.info(f"Intervention logged with ID: {intervention_record.id}")
        
        return {
            "intervention_id": intervention_record.id,
            "status": "logged",
            "message": "Intervention successfully recorded"
        }
    
    def generate_report(
        self,
        db: Session,
        asha_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> ASHAReport:
        """
        Generate ASHA performance report
        
        Args:
            db: Database session
            asha_id: ASHA worker ID
            start_date: Report start date
            end_date: Report end date
        
        Returns:
            Performance report with metrics
        """
        logger.info(f"Generating report for ASHA {asha_id} ({start_date} to {end_date})")
        
        # Get all interventions in period
        interventions = db.query(HealthRecord).filter(
            and_(
                HealthRecord.event_type == "intervention",
                HealthRecord.recorded_at >= start_date,
                HealthRecord.recorded_at <= end_date,
                HealthRecord.event_data["asha_id"].astext == str(asha_id)
            )
        ).all()
        
        # Count by type
        total_interventions = len(interventions)
        home_visits = sum(1 for i in interventions if i.event_data.get("intervention_type") == "home_visit")
        phone_counseling = sum(1 for i in interventions if i.event_data.get("intervention_type") == "phone_counseling")
        referrals = sum(1 for i in interventions if i.event_data.get("intervention_type") == "referral")
        screenings = sum(1 for i in interventions if i.event_data.get("intervention_type") == "screening_conducted")
        
        # Get caseload metrics
        caseload = self.get_caseload(db, asha_id)
        
        # Calculate outcome metrics (simplified)
        high_risk_identified = caseload.high_risk_cases + caseload.critical_cases
        
        report_period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        logger.info(
            f"Report generated: {total_interventions} interventions, "
            f"{high_risk_identified} high-risk cases"
        )
        
        return ASHAReport(
            asha_id=asha_id,
            asha_name=f"ASHA Worker {asha_id}",
            report_period=report_period,
            total_interventions=total_interventions,
            home_visits=home_visits,
            phone_counseling=phone_counseling,
            referrals=referrals,
            screenings_conducted=screenings,
            high_risk_cases_identified=high_risk_identified,
            successful_referrals=referrals,  # Simplified
            ppd_cases_prevented=0,  # Would need longitudinal tracking
            total_assigned_users=caseload.total_cases,
            active_users=caseload.total_cases,  # Simplified
            generated_at=datetime.utcnow()
        )
    
    def aggregate_alerts(
        self,
        db: Session,
        asha_id: int
    ) -> Dict[str, Any]:
        """
        Aggregate alerts by type and priority
        
        Args:
            db: Database session
            asha_id: ASHA worker ID
        
        Returns:
            Aggregated alerts grouped by type and priority
        """
        alerts = self._get_recent_alerts(db, asha_id, limit=100)
        
        # Group by type
        by_type = {}
        for alert in alerts:
            alert_type = alert.alert_type.value
            if alert_type not in by_type:
                by_type[alert_type] = []
            by_type[alert_type].append(alert)
        
        # Group by priority
        by_priority = {}
        for alert in alerts:
            priority = alert.priority.value
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(alert)
        
        # Count statistics
        stats = {
            "total_alerts": len(alerts),
            "critical": len(by_priority.get("critical", [])),
            "high": len(by_priority.get("high", [])),
            "moderate": len(by_priority.get("moderate", [])),
            "low": len(by_priority.get("low", []))
        }
        
        logger.info(
            f"Alerts aggregated for ASHA {asha_id}: "
            f"{stats['total_alerts']} total, {stats['critical']} critical"
        )
        
        return {
            "by_type": {k: [self._alert_to_dict(a) for a in v] for k, v in by_type.items()},
            "by_priority": {k: [self._alert_to_dict(a) for a in v] for k, v in by_priority.items()},
            "stats": stats
        }
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert Alert to dictionary"""
        return {
            "alert_id": alert.alert_id,
            "user_id": alert.user_id,
            "user_name": alert.user_name,
            "alert_type": alert.alert_type.value,
            "priority": alert.priority.value,
            "title": alert.title,
            "message": alert.message,
            "created_at": alert.created_at.isoformat(),
            "acknowledged": alert.acknowledged
        }


# Global service instance
asha_service: Optional[ASHAService] = None


def get_asha_service() -> ASHAService:
    """
    Get or create global ASHA service instance
    
    Returns:
        ASHAService instance
    """
    global asha_service
    
    if asha_service is None:
        asha_service = ASHAService()
        logger.info("ASHA service initialized")
    
    return asha_service
