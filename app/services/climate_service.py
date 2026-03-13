"""Climate-Health Shield Service for heat stress and WASH resource management"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from app.core.logging import logger


class WBGTRiskLevel(str, Enum):
    """WBGT risk levels"""
    SAFE = "safe"
    CAUTION = "caution"
    EXTREME_CAUTION = "extreme_caution"
    DANGER = "danger"
    EXTREME_DANGER = "extreme_danger"


class ActivityLevel(str, Enum):
    """Physical activity levels"""
    REST = "rest"
    LIGHT = "light"  # Light work (household chores)
    MODERATE = "moderate"  # Moderate work (farming, walking)
    HEAVY = "heavy"  # Heavy work (agricultural labor)


@dataclass
class WeatherData:
    """Weather data from IMD or NASA"""
    temperature_celsius: float  # Dry bulb temperature
    humidity_percent: float  # Relative humidity
    location: str
    timestamp: datetime
    source: str  # "IMD" or "NASA"


@dataclass
class WBGTCalculation:
    """WBGT calculation result"""
    wbgt_celsius: float
    risk_level: WBGTRiskLevel
    temperature: float
    humidity: float
    location: str
    calculated_at: datetime
    recommendations: List[str]


@dataclass
class HeatIncident:
    """Heat-related health incident"""
    user_id: int
    incident_type: str  # "heat_exhaustion", "heat_cramps", "heat_stroke", "dehydration"
    severity: str  # "mild", "moderate", "severe"
    symptoms: List[str]
    wbgt_at_incident: float
    activity_level: ActivityLevel
    reported_at: datetime
    location: str


@dataclass
class WASHFacility:
    """WASH facility information"""
    facility_id: str
    facility_type: str  # "toilet", "water_point", "sanitation"
    name: str
    latitude: float
    longitude: float
    status: str  # "operational", "non_operational", "under_maintenance"
    last_updated: datetime
    reported_by: Optional[str] = None
    notes: Optional[str] = None


class ClimateHealthService:
    """
    Climate-Health Shield service for heat stress management and WASH resources
    
    Features:
    - WBGT calculation from weather data
    - Heat risk classification
    - Work-rest cycle recommendations
    - Hydration guidance
    - Heat incident logging and adaptation
    - Cumulative heat exposure tracking
    - WASH facility mapping and search
    - Community reporting for facility status
    """
    
    # WBGT risk thresholds (°C)
    WBGT_THRESHOLDS = {
        WBGTRiskLevel.SAFE: 27.0,
        WBGTRiskLevel.CAUTION: 29.0,
        WBGTRiskLevel.EXTREME_CAUTION: 31.0,
        WBGTRiskLevel.DANGER: 33.0,
        WBGTRiskLevel.EXTREME_DANGER: 35.0
    }
    
    def __init__(self):
        """Initialize climate health service"""
        self.heat_incidents: Dict[int, List[HeatIncident]] = {}
        self.wash_facilities: Dict[str, WASHFacility] = {}
    
    def calculate_wbgt(self, weather: WeatherData) -> WBGTCalculation:
        """
        Calculate Wet Bulb Globe Temperature (WBGT)
        
        Simplified formula for outdoor shade:
        WBGT = 0.7 × Twb + 0.2 × Tg + 0.1 × Tdb
        
        Where:
        - Twb = Wet bulb temperature (estimated from temp + humidity)
        - Tg = Globe temperature (approximated as Tdb + 2°C in sun)
        - Tdb = Dry bulb temperature (actual air temperature)
        
        Args:
            weather: Weather data
        
        Returns:
            WBGT calculation with risk level and recommendations
        """
        # Estimate wet bulb temperature from dry bulb and humidity
        twb = self._estimate_wet_bulb_temp(
            weather.temperature_celsius,
            weather.humidity_percent
        )
        
        # Approximate globe temperature (in shade, Tg ≈ Tdb)
        tg = weather.temperature_celsius
        tdb = weather.temperature_celsius
        
        # Calculate WBGT
        wbgt = 0.7 * twb + 0.2 * tg + 0.1 * tdb
        
        # Classify risk level
        risk_level = self._classify_wbgt_risk(wbgt)
        
        # Generate recommendations
        recommendations = self._generate_heat_recommendations(wbgt, risk_level)
        
        logger.info(
            f"WBGT calculated: {wbgt:.1f}°C (risk: {risk_level.value}) "
            f"at {weather.location}"
        )
        
        return WBGTCalculation(
            wbgt_celsius=round(wbgt, 1),
            risk_level=risk_level,
            temperature=weather.temperature_celsius,
            humidity=weather.humidity_percent,
            location=weather.location,
            calculated_at=datetime.utcnow(),
            recommendations=recommendations
        )
    
    def _estimate_wet_bulb_temp(self, temp_c: float, humidity_percent: float) -> float:
        """
        Estimate wet bulb temperature using Stull's formula
        
        Simplified approximation:
        Twb = T × atan(0.151977 × √(RH + 8.313659)) + atan(T + RH) 
              - atan(RH - 1.676331) + 0.00391838 × RH^(3/2) × atan(0.023101 × RH) 
              - 4.686035
        
        For simplicity, using a more practical approximation
        """
        rh = humidity_percent / 100.0
        
        # Simplified wet bulb approximation
        twb = temp_c * math.atan(0.151977 * math.sqrt(humidity_percent + 8.313659))
        twb += math.atan(temp_c + humidity_percent)
        twb -= math.atan(humidity_percent - 1.676331)
        twb += 0.00391838 * (humidity_percent ** 1.5) * math.atan(0.023101 * humidity_percent)
        twb -= 4.686035
        
        return twb
    
    def _classify_wbgt_risk(self, wbgt: float) -> WBGTRiskLevel:
        """Classify WBGT risk level"""
        if wbgt >= self.WBGT_THRESHOLDS[WBGTRiskLevel.EXTREME_DANGER]:
            return WBGTRiskLevel.EXTREME_DANGER
        elif wbgt >= self.WBGT_THRESHOLDS[WBGTRiskLevel.DANGER]:
            return WBGTRiskLevel.DANGER
        elif wbgt >= self.WBGT_THRESHOLDS[WBGTRiskLevel.EXTREME_CAUTION]:
            return WBGTRiskLevel.EXTREME_CAUTION
        elif wbgt >= self.WBGT_THRESHOLDS[WBGTRiskLevel.CAUTION]:
            return WBGTRiskLevel.CAUTION
        else:
            return WBGTRiskLevel.SAFE
    
    def _generate_heat_recommendations(
        self,
        wbgt: float,
        risk_level: WBGTRiskLevel
    ) -> List[str]:
        """Generate heat safety recommendations"""
        recommendations = []
        
        if risk_level == WBGTRiskLevel.SAFE:
            recommendations.append("✓ Safe conditions. Normal activities permitted.")
            recommendations.append("💧 Maintain regular hydration (2-3 liters/day).")
        
        elif risk_level == WBGTRiskLevel.CAUTION:
            recommendations.append("⚠️ CAUTION: Heat stress possible with prolonged exposure.")
            recommendations.append("💧 Increase fluid intake (3-4 liters/day).")
            recommendations.append("⏰ Take breaks every 2 hours in shade.")
            recommendations.append("👒 Wear light-colored, loose clothing and head covering.")
        
        elif risk_level == WBGTRiskLevel.EXTREME_CAUTION:
            recommendations.append("⚠️ EXTREME CAUTION: Heat exhaustion and cramps likely.")
            recommendations.append("💧 Drink 4-5 liters of water daily with ORS.")
            recommendations.append("⏰ Work-rest cycle: 45 min work, 15 min rest in shade.")
            recommendations.append("🌅 Avoid outdoor work 11 AM - 3 PM.")
            recommendations.append("🧊 Use cooling measures: wet cloth on neck, cold water.")
        
        elif risk_level == WBGTRiskLevel.DANGER:
            recommendations.append("🚨 DANGER: Heat stroke highly likely.")
            recommendations.append("⛔ Avoid all non-essential outdoor activities.")
            recommendations.append("💧 Drink 5-6 liters with ORS. Monitor urine color.")
            recommendations.append("⏰ If work essential: 30 min work, 30 min rest.")
            recommendations.append("🏥 Watch for symptoms: dizziness, nausea, confusion.")
            recommendations.append("📞 Emergency contact ready. Know nearest health facility.")
        
        elif risk_level == WBGTRiskLevel.EXTREME_DANGER:
            recommendations.append("🚨 EXTREME DANGER: Heat stroke imminent.")
            recommendations.append("⛔ STOP all outdoor work immediately.")
            recommendations.append("🏠 Stay indoors in coolest area.")
            recommendations.append("💧 Continuous hydration with ORS.")
            recommendations.append("🧊 Active cooling: wet sheets, fans, cold water.")
            recommendations.append("🏥 Seek medical attention if any symptoms appear.")
            recommendations.append("📞 Alert ASHA worker and community.")
        
        return recommendations
    
    def get_work_rest_cycle(
        self,
        wbgt: float,
        activity_level: ActivityLevel
    ) -> Dict[str, Any]:
        """
        Calculate work-rest cycle based on WBGT and activity level
        
        Args:
            wbgt: WBGT value
            activity_level: Physical activity level
        
        Returns:
            Work-rest cycle recommendations
        """
        # Activity multipliers (higher activity = more rest needed)
        activity_multipliers = {
            ActivityLevel.REST: 1.0,
            ActivityLevel.LIGHT: 1.2,
            ActivityLevel.MODERATE: 1.5,
            ActivityLevel.HEAVY: 2.0
        }
        
        multiplier = activity_multipliers[activity_level]
        
        # Base work-rest ratios by WBGT
        if wbgt < 27:
            work_min, rest_min = 60, 0
        elif wbgt < 29:
            work_min, rest_min = 50, 10
        elif wbgt < 31:
            work_min, rest_min = 40, 20
        elif wbgt < 33:
            work_min, rest_min = 30, 30
        elif wbgt < 35:
            work_min, rest_min = 20, 40
        else:
            work_min, rest_min = 0, 60  # No work recommended
        
        # Adjust for activity level
        rest_min = int(rest_min * multiplier)
        work_min = max(0, 60 - rest_min)
        
        return {
            "work_minutes": work_min,
            "rest_minutes": rest_min,
            "cycle_description": f"{work_min} min work, {rest_min} min rest per hour",
            "activity_level": activity_level.value,
            "wbgt": wbgt,
            "recommendation": "No outdoor work" if work_min == 0 else "Follow work-rest cycle strictly"
        }
    
    def log_heat_incident(self, incident: HeatIncident):
        """
        Log heat-related health incident
        
        Args:
            incident: Heat incident details
        """
        if incident.user_id not in self.heat_incidents:
            self.heat_incidents[incident.user_id] = []
        
        self.heat_incidents[incident.user_id].append(incident)
        
        logger.warning(
            f"Heat incident logged: {incident.incident_type} ({incident.severity}) "
            f"for user {incident.user_id} at WBGT {incident.wbgt_at_incident}°C"
        )
    
    def adapt_recommendations(
        self,
        user_id: int,
        current_wbgt: float
    ) -> List[str]:
        """
        Adapt recommendations based on user's heat incident history
        
        Args:
            user_id: User ID
            current_wbgt: Current WBGT value
        
        Returns:
            Personalized recommendations
        """
        incidents = self.heat_incidents.get(user_id, [])
        
        if not incidents:
            return []
        
        # Check for recent incidents (last 30 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        recent_incidents = [i for i in incidents if i.reported_at >= recent_cutoff]
        
        if not recent_incidents:
            return []
        
        # Analyze incident patterns
        severe_incidents = [i for i in recent_incidents if i.severity == "severe"]
        incident_wbgts = [i.wbgt_at_incident for i in recent_incidents]
        min_incident_wbgt = min(incident_wbgts) if incident_wbgts else 999
        
        recommendations = []
        
        if severe_incidents:
            recommendations.append(
                "⚠️ PERSONALIZED ALERT: You have history of severe heat incidents. "
                "Extra caution required."
            )
        
        if current_wbgt >= min_incident_wbgt - 2:
            recommendations.append(
                f"⚠️ Current conditions ({current_wbgt:.1f}°C WBGT) similar to your "
                f"previous heat incident ({min_incident_wbgt:.1f}°C). Take extra precautions."
            )
            recommendations.append("💧 Increase hydration by 1-2 liters above normal.")
            recommendations.append("⏰ Reduce work duration by 25%.")
        
        if len(recent_incidents) >= 3:
            recommendations.append(
                "🏥 Multiple heat incidents detected. Consult healthcare provider "
                "for heat sensitivity assessment."
            )
        
        return recommendations
    
    def track_cumulative_heat_exposure(
        self,
        user_id: int,
        wbgt_readings: List[Tuple[datetime, float]],
        season_start: datetime
    ) -> Dict[str, Any]:
        """
        Track cumulative heat exposure over agricultural season
        
        Args:
            user_id: User ID
            wbgt_readings: List of (timestamp, WBGT) tuples
            season_start: Start of agricultural season
        
        Returns:
            Cumulative exposure analysis
        """
        if not wbgt_readings:
            return {"exposure_hours": 0, "risk": "no_data"}
        
        # Calculate exposure hours above danger threshold
        danger_threshold = self.WBGT_THRESHOLDS[WBGTRiskLevel.DANGER]
        
        exposure_hours = 0
        high_risk_days = 0
        
        for timestamp, wbgt in wbgt_readings:
            if wbgt >= danger_threshold:
                exposure_hours += 1  # Assuming hourly readings
                
        # Count days with high exposure
        exposure_dates = set(ts.date() for ts, wbgt in wbgt_readings if wbgt >= danger_threshold)
        high_risk_days = len(exposure_dates)
        
        # Calculate season duration
        season_days = (datetime.utcnow() - season_start).days
        
        # Risk classification
        if exposure_hours > 200:  # >200 hours of danger-level exposure
            risk = "critical"
        elif exposure_hours > 100:
            risk = "high"
        elif exposure_hours > 50:
            risk = "moderate"
        else:
            risk = "low"
        
        logger.info(
            f"Cumulative heat exposure for user {user_id}: "
            f"{exposure_hours} hours over {season_days} days (risk: {risk})"
        )
        
        return {
            "user_id": user_id,
            "season_start": season_start.isoformat(),
            "season_days": season_days,
            "exposure_hours_above_danger": exposure_hours,
            "high_risk_days": high_risk_days,
            "risk_level": risk,
            "recommendations": self._get_cumulative_exposure_recommendations(risk, exposure_hours)
        }
    
    def _get_cumulative_exposure_recommendations(self, risk: str, hours: int) -> List[str]:
        """Get recommendations based on cumulative exposure"""
        if risk == "critical":
            return [
                "🚨 CRITICAL: Excessive heat exposure this season.",
                "🏥 Medical evaluation recommended for heat-related health issues.",
                "⏰ Reduce outdoor work hours significantly.",
                "💼 Consider alternative income sources during peak heat months.",
                "🧊 Implement aggressive cooling strategies."
            ]
        elif risk == "high":
            return [
                "⚠️ HIGH: Significant heat exposure accumulated.",
                "💧 Maintain strict hydration protocols.",
                "⏰ Limit outdoor work to early morning/evening.",
                "🏥 Monitor for chronic heat stress symptoms."
            ]
        elif risk == "moderate":
            return [
                "⚠️ MODERATE: Monitor heat exposure carefully.",
                "💧 Continue good hydration practices.",
                "⏰ Follow work-rest cycles consistently."
            ]
        else:
            return ["✓ Heat exposure within safe limits this season."]
    
    def add_wash_facility(self, facility: WASHFacility):
        """Add or update WASH facility"""
        self.wash_facilities[facility.facility_id] = facility
        logger.info(f"WASH facility added: {facility.name} ({facility.facility_type})")
    
    def search_wash_facilities(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        facility_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for WASH facilities near location
        
        Args:
            latitude: User latitude
            longitude: User longitude
            radius_km: Search radius in kilometers
            facility_type: Filter by facility type (optional)
        
        Returns:
            List of nearby facilities sorted by distance
        """
        nearby = []
        
        for facility in self.wash_facilities.values():
            # Calculate distance
            distance = self._calculate_distance(
                latitude, longitude,
                facility.latitude, facility.longitude
            )
            
            if distance <= radius_km:
                # Filter by type if specified
                if facility_type and facility.facility_type != facility_type:
                    continue
                
                nearby.append({
                    "facility": facility,
                    "distance_km": round(distance, 2)
                })
        
        # Sort by distance
        nearby.sort(key=lambda x: x["distance_km"])
        
        logger.info(
            f"Found {len(nearby)} WASH facilities within {radius_km}km "
            f"of ({latitude}, {longitude})"
        )
        
        return nearby
    
    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        
        Returns:
            Distance in kilometers
        """
        # Earth radius in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def update_facility_status(
        self,
        facility_id: str,
        status: str,
        reported_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update WASH facility status via community reporting
        
        Args:
            facility_id: Facility identifier
            status: New status
            reported_by: Reporter identifier (user ID or ASHA ID)
            notes: Optional notes
        
        Returns:
            True if updated successfully
        """
        facility = self.wash_facilities.get(facility_id)
        
        if not facility:
            logger.warning(f"Facility not found: {facility_id}")
            return False
        
        facility.status = status
        facility.last_updated = datetime.utcnow()
        facility.reported_by = reported_by
        if notes:
            facility.notes = notes
        
        logger.info(
            f"Facility status updated: {facility.name} -> {status} "
            f"(reported by: {reported_by})"
        )
        
        return True


# Global service instance
climate_service: Optional[ClimateHealthService] = None


def get_climate_service() -> ClimateHealthService:
    """
    Get or create global climate health service instance
    
    Returns:
        ClimateHealthService instance
    """
    global climate_service
    
    if climate_service is None:
        climate_service = ClimateHealthService()
        logger.info("Climate health service initialized")
    
    return climate_service
