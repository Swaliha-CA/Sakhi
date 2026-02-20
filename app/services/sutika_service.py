"""Sutika Paricharya (Ayurvedic Postpartum Recovery) Service

CRITICAL: Requires Ministry of AYUSH collaboration to standardize protocols
and cross-check herbal recommendations for contraindications with IFA supplements.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.core.logging import logger


class Region(str, Enum):
    """Indian regions for food recommendations"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    CENTRAL = "central"


class Season(str, Enum):
    """Seasons for availability filtering"""
    SUMMER = "summer"
    MONSOON = "monsoon"
    WINTER = "winter"
    SPRING = "spring"


class RecoveryPhase(str, Enum):
    """45-day recovery phases"""
    PHASE_1 = "phase_1"  # Days 1-15: Rest & Recovery
    PHASE_2 = "phase_2"  # Days 16-30: Gradual Activity
    PHASE_3 = "phase_3"  # Days 31-45: Strengthening


@dataclass
class HeritageRecipe:
    """Traditional recipe with nutritional profile"""
    recipe_id: str
    name: str
    region: Region
    ingredients: List[str]
    preparation: str
    nutritional_benefits: List[str]
    micronutrients: Dict[str, str]  # e.g., {"iron": "high", "calcium": "medium"}
    season: Optional[Season] = None
    voice_recording_url: Optional[str] = None
    contributed_by: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class DailyCheckIn:
    """Daily postpartum check-in"""
    user_id: int
    day_number: int  # 1-45
    recovery_phase: RecoveryPhase
    energy_level: int  # 1-10
    pain_level: int  # 1-10
    mood_score: int  # 1-10
    breastfeeding_issues: bool
    bleeding_status: str  # "normal", "heavy", "minimal"
    notes: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class SutikaParicharya:
    """
    Sutika Paricharya (Traditional Postpartum Care) Service
    
    Features:
    - 45-day recovery regimen tracking
    - Regional food recommendations (North vs South Indian)
    - Heritage recipe database with nutritional profiles
    - Voice-recorded recipe sharing
    - Daily check-ins in user's preferred language
    - Recovery milestone tracking
    - Deficiency-based food suggestions
    - Seasonal availability filtering
    
    CRITICAL: All herbal recommendations must be validated by Ministry of AYUSH
    for contraindications with allopathic IFA supplements.
    """
    
    # Recovery milestones by phase
    MILESTONES = {
        RecoveryPhase.PHASE_1: [
            "Complete bed rest with minimal activity",
            "Focus on wound healing and uterine involution",
            "Establish breastfeeding",
            "Consume warm, easily digestible foods",
            "Avoid cold foods and beverages"
        ],
        RecoveryPhase.PHASE_2: [
            "Gradual increase in light activities",
            "Continue nutritious diet",
            "Strengthen pelvic floor muscles",
            "Maintain good hydration",
            "Monitor for postpartum complications"
        ],
        RecoveryPhase.PHASE_3: [
            "Resume normal household activities gradually",
            "Focus on strengthening foods",
            "Prepare for return to work (if applicable)",
            "Continue breastfeeding support",
            "Plan for long-term health"
        ]
    }
    
    # Ayurvedic herbs (REQUIRES AYUSH VALIDATION)
    AYURVEDIC_HERBS = {
        "shatavari": {
            "benefits": ["Lactation support", "Hormonal balance", "Immunity"],
            "contraindications": ["Check with AYUSH - may interact with hormonal medications"],
            "dosage": "Consult Ayurvedic practitioner",
            "warning": "⚠️ AYUSH validation pending. Consult healthcare provider."
        },
        "ashwagandha": {
            "benefits": ["Stress reduction", "Energy", "Recovery"],
            "contraindications": ["Check with AYUSH - may interact with thyroid medications"],
            "dosage": "Consult Ayurvedic practitioner",
            "warning": "⚠️ AYUSH validation pending. Consult healthcare provider."
        },
        "bala": {
            "benefits": ["Strength", "Tissue repair", "Immunity"],
            "contraindications": ["Check with AYUSH"],
            "dosage": "Consult Ayurvedic practitioner",
            "warning": "⚠️ AYUSH validation pending. Consult healthcare provider."
        },
        "guduchi": {
            "benefits": ["Immunity", "Detoxification", "Fever management"],
            "contraindications": ["Check with AYUSH - may interact with immunosuppressants"],
            "dosage": "Consult Ayurvedic practitioner",
            "warning": "⚠️ AYUSH validation pending. Consult healthcare provider."
        }
    }
    
    def __init__(self):
        """Initialize Sutika Paricharya service"""
        self.recipes: Dict[str, HeritageRecipe] = {}
        self.check_ins: Dict[int, List[DailyCheckIn]] = {}
        self._initialize_default_recipes()
    
    def _initialize_default_recipes(self):
        """Initialize with traditional recipes from different regions"""
        
        # ===== NORTH INDIAN RECIPES =====
        self.add_recipe(HeritageRecipe(
            recipe_id="north_panjiri",
            name="Panjiri (North Indian)",
            region=Region.NORTH,
            ingredients=[
                "Whole wheat flour - 2 cups",
                "Ghee - 1 cup",
                "Jaggery - 1 cup",
                "Dry fruits (almonds, cashews) - 1/2 cup",
                "Gond (edible gum) - 1/4 cup",
                "Dried coconut - 1/4 cup",
                "Cardamom powder - 1 tsp"
            ],
            preparation="Roast wheat flour in ghee until golden. Add roasted gond, dry fruits, jaggery, and cardamom. Mix well. Store in airtight container. Consume 2-3 tablespoons daily.",
            nutritional_benefits=[
                "High energy for recovery",
                "Supports lactation",
                "Provides essential fats",
                "Rich in iron and calcium"
            ],
            micronutrients={
                "iron": "high",
                "calcium": "high",
                "protein": "medium",
                "healthy_fats": "high"
            },
            season=Season.WINTER,
            tags=["energy", "lactation", "traditional", "warming"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="north_gajar_halwa",
            name="Gajar Halwa (Carrot Pudding)",
            region=Region.NORTH,
            ingredients=[
                "Grated carrots - 4 cups",
                "Full-fat milk - 2 cups",
                "Ghee - 1/4 cup",
                "Jaggery - 3/4 cup",
                "Cashews and raisins - 1/4 cup",
                "Cardamom powder - 1/2 tsp"
            ],
            preparation="Cook grated carrots in milk until soft. Add ghee and jaggery. Cook until thick. Garnish with roasted nuts.",
            nutritional_benefits=[
                "Rich in Vitamin A",
                "Supports vision and immunity",
                "Provides calcium from milk",
                "Easy to digest"
            ],
            micronutrients={
                "vitamin_a": "very_high",
                "calcium": "high",
                "iron": "medium",
                "healthy_fats": "high"
            },
            season=Season.WINTER,
            tags=["vitamin_a", "immunity", "traditional", "sweet"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="north_bajra_khichdi",
            name="Bajra Khichdi (Pearl Millet Porridge)",
            region=Region.NORTH,
            ingredients=[
                "Bajra (pearl millet) - 1 cup",
                "Moong dal - 1/2 cup",
                "Ghee - 2 tbsp",
                "Cumin seeds - 1 tsp",
                "Turmeric - 1/2 tsp",
                "Salt to taste",
                "Water - 4 cups"
            ],
            preparation="Wash bajra and dal. Pressure cook with water, turmeric, and salt. Temper with ghee and cumin. Serve warm.",
            nutritional_benefits=[
                "High in iron and protein",
                "Warming and strengthening",
                "Easy to digest",
                "Supports energy levels"
            ],
            micronutrients={
                "iron": "very_high",
                "protein": "high",
                "fiber": "high",
                "b_vitamins": "high"
            },
            season=Season.WINTER,
            tags=["iron", "protein", "warming", "easy_digest"]
        ))
        
        # ===== SOUTH INDIAN RECIPES =====
        self.add_recipe(HeritageRecipe(
            recipe_id="south_ragi_kanji",
            name="Ragi Kanji (Finger Millet Porridge)",
            region=Region.SOUTH,
            ingredients=[
                "Ragi (finger millet) flour - 1/2 cup",
                "Water - 2 cups",
                "Jaggery - 2 tbsp",
                "Cardamom - 2 pods",
                "Ghee - 1 tsp"
            ],
            preparation="Mix ragi flour with water. Cook on low heat, stirring continuously. Add jaggery and cardamom. Cook until thick porridge consistency. Add ghee before serving.",
            nutritional_benefits=[
                "Rich in calcium and iron",
                "Easy to digest",
                "Supports bone health",
                "Provides sustained energy"
            ],
            micronutrients={
                "calcium": "very_high",
                "iron": "high",
                "fiber": "high",
                "protein": "medium"
            },
            season=None,  # Available year-round
            tags=["calcium", "iron", "easy_digest", "traditional"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="south_ellu_urundai",
            name="Ellu Urundai (Sesame Balls)",
            region=Region.SOUTH,
            ingredients=[
                "Sesame seeds (white) - 2 cups",
                "Jaggery - 1.5 cups",
                "Cardamom powder - 1 tsp",
                "Ghee - 1 tbsp (for greasing)"
            ],
            preparation="Dry roast sesame seeds until aromatic. Melt jaggery with little water to make syrup. Mix sesame and jaggery. Shape into balls while warm.",
            nutritional_benefits=[
                "Extremely high in calcium",
                "Supports bone and teeth health",
                "Rich in healthy fats",
                "Provides iron and protein"
            ],
            micronutrients={
                "calcium": "very_high",
                "iron": "high",
                "protein": "high",
                "healthy_fats": "very_high"
            },
            season=None,
            tags=["calcium", "lactation", "traditional", "energy"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="south_moong_dal_payasam",
            name="Moong Dal Payasam (Sweet Lentil Pudding)",
            region=Region.SOUTH,
            ingredients=[
                "Moong dal - 1/2 cup",
                "Jaggery - 3/4 cup",
                "Coconut milk - 1 cup",
                "Cardamom - 3 pods",
                "Ghee - 2 tbsp",
                "Cashews - 10"
            ],
            preparation="Roast moong dal in ghee until golden. Cook with water until soft. Add jaggery and coconut milk. Simmer. Garnish with roasted cashews.",
            nutritional_benefits=[
                "High protein from dal",
                "Easy to digest",
                "Provides energy",
                "Supports recovery"
            ],
            micronutrients={
                "protein": "high",
                "iron": "medium",
                "b_vitamins": "high",
                "healthy_fats": "medium"
            },
            season=None,
            tags=["protein", "easy_digest", "traditional", "sweet"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="south_drumstick_leaves_soup",
            name="Murungai Keerai Soup (Drumstick Leaves)",
            region=Region.SOUTH,
            ingredients=[
                "Drumstick leaves - 2 cups",
                "Moong dal - 1/4 cup",
                "Garlic - 3 cloves",
                "Cumin - 1 tsp",
                "Black pepper - 1/2 tsp",
                "Ghee - 1 tbsp",
                "Salt to taste"
            ],
            preparation="Cook dal until soft. Add drumstick leaves and cook for 5 minutes. Temper with ghee, cumin, garlic, and pepper. Serve warm.",
            nutritional_benefits=[
                "Extremely rich in iron and calcium",
                "Excellent for lactation",
                "Boosts immunity",
                "Provides vitamins A and C"
            ],
            micronutrients={
                "iron": "very_high",
                "calcium": "very_high",
                "vitamin_a": "high",
                "vitamin_c": "high",
                "protein": "medium"
            },
            season=Season.MONSOON,
            tags=["iron", "calcium", "lactation", "immunity"]
        ))
        
        # ===== UNIVERSAL/CENTRAL RECIPES =====
        self.add_recipe(HeritageRecipe(
            recipe_id="universal_methi_ladoo",
            name="Methi Ladoo (Fenugreek Balls)",
            region=Region.CENTRAL,
            ingredients=[
                "Fenugreek seeds - 1 cup",
                "Whole wheat flour - 2 cups",
                "Ghee - 1 cup",
                "Jaggery powder - 1.5 cups",
                "Dry ginger powder - 1 tsp",
                "Cardamom powder - 1 tsp"
            ],
            preparation="Dry roast fenugreek seeds and grind to powder. Roast wheat flour in ghee. Mix all ingredients. Shape into ladoos while warm.",
            nutritional_benefits=[
                "Excellent for lactation",
                "Controls blood sugar",
                "Anti-inflammatory",
                "Aids digestion"
            ],
            micronutrients={
                "iron": "high",
                "fiber": "high",
                "protein": "medium",
                "galactagogue": "very_high"
            },
            season=None,
            tags=["lactation", "blood_sugar", "digestion", "traditional"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="universal_dates_milk",
            name="Khajoor Doodh (Dates Milk)",
            region=Region.CENTRAL,
            ingredients=[
                "Dates (pitted) - 6-8",
                "Full-fat milk - 2 cups",
                "Almonds - 5",
                "Cardamom - 2 pods",
                "Saffron - few strands (optional)"
            ],
            preparation="Soak dates and almonds overnight. Blend with milk. Heat gently with cardamom and saffron. Serve warm.",
            nutritional_benefits=[
                "Rich in iron and calcium",
                "Natural energy booster",
                "Supports lactation",
                "Improves hemoglobin"
            ],
            micronutrients={
                "iron": "very_high",
                "calcium": "high",
                "potassium": "high",
                "natural_sugars": "high"
            },
            season=None,
            tags=["iron", "energy", "lactation", "anemia"]
        ))
        
        self.add_recipe(HeritageRecipe(
            recipe_id="universal_jeera_water",
            name="Jeera Pani (Cumin Water)",
            region=Region.CENTRAL,
            ingredients=[
                "Cumin seeds - 2 tsp",
                "Water - 2 cups",
                "Jaggery - 1 tsp (optional)"
            ],
            preparation="Boil cumin seeds in water for 5 minutes. Strain. Add jaggery if desired. Drink warm throughout the day.",
            nutritional_benefits=[
                "Aids digestion",
                "Reduces gas and bloating",
                "Supports lactation",
                "Helps with uterine involution"
            ],
            micronutrients={
                "iron": "medium",
                "antioxidants": "high",
                "digestive_enzymes": "high"
            },
            season=None,
            tags=["digestion", "lactation", "simple", "daily"]
        ))
    
    def add_recipe(self, recipe: HeritageRecipe):
        """Add heritage recipe to database"""
        self.recipes[recipe.recipe_id] = recipe
        logger.info(f"Recipe added: {recipe.name} ({recipe.region.value})")
    
    def add_voice_recorded_recipe(
        self,
        name: str,
        region: Region,
        ingredients: List[str],
        preparation: str,
        voice_recording_url: str,
        contributed_by: str,
        nutritional_benefits: Optional[List[str]] = None,
        micronutrients: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add a voice-recorded heritage recipe from community member
        
        Args:
            name: Recipe name
            region: Region of origin
            ingredients: List of ingredients
            preparation: Preparation instructions
            voice_recording_url: URL to voice recording
            contributed_by: User ID or name of contributor
            nutritional_benefits: Optional nutritional benefits
            micronutrients: Optional micronutrient profile
            tags: Optional tags
        
        Returns:
            Recipe ID
        """
        import uuid
        recipe_id = f"community_{uuid.uuid4().hex[:8]}"
        
        recipe = HeritageRecipe(
            recipe_id=recipe_id,
            name=name,
            region=region,
            ingredients=ingredients,
            preparation=preparation,
            nutritional_benefits=nutritional_benefits or ["Traditional recipe from community"],
            micronutrients=micronutrients or {},
            voice_recording_url=voice_recording_url,
            contributed_by=contributed_by,
            tags=tags or ["community", "voice_recorded"]
        )
        
        self.add_recipe(recipe)
        logger.info(f"Voice-recorded recipe added: {name} by {contributed_by}")
        
        return recipe_id
    
    def get_regional_recommendations(
        self,
        region: Region,
        deficiencies: Optional[List[str]] = None,
        season: Optional[Season] = None
    ) -> List[HeritageRecipe]:
        """
        Get region-appropriate food recommendations
        
        Args:
            region: User's region
            deficiencies: List of nutrient deficiencies (e.g., ["iron", "calcium"])
            season: Current season for availability filtering
        
        Returns:
            List of recommended recipes
        """
        recommendations = []
        
        for recipe in self.recipes.values():
            # Match region (or universal recipes)
            if recipe.region != region and recipe.region != Region.CENTRAL:
                continue
            
            # Filter by season if specified
            if season and recipe.season and recipe.season != season:
                continue
            
            # Prioritize recipes addressing deficiencies
            if deficiencies:
                addresses_deficiency = any(
                    deficiency in recipe.micronutrients and 
                    recipe.micronutrients[deficiency] in ["high", "very_high"]
                    for deficiency in deficiencies
                )
                if addresses_deficiency:
                    recommendations.insert(0, recipe)  # Priority
                else:
                    recommendations.append(recipe)
            else:
                recommendations.append(recipe)
        
        logger.info(
            f"Generated {len(recommendations)} recommendations for {region.value} "
            f"(deficiencies: {deficiencies}, season: {season})"
        )
        
        return recommendations
    
    def record_daily_checkin(self, checkin: DailyCheckIn):
        """Record daily postpartum check-in"""
        if checkin.user_id not in self.check_ins:
            self.check_ins[checkin.user_id] = []
        
        self.check_ins[checkin.user_id].append(checkin)
        
        logger.info(
            f"Daily check-in recorded: User {checkin.user_id}, Day {checkin.day_number}, "
            f"Phase {checkin.recovery_phase.value}"
        )
    
    def get_recovery_phase(self, day_number: int) -> RecoveryPhase:
        """Determine recovery phase based on day number"""
        if day_number <= 15:
            return RecoveryPhase.PHASE_1
        elif day_number <= 30:
            return RecoveryPhase.PHASE_2
        else:
            return RecoveryPhase.PHASE_3
    
    def get_daily_guidance(
        self,
        day_number: int,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get daily guidance for postpartum recovery
        
        Args:
            day_number: Day in recovery (1-45)
            language: Preferred language
        
        Returns:
            Daily guidance with activities, diet, and milestones
        """
        phase = self.get_recovery_phase(day_number)
        milestones = self.MILESTONES[phase]
        
        # Phase-specific guidance
        if phase == RecoveryPhase.PHASE_1:
            activities = [
                "Complete rest - stay in bed most of the day",
                "Gentle walking to bathroom only",
                "Focus on bonding with baby",
                "Accept help from family for all tasks"
            ]
            diet_focus = "Warm, liquid, easily digestible foods"
            
        elif phase == RecoveryPhase.PHASE_2:
            activities = [
                "Short walks around the house (5-10 minutes)",
                "Light stretching exercises",
                "Gradually increase sitting time",
                "Begin light household supervision"
            ]
            diet_focus = "Nutritious, strengthening foods with variety"
            
        else:  # PHASE_3
            activities = [
                "Longer walks (15-20 minutes)",
                "Pelvic floor exercises",
                "Light household tasks",
                "Prepare for return to routine"
            ]
            diet_focus = "Balanced diet with focus on iron and calcium"
        
        return {
            "day_number": day_number,
            "phase": phase.value,
            "phase_description": f"Phase {day_number//15 + 1} of 3",
            "milestones": milestones,
            "activities": activities,
            "diet_focus": diet_focus,
            "ayurvedic_note": "⚠️ Consult Ayurvedic practitioner for herbal recommendations. AYUSH validation pending.",
            "warning": "🏥 Contact healthcare provider immediately if: heavy bleeding, fever, severe pain, or signs of infection."
        }
    
    def analyze_recovery_progress(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Analyze recovery progress based on check-ins
        
        Args:
            user_id: User ID
        
        Returns:
            Recovery progress analysis
        """
        checkins = self.check_ins.get(user_id, [])
        
        if not checkins:
            return {
                "status": "no_data",
                "message": "No check-ins recorded yet"
            }
        
        # Sort by day number
        checkins.sort(key=lambda x: x.day_number)
        
        latest = checkins[-1]
        
        # Calculate averages
        avg_energy = sum(c.energy_level for c in checkins) / len(checkins)
        avg_pain = sum(c.pain_level for c in checkins) / len(checkins)
        avg_mood = sum(c.mood_score for c in checkins) / len(checkins)
        
        # Trend analysis (last 7 days vs previous 7 days)
        if len(checkins) >= 14:
            recent = checkins[-7:]
            previous = checkins[-14:-7]
            
            energy_trend = (sum(c.energy_level for c in recent) / 7) - (sum(c.energy_level for c in previous) / 7)
            pain_trend = (sum(c.pain_level for c in recent) / 7) - (sum(c.pain_level for c in previous) / 7)
            mood_trend = (sum(c.mood_score for c in recent) / 7) - (sum(c.mood_score for c in previous) / 7)
        else:
            energy_trend = pain_trend = mood_trend = 0
        
        # Identify concerns
        concerns = []
        if avg_pain > 7:
            concerns.append("High pain levels - consult healthcare provider")
        if avg_mood < 4:
            concerns.append("Low mood scores - PPD screening recommended")
        if avg_energy < 3:
            concerns.append("Very low energy - check for anemia")
        if latest.bleeding_status == "heavy" and latest.day_number > 10:
            concerns.append("Heavy bleeding after day 10 - immediate medical attention needed")
        
        # Recovery status
        if concerns:
            status = "needs_attention"
        elif avg_energy > 6 and avg_pain < 4 and avg_mood > 6:
            status = "good_progress"
        else:
            status = "normal_progress"
        
        logger.info(
            f"Recovery analysis for user {user_id}: {status} "
            f"(energy: {avg_energy:.1f}, pain: {avg_pain:.1f}, mood: {avg_mood:.1f})"
        )
        
        return {
            "user_id": user_id,
            "current_day": latest.day_number,
            "current_phase": latest.recovery_phase.value,
            "total_checkins": len(checkins),
            "averages": {
                "energy": round(avg_energy, 1),
                "pain": round(avg_pain, 1),
                "mood": round(avg_mood, 1)
            },
            "trends": {
                "energy": "improving" if energy_trend > 0.5 else "declining" if energy_trend < -0.5 else "stable",
                "pain": "improving" if pain_trend < -0.5 else "worsening" if pain_trend > 0.5 else "stable",
                "mood": "improving" if mood_trend > 0.5 else "declining" if mood_trend < -0.5 else "stable"
            },
            "status": status,
            "concerns": concerns,
            "recommendations": self._get_recovery_recommendations(status, concerns, latest)
        }
    
    def _get_recovery_recommendations(
        self,
        status: str,
        concerns: List[str],
        latest_checkin: DailyCheckIn
    ) -> List[str]:
        """Generate recovery recommendations"""
        recommendations = []
        
        if status == "needs_attention":
            recommendations.append("🏥 Schedule check-up with healthcare provider")
            recommendations.append("📞 Contact ASHA worker for home visit")
        
        if "pain" in str(concerns).lower():
            recommendations.append("💊 Review pain management with doctor")
            recommendations.append("🧘 Try gentle relaxation techniques")
        
        if "mood" in str(concerns).lower():
            recommendations.append("🧠 Complete PPD screening (EPDS/PHQ-9)")
            recommendations.append("👥 Increase social support and family involvement")
        
        if "energy" in str(concerns).lower():
            recommendations.append("🔬 Check hemoglobin and iron levels")
            recommendations.append("🍽️ Increase iron-rich foods and IFA supplementation")
        
        if "bleeding" in str(concerns).lower():
            recommendations.append("🚨 URGENT: Seek immediate medical attention")
        
        if latest_checkin.breastfeeding_issues:
            recommendations.append("🤱 Consult lactation counselor")
            recommendations.append("🍵 Try galactagogue foods (methi, jeera, saunf)")
        
        if not recommendations:
            recommendations.append("✓ Continue current recovery regimen")
            recommendations.append("📅 Maintain daily check-ins")
        
        return recommendations
    
    def get_ayurvedic_herb_info(self, herb_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about Ayurvedic herb
        
        CRITICAL: All information pending AYUSH validation
        
        Args:
            herb_name: Name of herb
        
        Returns:
            Herb information with warnings
        """
        herb = self.AYURVEDIC_HERBS.get(herb_name.lower())
        
        if not herb:
            return None
        
        return {
            "herb": herb_name,
            "benefits": herb["benefits"],
            "contraindications": herb["contraindications"],
            "dosage": herb["dosage"],
            "warning": herb["warning"],
            "ayush_status": "⚠️ PENDING VALIDATION - Ministry of AYUSH standardization required",
            "safety_note": "Always consult both Ayurvedic practitioner AND allopathic doctor before use, especially if taking IFA supplements or other medications."
        }


# Global service instance
sutika_service: Optional[SutikaParicharya] = None


def get_sutika_service() -> SutikaParicharya:
    """
    Get or create global Sutika Paricharya service instance
    
    Returns:
        SutikaParicharya instance
    """
    global sutika_service
    
    if sutika_service is None:
        sutika_service = SutikaParicharya()
        logger.info("Sutika Paricharya service initialized")
    
    return sutika_service
