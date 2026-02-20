"""Micronutrient Tracking Service for deficiency detection and alerting"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.core.logging import logger


class NutrientType(str, Enum):
    """Types of micronutrients tracked"""
    HEMOGLOBIN = "hemoglobin"
    FERRITIN = "ferritin"
    VITAMIN_B12 = "vitamin_b12"
    FOLATE = "folate"
    VITAMIN_D = "vitamin_d"
    PROGESTERONE = "progesterone"
    ESTROGEN = "estrogen"
    THYROID_TSH = "thyroid_tsh"


@dataclass
class NutrientRange:
    """Normal range for a nutrient"""
    min_value: float
    max_value: float
    unit: str
    deficiency_threshold: float
    severe_deficiency_threshold: Optional[float] = None


# Clinical reference ranges
NUTRIENT_RANGES = {
    NutrientType.HEMOGLOBIN: NutrientRange(
        min_value=12.0,
        max_value=16.0,
        unit="g/dL",
        deficiency_threshold=12.0,
        severe_deficiency_threshold=10.0
    ),
    NutrientType.FERRITIN: NutrientRange(
        min_value=15.0,
        max_value=150.0,
        unit="ng/mL",
        deficiency_threshold=30.0,
        severe_deficiency_threshold=15.0
    ),
    NutrientType.VITAMIN_B12: NutrientRange(
        min_value=200.0,
        max_value=900.0,
        unit="pg/mL",
        deficiency_threshold=200.0,
        severe_deficiency_threshold=150.0
    ),
    NutrientType.FOLATE: NutrientRange(
        min_value=2.0,
        max_value=20.0,
        unit="ng/mL",
        deficiency_threshold=2.0,
        severe_deficiency_threshold=1.5
    ),
    NutrientType.VITAMIN_D: NutrientRange(
        min_value=30.0,
        max_value=100.0,
        unit="ng/mL",
        deficiency_threshold=30.0,
        severe_deficiency_threshold=20.0
    ),
    NutrientType.PROGESTERONE: NutrientRange(
        min_value=0.1,
        max_value=1.5,
        unit="ng/mL (postpartum)",
        deficiency_threshold=0.5,
        severe_deficiency_threshold=0.2
    ),
    NutrientType.THYROID_TSH: NutrientRange(
        min_value=0.4,
        max_value=4.0,
        unit="mIU/L",
        deficiency_threshold=0.4,  # Low TSH (hyperthyroid)
        severe_deficiency_threshold=None
    )
}


@dataclass
class LabResult:
    """Lab test result"""
    nutrient_type: NutrientType
    value: float
    unit: str
    tested_at: datetime
    user_id: int
    notes: Optional[str] = None


@dataclass
class DeficiencyAlert:
    """Deficiency detection alert"""
    nutrient_type: NutrientType
    severity: str  # "mild", "moderate", "severe"
    current_value: float
    normal_range: str
    recommendations: List[str]
    alert_asha: bool
    correlations: List[str]  # Correlations with mood/PPD


class MicronutrientService:
    """
    Micronutrient tracking and deficiency detection service
    
    Features:
    - Lab result validation against physiological ranges
    - Deficiency detection with severity classification
    - Trend analysis over time
    - Chronic deficiency escalation
    - Correlation with mood screening results
    - ASHA worker alerts for severe deficiencies
    """
    
    def __init__(self):
        """Initialize micronutrient service"""
        self.nutrient_ranges = NUTRIENT_RANGES
    
    def validate_lab_result(self, result: LabResult) -> Dict[str, Any]:
        """
        Validate lab result against physiological ranges
        
        Args:
            result: Lab result to validate
        
        Returns:
            Validation result with warnings
        """
        nutrient_range = self.nutrient_ranges.get(result.nutrient_type)
        
        if not nutrient_range:
            return {
                "valid": False,
                "error": f"Unknown nutrient type: {result.nutrient_type}"
            }
        
        # Check if value is within reasonable bounds
        if result.value < 0:
            return {
                "valid": False,
                "error": "Value cannot be negative"
            }
        
        # Check if value is extremely high (possible data entry error)
        if result.value > nutrient_range.max_value * 3:
            return {
                "valid": False,
                "error": f"Value {result.value} {result.unit} is unusually high. Please verify.",
                "warning": "Possible data entry error"
            }
        
        # Check unit consistency
        if result.unit != nutrient_range.unit:
            return {
                "valid": False,
                "error": f"Unit mismatch: expected {nutrient_range.unit}, got {result.unit}"
            }
        
        return {
            "valid": True,
            "in_normal_range": nutrient_range.min_value <= result.value <= nutrient_range.max_value
        }
    
    def detect_deficiency(self, result: LabResult) -> Optional[DeficiencyAlert]:
        """
        Detect nutrient deficiency and classify severity
        
        Args:
            result: Lab result to analyze
        
        Returns:
            DeficiencyAlert if deficiency detected, None otherwise
        """
        nutrient_range = self.nutrient_ranges.get(result.nutrient_type)
        
        if not nutrient_range:
            return None
        
        # Special handling for TSH (both high and low are abnormal)
        if result.nutrient_type == NutrientType.THYROID_TSH:
            if result.value < nutrient_range.min_value:
                severity = "severe" if result.value < 0.1 else "moderate"
                return self._create_thyroid_alert(result, severity, "low")
            elif result.value > nutrient_range.max_value:
                severity = "severe" if result.value > 10.0 else "moderate"
                return self._create_thyroid_alert(result, severity, "high")
            return None
        
        # Check for deficiency
        if result.value >= nutrient_range.deficiency_threshold:
            return None  # No deficiency
        
        # Classify severity
        if nutrient_range.severe_deficiency_threshold and result.value < nutrient_range.severe_deficiency_threshold:
            severity = "severe"
        elif result.value < nutrient_range.deficiency_threshold * 0.8:
            severity = "moderate"
        else:
            severity = "mild"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(result.nutrient_type, severity)
        
        # Determine if ASHA alert needed
        alert_asha = severity in ["severe", "moderate"]
        
        # Identify correlations with mood/PPD
        correlations = self._identify_mood_correlations(result.nutrient_type)
        
        logger.info(
            f"Deficiency detected: {result.nutrient_type.value} = {result.value} {result.unit} "
            f"(severity: {severity})"
        )
        
        return DeficiencyAlert(
            nutrient_type=result.nutrient_type,
            severity=severity,
            current_value=result.value,
            normal_range=f"{nutrient_range.min_value}-{nutrient_range.max_value} {nutrient_range.unit}",
            recommendations=recommendations,
            alert_asha=alert_asha,
            correlations=correlations
        )
    
    def _create_thyroid_alert(self, result: LabResult, severity: str, direction: str) -> DeficiencyAlert:
        """Create alert for thyroid dysfunction"""
        nutrient_range = self.nutrient_ranges[NutrientType.THYROID_TSH]
        
        if direction == "low":
            recommendations = [
                "🔬 Hyperthyroidism suspected. Refer to endocrinologist immediately.",
                "⚠️ Monitor for symptoms: anxiety, weight loss, rapid heartbeat, tremors.",
                "📋 Additional tests needed: Free T4, Free T3, thyroid antibodies."
            ]
        else:
            recommendations = [
                "🔬 Hypothyroidism suspected. Refer to endocrinologist immediately.",
                "⚠️ Monitor for symptoms: fatigue, weight gain, depression, cold intolerance.",
                "💊 Thyroid hormone replacement may be needed.",
                "📋 Additional tests needed: Free T4, thyroid antibodies."
            ]
        
        return DeficiencyAlert(
            nutrient_type=result.nutrient_type,
            severity=severity,
            current_value=result.value,
            normal_range=f"{nutrient_range.min_value}-{nutrient_range.max_value} {nutrient_range.unit}",
            recommendations=recommendations,
            alert_asha=True,  # Always alert for thyroid issues
            correlations=["Postpartum thyroiditis is common", "Strong correlation with PPD"]
        )
    
    def _generate_recommendations(self, nutrient_type: NutrientType, severity: str) -> List[str]:
        """Generate personalized recommendations for deficiency"""
        recommendations = []
        
        if nutrient_type == NutrientType.HEMOGLOBIN:
            if severity == "severe":
                recommendations.append("🚨 SEVERE ANEMIA: Immediate medical attention required.")
                recommendations.append("💉 Blood transfusion may be needed if Hb < 7 g/dL.")
            recommendations.append("💊 Start iron supplementation (IFA tablets): 100-200mg elemental iron daily.")
            recommendations.append("🍽️ Increase iron-rich foods: spinach, lentils, jaggery, dates, pomegranate.")
            recommendations.append("🍊 Take with vitamin C (citrus fruits) to enhance absorption.")
            recommendations.append("☕ Avoid tea/coffee with meals (reduces iron absorption).")
            recommendations.append("🔬 Recheck hemoglobin in 4 weeks.")
        
        elif nutrient_type == NutrientType.FERRITIN:
            recommendations.append("💊 Iron supplementation needed: 100-200mg elemental iron daily.")
            recommendations.append("🍽️ Increase dietary iron: red meat, liver, dark leafy greens, fortified cereals.")
            recommendations.append("⚠️ Low ferritin increases PPD risk. Monitor mood closely.")
            recommendations.append("🔬 Recheck ferritin in 8-12 weeks.")
        
        elif nutrient_type == NutrientType.VITAMIN_B12:
            if severity == "severe":
                recommendations.append("💉 B12 injections may be needed (1000 mcg IM weekly).")
            recommendations.append("💊 Oral B12 supplementation: 1000-2000 mcg daily.")
            recommendations.append("🍽️ Increase B12-rich foods: eggs, dairy, fish, fortified foods.")
            recommendations.append("⚠️ B12 deficiency linked to depression and cognitive issues.")
            recommendations.append("🔬 Recheck B12 in 8-12 weeks.")
        
        elif nutrient_type == NutrientType.FOLATE:
            recommendations.append("💊 Folic acid supplementation: 400-800 mcg daily.")
            recommendations.append("🍽️ Increase folate-rich foods: leafy greens, legumes, citrus fruits, fortified grains.")
            recommendations.append("⚠️ Critical for postpartum recovery and future pregnancy.")
            recommendations.append("🔬 Recheck folate in 8-12 weeks.")
        
        elif nutrient_type == NutrientType.VITAMIN_D:
            if severity == "severe":
                recommendations.append("💊 High-dose vitamin D: 50,000 IU weekly for 8 weeks, then maintenance.")
            else:
                recommendations.append("💊 Vitamin D supplementation: 1000-2000 IU daily.")
            recommendations.append("☀️ Increase sun exposure: 15-20 minutes daily (arms/legs exposed).")
            recommendations.append("🍽️ Increase vitamin D foods: fortified milk, fatty fish, egg yolks.")
            recommendations.append("⚠️ Vitamin D deficiency linked to PPD and bone health issues.")
            recommendations.append("🔬 Recheck vitamin D in 12 weeks.")
        
        elif nutrient_type == NutrientType.PROGESTERONE:
            recommendations.append("🔬 Postpartum progesterone drop is normal but monitor symptoms.")
            recommendations.append("⚠️ Low progesterone linked to PPD. Increase mood screening frequency.")
            recommendations.append("🧘 Stress reduction: yoga, meditation, adequate sleep.")
            recommendations.append("💊 Hormonal therapy may be considered (consult gynecologist).")
        
        return recommendations
    
    def _identify_mood_correlations(self, nutrient_type: NutrientType) -> List[str]:
        """Identify correlations between nutrient deficiency and mood/PPD"""
        correlations = {
            NutrientType.HEMOGLOBIN: [
                "Anemia strongly correlated with fatigue and depression",
                "Low hemoglobin reduces oxygen delivery to brain"
            ],
            NutrientType.FERRITIN: [
                "Iron deficiency linked to PPD even without anemia",
                "Low ferritin affects neurotransmitter synthesis"
            ],
            NutrientType.VITAMIN_B12: [
                "B12 deficiency causes depression and cognitive impairment",
                "Critical for nervous system function"
            ],
            NutrientType.FOLATE: [
                "Folate deficiency linked to depression",
                "Important for neurotransmitter production"
            ],
            NutrientType.VITAMIN_D: [
                "Vitamin D deficiency strongly associated with PPD",
                "Acts as neurosteroid affecting mood regulation"
            ],
            NutrientType.PROGESTERONE: [
                "Postpartum progesterone drop is major PPD risk factor",
                "Affects GABA receptors and mood stability"
            ]
        }
        
        return correlations.get(nutrient_type, [])
    
    def analyze_trends(
        self,
        user_id: int,
        nutrient_type: NutrientType,
        results: List[LabResult]
    ) -> Dict[str, Any]:
        """
        Analyze trends in nutrient levels over time
        
        Args:
            user_id: User ID
            nutrient_type: Type of nutrient
            results: List of lab results (chronologically ordered)
        
        Returns:
            Trend analysis with predictions
        """
        if len(results) < 2:
            return {
                "trend": "insufficient_data",
                "message": "Need at least 2 measurements for trend analysis"
            }
        
        # Calculate trend (improving, stable, declining)
        values = [r.value for r in results]
        
        # Simple linear trend
        if values[-1] > values[0]:
            trend = "improving"
        elif values[-1] < values[0]:
            trend = "declining"
        else:
            trend = "stable"
        
        # Calculate rate of change
        time_span = (results[-1].tested_at - results[0].tested_at).days
        if time_span > 0:
            rate_of_change = (values[-1] - values[0]) / time_span
        else:
            rate_of_change = 0
        
        # Predict next deficiency risk
        nutrient_range = self.nutrient_ranges[nutrient_type]
        current_value = values[-1]
        
        if trend == "declining" and rate_of_change < 0:
            # Estimate days until deficiency
            if current_value > nutrient_range.deficiency_threshold:
                days_to_deficiency = int(
                    (current_value - nutrient_range.deficiency_threshold) / abs(rate_of_change)
                )
            else:
                days_to_deficiency = 0
        else:
            days_to_deficiency = None
        
        logger.info(
            f"Trend analysis for {nutrient_type.value}: {trend} "
            f"(rate: {rate_of_change:.2f}/day)"
        )
        
        return {
            "trend": trend,
            "rate_of_change_per_day": round(rate_of_change, 3),
            "current_value": current_value,
            "previous_value": values[0],
            "measurements_count": len(results),
            "time_span_days": time_span,
            "days_to_deficiency": days_to_deficiency,
            "recommendation": self._get_trend_recommendation(trend, days_to_deficiency)
        }
    
    def _get_trend_recommendation(self, trend: str, days_to_deficiency: Optional[int]) -> str:
        """Get recommendation based on trend"""
        if trend == "improving":
            return "✓ Levels are improving. Continue current treatment."
        elif trend == "stable":
            return "→ Levels are stable. Maintain current regimen."
        elif trend == "declining":
            if days_to_deficiency and days_to_deficiency < 30:
                return f"⚠️ URGENT: Declining rapidly. Deficiency expected in {days_to_deficiency} days. Increase supplementation."
            elif days_to_deficiency and days_to_deficiency < 90:
                return f"⚠️ Declining trend. Deficiency risk in {days_to_deficiency} days. Review treatment plan."
            else:
                return "⚠️ Declining trend detected. Monitor closely and adjust treatment."
        return "Continue monitoring."
    
    def check_chronic_deficiency(
        self,
        user_id: int,
        nutrient_type: NutrientType,
        results: List[LabResult],
        threshold_months: int = 3
    ) -> Dict[str, Any]:
        """
        Check for chronic deficiency (persistent for >3 months)
        
        Args:
            user_id: User ID
            nutrient_type: Type of nutrient
            results: List of lab results
            threshold_months: Months to consider chronic
        
        Returns:
            Chronic deficiency status and escalation recommendations
        """
        if not results:
            return {"chronic": False, "message": "No results available"}
        
        nutrient_range = self.nutrient_ranges[nutrient_type]
        threshold_days = threshold_months * 30
        
        # Check if all results in time window show deficiency
        cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)
        recent_results = [r for r in results if r.tested_at >= cutoff_date]
        
        if not recent_results:
            return {"chronic": False, "message": "No recent results"}
        
        # Check if all recent results show deficiency
        all_deficient = all(
            r.value < nutrient_range.deficiency_threshold
            for r in recent_results
        )
        
        if all_deficient and len(recent_results) >= 2:
            logger.warning(
                f"CHRONIC DEFICIENCY detected: {nutrient_type.value} for user {user_id} "
                f"({len(recent_results)} deficient results over {threshold_months} months)"
            )
            
            return {
                "chronic": True,
                "duration_months": threshold_months,
                "measurements_count": len(recent_results),
                "escalation_needed": True,
                "recommendations": [
                    "🚨 CHRONIC DEFICIENCY: Escalate to specialist.",
                    "🔬 Investigate underlying causes (malabsorption, chronic disease).",
                    "💊 Review treatment compliance and dosage.",
                    "📋 Consider alternative treatment approaches.",
                    "⚠️ High-priority ASHA follow-up required."
                ]
            }
        
        return {"chronic": False, "message": "No chronic deficiency detected"}


# Global service instance
micronutrient_service: Optional[MicronutrientService] = None


def get_micronutrient_service() -> MicronutrientService:
    """
    Get or create global micronutrient service instance
    
    Returns:
        MicronutrientService instance
    """
    global micronutrient_service
    
    if micronutrient_service is None:
        micronutrient_service = MicronutrientService()
        logger.info("Micronutrient service initialized")
    
    return micronutrient_service
